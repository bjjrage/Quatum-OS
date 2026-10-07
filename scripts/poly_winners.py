"""Who wins on Polymarket up/down, does it persist, what do they do, and can it be copied late?

    uv run python scripts/poly_winners.py --data data/research/poly_trades

Uses the cache of poly_trades_fetch.py (taker trades with wallet). Every trade = "bought outcome O at q"
(selling O at p == buying the other side at 1-p); result per share = win - q - taker fee.
1) Persistence: split the period in two halves by time. Wallets with >= --min-trades in both halves. Top N of half A by
   PnL -> their PnL in half B (and the reverse), against N random wallets and against everybody.
2) Profile of wallets that are top in BOTH halves vs everybody: time left at entry, price paid, share of "favourite"
   buys (q > 0.5), coins, size, trades per market, and the Binance model edge at entry (lag 5 s).
3) Copy test in half B: for each trade of the half-A top wallets, we buy the same outcome at the first later trade of that
   outcome in the same market at least D seconds after theirs (that price really traded), D = 5/15/30/60 s.
"""
import argparse
import math
import random
from collections import defaultdict
from pathlib import Path

from poly_maker_study import load, tfee
from poly_trades_edge import DUR, phi, price_at, sigma, tstat


def pnl(r):
    return (r["win"] - r["q"] - tfee(r["q"], r["fee_rate"], r["fee_exp"])) * r["size"]


