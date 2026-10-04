"""'Guardar versión': run the tests, and only if they pass, git add + commit + push — on the user's own PC.

Runs git with the PC's own credentials (Git Credential Manager). Never forces, never rewrites history.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
_lock = threading.Lock()
_state: Dict[str, Any] = {"state": "IDLE", "steps": []}


def _run(cmd: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}          # never hang waiting for a password prompt
    kw = {"creationflags": 0x08000000} if sys.platform == "win32" else {}
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout, env=env, **kw)


def _step(name: str, ok: bool, out: str) -> None:
    with _lock:
        _state["steps"].append({"step": name, "ok": ok, "output": out[-1500:]})


def _work(message: str, push: bool) -> None:
    try:
        t = _run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], timeout=900)
        last = (t.stdout.strip().splitlines() or [""])[-1]
        _step("tests", t.returncode == 0, last)
        if t.returncode != 0:
            with _lock:
                _state.update(state="ERROR", message=f"Los tests fallan, no se guardó nada: {last}")
            return
        _run(["git", "add", "-A"])
        diff = _run(["git", "diff", "--cached", "--stat"])
        if not diff.stdout.strip():
            _step("commit", True, "nada nuevo para guardar")
        else:
            c = _run(["git", "commit", "-m", message])
            _step("commit", c.returncode == 0, (c.stdout + c.stderr).strip())
            if c.returncode != 0:
                with _lock:
                    _state.update(state="ERROR", message="No se pudo hacer el commit.")
                return
        sha = _run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
        if push:
            p = _run(["git", "push", "origin", branch], timeout=180)
            _step("push", p.returncode == 0, (p.stdout + p.stderr).strip())
            if p.returncode != 0:
                with _lock:
                    _state.update(state="ERROR", sha=sha, branch=branch,
                                  message=f"Guardado en tu PC ({sha}) pero no se pudo subir a GitHub.")
                return
        with _lock:
            _state.update(state="DONE", sha=sha, branch=branch,
                          message=f"Versión {sha} guardada" + (f" y subida a GitHub ({branch})." if push else "."))
    except Exception as ex:
        with _lock:
            _state.update(state="ERROR", message=f"{type(ex).__name__}: {ex}")


def start(message: str, push: bool = True) -> Dict[str, Any]:
    with _lock:
        if _state["state"] == "RUNNING":
            return {"ok": False, "state": "RUNNING", "message": "Ya se está guardando una versión."}
        _state.clear()
        _state.update(state="RUNNING", steps=[], message="Corriendo los tests...")
    threading.Thread(target=_work, args=(message, push), daemon=True).start()
    return {"ok": True, "state": "RUNNING"}


def status() -> Dict[str, Any]:
    with _lock:
        return {**_state, "steps": list(_state.get("steps", []))}
