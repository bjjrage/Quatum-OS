"""Resumen del paper en vivo de Polymarket up/down (data/paper/poly_updown/events.jsonl).

    uv run python scripts/score_poly_updown_paper.py            # imprime
    uv run python scripts/score_poly_updown_paper.py -o docs/poly_updown_paper.md

Criterio para pasar a plata real (decidido ANTES de ver resultados): >= 300 apuestas llenadas, PnL oficial neto > 0
y t por ventana > 2. Si no se cumple en 2-3 semanas, la estrategia se descarta.
"""
import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tstat(x):
    n = len(x)
    if n < 3:
        return float("nan")
    mu = sum(x) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in x) / (n - 1))
    return mu / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=ROOT / "data" / "paper" / "poly_updown" / "events.jsonl")
    ap.add_argument("-o", "--output", type=Path)
    a = ap.parse_args()
    ev = [json.loads(x) for x in a.file.read_text(encoding="utf-8").splitlines() if x.strip()] if a.file.exists() else []
    fills = {e["slug"]: e for e in ev if e["kind"] == "fill"}
    settles = {e["slug"]: e for e in ev if e["kind"] == "settle"}
    res = {e["slug"]: e for e in ev if e["kind"] == "resolve"}
    signals = sum(1 for e in ev if e["kind"] == "signal")
    misses = sum(1 for e in ev if e["kind"] == "miss")
    usd = sum(f["usd"] for f in fills.values())
    pnl_b = [settles[s]["pnl"] for s in fills if s in settles]
    pnl_o = [res[s]["pnl_official"] for s in fills if s in res]
    by_window = defaultdict(list)
    for s in fills:
        if s in res:
            by_window[s.rsplit("-", 1)[-1]].append(res[s]["pnl_official"])
    cl = [sum(v) / len(v) for v in by_window.values()]
    agree = [e["agrees_with_binance"] for e in res.values() if e.get("agrees_with_binance") is not None]
    span_d = (ev[-1]["ts"] - ev[0]["ts"]) / 86400 if len(ev) > 1 else 0
    lines = [f"# Paper en vivo: Polymarket up/down ({datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC)", "",
             f"- Período: {span_d:.1f} días. Señales {signals}, llenadas {len(fills)}, no llenadas {misses} "
             f"({misses / max(signals, 1) * 100:.0f}% de las señales).",
             f"- Invertido: US$ {usd:,.2f}. PnL con Binance al cierre: US$ {sum(pnl_b):,.2f} ({len(pnl_b)} liquidadas).",
             f"- **PnL con la resolución oficial: US$ {sum(pnl_o):,.2f}** ({len(pnl_o)} resueltas); "
             f"por US$ invertido: {sum(pnl_o) / max(sum(fills[s]['usd'] for s in fills if s in res), 1e-9) * 100:+.1f}%; "
             (f"por día: US$ {sum(pnl_o) / span_d:,.2f}." if span_d >= 0.5 else "por día: (menos de medio día de datos)."),
             f"- Aciertos: {sum(1 for x in pnl_o if x > 0) / max(len(pnl_o), 1) * 100:.0f}%. t por apuesta {tstat(pnl_o):.2f}; "
             f"t por ventana {tstat(cl):.2f} ({len(cl)} ventanas).",
             f"- Binance vs resolución oficial coinciden en {sum(agree) / max(len(agree), 1) * 100:.0f}% de las resueltas.", ""]
    for key, name in (("minutes", "duración (min)"), ("asset", "activo"), ("side", "lado")):
        groups = defaultdict(list)
        for s, f in fills.items():
            if s in res:
                groups[f.get(key)].append(res[s]["pnl_official"])
        lines += [f"| {name} | n | PnL oficial US$ | t |", "|---|---|---|---|"]
        lines += [f"| {k} | {len(v)} | {sum(v):,.2f} | {tstat(v):.2f} |" for k, v in sorted(groups.items(), key=str)]
        lines.append("")
    ok = len(pnl_o) >= 300 and sum(pnl_o) > 0 and tstat(cl) > 2
    lines.append(f"**Criterio para plata real (≥300 resueltas, PnL > 0, t por ventana > 2): {'CUMPLE' if ok else 'todavía no'}.**")
    text = "\n".join(lines)
    print(text)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
