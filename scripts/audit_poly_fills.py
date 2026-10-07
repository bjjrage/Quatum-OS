"""Which paper fills of the Polymarket up/down bot were at prices that really existed?

    uv run python scripts/audit_poly_fills.py [--events data/paper/poly_updown/events.jsonl] [--data data/raw]

The live paper kept its last quote after the Polymarket WS dropped, so some fills may have used prices that were
already gone. The markets recorder writes the Polymarket L2 book independently (polymarket/orderbook_l2_depth, same PC
clock). For every fill we take the recorded book of the Up token at the fill time (ASOF, last snapshot before it):
  real      the recorded price to buy that side was <= fill price + 1 cent, and the snapshot is <= 15 s old
  fantasma  the recorded price was worse than the fill price (nobody would have sold at that price)
  sin_dato  no recorded snapshot <= 15 s old (cannot tell)
Buying Down is checked against the Up bid (buying Down at 1-b == selling Up at b).
Reports PnL (Binance settle) per group, so we see how much of the profit survives with only real fills.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.research.recorder_studies import _files, updown_markets  # noqa: E402

SLUG = re.compile(r"^(btc|eth|sol)-updown-(\d+)m-(\d+)$")
ASSET = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT"}
MAX_AGE_S, TOL = 15.0, 0.01


def classify(side: str, price: float, best_ask, best_bid, age_s) -> str:
    if age_s is None or age_s > MAX_AGE_S:
        return "sin_dato"
    avail = best_ask if side == "up" else (1 - best_bid if best_bid is not None else None)
    if avail is None or not 0 < avail < 1:
        return "fantasma"
    return "real" if avail <= price + TOL else "fantasma"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=Path, default=ROOT / "data" / "paper" / "poly_updown" / "events.jsonl")
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "docs" / "poly_fill_audit.md")
    a = ap.parse_args()
    import duckdb

    ev = [json.loads(ln) for ln in a.events.read_text(encoding="utf-8").splitlines() if ln.strip()]
    fills = [e for e in ev if e.get("kind") == "fill"]
    settle = {e["slug"]: e["pnl"] for e in ev if e.get("kind") == "settle"}
    tokens = {(m["asset"], m["minutes"], m["start_s"]): m["up_token"] for m in updown_markets(a.data)}
    rows = []
    for i, f in enumerate(fills):
        m = SLUG.match(f["slug"])
        tok = tokens.get((ASSET[m.group(1)], int(m.group(2)), int(m.group(3)))) if m else None
        rows.append((i, tok or "", int(f["t"] * 1e9)))
    l2 = _files(a.data, "polymarket", "orderbook_l2_depth")
    book = {}
    if l2:
        con = duckdb.connect()
        con.execute("CREATE TEMP TABLE bt(i INTEGER, token VARCHAR, ts BIGINT)")
        con.executemany("INSERT INTO bt VALUES (?, ?, ?)", rows)
        for i, ts, ba, bb in con.execute(f"""
                WITH l2 AS (SELECT symbol, ts_received_utc_ns AS ts, asks_price, bids_price
                            FROM read_parquet({l2!r}, union_by_name=true)
                            WHERE symbol IN (SELECT DISTINCT token FROM bt))
                SELECT bt.i, bt.ts - l2.ts, list_min(l2.asks_price), list_max(l2.bids_price)
                FROM bt ASOF JOIN l2 ON bt.token = l2.symbol AND bt.ts >= l2.ts""").fetchall():
            book[i] = (ts / 1e9, None if ba is None else float(ba), None if bb is None else float(bb))
    groups = defaultdict(list)
    detail = []
    for i, f in enumerate(fills):
        age, ba, bb = book.get(i, (None, None, None))
        g = classify(f["side"], f["price"], ba, bb, age)
        groups[g].append(settle.get(f["slug"]))
        pnl = settle.get(f["slug"])
        detail.append(f"| {f['slug']} | {f['side']} | {f['price']:.2f} | "
                      f"{'-' if ba is None else f'{ba:.2f}'} / {'-' if bb is None else f'{bb:.2f}'} | "
                      f"{'-' if age is None else f'{age:.1f}'} | {g} | "
                      f"{'-' if pnl is None else f'{pnl:+.2f}'} |")
    out = ["# Auditoría de llenadas del paper de Polymarket", "",
           f"Llenadas: {len(fills)}. Libro grabado por el recorder: {'sí' if l2 else 'NO (no se puede auditar)'}.", "",
           "| grupo | apuestas | liquidadas | PnL Binance US$ | aciertos |", "|---|---|---|---|---|"]
    for g in ("real", "fantasma", "sin_dato"):
        p = [x for x in groups[g] if x is not None]
        out.append(f"| {g} | {len(groups[g])} | {len(p)} | {sum(p):+.2f} | "
                   f"{(sum(1 for x in p if x > 0) / len(p) * 100) if p else 0:.0f}% |")
    out += ["", "## Detalle", "", "| mercado | lado | precio paper | ask / bid grabado (Up) | antigüedad s | grupo | PnL |",
            "|---|---|---|---|---|---|---|", *detail]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out[:9]))
    print(f"Detalle en {a.output}")


if __name__ == "__main__":
    main()
