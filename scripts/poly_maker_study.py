"""Would a simple market maker have made money on Polymarket up/down? Uses the cache from poly_trades_fetch.py.

    uv run python scripts/poly_maker_study.py --data data/research/poly_trades

1) Aggregate: what all makers together earned = minus the takers' gross result (+ maker rebate).
2) Simulated quoter: at every second we rest a sell of each outcome O at fair_O + h, where fair comes from the Binance
   model (P(up) = Phi(ln(S_t/S_0)/(sigma*sqrt(tau)))) computed with Binance `lag` seconds old (our reaction time).
   A real taker trade "buys O at q" at time t fills us if q >= our ask (our price was as good or better, so the taker
   would have hit us first). We sell min(trade size, --max-shares) at our ask a; result per share = a - win_O
   + rebate (rebateRate * taker fee at a). Quotes are pulled in the last --stop-s seconds of each market.
   Optimistic on queue position (we assume we are first at our price) and ignores that our fill would have changed
   the trade; pessimistic in that adverse selection is fully counted (real outcomes).
Reported per h, lag, coin, duration, time left and halves; t-stat on per-window sums.
"""
import argparse
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

from poly_trades_edge import DUR, phi, price_at, sigma, tstat


def load(d: Path):
    px = {}
    for c in ("btc", "eth", "sol"):
        with gzip.open(d / f"binance_{c}.json.gz", "rt") as f:
            px[c] = {int(k): v for k, v in json.load(f).items()}
    rows = []
    with gzip.open(d / "trades.jsonl.gz", "rt") as f:
        for ln in f:
            r = json.loads(ln)
            o_up, q = r["outcome_up"], r["price"]
            if r["side"] == "SELL":
                o_up, q = not o_up, 1 - q
            r["o_up"], r["q"] = o_up, q
            r["win"] = 1.0 if o_up == r["up_won"] else 0.0
            rows.append(r)
    return px, rows


