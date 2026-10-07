"""Resolve the Polymarket paper's fills with Polymarket's OFFICIAL result, from events.jsonl alone.

    uv run python scripts/poly_backfill_official.py            # appends the missing 'resolve' events
    uv run python scripts/poly_backfill_official.py --dry-run  # only prints what it would add

The live paper only asks Gamma for the official result while the market is still in its memory, so every restart of the
OS lost the pending bets and they were never resolved (PnL oficial stuck at 0). This reads every 'fill' without a
'resolve', asks Gamma (closed=true) and appends the same 'resolve' event the bot writes. Safe to run any time and as
many times as you like: fills already resolved are skipped. Stop the paper first or run it while it is stopped (two
writers on the same file would interleave lines).
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.paper.poly_updown_paper import official_up_won, settle_pnl  # noqa: E402

GAMMA = "https://gamma-api.polymarket.com/markets"


def fetch(slug: str):
    u = GAMMA + "?" + urllib.parse.urlencode({"slug": slug, "closed": "true"})
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "quant-os"}), timeout=20) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1 + i)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=ROOT / "data" / "paper" / "poly_updown" / "events.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        from src.common.dns_patch import apply_dns_fallback
        apply_dns_fallback()                       # some ISPs cannot resolve polymarket.com
    except Exception:
        pass
    ev = [json.loads(x) for x in a.file.read_text(encoding="utf-8").splitlines() if x.strip()]
    resolved = {e["slug"] for e in ev if e["kind"] == "resolve"}
    settles = {e["slug"]: e for e in ev if e["kind"] == "settle"}
    todo = [e for e in ev if e["kind"] == "fill" and e["slug"] not in resolved]
    print(f"{len(todo)} apuestas sin resultado oficial", flush=True)
    new, pending, total = [], 0, 0.0
    for f in todo:
        items = fetch(f["slug"])
        won = official_up_won(items[0]) if items else None
        if won is None:
            pending += 1
            continue
        pnl = settle_pnl(f, won)
        b = settles.get(f["slug"])
        row = {"ts": time.time(), "kind": "resolve", "slug": f["slug"], "up_won_official": won, "pnl_official": pnl,
               "agrees_with_binance": (b["pnl"] > 0) == (pnl > 0) if b else None, "backfilled": True}
        new.append(row)
        total += pnl
    agree = [r["agrees_with_binance"] for r in new if r["agrees_with_binance"] is not None]
    print(f"Resueltas ahora: {len(new)} (PnL oficial US$ {total:+,.2f}). Todavía sin cerrar en Polymarket: {pending}.")
    if agree:
        print(f"Binance y la resolución oficial coinciden en {sum(agree) / len(agree) * 100:.0f}% de las apuestas.")
    if new and not a.dry_run:
        with a.file.open("a", encoding="utf-8") as fh:
            for r in new:
                fh.write(json.dumps(r) + "\n")
        print(f"Agregado a {a.file}. Recargá el panel.")


if __name__ == "__main__":
    main()
