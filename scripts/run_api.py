"""Backend supervisor: runs the API and restarts it automatically when the code changes.

Why not `uvicorn --reload`: on Windows its reloader hands the listening socket to a multiprocessing
child, and when the parent dies the child keeps serving OLD code on port 8000 ("ghost backend").
Here the API child opens its own socket and is a plain subprocess of this window: closing the window
closes both, and a restart is a clean terminate + start.

Never touches the recorder (it is an independent process).
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable

ROOT = Path(__file__).resolve().parents[1]
WATCH_DIRS = ("apps/api", "src", "config")
POLL_S = 1.5


def snapshot(root: Path = ROOT, dirs: Iterable[str] = WATCH_DIRS) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for d in dirs:
        base = root / d
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            try:
                out[str(p)] = p.stat().st_mtime
            except OSError:
                pass
    return out


def changed(before: Dict[str, float], after: Dict[str, float]) -> bool:
    return before != after


def start_api() -> subprocess.Popen:
    cmd = [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8000"]
    return subprocess.Popen(cmd, cwd=str(ROOT))


def stop_api(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def main() -> None:
    print("[supervisor] Backend con reinicio automatico al cambiar el codigo. No cierres esta ventana.")
    snap = snapshot()
    proc = start_api()
    try:
        while True:
            time.sleep(POLL_S)
            new = snapshot()
            if changed(snap, new):
                time.sleep(1.0)                 # let a multi-file update finish landing
                snap = snapshot()
                print("[supervisor] Codigo actualizado: reiniciando el backend...")
                stop_api(proc)
                proc = start_api()
            elif proc.poll() is not None:
                print("[supervisor] El backend se detuvo (posible error en el codigo). "
                      "Se reintenta solo cuando cambie el codigo, o en 30 s.")
                for _ in range(20):
                    time.sleep(POLL_S)
                    if changed(snap, snapshot()):
                        break
                snap = snapshot()
                proc = start_api()
    except KeyboardInterrupt:
        pass
    finally:
        stop_api(proc)


if __name__ == "__main__":
    main()
