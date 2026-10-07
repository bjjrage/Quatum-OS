"""Stress-test the Polymarket up/down vs Binance signal found by src.research.recorder_studies.

    uv run python scripts/poly_edge_check.py --data "<ruta>/data/raw"

Same model and data as study_poly (P(up) from Binance mid and 30-min realised vol; bet when the model beats the
Polymarket ask/bid by >= threshold), plus what decides if it is tradable:
  * Polymarket taker fee per market from its recorded fee schedule: shares * p * rate * (p(1-p))^exponent.
    If missing, the worse of (0.07, 1) and (0.25, 2) is used.
  * Execution delay 5 / 10 / 30 s (quotes are 5 s buckets: the last quote of the bucket).
  * Halves of the period, per duration (5/15/60 min), per asset.
  * Clustering: BTC/ETH/SOL markets of the same window move together; t-stat also on per-window means.
  * Size: shares resting at the best ask/bid in orderbook_l2_depth at execution time -> dollars per bet.
Writes a compact Markdown report.
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.research.recorder_studies import (_files, _mid_near, binance_seconds, model_prob,  # noqa: E402
                                           poly_quotes, updown_markets)

THRESHOLDS = (0.03, 0.05, 0.10)
DELAYS = (5, 10, 30)


def fee_params(raw: str):
    try:
        d = json.loads(raw)
        return float(d["rate"]), float(d.get("exponent", 1))
    except Exception:
        return None


def fee_per_share(p: float, params) -> float:
    if params:
        r, e = params
        return p * r * (p * (1 - p)) ** e
    return max(p * 0.07 * (p * (1 - p)), p * 0.25 * (p * (1 - p)) ** 2)


def tstat(x):
    n = len(x)
    if n < 3:
        return float("nan")
    mu = sum(x) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in x) / (n - 1))
    return mu / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def collect(mk, q, s0, quotes, thr, delay):
    bets = []
    for m in mk:
        b, a = q[m["asset"]]
        S0, S1 = _mid_near(b, a, m["start_s"] - s0), _mid_near(b, a, m["end_s"] - s0)
        if not (S0 == S0 and S1 == S1) or abs(S1 / S0 - 1) < 0.0001:
            continue
        up = 1.0 if S1 > S0 else 0.0
        qt = quotes.get(m["up_token"], {})
        params = fee_params(m["fee_raw"])
        for t in range(m["start_s"] + 60, m["end_s"] - 30, 5):
            qq, nxt = qt.get(t), qt.get(t + delay)
            if not qq or not nxt or t + delay >= m["end_s"]:
                continue
            p = model_prob(b, a, s0, m["start_s"], t, m["end_s"])
            if p != p:
                continue
            bid, ask = qq
            nb, na = nxt
            if p - ask >= thr:
                price, win, side = na, up, "up"
            elif bid - p >= thr:
                price, win, side = 1.0 - nb, 1.0 - up, "down"
            else:
                continue
            if not 0 < price < 1:
                break
            gross = win - price
            fee = fee_per_share(price, params)
            bets.append({"t": t, "exec_t": t + delay, "start": m["start_s"], "min": m["minutes"], "asset": m["asset"],
                         "token": m["up_token"], "side": side, "price": price, "gross": gross, "net": gross - fee,
                         "fee": fee, "fee_params": params, "win": win,
                         "edge": (p - ask) if side == "up" else (bid - p)})
            break
    return bets


def summarize(bets):
    if not bets:
        return None
    net = [b["net"] for b in bets]
    per_dollar = sum(b["net"] for b in bets) / sum(b["price"] for b in bets)
    win = defaultdict(list)
    for b in bets:
        win[b["start"]].append(b["net"])
    cl = [sum(v) / len(v) for v in win.values()]
    return {"n": len(bets), "net_share": sum(net) / len(net), "per_dollar": per_dollar,
            "fee_share": sum(b["fee"] for b in bets) / len(bets), "hit": sum(1 for b in bets if b["net"] > 0) / len(bets),
            "t": tstat(net), "n_windows": len(cl), "t_windows": tstat(cl)}


def fmt(name, s):
    if not s:
        return f"| {name} | 0 | - | - | - | - | - | - |"
    return (f"| {name} | {s['n']} | {s['net_share']:+.3f} | {s['per_dollar'] * 100:+.1f}% | {s['fee_share']:.4f} | "
            f"{s['hit'] * 100:.0f}% | {s['t']:.1f} | {s['t_windows']:.1f} ({s['n_windows']}) |")


def depth(base: Path, bets, offset_ns: int):
    import duckdb
    f = _files(base, "polymarket", "orderbook_l2_depth")
    if not f or not bets:
        return {}
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE bt(i INTEGER, token VARCHAR, ts BIGINT)")
    con.executemany("INSERT INTO bt VALUES (?, ?, ?)",
                    [(i, b["token"], int(b["exec_t"]) * 10**9 + int(offset_ns) + 5 * 10**9 - 1) for i, b in enumerate(bets)])
    rows = con.execute(f"""
        WITH l2 AS (SELECT symbol, ts_received_utc_ns AS ts, asks_price, asks_size, bids_price, bids_size
                    FROM read_parquet({f!r}, union_by_name=true) WHERE symbol IN (SELECT DISTINCT token FROM bt))
        SELECT bt.i, l2.ts,
               list_min(asks_price) AS best_ask, asks_size[list_position(asks_price, list_min(asks_price))] AS ask_sz,
               list_max(bids_price) AS best_bid, bids_size[list_position(bids_price, list_max(bids_price))] AS bid_sz
        FROM bt ASOF JOIN l2 ON bt.token = l2.symbol AND bt.ts >= l2.ts""").fetchall()
    out = {}
    for i, ts, ba, asz, bb, bsz in rows:
        ba, asz, bb, bsz = (None if v is None else float(v) for v in (ba, asz, bb, bsz))
        b = bets[i]
        age = (int(b["exec_t"]) * 10**9 + int(offset_ns) + 5 * 10**9 - 1 - ts) / 1e9
        if b["side"] == "up":
            px = ba if ba is not None and 0 < ba < 1 else None
            out[i] = (asz or 0.0) * (ba or 0.0), age, px
        else:  # buying "down" = selling "up" into the bid
            px = 1 - bb if bb is not None and 0 < bb < 1 else None
            out[i] = (bsz or 0.0) * (1 - (bb or 1.0)), age, px
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "docs" / "poly_edge_check.md")
    args = ap.parse_args()
    print("Leyendo Binance por segundo...", flush=True)
    s0, q, off = binance_seconds(args.data)
    s1 = s0 + len(next(iter(q.values()))[0]) - 1
    mk = [m for m in updown_markets(args.data) if m["asset"] in q and m["start_s"] - 1800 >= s0 and m["end_s"] + 5 <= s1]
    print(f"{len(mk)} mercados; leyendo cotizaciones de Polymarket...", flush=True)
    quotes = poly_quotes(args.data, [m["up_token"] for m in mk], off)
    mid = sorted(m["start_s"] for m in mk)[len(mk) // 2] if mk else 0
    head = "| grupo | apuestas | neto/acción | neto por US$ | fee/acción | aciertos | t | t por ventana (n) |"
    sep = "|---|---|---|---|---|---|---|---|"
    out = ["# Polymarket up/down vs Binance: ¿es operable?", "",
           f"{len(mk)} mercados dentro del período. Fee por mercado según su `fee_schedule` grabado "
           "(`acciones × p × rate × (p(1−p))^exp`). Neto = después de fee. Precio = ask (o 1−bid) del bucket de 5 s "
           "posterior al retraso.", ""]
    base_bets = None
    for delay in DELAYS:
        out += [f"## Retraso de ejecución {delay} s", "", head, sep]
        for thr in THRESHOLDS:
            bets = collect(mk, q, s0, quotes, thr, delay)
            if delay == 5 and thr == 0.05:
                base_bets = bets
            out.append(fmt(f"umbral {thr * 100:.0f} pts", summarize(bets)))
        out.append("")
    if base_bets:
        out += ["## Desglose (retraso 5 s, umbral 5 pts)", "", head, sep]
        out.append(fmt("1ª mitad", summarize([b for b in base_bets if b["start"] < mid])))
        out.append(fmt("2ª mitad", summarize([b for b in base_bets if b["start"] >= mid])))
        for k in sorted({b["min"] for b in base_bets}):
            out.append(fmt(f"mercados de {k} min", summarize([b for b in base_bets if b["min"] == k])))
        for a in sorted({b["asset"] for b in base_bets}):
            out.append(fmt(a, summarize([b for b in base_bets if b["asset"] == a])))
        for sd in ("up", "down"):
            out.append(fmt(f"lado {sd}", summarize([b for b in base_bets if b["side"] == sd])))
        print("Midiendo tamaño disponible en el libro...", flush=True)
        try:
            dp = depth(args.data, base_bets, off)
            usd = sorted(v[0] for v in dp.values())
            age = sorted(v[1] for v in dp.values())
            if usd:
                pnl_cap = sum(base_bets[i]["net"] / base_bets[i]["price"] * min(v[0], 1000) for i, v in dp.items())
                days = (s1 - s0) / 86400
                out += ["", "## Tamaño disponible al ejecutar (mejor nivel del libro L2)", "",
                        f"- Apuestas con libro: {len(usd)} de {len(base_bets)}. US$ en el mejor nivel: mediana {usd[len(usd) // 2]:.0f}, "
                        f"p25 {usd[len(usd) // 4]:.0f}, p75 {usd[3 * len(usd) // 4]:.0f}.",
                        f"- Antigüedad del snapshot L2 usado: mediana {age[len(age) // 2]:.0f} s (el libro se graba por snapshots).",
                        f"- Ganancia neta tomando solo el mejor nivel (tope US$ 1.000 por apuesta): US$ {pnl_cap:,.0f} en "
                        f"{days:.1f} días (≈ US$ {pnl_cap / max(days, 1e-9):,.0f}/día). Cota optimista: supone que nadie se lo llevó antes."]
                pnl_100 = sum(base_bets[i]["net"] / base_bets[i]["price"] * min(v[0], 100) for i, v in dp.items())
                out.append(f"- Con tope US$ 100 por apuesta (más realista para empezar): US$ {pnl_100:,.0f} "
                           f"(≈ US$ {pnl_100 / max(days, 1e-9):,.0f}/día).")
                # cross-check: the recorded BBO had an ordering bug; re-price every bet with the L2 book
                l2 = [(i, v[2]) for i, v in dp.items() if v[2] is not None and v[1] <= 30]
                if l2:
                    agree = sum(1 for i, px in l2 if abs(px - base_bets[i]["price"]) <= 0.01) / len(l2)
                    re = []
                    for i, px in l2:
                        b = base_bets[i]
                        re.append({**b, "price": px, "net": b["win"] - px - fee_per_share(px, b["fee_params"])})
                    out += ["", "## Control del BBO grabado (bug de orden en el recorder)", "",
                            f"- Apuestas con snapshot L2 de ≤30 s: {len(l2)}. Precio del BBO = mejor nivel L2 (±1 centavo) "
                            f"en el {agree * 100:.0f}% de los casos.",
                            "- Si el edge es real, tiene que sobrevivir usando el precio del libro L2:", "", head, sep,
                            fmt("con precio BBO (original)", summarize([base_bets[i] for i, _ in l2])),
                            fmt("con precio L2 (control)", summarize(re))]
        except Exception as ex:
            out += ["", f"No se pudo medir el libro: `{type(ex).__name__}: {ex}`"]
    out += ["", "## Cómo leerlo", "",
            "- Vale si el neto por US$ es positivo con retraso de 10-30 s, en ambas mitades y con t por ventana > 2.",
            "- Si muere al pasar de 5 a 10 s, es arbitraje de latencia: requiere un bot rápido y el tamaño manda.",
            "- El tamaño en el mejor nivel limita cuánto se puede ganar por día, por bueno que sea el edge."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")


if __name__ == "__main__":
    main()
