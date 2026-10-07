"""Paper trading en vivo de los mercados up/down de Polymarket (no envía órdenes reales).

    uv run python scripts/run_poly_updown_paper.py
    uv run python scripts/run_poly_updown_paper.py --threshold 0.05 --delay 2 --max-usd 25

Dejar la ventana abierta. Calienta 30 min (volatilidad) antes de la primera apuesta.
Resultados: data/paper/poly_updown/events.jsonl y state.json; resumen con scripts/score_poly_updown_paper.py.
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.paper.poly_updown_paper import Config, PolyUpDownPaper  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--threshold", type=float, default=0.05, help="ventaja mínima en probabilidad (0.05 = 5 pts)")
ap.add_argument("--delay", type=float, default=2.0, help="segundos entre la señal y la orden simulada")
ap.add_argument("--max-usd", type=float, default=25.0, help="tope por apuesta en US$")
a = ap.parse_args()
try:
    asyncio.run(PolyUpDownPaper(Config(threshold=a.threshold, delay_s=a.delay, max_usd=a.max_usd)).run())
except KeyboardInterrupt:
    print("Paper detenido.")
