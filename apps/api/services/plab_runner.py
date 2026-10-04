"""Laboratorio de carteras (días a semanas) en segundo plano: el cockpit lo lanza y consulta el resultado."""
from __future__ import annotations

import json
import threading
import traceback
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
HIST_ROOT = ROOT / "data" / "historical" / "binance_um"
OUT = ROOT / "data" / "research" / "portfolio_lab_latest.json"

_lock = threading.Lock()
_state: Dict[str, Any] = {"state": "IDLE", "message": "Todavía no se corrió el laboratorio de carteras.", "result": None}


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


def _run(days: float, which: str = "main") -> None:
    from src.research.portfolio_lab import load_daily, run_portfolio_lab, taker_robustness
    try:
        with _lock:
            _state["message"] = "Leyendo años de velas de 1 hora..."
        g = load_daily(HIST_ROOT)

        def say(m: str) -> None:
            with _lock:
                _state["message"] = m
        res = _finite(run_portfolio_lab(g, taker_robustness() if which == "taker" else None, say=say))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        (OUT if which == "main" else OUT.with_name("portfolio_lab_taker.json")).write_text(json.dumps(res), encoding="utf-8")
        with _lock:
            _state.update(state="DONE", message="Laboratorio de carteras terminado.", result=res)
    except Exception as ex:
        with _lock:
            _state.update(state="ERROR", message=f"{type(ex).__name__}: {ex}", result=None)
        (ROOT / "data" / "research").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "research" / "portfolio_lab_error.log").write_text(traceback.format_exc(), encoding="utf-8")


def start(days: float = 365.0, which: str = "main") -> Dict[str, Any]:
    with _lock:
        if _state["state"] == "RUNNING":
            return {"ok": False, "state": "RUNNING", "message": "Ya hay una búsqueda corriendo."}
        _state.update(state="RUNNING", message="Arrancando...", result=None)
    threading.Thread(target=_run, args=(days, which), daemon=True).start()
    return {"ok": True, "state": "RUNNING", "message": "Búsqueda iniciada."}
