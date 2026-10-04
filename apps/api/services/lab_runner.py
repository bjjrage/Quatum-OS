"""Laboratorio de estrategias en segundo plano: el cockpit lo lanza y consulta el resultado."""
from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
HIST_ROOT = ROOT / "data" / "historical" / "binance_um"
OUT = ROOT / "data" / "research" / "strategy_lab_latest.json"

_lock = threading.Lock()
_state: Dict[str, Any] = {"state": "IDLE", "message": "Todavía no se corrió el laboratorio.", "result": None}


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


def _run(days: float) -> None:
    from src.research.strategy_lab import run_lab
    try:
        symbols = sorted(p.name.split("=", 1)[1] for p in (HIST_ROOT / "klines_1m").glob("symbol=*"))

        def say(m: str) -> None:
            with _lock:
                _state["message"] = m
        res = _finite(run_lab(HIST_ROOT, symbols, days=days, on_status=say))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(res), encoding="utf-8")
        with _lock:
            _state.update(state="DONE", message="Laboratorio terminado.", result=res)
    except Exception as ex:
        with _lock:
            _state.update(state="ERROR", message=f"{type(ex).__name__}: {ex}", result=None)
        (ROOT / "data" / "research").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "research" / "strategy_lab_error.log").write_text(traceback.format_exc(), encoding="utf-8")


def start(days: float = 365.0) -> Dict[str, Any]:
    with _lock:
        if _state["state"] == "RUNNING":
            return {"ok": False, "state": "RUNNING", "message": "Ya hay una búsqueda corriendo."}
        _state.update(state="RUNNING", message="Arrancando...", result=None)
    threading.Thread(target=_run, args=(days,), daemon=True).start()
    return {"ok": True, "state": "RUNNING", "message": "Búsqueda iniciada."}
