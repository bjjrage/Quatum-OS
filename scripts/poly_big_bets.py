"""Follow the big money in Polymarket's long-dated markets (politics, sports, events): do large bets know something?

    uv run python scripts/poly_big_bets.py --markets 600 --min-usd 1000

Resolved markets (Gamma closed=true, highest volume first, short crypto up/down excluded). For each one, the trades of at
least --min-usd (data-api filterType=CASH) with wallet, side, price, time. Each trade = "bought outcome O at q"
(selling O at p == buying the other side at 1-p). Edge of a bet = win - q (a fair bet averages 0; taker fees on these
markets are small or zero and are ignored).
Groups: price bucket (longshots < 0.2 are where insiders would show), size, time before the end, and "new wallets"
(wallets that appear in only 1 market of the sample: fresh accounts betting big are the classic insider pattern).
Follow test: for every bet, the price of the next big trade of the same outcome >= 1 h later (what a follower pays).
t-stats are per market (bets in the same market are not independent).
"""
import argparse
import json
import math
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from poly_trades_edge import get

GAMMA = "https://gamma-api.polymarket.com/markets"
TRADES = "https://data-api.polymarket.com/trades"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def ts(iso):
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def tstat_cluster(items):
    """items: list of (cluster, value) -> t of the per-cluster means."""
    g = defaultdict(list)
    for c, v in items:
        g[c].append(v)
    x = [sum(v) / len(v) for v in g.values()]
    n = len(x)
    if n < 3:
        return float("nan"), n
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return (m / (sd / math.sqrt(n)) if sd > 0 else float("nan")), n


def market_trades(m, min_usd):
    out, off = [], 0
    while off < 3000:
        try:
            page = get(TRADES, {"market": m["conditionId"], "limit": 500, "offset": off,
                                "filterType": "CASH", "filterAmount": min_usd})
        except Exception:
            break
        out += page or []
        if not page or len(page) < 500:
            break
        off += 500
    return m, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", type=int, default=600)
    ap.add_argument("--min-usd", type=float, default=1000)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/poly_big_bets.md"))
    a = ap.parse_args()
    mk, off = [], 0
    while len(mk) < a.markets and off < 20000:
        page = get(GAMMA, {"closed": "true", "order": "volumeNum", "ascending": "false", "limit": 100, "offset": off})
        if not page:
            break
        for m in page:
            slug = m.get("slug") or ""
            if "updown" in slug or "up-or-down" in slug:
                continue
            try:
                pr = [float(x) for x in json.loads(m["outcomePrices"])]
                outs = json.loads(m["outcomes"])
            except Exception:
                continue
            if len(pr) != 2 or max(pr) < 0.99:
                continue
            m["_win"] = outs[pr.index(max(pr))]
            m["_end"] = ts(m.get("closedTime") or m.get("endDate"))
            mk.append(m)
        off += 100
    print(f"{len(mk)} mercados resueltos", flush=True)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda m: market_trades(m, a.min_usd), mk[:a.markets]))
    bets = []
    for m, trs in res:
        outs = json.loads(m["outcomes"])
        for tr in trs:
            o, q = tr.get("outcome"), float(tr["price"])
            if tr["side"] == "SELL":
                o, q = [x for x in outs if x != o][0], 1 - q
            if not 0.01 <= q <= 0.99:
                continue
            bets.append({"m": m["conditionId"], "o": o, "q": q, "usd": float(tr["size"]) * float(tr["price"]),
                         "w": tr.get("proxyWallet"), "t": int(tr["timestamp"]), "end": m["_end"],
                         "win": 1.0 if o == m["_win"] else 0.0, "title": m.get("question", "")[:70]})
    nm = defaultdict(set)
    for b in bets:
        nm[b["w"]].add(b["m"])
    by_mo = defaultdict(list)
    for b in bets:
        by_mo[(b["m"], b["o"])].append(b)
    for v in by_mo.values():
        v.sort(key=lambda b: b["t"])
    for b in bets:
        nxt = next((x for x in by_mo[(b["m"], b["o"])] if x["t"] >= b["t"] + 3600), None)
        b["follow_q"] = nxt["q"] if nxt else None

    def line(name, sel):
        if len(sel) < 30:
            return f"| {name} | {len(sel)} | | | | | |"
        e = [(b["m"], b["win"] - b["q"]) for b in sel]
        t, n = tstat_cluster(e)
        usd = sum(b["usd"] for b in sel)
        roi = sum((b["win"] - b["q"]) / b["q"] * b["usd"] for b in sel) / usd
        f = [(b["m"], b["win"] - b["follow_q"]) for b in sel if b["follow_q"] is not None]
        tf, _ = tstat_cluster(f)
        return (f"| {name} | {len(sel):,} ({n} merc.) | {sum(b['q'] for b in sel) / len(sel):.2f} | "
                f"{sum(v for _, v in e) / len(e) * 100:+.1f} pts (t {t:.1f}) | {roi * 100:+.1f}% | "
                f"{(sum(v for _, v in f) / len(f) * 100) if f else float('nan'):+.1f} pts (t {tf:.1f}, n {len(f)}) | "
                f"{sum(b['win'] for b in sel) / len(sel) * 100:.0f}% |")

    head = ("| grupo | apuestas | precio medio | ventaja (gana − precio) | retorno sobre lo apostado | "
            "siguiéndolos 1 h después | aciertos |")
    sep = "|---|---|---|---|---|---|---|"
    out = ["# Seguir el dinero grande en los mercados largos de Polymarket", "",
           f"{len(res)} mercados resueltos de más volumen (sin cripto de corto plazo), apuestas de ≥ US$ {a.min_usd:,.0f}: "
           f"{len(bets):,}. Billeteras distintas: {len(nm):,}.", "", head, sep, line("todas", bets)]
    for lo, hi in ((0, .1), (.1, .2), (.2, .4), (.4, .6), (.6, .8), (.8, .9), (.9, 1)):
        out.append(line(f"precio {lo:.1f}–{hi:.1f}", [b for b in bets if lo <= b["q"] < hi]))
    out += ["", "## Tamaño, antigüedad de la billetera y cuándo apuestan", "", head, sep]
    for lo, hi in ((1e3, 5e3), (5e3, 2e4), (2e4, 1e5), (1e5, 1e12)):
        out.append(line(f"US$ {lo:,.0f}–{hi:,.0f}", [b for b in bets if lo <= b["usd"] < hi]))
    fresh = [b for b in bets if len(nm[b["w"]]) == 1]
    out.append(line("billetera en 1 solo mercado", fresh))
    out.append(line("billetera en 1 solo mercado, precio < 0.3", [b for b in fresh if b["q"] < 0.3]))
    out.append(line("billetera en 1 solo mercado, ≥ US$ 10k, precio < 0.5", [b for b in fresh if b["usd"] >= 1e4 and b["q"] < .5]))
    out.append(line("billetera en ≥ 10 mercados", [b for b in bets if len(nm[b["w"]]) >= 10]))
    for lo, hi, name in ((0, 86400, "< 1 día antes del final"), (86400, 7 * 86400, "1–7 días antes"),
                         (7 * 86400, 1e12, "> 7 días antes")):
        out.append(line(name, [b for b in bets if b["end"] and lo <= b["end"] - b["t"] < hi]))
    out += ["", "Ventaja en puntos = gana (1/0) − precio pagado: 0 es apuesta justa. "
            "'Siguiéndolos' = misma apuesta al precio del siguiente trade grande ≥ 1 h después. t por mercado."]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
