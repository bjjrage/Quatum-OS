"""Live scan: same 15-minute "BTC/ETH/SOL up?" window on Polymarket and Kalshi. Is there a pair that costs < $1?

    uv run python scripts/arb_scan_poly_kalshi.py --minutes 60 --out data/research/arb_scan.jsonl

Every --every seconds, for the current 15 min window of each coin:
  Polymarket  {coin}-updown-15m-{start}: best ask (and size) of Up and Down from clob.polymarket.com/book
  Kalshi      KX{COIN}15M market with open_time == start: Kalshi books only list bids, so
              ask(Yes) = 1 - best No bid, ask(No) = 1 - best Yes bid
  pair A = Poly Up + Kalshi No,  pair B = Poly Down + Kalshi Yes  (one of the two pays $1 if both venues agree)
  cost = asks + Polymarket taker fee (q*rate*(q(1-q))^exp) + Kalshi taker fee (0.07*P*(1-P), ignoring cent rounding)
  edge = 1 - cost, size = min of the two best-level sizes (shares/contracts).
Basis risk: Polymarket settles on Chainlink (end vs start), Kalshi on the 60 s average of CF BRTI; if the price ends
very close to the start both legs can lose (or both win). The study reports how often that would have mattered.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from poly_trades_edge import GAMMA, get

CLOB_BOOK = "https://clob.polymarket.com/book"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
COINS = {"btc": "KXBTC15M", "eth": "KXETH15M", "sol": "KXSOL15M"}


def poly_fee(q, rate=0.07, exp=1.0):
    return q * rate * (q * (1 - q)) ** exp


def kalshi_fee(p):
    return 0.07 * p * (1 - p)


def best_ask(book):
    asks = [(float(x["price"]), float(x["size"])) for x in (book or {}).get("asks") or [] if float(x["size"]) > 0]
    return min(asks) if asks else (None, 0.0)


def kalshi_best(ob, side):
    """Best bid (price, size) on 'yes' or 'no' from the fixed-point orderbook."""
    lv = ((ob or {}).get("orderbook_fp") or {}).get(f"{side}_dollars") or []
    lv = [(float(p), float(s)) for p, s in lv if float(s) > 0]
    return max(lv) if lv else (None, 0.0)


def pair(q_poly, sz_poly, k_ask, sz_k, rate, exp):
    if q_poly is None or k_ask is None or not (0 < q_poly < 1 and 0 < k_ask < 1):
        return None
    cost = q_poly + k_ask + poly_fee(q_poly, rate, exp) + kalshi_fee(k_ask)
    return {"poly": q_poly, "kalshi": k_ask, "cost": cost, "edge": 1 - cost, "size": min(sz_poly, sz_k)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=60)
    ap.add_argument("--every", type=float, default=2.0)
    ap.add_argument("--out", type=Path, default=Path("data/research/arb_scan.jsonl"))
    a = ap.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    cache = {}
    end = time.time() + a.minutes * 60
    with a.out.open("a", encoding="utf-8") as f:
        while time.time() < end:
            t0 = time.time()
            start = int(t0 // 900 * 900)
            for coin, series in COINS.items():
                try:
                    key = (coin, start)
                    if key not in cache:
                        pm = get(GAMMA, {"slug": f"{coin}-updown-15m-{start}"})[0]
                        toks = json.loads(pm["clobTokenIds"])
                        outs = [str(o).lower() for o in json.loads(pm["outcomes"])]
                        fs = pm.get("feeSchedule") or {}
                        km = get(f"{KALSHI}/markets", {"series_ticker": series, "status": "open", "limit": 10})["markets"]
                        iso = datetime.fromtimestamp(start, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        kt = next(m["ticker"] for m in km if m.get("open_time") == iso)
                        cache[key] = (toks[outs.index("up")], toks[outs.index("down")], kt,
                                      float(fs.get("rate", 0.07)), float(fs.get("exponent", 1)))
                    up_tok, dn_tok, kt, rate, exp = cache[key]
                    qu, su = best_ask(get(CLOB_BOOK, {"token_id": up_tok}))
                    qd, sd = best_ask(get(CLOB_BOOK, {"token_id": dn_tok}))
                    ob = get(f"{KALSHI}/markets/{kt}/orderbook", {})
                    yb, ys = kalshi_best(ob, "yes")
                    nb, ns = kalshi_best(ob, "no")
                    k_yes_ask = 1 - nb if nb is not None else None
                    k_no_ask = 1 - yb if yb is not None else None
                    row = {"ts": round(t0, 2), "coin": coin, "start": start, "left_s": start + 900 - int(t0),
                           "A_polyUp_kalshiNo": pair(qu, su, k_no_ask, ys, rate, exp),
                           "B_polyDown_kalshiYes": pair(qd, sd, k_yes_ask, ns, rate, exp),
                           "poly_up": qu, "poly_down": qd, "kalshi_yes_ask": k_yes_ask, "kalshi_no_ask": k_no_ask}
                    f.write(json.dumps(row) + "\n")
                except Exception as e:
                    f.write(json.dumps({"ts": round(t0, 2), "coin": coin, "error": f"{type(e).__name__}: {e}"[:200]}) + "\n")
            f.flush()
            time.sleep(max(0.0, a.every - (time.time() - t0)))


if __name__ == "__main__":
    main()
