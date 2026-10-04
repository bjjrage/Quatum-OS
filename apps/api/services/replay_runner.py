"""Runs the STR-002 replay in a background thread so the cockpit can start it and poll the result."""
from __future__ import annotations

import json
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "research" / "str002_replay_latest.json"

_lock = threading.Lock()
_state: Dict[str, Any] = {"state": "IDLE", "message": "Todavía no se corrió ninguna prueba.", "result": None}


def _finite(x: Any) -> Any:
    """JSON for the browser cannot carry NaN/Infinity (e.g. profit factor with no losses): use None."""
    import math
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_finite(v) for v in x]
    return x


def _slim(res: Dict[str, Any]) -> Dict[str, Any]:
    """Result without the per-trade lists (those stay in the JSON file on disk)."""
    strip = lambda d: {k: {kk: vv for kk, vv in v.items() if kk != "trades"} for k, v in (d or {}).items()}
    return _finite({**res, "variants": strip(res.get("variants")), "exit_comparison": strip(res.get("exit_comparison"))})


def status() -> Dict[str, Any]:
    with _lock:
        s = dict(_state)
    if s["result"] is None and OUT.exists() and s["state"] == "IDLE":
        try:
            s["result"] = _slim(json.loads(OUT.read_text(encoding="utf-8")))
            s["message"] = "Último resultado guardado."
            s["state"] = "DONE"
        except Exception:
            pass
    return s


HIST_ROOT = ROOT / "data" / "historical" / "binance_um"


def _run(days: float, source: str = "recorded") -> None:
    from config.settings import settings
    from src.research.str002_replay import (VARIANTS, historical_range, load_panel, load_panel_historical,
                                            run_replay, shock_counts)
    try:
        symbols = list(settings.binance.initial_calibration_sample_v0) if hasattr(settings, "binance") \
            else ["BTCUSDT", "ETHUSDT"]
        if source == "history":
            rng = historical_range(HIST_ROOT)
            if rng is None:
                raise FileNotFoundError("Todavía no hay historial de Binance descargado: usá el botón de descarga.")
            end_ns = rng[1]
            start_ns = max(rng[0], end_ns - int(days * 86400 * 1e9))
            with _lock:
                _state["message"] = f"Leyendo {days:g} días del historial de Binance (puede tardar 1-3 minutos)..."
            panel = load_panel_historical(HIST_ROOT, symbols, start_ns=start_ns, end_ns=end_ns)
        else:
            end_ns = time.time_ns()
            start_ns = end_ns - int(days * 86400 * 1e9)
            with _lock:
                _state["message"] = "Leyendo los datos grabados..."
            panel = load_panel(ROOT / settings.storage.base_data_path, symbols, start_ns=start_ns, end_ns=end_ns)
        with _lock:
            _state["message"] = f"Datos listos ({len(panel.minutes)} minutos, {len(panel.bars) - 2} criptos). Probando las 3 versiones..."
        counts = shock_counts(panel)
        res = run_replay(panel, list(VARIANTS.values()))
        res["impulse_counts"] = counts
        res["source"] = source
        for group in ("variants", "exit_comparison"):          # keep the saved file small on long histories
            for v in res.get(group, {}).values():
                tr = v.get("trades") or []
                if len(tr) > 2000:
                    v["trades"], v["trades_truncated"] = tr[-2000:], len(tr)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(res, default=str), encoding="utf-8")
        slim = _slim(res)
        with _lock:
            _state.update(state="DONE", message="Prueba terminada.", result=slim)
    except Exception as ex:  # surface the failure in the UI instead of dying silently
        with _lock:
            _state.update(state="ERROR", message=f"{type(ex).__name__}: {ex}", result=None)
        (ROOT / "data" / "research").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "research" / "str002_replay_error.log").write_text(traceback.format_exc(), encoding="utf-8")


def start(days: float = 7.0, source: str = "recorded") -> Dict[str, Any]:
    with _lock:
        if _state["state"] == "RUNNING":
            return {"ok": False, "state": "RUNNING", "message": "Ya hay una prueba corriendo."}
        _state.update(state="RUNNING", message="Arrancando...", result=None)
    threading.Thread(target=_run, args=(days, source), daemon=True).start()
    return {"ok": True, "state": "RUNNING", "message": "Prueba iniciada."}
