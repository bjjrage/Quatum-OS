"""Summarise an arb_scan_poly_kalshi.py log: how often a pair cost < $1, how long it lasted, how much size.

    uv run python scripts/arb_scan_report.py data/research/arb_scan_long.jsonl [--min-edge 0.01] [--min-left 120]

An "episode" = consecutive readings of the same pair/coin/window with edge >= --min-edge. Money per episode is the best
(edge * size) seen in it, i.e. what one fill at the best level would have made (an upper bound for a single order).
Readings with less than --min-left seconds to the close or with a slow fetch (> --max-fetch s) are excluded: in the last
minute prices jump and two books fetched a fraction of a second apart can show a gap that never existed.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

PAIRS = {"A_polyUp_kalshiNo": "Poly Up + Kalshi No", "B_polyDown_kalshiYes": "Poly Down + Kalshi Yes",
         "C_polyUp_limDown": "Poly Up + Limitless Down", "D_polyDown_limUp": "Poly Down + Limitless Up",
         "E_kalshiYes_limDown": "Kalshi Yes + Limitless Down", "F_kalshiNo_limUp": "Kalshi No + Limitless Up"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    ap.add_argument("--min-edge", type=float, default=0.01)
    ap.add_argument("--min-left", type=int, default=120)
    ap.add_argument("--max-fetch", type=float, default=1.0)
    ap.add_argument("-o", "--output", type=Path, default=None)
    a = ap.parse_args()
    rows = [json.loads(ln) for ln in a.log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    ok = [r for r in rows if "error" not in r and r["left_s"] >= a.min_left and r.get("fetch_s", 0) <= a.max_fetch]
    hours = (ok[-1]["ts"] - ok[0]["ts"]) / 3600 if ok else 0
    out = [f"# Arbitraje entre plataformas — {a.log.name}", "",
           f"{len(rows):,} lecturas, {len(ok):,} válidas (≥ {a.min_left} s al cierre, pedido ≤ {a.max_fetch} s), "
           f"{hours:.1f} h, {len({(r['coin'], r['start']) for r in ok})} ventanas. Umbral {a.min_edge:.1%} después de fees.",
           "", "| par | lecturas con ganancia | episodios | duración mediana | ganancia máx. | US$ por episodio (mediana) | US$ total | US$ por hora |",
           "|---|---|---|---|---|---|---|---|"]
    for k, name in PAIRS.items():
        seen = [r for r in ok if r.get(k)]
        if not seen:
            continue
        eps, cur = [], {}
        for r in seen:
            key = (r["coin"], r["start"])
            p = r[k]
            if p["edge"] >= a.min_edge:
                e = cur.get(key)
                if e and r["ts"] - e["last"] <= 10:
                    e["last"], e["best"] = r["ts"], max(e["best"], p["edge"] * p["size"])
                    e["edge"] = max(e["edge"], p["edge"])
                else:
                    e = cur[key] = {"first": r["ts"], "last": r["ts"], "best": p["edge"] * p["size"], "edge": p["edge"]}
                    eps.append(e)
        n_pos = sum(1 for r in seen if r[k]["edge"] >= a.min_edge)
        if not eps:
            out.append(f"| {name} | 0 / {len(seen):,} | 0 | | | | | |")
            continue
        dur = sorted(e["last"] - e["first"] for e in eps)
        usd = sorted(e["best"] for e in eps)
        tot = sum(usd)
        out.append(f"| {name} | {n_pos:,} / {len(seen):,} | {len(eps)} | {dur[len(dur) // 2]:.0f} s | "
                   f"{max(e['edge'] for e in eps):.1%} | {usd[len(usd) // 2]:.2f} | {tot:.0f} | {tot / hours:.1f} |")
    out += ["", "US$ por episodio = mejor (ganancia × tamaño al mejor precio) del episodio: una sola orden, sin recargar."]
    text = "\n".join(out)
    if a.output:
        a.output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
