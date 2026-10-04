"""Download Binance historical futures data in the background so the cockpit can start it and watch progress."""
from __future__ import annotations

import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
HIST_ROOT = ROOT / "data" / "historical" / "binance_um"

_lock = threading.Lock()
_state: Dict[str, Any] = {"state": "IDLE", "message": "", "progress": None}


def status() -> Dict[str, Any]:
    from src.data.binance_history import inventory
    with _lock:
        s = {**_state}
    try:
        inv = inventory(HIST_ROOT)
    except Exception:
        inv = {}
    s["inventory"] = inv
    s["symbols_on_disk"] = len(inv)
    if inv:
        s["first_period"] = min(v["first"] for v in inv.values())
        s["last_period"] = max(v["last"] for v in inv.values())
    try:
        s["size_mb"] = round(sum(p.stat().st_size for p in HIST_ROOT.rglob("*.parquet")) / 1e6, 1)
    except Exception:
        s["size_mb"] = 0.0
    return s


def _run(months: int) -> None:
    import httpx
    from config.settings import settings
    from src.data.binance_history import download_funding, download_klines
    symbols = list(settings.binance.initial_calibration_sample_v0)

    def on_progress(p) -> None:
        with _lock:
            _state["progress"] = asdict(p)
            _state["message"] = f"Descargando {p.current} ({p.done}/{p.total})"

    try:
        t0 = time.time()
        with httpx.Client(headers={"User-Agent": "quant-os-history/1.0"}, follow_redirects=True) as client:
            prog = download_klines(client, HIST_ROOT, symbols, months=months, on_progress=on_progress)
            with _lock:
                _state["message"] = "Descargando historial de funding..."
            try:
                funding = download_funding(client, HIST_ROOT, symbols, months=months)
            except Exception as ex:   # funding is a bonus; klines are what matters
                funding = {"error": f"{type(ex).__name__}: {ex}"}
        msg = (f"Listo en {int(time.time() - t0)} s: {prog.downloaded} archivos nuevos, {prog.skipped} ya estaban, "
               f"{prog.missing} no existen en Binance (cripto listada después), {prog.failed} fallaron.")
        with _lock:
            _state.update(state="DONE" if prog.failed == 0 else "DONE_WITH_ERRORS", message=msg,
                          progress=asdict(prog), funding_rows=funding)
    except Exception as ex:
        with _lock:
            _state.update(state="ERROR", message=f"{type(ex).__name__}: {ex}")
        HIST_ROOT.mkdir(parents=True, exist_ok=True)
        (HIST_ROOT / "download_error.log").write_text(traceback.format_exc(), encoding="utf-8")


def start(months: int = 12) -> Dict[str, Any]:
    with _lock:
        if _state["state"] == "RUNNING":
            return {"ok": False, "state": "RUNNING", "message": "Ya hay una descarga en curso."}
        _state.update(state="RUNNING", message="Arrancando la descarga...", progress=None)
    threading.Thread(target=_run, args=(months,), daemon=True).start()
    return {"ok": True, "state": "RUNNING", "message": "Descarga iniciada."}
