"""Run the existing strategy studies over the recorded data and save compact, shareable results.

    uv run python scripts/run_strategy_tests.py --data "<ruta>/data/raw"

Writes docs/strategy_tests/*.json (trade lists removed, summaries only):
  recorder_studies.json  BTC -> alts lead-lag and Polymarket up/down vs Binance (src.research.recorder_studies)
  str002_replay.json     STR-002 liquidity shock reversal, all VARIANTS (src.research.str002_replay)
A failure in one study is recorded in its file and does not stop the other.
"""
import argparse
import json
import math
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def compact(x):
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: compact(v) for k, v in x.items() if k != "trades"}
    if isinstance(x, (list, tuple)):
        return [compact(v) for v in x]
    return x


def save(out: Path, name: str, fn) -> None:
    print(f"== {name} ==", flush=True)
    try:
        res = compact(fn())
    except Exception as ex:
        res = {"status": "ERROR", "error": f"{type(ex).__name__}: {ex}", "traceback": traceback.format_exc()}
    path = out / f"{name}.json"
    path.write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"   -> {path} ({path.stat().st_size / 1024:.1f} KB)", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "strategy_tests")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    def recorder():
        from src.research.recorder_studies import run_recorder_studies
        return run_recorder_studies(args.data, say=lambda m: print("  ", m, flush=True))

    def str002():
        from config.settings import settings
        from src.research.str002_replay import VARIANTS, load_panel, run_replay, shock_counts
        symbols = list(settings.binance.initial_calibration_sample_v0)
        print(f"   símbolos: {symbols}", flush=True)
        panel = load_panel(args.data, symbols)
        res = run_replay(panel, list(VARIANTS.values()))
        res["impulse_counts"] = shock_counts(panel)
        res["symbols"] = symbols
        return res

    save(args.out, "recorder_studies", recorder)
    save(args.out, "str002_replay", str002)


if __name__ == "__main__":
    main()