def tfee(q, rate, exp):
    return q * rate * (q * (1 - q)) ** exp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/research/poly_trades"))
    ap.add_argument("--max-shares", type=float, default=20)
    ap.add_argument("--stop-s", type=int, default=30)
    ap.add_argument("--rebate", type=float, default=0.2)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/poly_maker_study.md"))
    a = ap.parse_args()
    px, rows = load(a.data)
    rows = [r for r in rows if r["start"] <= r["t"] < r["start"] + DUR[r["min"]] and 0.01 <= r["q"] <= 0.99]
    out = ["# ¿Gana un market maker en Polymarket up/down?", "",
           f"{len(rows):,} trades tomadores dentro de la ventana, {len({r['slug'] for r in rows})} mercados, "
           f"{(max(r['t'] for r in rows) - min(r['t'] for r in rows)) / 3600:.1f} h.", ""]

    # 1) all makers together
    vol = sum(r["q"] * r["size"] for r in rows)
    taker_gross = sum((r["win"] - r["q"]) * r["size"] for r in rows)
    fees = sum(tfee(r["q"], r["fee_rate"], r["fee_exp"]) * r["size"] for r in rows)
    out += ["## Todos los makers juntos", "",
            f"- Volumen US$ {vol:,.0f}. Resultado bruto de los tomadores US$ {taker_gross:+,.0f} "
            f"({taker_gross / vol * 100:+.2f}%), fees pagadas US$ {fees:,.0f}.",
            f"- Makers juntos (antes de devolución) US$ {-taker_gross:+,.0f} ({-taker_gross / vol * 100:+.2f}%); "
            f"devolución {a.rebate:.0%} de las fees ≈ US$ {fees * a.rebate:,.0f}.", ""]
    by_left = defaultdict(lambda: [0.0, 0.0])
    for r in rows:
        left = r["start"] + DUR[r["min"]] - r["t"]
        b = "≤30 s" if left <= 30 else "30 s–2 min" if left <= 120 else "2–5 min" if left <= 300 else "> 5 min"
        by_left[b][0] += -(r["win"] - r["q"]) * r["size"]
        by_left[b][1] += r["q"] * r["size"]
    out += ["| tiempo restante | volumen | makers juntos | por US$ |", "|---|---|---|---|"]
    for b in ("> 5 min", "2–5 min", "30 s–2 min", "≤30 s"):
        p, v = by_left[b]
        if v:
            out.append(f"| {b} | US$ {v:,.0f} | US$ {p:+,.0f} | {p / v * 100:+.2f}% |")

    # 2) simulated quoter
    sig = {}
    out += ["", "## Cotizador simulado (vende cada lado a justo + h, con Binance de `lag` s atrás)", "",
            "| h (pts) | lag | llenadas | acciones | PnL US$ | por acción | t por ventana (n) | 1ª mitad | 2ª mitad |",
            "|---|---|---|---|---|---|---|---|---|"]
    cut = sorted(r["t"] for r in rows)[len(rows) // 2]
    best = None
    for h in (0.01, 0.02, 0.03, 0.05):
        for lag in (1, 2, 5):
            fills = []
            for r in rows:
                end = r["start"] + DUR[r["min"]]
                if end - r["t"] <= a.stop_s:
                    continue
                p = px[r["coin"]]
                s0 = price_at(p, r["start"])
                key = (r["coin"], r["start"])
                if key not in sig:
                    sig[key] = sigma(p, r["start"])
                st = price_at(p, r["t"] - lag)
                if not (s0 and st and sig[key]):
                    continue
                pu = phi(math.log(st / s0) / (sig[key] * math.sqrt(end - (r["t"] - lag))))
                ask = (pu if r["o_up"] else 1 - pu) + h
                if ask >= 0.99 or r["q"] < ask:
                    continue
                sh = min(r["size"], a.max_shares)
                res = ask - r["win"] + a.rebate * tfee(ask, r["fee_rate"], r["fee_exp"])
                fills.append((r, sh, res))
            if not fills:
                continue
            per_w = defaultdict(float)
            for r, sh, res in fills:
                per_w[(r["start"], r["min"])] += res * sh
            pnl = sum(res * sh for _, sh, res in fills)
            shares = sum(sh for _, sh, _ in fills)
            h1 = sum(res * sh for r, sh, res in fills if r["t"] < cut)
            h2 = pnl - h1
            out.append(f"| {h * 100:.0f} | {lag} s | {len(fills):,} | {shares:,.0f} | {pnl:+,.0f} | "
                       f"{pnl / shares * 100:+.2f}¢ | {tstat(list(per_w.values())):.1f} ({len(per_w)}) | "
                       f"{h1:+,.0f} | {h2:+,.0f} |")
            if lag == 2 and (best is None or pnl > best[0]):
                best = (pnl, h, fills)
    if best:
        _, h, fills = best
        out += ["", f"## Desglose del mejor con lag 2 s (h = {h * 100:.0f} pts)", "",
                "| grupo | llenadas | PnL US$ | t por ventana |", "|---|---|---|---|"]
        groups = {"BTC": lambda r: r["coin"] == "btc", "ETH": lambda r: r["coin"] == "eth",
                  "SOL": lambda r: r["coin"] == "sol", "5 min": lambda r: r["min"] == 5,
                  "15 min": lambda r: r["min"] == 15,
                  "quedan > 2 min": lambda r: r["start"] + DUR[r["min"]] - r["t"] > 120,
                  "quedan ≤ 2 min": lambda r: r["start"] + DUR[r["min"]] - r["t"] <= 120}
        for name, f in groups.items():
            sub = [(r, sh, res) for r, sh, res in fills if f(r)]
            per_w = defaultdict(float)
            for r, sh, res in sub:
                per_w[(r["start"], r["min"])] += res * sh
            out.append(f"| {name} | {len(sub):,} | {sum(res * sh for _, sh, res in sub):+,.0f} | "
                       f"{tstat(list(per_w.values())):.1f} ({len(per_w)}) |")
    out += ["", "Optimista: supone que nuestra orden estaba primera en la fila a ese precio. "
            "Pesimista: la selección adversa está completa (resultados reales)."]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