def med(x):
    x = sorted(x)
    return x[len(x) // 2] if x else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=Path("data/research/poly_trades"))
    ap.add_argument("--min-trades", type=int, default=30)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/poly_winners.md"))
    a = ap.parse_args()
    px, rows = load(a.data)
    rows = [r for r in rows if r.get("wallet") and 0.01 <= r["q"] <= 0.99 and r["start"] <= r["t"] < r["start"] + DUR[r["min"]]]
    for r in rows:
        r["left"] = r["start"] + DUR[r["min"]] - r["t"]
        r["pnl"] = pnl(r)
        r["usd"] = r["q"] * r["size"]
    cut = med([r["t"] for r in rows])
    halves = {"A": [r for r in rows if r["t"] < cut], "B": [r for r in rows if r["t"] >= cut]}
    stats = {h: defaultdict(lambda: [0, 0.0, 0.0]) for h in halves}
    for h, rs in halves.items():
        for r in rs:
            s = stats[h][r["wallet"]]
            s[0] += 1
            s[1] += r["pnl"]
            s[2] += r["usd"]
    both = [w for w in stats["A"] if stats["A"][w][0] >= a.min_trades and stats["B"].get(w, [0])[0] >= a.min_trades]
    out = ["# Ganadores de Polymarket up/down: ¿persisten, qué hacen, se pueden copiar?", "",
           f"{len(rows):,} trades tomadores, {len({r['wallet'] for r in rows}):,} billeteras, "
           f"{(max(r['t'] for r in rows) - min(r['t'] for r in rows)) / 3600:.1f} h. "
           f"Billeteras con ≥ {a.min_trades} trades en las dos mitades: {len(both):,}.", ""]

    # 1) persistence
    out += ["## 1. ¿El que gana en una mitad gana en la otra?", "",
            "| elegidas en | grupo | billeteras | PnL en la otra mitad | por US$ |", "|---|---|---|---|---|"]
    rnd = random.Random(7)
    winners = {}
    for sel, other in (("A", "B"), ("B", "A")):
        ranked = sorted(both, key=lambda w: -stats[sel][w][1])
        groups = {f"top {a.top}": ranked[:a.top], f"peores {a.top}": ranked[-a.top:],
                  f"{a.top} al azar": rnd.sample(both, min(a.top, len(both))), "todas": both}
        winners[sel] = set(ranked[:a.top])
        for name, ws in groups.items():
            p = sum(stats[other][w][1] for w in ws)
            u = sum(stats[other][w][2] for w in ws)
            out.append(f"| {sel} | {name} | {len(ws)} | US$ {p:+,.0f} | {p / u * 100:+.2f}% |")
    # rank correlation of PnL per $ between halves
    xa = [stats["A"][w][1] / stats["A"][w][2] for w in both]
    xb = [stats["B"][w][1] / stats["B"][w][2] for w in both]

    def ranks(x):
        o = sorted(range(len(x)), key=lambda i: x[i])
        rk = [0] * len(x)
        for i, j in enumerate(o):
            rk[j] = i
        return rk
    ra, rb = ranks(xa), ranks(xb)
    n = len(both)
    rho = 1 - 6 * sum((ra[i] - rb[i]) ** 2 for i in range(n)) / (n * (n * n - 1)) if n > 2 else float("nan")
    out += ["", f"Correlación de rangos (PnL por US$, mitad A vs B) entre {n} billeteras: **{rho:+.2f}** "
            "(0 = suerte pura, cerca de 1 = habilidad que se repite)."]

    # 2) profile
    stable = [w for w in both if stats["A"][w][1] > 0 and stats["B"][w][1] > 0
              and stats["A"][w][1] / stats["A"][w][2] > 0.02 and stats["B"][w][1] / stats["B"][w][2] > 0.02]
    sig = {}

    def model_edge(r):
        p = px[r["coin"]]
        key = (r["coin"], r["start"])
        if key not in sig:
            sig[key] = sigma(p, r["start"])
        s0, st = price_at(p, r["start"]), price_at(p, r["t"] - 5)
        if not (s0 and st and sig[key]):
            return None
        pu = phi(math.log(st / s0) / (sig[key] * math.sqrt(r["left"] + 5)))
        return (pu if r["o_up"] else 1 - pu) - r["q"]

    def profile(rs):
        if not rs:
            return None
        per_mkt = defaultdict(int)
        for r in rs:
            per_mkt[(r["wallet"], r["slug"])] += 1
        me = [m for m in (model_edge(r) for r in rs[:20000]) if m is not None]
        u = sum(r["usd"] for r in rs)
        return {"n": len(rs), "pnl%": sum(r["pnl"] for r in rs) / u * 100, "left": med([r["left"] for r in rs]),
                "q": med([r["q"] for r in rs]), "fav": sum(r["q"] > 0.5 for r in rs) / len(rs) * 100,
                "usd": med([r["usd"] for r in rs]), "tpm": med(list(per_mkt.values())),
                "btc": sum(r["coin"] == "btc" for r in rs) / len(rs) * 100,
                "m5": sum(r["min"] == 5 for r in rs) / len(rs) * 100,
                "edge": med(me) * 100 if me else float("nan"),
                "with_model": sum(m > 0 for m in me) / len(me) * 100 if me else float("nan")}
    out += ["", f"## 2. Qué hacen distinto las que ganan en las dos mitades (> 2% por US$ en cada una): "
            f"{len(stable)} billeteras", "",
            "| grupo | trades | PnL por US$ | seg. al cierre (med.) | precio (med.) | % compra favorito | US$ por trade (med.) "
            "| trades por mercado | % BTC | % 5 min | ventaja modelo Binance (med., pts) | % a favor del modelo |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    sw = set(stable)
    for name, rs in (("ganadoras estables", [r for r in rows if r["wallet"] in sw]),
                     ("todas las demás", [r for r in rows if r["wallet"] not in sw])):
        p = profile(rs)
        if p:
            out.append(f"| {name} | {p['n']:,} | {p['pnl%']:+.2f}% | {p['left']:.0f} | {p['q']:.2f} | {p['fav']:.0f}% | "
                       f"{p['usd']:.1f} | {p['tpm']} | {p['btc']:.0f}% | {p['m5']:.0f}% | {p['edge']:+.1f} | "
                       f"{p['with_model']:.0f}% |")
    if stable:
        out += ["", "Las 10 más grandes (por volumen):", "",
                "| billetera | trades A / B | PnL A | PnL B | volumen | seg. al cierre | precio med. | % favorito |",
                "|---|---|---|---|---|---|---|---|"]
        for w in sorted(stable, key=lambda w: -(stats["A"][w][2] + stats["B"][w][2]))[:10]:
            rs = [r for r in rows if r["wallet"] == w]
            out.append(f"| `{w[:10]}…` | {stats['A'][w][0]} / {stats['B'][w][0]} | {stats['A'][w][1]:+,.0f} | "
                       f"{stats['B'][w][1]:+,.0f} | {stats['A'][w][2] + stats['B'][w][2]:,.0f} | "
                       f"{med([r['left'] for r in rs]):.0f} | {med([r['q'] for r in rs]):.2f} | "
                       f"{sum(r['q'] > 0.5 for r in rs) / len(rs) * 100:.0f}% |")

    # 3) copy test
    by_mkt = defaultdict(list)
    for r in rows:
        by_mkt[(r["slug"], r["o_up"])].append(r)
    for v in by_mkt.values():
        v.sort(key=lambda r: r["t"])
    out += ["", "## 3. ¿Se puede copiar? (elegidas en A, copiadas en B comprando lo mismo D segundos después)", "",
            "| atraso D | trades copiados | PnL de ellas | PnL copiando (por acción, mismo tamaño) | por US$ | t por ventana |",
            "|---|---|---|---|---|---|"]
    lead = [r for r in halves["B"] if r["wallet"] in winners["A"]]
    for d in (5, 15, 30, 60):
        cp, theirs, per_w, usd = [], 0.0, defaultdict(float), 0.0
        for r in lead:
            nxt = next((x for x in by_mkt[(r["slug"], r["o_up"])] if x["t"] >= r["t"] + d), None)
            if not nxt or nxt["left"] < 5:
                continue
            q = nxt["q"]
            res = (r["win"] - q - tfee(q, r["fee_rate"], r["fee_exp"])) * r["size"]
            cp.append(res)
            theirs += r["pnl"]
            usd += q * r["size"]
            per_w[(r["start"], r["min"])] += res
        if cp:
            out.append(f"| {d} s | {len(cp):,} | US$ {theirs:+,.0f} | US$ {sum(cp):+,.0f} | {sum(cp) / usd * 100:+.2f}% | "
                       f"{tstat(list(per_w.values())):.1f} ({len(per_w)}) |")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
