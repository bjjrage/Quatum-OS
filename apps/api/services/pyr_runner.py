"""Corre el análisis "activos parecidos a PYR" en segundo plano (el cockpit lo lanza y consulta el resultado)."""
from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
HIST_ROOT = ROOT / "data" / "historical" / "binance_um"
OUT = ROOT / "data" / "research" / "pyr_like_latest.json"

_lock = threading.Lock()
_state: Dict[str, Any] = {"state": "IDLE", "message": "Todavía no se corrió el análisis.", "result": None}


def _finite(x: Any) -> Any:
    import math
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: _finite(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_finite(v) for v in x]
    return x


def status() -> Dict[str, Any]:
    with _lock:
        s = dict(_state)
    if s["result"] is None and OUT.exists() and s["state"] == "IDLE":
        try:
            s["result"] = _finite(json.loads(OUT.read_text(encoding="utf-8")))
            s["state"], s["message"] = "DONE", "Último resultado guardado."
        except Exception:
            pass
    return s


def _run(train_days: float, test_days: float) -> None:
    from config.settings import settings
    from src.research.pyr_like import run_pyr_analysis
    try:
        def say(m: str) -> None:
            with _lock:
                _state["message"] = m
        res = run_pyr_analysis(HIST_ROOT, list(settings.binance.initial_calibration_sample_v0),
                               train_days=train_days, test_days=test_days, on_status=say)
        res = _finite(res)
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(res), encoding="utf-8")
        with _lock:
            _state.update(state="DONE", message="Análisis terminado.", result=res)
    except Exception as ex:
        with _lock:
            _state.update(state="ERROR", message=f"{type(ex).__name__}: {ex}", result=None)
        (ROOT / "data" / "research").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "research" / "pyr_like_error.log").write_text(traceback.format_exc(), encoding="utf-8")


def start(train_days: float = 90.0, test_days: float = 60.0) -> Dict[str, Any]:
    with _lock:
        if _state["state"] == "RUNNING":
            return {"ok": False, "state": "RUNNING", "message": "Ya hay un análisis corriendo."}
        _state.update(state="RUNNING", message="Arrancando...", result=None)
    threading.Thread(target=_run, args=(train_days, test_days), daemon=True).start()
    return {"ok": True, "state": "RUNNING", "message": "Análisis iniciado."}
