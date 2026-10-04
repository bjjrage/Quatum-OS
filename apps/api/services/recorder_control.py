"""Start / stop the market-data recorder as a detached process, from the cockpit.

Stop is graceful: a STOP file is written and the recorder flushes its Parquet buffers and exits.
Only if it ignores the request for `grace_s` seconds is the process terminated.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import psutil

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "data" / "runtime"
STOP_FILE = RUNTIME / "STOP_RECORDER"
MANIFEST = RUNTIME / "current_run.json"


def _pid() -> int:
    try:
        return int(json.loads(MANIFEST.read_text(encoding="utf-8")).get("pid", 0))
    except Exception:
        return 0


def is_running() -> bool:
    pid = _pid()
    if pid <= 0 or not psutil.pid_exists(pid):
        return False
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def _start_outside_job(cmd) -> bool:
    """Windows: create the recorder through WMI so it is NOT a member of the backend's job object
    (uv/console jobs kill their members when the backend window closes). Returns False if unavailable."""
    logp = ROOT / "data" / "runtime" / "recorder_stdout.log"
    inner = " ".join(f'"{c}"' for c in cmd) + f' >> "{logp}" 2>&1'
    line = f'cmd.exe /c "{inner}"'.replace("'", "''")
    ps = ("$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
          f"@{{CommandLine='{line}'; CurrentDirectory='{str(ROOT)}'}}; exit [int]$r.ReturnValue")
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=20,
                             creationflags=0x08000000)
        return res.returncode == 0
    except Exception:
        return False


def start(new_run: bool = False) -> Dict[str, Any]:
    if is_running():
        return {"ok": False, "state": "ALREADY_RUNNING", "pid": _pid(), "message": "El recorder ya está corriendo."}
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STOP_FILE.unlink(missing_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts" / "run_recorder.py")]
    if new_run:
        cmd.append("--new-run")
    if sys.platform == "win32" and _start_outside_job(cmd):
        for _ in range(20):                       # the recorder writes its PID into the manifest on start
            time.sleep(0.5)
            if is_running():
                return {"ok": True, "state": "STARTED", "pid": _pid(), "message": "Recorder iniciado."}
        return {"ok": False, "state": "FAILED_TO_START",
                "message": "El recorder no arrancó; mirá data/runtime/recorder_stdout.log."}
    log = open(ROOT / "data" / "runtime" / "recorder_stdout.log", "ab")
    kwargs: Dict[str, Any] = {}
    if sys.platform == "win32":
        # BREAKAWAY_FROM_JOB: `uv run` places the backend in a Windows job object that kills every child
        # when the backend window closes. The recorder must survive backend restarts, so it leaves the job.
        base = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        flags_try = [base | 0x01000000, base]
    else:
        kwargs["start_new_session"] = True
        flags_try = [0]
    proc = None
    for fl in flags_try:
        try:
            extra = {"creationflags": fl} if sys.platform == "win32" else {}
            proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, **kwargs, **extra)
            break
        except OSError:
            continue
    if proc is None:
        return {"ok": False, "state": "FAILED_TO_START", "message": "Windows no permitió lanzar el recorder."}
    time.sleep(2.0)
    if proc.poll() is not None:
        return {"ok": False, "state": "FAILED_TO_START", "message": "El recorder se cerró al arrancar; mirá data/runtime/recorder_stdout.log."}
    return {"ok": True, "state": "STARTED", "pid": proc.pid, "message": "Recorder iniciado."}


def stop(grace_s: float = 30.0) -> Dict[str, Any]:
    pid = _pid()
    if not is_running():
        return {"ok": True, "state": "ALREADY_STOPPED", "message": "El recorder ya estaba apagado."}
    RUNTIME.mkdir(parents=True, exist_ok=True)
    STOP_FILE.write_text(str(time.time()), encoding="utf-8")
    deadline = time.time() + grace_s
    while time.time() < deadline:
        if not psutil.pid_exists(pid):
            STOP_FILE.unlink(missing_ok=True)
            return {"ok": True, "state": "STOPPED_CLEANLY", "message": "Recorder apagado y datos guardados."}
        time.sleep(0.5)
    try:  # recorder did not honour the request (e.g. started by an older version): last resort
        psutil.Process(pid).terminate()
    except psutil.Error:
        pass
    STOP_FILE.unlink(missing_ok=True)
    return {"ok": True, "state": "STOPPED_FORCED", "message": "Se apagó a la fuerza (no respondió); puede haberse perdido el último tramo sin guardar."}
