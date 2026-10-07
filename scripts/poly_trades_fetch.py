"""Download Polymarket up/down taker trades + results + Binance 1 s prices once, for offline studies.

    uv run python scripts/poly_trades_fetch.py --hours 24 --out data/research/poly_trades

Writes <out>/trades.jsonl.gz (one row per taker trade: slug, coin, min, start, t, outcome_up, side, price, size,
wallet, up_won, fee_rate, fee_exp) and <out>/binance_<coin>.json.gz ({second: close}). Markets are fetched with
closed=true (Gamma hides closed markets otherwise). data-api returns newest trades first; up to --max-trades per
market are kept (all of them for almost every market).
"""
import argparse
import gzip
import json
import time
from pathlib import Path

from poly_trades_edge import COINS, DUR, GAMMA, TRADES, binance_seconds, get


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=24)
    ap.add_argument("--max-trades", type=int, default=10000)
    ap.add_argument("--out", type=Path, default=Path("data/research/poly_trades"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    now = int(time.time())
    t_lo = now - int(a.hours * 3600)
    for c, sym in COINS.items():
        px = binance_seconds(sym, t_lo - 1900, now)
        with gzip.open(a.out / f"binance_{c}.json.gz", "wt") as f:
            json.dump(px, f)
        print(f"Binance {c}: {len(px)} s", flush=True)
    markets = [(c, m, s) for c in COINS for m, d in DUR.items()
               for s in range((t_lo // d + 1) * d, now - 120 - d + 1, d)]
    n = 0
    with gzip.open(a.out / "trades.jsonl.gz", "wt") as f:
        for i, (coin, mins, s) in enumerate(markets):
            slug = f"{coin}-updown-{mins}m-{s}"
            try:
                m = get(GAMMA, {"slug": slug, "closed": "true"})
            except Exception:
                continue
            if not m:
                continue
            m = m[0]
            try:
                prices = [float(x) for x in json.loads(m["outcomePrices"])]
                outs = [str(o).lower() for o in json.loads(m["outcomes"])]
            except Exception:
                continue
            if max(prices) < 0.99:
                continue
            up_won = prices[outs.index("up")] >= 0.99
            fs = m.get("feeSchedule") or {}
            off = 0
            while off < a.max_trades:
                try:
                    page = get(TRADES, {"market": m["conditionId"], "limit": 500, "offset": off})
                except Exception:
                    break
                for tr in page or []:
                    f.write(json.dumps({"slug": slug, "coin": coin, "min": mins, "start": s, "t": int(tr["timestamp"]),
                                        "outcome_up": str(tr["outcome"]).lower() == "up", "side": tr["side"],
                                        "price": float(tr["price"]), "size": float(tr["size"]),
                                        "wallet": tr.get("proxyWallet"), "up_won": up_won,
                                        "fee_rate": float(fs.get("rate", 0.07)),
                                        "fee_exp": float(fs.get("exponent", 1))}) + "\n")
                    n += 1
                if not page or len(page) < 500:
                    break
                off += 500
            if i % 50 == 0:
                print(f"  {i}/{len(markets)} mercados, {n} trades", flush=True)
    print(f"Listo: {n} trades en {a.out}")


if __name__ == "__main__":
    main()
