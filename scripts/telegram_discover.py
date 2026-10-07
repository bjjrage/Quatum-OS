"""Find memecoin call channels on Telegram with YOUR session, rank them by how many contract addresses they post,
and optionally join the best ones and write config/telegram_channels.txt.

    uv run python scripts/telegram_discover.py              # only searches and ranks (joins nothing)
    uv run python scripts/telegram_discover.py --join 25    # joins the top 25 and writes the channel list

Read-only except for --join (joining is reversible: leave the channel in the app). It never posts, never clicks
links, never talks to bots. Public channels' last messages are read without joining. Results also go to
config/telegram_candidates.csv. Needs the session from scripts/telegram_login.py.
"""
import argparse
import asyncio
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.collectors.telegram_watcher import CHANNELS_FILE, SESSION, extract_addresses, read_secret  # noqa: E402

KEYWORDS = ["solana calls", "sol calls", "pump fun calls", "pumpfun", "memecoin calls", "meme calls", "degen calls",
            "gem calls", "sol gems", "100x calls", "crypto calls", "bsc calls", "base calls", "alpha calls", "kol calls"]


def score(messages, now_s: float) -> dict:
    """messages: [(unix_s, text)]. Contract-address posts per day over the sampled window, chains, freshness."""
    if not messages:
        return {"msgs": 0, "ca_posts": 0, "ca_per_day": 0.0, "solana_share": 0.0, "last_post_h": float("inf")}
    ts = [t for t, _ in messages]
    span_d = max((max(ts) - min(ts)) / 86400, 1 / 24)
    ca = [extract_addresses(x or "") for _, x in messages]
    ca_msgs = [c for c in ca if c]
    sol = sum(1 for c in ca_msgs if any(ch == "solana" for ch, _ in c))
    return {"msgs": len(messages), "ca_posts": len(ca_msgs), "ca_per_day": len(ca_msgs) / span_d,
            "solana_share": sol / len(ca_msgs) if ca_msgs else 0.0, "last_post_h": (now_s - max(ts)) / 3600}


def keep(s: dict, min_ca_day: float, max_idle_h: float) -> bool:
    return s["ca_per_day"] >= min_ca_day and s["last_post_h"] <= max_idle_h


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="*", default=KEYWORDS)
    ap.add_argument("--per-keyword", type=int, default=40)
    ap.add_argument("--sample", type=int, default=100, help="recent messages read per channel")
    ap.add_argument("--min-ca-day", type=float, default=3.0)
    ap.add_argument("--max-idle-h", type=float, default=24.0)
    ap.add_argument("--join", type=int, default=0, help="join the top N and write config/telegram_channels.txt")
    args = ap.parse_args()

    from telethon import TelegramClient
    from telethon.errors import FloodWaitError
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.tl.functions.contacts import SearchRequest
    api_id, api_hash = read_secret("TELEGRAM_API_ID"), read_secret("TELEGRAM_API_HASH")
    if not api_id or not api_hash or not SESSION.exists():
        raise SystemExit("Primero: TELEGRAM_API_ID/HASH en .env y `uv run python scripts/telegram_login.py`.")
    client = TelegramClient(str(SESSION.with_suffix("")), int(api_id), api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Sesión no autorizada: correr scripts/telegram_login.py.")

    found = {}
    for kw in args.keywords:
        try:
            res = await client(SearchRequest(q=kw, limit=args.per_keyword))
        except FloodWaitError as e:
            print(f"Telegram pide esperar {e.seconds}s; sigo con lo encontrado.")
            break
        for ch in res.chats:
            if getattr(ch, "username", None) and (getattr(ch, "broadcast", False) or getattr(ch, "megagroup", False)):
                found.setdefault(ch.username.lower(), ch)
        print(f"  '{kw}': {len(found)} canales únicos hasta ahora", flush=True)
        await asyncio.sleep(1.5)

    rows, now = [], time.time()
    for i, (uname, ch) in enumerate(found.items(), 1):
        try:
            msgs = await client.get_messages(ch, limit=args.sample)
        except FloodWaitError as e:
            print(f"Telegram pide esperar {e.seconds}s; corto la lectura acá.")
            break
        except Exception as e:
            print(f"  @{uname}: no se pudo leer ({type(e).__name__})")
            continue
        s = score([(m.date.timestamp(), m.message or "") for m in msgs if m and m.date], now)
        rows.append({"username": uname, "title": (ch.title or "")[:60], "subscribers": getattr(ch, "participants_count", None) or "",
                     "type": "canal" if getattr(ch, "broadcast", False) else "grupo", **s})
        if i % 10 == 0:
            print(f"  leídos {i}/{len(found)}", flush=True)
        await asyncio.sleep(1.0)

    rows.sort(key=lambda r: r["ca_per_day"], reverse=True)
    out = ROOT / "config" / "telegram_candidates.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["username"])
        w.writeheader()
        w.writerows(rows)
    good = [r for r in rows if keep(r, args.min_ca_day, args.max_idle_h)]
    print(f"\n{len(rows)} canales leídos, {len(good)} publican ≥{args.min_ca_day:g} contratos/día y postearon en las "
          f"últimas {args.max_idle_h:g} h:\n")
    print(f"{'canal':<32}{'tipo':<7}{'subs':>9}{'CA/día':>8}{'%solana':>9}{'último(h)':>10}")
    for r in good[:60]:
        print(f"@{r['username']:<31}{r['type']:<7}{str(r['subscribers']):>9}{r['ca_per_day']:>8.1f}"
              f"{r['solana_share'] * 100:>8.0f}%{r['last_post_h']:>10.1f}")
    print(f"\nTodo en {out}")

    if args.join and good:
        chosen = good[:args.join]
        existing = set()
        if CHANNELS_FILE.exists():
            existing = {line.strip().lstrip("@").lower() for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines()}
        joined = []
        for r in chosen:
            try:
                await client(JoinChannelRequest(found[r["username"]]))
                joined.append(r["username"])
                print(f"  unido a @{r['username']}")
            except FloodWaitError as e:
                print(f"Telegram pide esperar {e.seconds}s antes de unirse a más; guardo los que van.")
                break
            except Exception as e:
                print(f"  no se pudo unir a @{r['username']} ({type(e).__name__})")
            await asyncio.sleep(5)
        new = [u for u in joined if u not in existing]
        with CHANNELS_FILE.open("a", encoding="utf-8") as fh:
            for u in new:
                fh.write(f"@{u}\n")
        print(f"\nUnido a {len(joined)}; {len(new)} agregados a {CHANNELS_FILE}. Reiniciá el recorder para escucharlos.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
