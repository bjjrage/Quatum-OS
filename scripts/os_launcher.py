"""Single-command, local Quant OS launcher for Windows (with a portable Python fallback)."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "data" / "runtime"
LOG_DIR = RUNTIME / "logs"
STOP_OS = RUNTIME / "STOP_OS"
STOP_RECORDER = RUNTIME / "STOP_RECORDER"
LAUNCHER_PID = RUNTIME / "os_launcher.pid"
API_PID = RUNTIME / "api.pid"
WEB_PID = RUNTIME / "web.pid"
RECORDER_PID = RUNTIME / "recorder_supervisor.pid"
POLY_PID = RUNTIME / "poly_paper.pid"
POLY_SCRIPT = ROOT / "scripts" / "run_poly_updown_paper.py"
API_URL = "http://127.0.0.1:8000"
WEB_URL = "http://127.0.0.1:3000"
IS_WINDOWS = os.name == "nt"
DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) if IS_WINDOWS else 0
CREATE_NEW_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200) if IS_WINDOWS else 0


def _poly_enabled() -> bool:
    """The Polymarket up/down paper is OFF unless config/os_launcher.json says {"poly_paper": true}: the strategy was
    discarded against real trades, and it only burns CPU/network on the recording PC."""
    try:
        return bool(json.loads((ROOT / "config" / "os_launcher.json").read_text(encoding="utf-8")).get("poly_paper", False))
    except (OSError, ValueError):
        return False


def parse_listen_pids(netstat_output: str, port: int) -> set[int]:
    """Extract only LISTENING PIDs for a TCP local port from netstat output."""
    found: set[int] = set()
    for line in netstat_output.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP" or fields[-2].upper() != "LISTENING":
            continue
        local = fields[1]
        if local.rsplit(":", 1)[-1] == str(port) and fields[-1].isdigit():
            found.add(int(fields[-1]))
    return found


def listening_pids(port: int) -> set[int]:
    if IS_WINDOWS:
        result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", check=False)
        if result.returncode:
            raise RuntimeError(f"netstat no pudo inspeccionar el puerto {port}: {result.stderr.strip()}")
        return parse_listen_pids(result.stdout, port)
    # On non-Windows, port binding is enough to avoid a duplicate; PID ownership is not used for stopping.
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return set()
        except OSError:
            return {-1}


def _http(url: str, timeout: float = 2.0) -> Tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": "Quant-OS-launcher/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(2_000_000)


def api_is_quant_os() -> bool:
    try:
        status, body = _http(f"{API_URL}/api/health")
        data = json.loads(body) if status == 200 else {}
        return data.get("system") == "Trading / Quant OS Cockpit API"
    except (OSError, ValueError, TimeoutError):
        return False


def web_is_quant_os() -> bool:
    try:
        status, body = _http(WEB_URL)
        return status == 200 and b"Quant Cockpit v1 | Trading OS" in body
    except (OSError, ValueError, TimeoutError):
        return False


def _health_file(component: str) -> Path:
    return RUNTIME / "health" / f"{component}.json"


def read_health(component: str) -> Dict[str, Any]:
    try:
        value = json.loads(_health_file(component).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def update_health(component: str, status: str, *, pid: Optional[int] = None,
                   error: Optional[str] = None, started: Optional[bool] = None,
                   success: Optional[bool] = None, **extra: Any) -> None:
    from src.common.runtime_health import RuntimeHealth
    kwargs: Dict[str, Any] = dict(extra)
    if pid is not None:
        kwargs["pid"] = pid
    if error:
        kwargs["error"] = RuntimeError(error)
    RuntimeHealth(component, ROOT).update(status,
                                          started=(status == "STARTING") if started is None else started,
                                          success=(status == "RUNNING") if success is None else success,
                                          **kwargs)


def write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(str(pid), encoding="ascii")
    tmp.replace(path)


def process_alive(pid: int) -> bool:
    if IS_WINDOWS:
        try:
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
            kernel32.CloseHandle.restype = wintypes.BOOL
            handle = kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            code = wintypes.DWORD()
            try:
                return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code)) and code.value == 259)
            finally:
                kernel32.CloseHandle(handle)
        except (OSError, ValueError, TypeError):
            return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError, SystemError):
        return False


def process_command_line(pid: int) -> str:
    if not IS_WINDOWS:
        try:
            return Path(f"/proc/{int(pid)}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            return ""
    command = ("$p=Get-CimInstance Win32_Process -Filter 'ProcessId = " + str(int(pid)) + "'; "
               "if ($p) { $p.CommandLine }")
    result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def is_this_launcher(pid: int) -> bool:
    if not process_alive(pid):
        return False
    command = process_command_line(pid).casefold()
    script = Path(__file__).name.casefold()
    return script in command and (" start" in command or "_supervise" in command)


def active_launcher_pid() -> Optional[int]:
    try:
        pid = int(LAUNCHER_PID.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return None
    return pid if is_this_launcher(pid) else None


def _service_command_matches(command: str, kind: str) -> bool:
    value = command.casefold()
    root = str(ROOT).casefold()
    if kind == "api":
        return root in value and "uvicorn apps.api.main:app" in value
    if kind == "web":
        expected = str(ROOT / "apps" / "web" / "node_modules" / "next" / "dist" / "bin" / "next").casefold()
        return expected in value and " dev " in value
    if kind == "recorder":
        expected = str(ROOT / "scripts" / "run_recorder.py").casefold()
        return expected in value
    if kind == "poly_paper":
        return str(POLY_SCRIPT).casefold() in value
    return False


def _owned_orphan_pids() -> Dict[str, int]:
    paths = {"api": API_PID, "web": WEB_PID, "recorder": RECORDER_PID, "poly_paper": POLY_PID}
    found = {}
    for kind, path in paths.items():
        try:
            pid = int(path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            continue
        if process_alive(pid) and _service_command_matches(process_command_line(pid), kind):
            found[kind] = pid
    return found


def _terminate_process_tree(pid: int) -> bool:
    """Stop exactly one verified launcher-owned PID and its children, never a process by name."""
    if not process_alive(pid):
        return True
    if IS_WINDOWS:
        result = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                                text=True, encoding="utf-8", errors="replace", check=False)
        return result.returncode == 0 or not process_alive(pid)
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return False
    return True


def _stop_orphaned_services(timeout_s: float = 90) -> bool:
    owned = _owned_orphan_pids()
    if not owned:
        return False
    print(f"Recuperando procesos huérfanos del launcher anterior: {', '.join(f'{k} PID {v}' for k, v in owned.items())}.")
    recorder_pid = owned.get("recorder")
    if recorder_pid:
        STOP_RECORDER.parent.mkdir(parents=True, exist_ok=True)
        STOP_RECORDER.write_text("launcher_recovery", encoding="ascii")
        deadline = time.monotonic() + timeout_s
        while process_alive(recorder_pid) and time.monotonic() < deadline:
            time.sleep(1)
        if process_alive(recorder_pid):
            print(f"Recorder no cerró en {timeout_s}s; se termina el árbol del PID verificado {recorder_pid}.")
            _terminate_process_tree(recorder_pid)
        update_health("supervisor", "STOPPED")
        RECORDER_PID.unlink(missing_ok=True)
    for kind in ("poly_paper", "web", "api"):
        pid = owned.get(kind)
        if pid and _terminate_process_tree(pid):
            if kind != "poly_paper":  # Its panel reads state.json; it is not in RuntimeHealth.COMPONENTS.
                update_health(kind, "STOPPED", owned_by_launcher=False)
            {"web": WEB_PID, "api": API_PID, "poly_paper": POLY_PID}[kind].unlink(missing_ok=True)
    STOP_RECORDER.unlink(missing_ok=True)
    return True


def _open_log(name: str):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return (LOG_DIR / f"{name}.log").open("ab", buffering=0)


def _spawn(command: list[str], *, cwd: Path, env: Dict[str, str], log_name: str) -> subprocess.Popen:
    handle = _open_log(log_name)
    try:
        proc = subprocess.Popen(command, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                stdout=handle, stderr=subprocess.STDOUT,
                                creationflags=DETACHED | CREATE_NEW_GROUP)
    except Exception:
        handle.close()
        raise
    return proc


def _check_minimum_dependencies() -> None:
    if not (ROOT / "apps" / "web" / "node_modules" / "next" / "dist" / "bin" / "next").exists():
        raise RuntimeError("Faltan dependencias web: ejecutá `cd apps/web && npm ci` una vez.")
    if not __import__("importlib.util").util.find_spec("uvicorn"):
        raise RuntimeError("uvicorn no está instalado en este Python; ejecutá `uv sync` desde la raíz.")
    if not _which("node"):
        raise RuntimeError("No se encontró Node.js en PATH.")


def _which(name: str) -> Optional[str]:
    from shutil import which
    return which(name)


def _new_service(kind: str, env: Dict[str, str]) -> Dict[str, Any]:
    if kind == "api":
        port, path, signature = 8000, API_PID, api_is_quant_os
        command = [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", str(port)]
        cwd, log = ROOT, "api"
    elif kind == "web":
        port, path, signature = 3000, WEB_PID, web_is_quant_os
        next_cli = ROOT / "apps" / "web" / "node_modules" / "next" / "dist" / "bin" / "next"
        command = [_which("node") or "node", str(next_cli), "dev", "-H", "127.0.0.1", "-p", str(port)]
        cwd, log = ROOT / "apps" / "web", "web"
    else:
        raise ValueError(kind)

    pids = listening_pids(port)
    if pids:
        if not signature():
            raise RuntimeError(f"El puerto {port} está ocupado por PID(s) {sorted(pids)} y no responde como este Quant OS; no se terminó ningún proceso.")
        pid = next(iter(sorted(pids)))
        update_health(kind, "RUNNING", pid=pid, owned_by_launcher=False)
        print(f"{kind.upper()}: ya estaba activo en :{port} (PID {pid}); se reutiliza, sin tomar propiedad.", flush=True)
        return {"proc": None, "pid": pid, "owned": False, "port": port, "path": path, "signature": signature}

    proc = _spawn(command, cwd=cwd, env=env, log_name=log)
    write_pid(path, proc.pid)
    update_health(kind, "STARTING", pid=proc.pid, owned_by_launcher=True)
    return {"proc": proc, "pid": proc.pid, "owned": True, "port": port, "path": path, "signature": signature}


def _wait_for(predicate, proc: Optional[subprocess.Popen], timeout_s: float, description: str) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        if proc is not None and proc.poll() is not None:
            break
        time.sleep(1)
    raise RuntimeError(f"{description} no quedó listo dentro de {timeout_s:.0f}s.")


def _stop_owned(proc: Optional[subprocess.Popen], *, timeout_s: float = 15) -> None:
    if proc is None or proc.poll() is not None:
        return
    if IS_WINDOWS:
        _terminate_process_tree(proc.pid)
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        proc.terminate()
        proc.wait(timeout=timeout_s)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        proc.terminate()
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def start(allow_paid_x: bool = False) -> int:
    current = active_launcher_pid()
    if current:
        print(f"Quant OS ya está supervisado por PID {current}; no se inició otra instancia.")
        return show_status()
    try:
        _check_minimum_dependencies()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    _stop_orphaned_services()
    STOP_OS.unlink(missing_ok=True)
    STOP_RECORDER.unlink(missing_ok=True)
    os.environ["QUANT_OS_NO_PAID_X"] = "0" if allow_paid_x else "1"
    return _supervise(allow_paid_x)


def _supervise(allow_paid_x: bool = False) -> int:
    env = os.environ.copy()
    env["QUANT_OS_NO_PAID_X"] = "0" if allow_paid_x else "1"
    api = web = recorder = poly = None
    poly_started_at = 0.0
    services: Dict[str, Dict[str, Any]] = {}
    update_health("os_launcher", "STARTING", started_by="scripts/os_launcher.py")
    write_pid(LAUNCHER_PID, os.getpid())
    try:
        api = _new_service("api", env)
        _wait_for(api["signature"], api["proc"], 60, "FastAPI /api/health")
        if api["proc"] and api["proc"].poll() is not None:
            raise RuntimeError("FastAPI terminó durante el arranque; revisar data/runtime/logs/api.log.")
        services["api"] = api
        update_health("api", "RUNNING", pid=api["pid"], owned_by_launcher=api["owned"])

        web = _new_service("web", env)
        _wait_for(web["signature"], web["proc"], 120, "Next.js frontend")
        if web["proc"] and web["proc"].poll() is not None:
            raise RuntimeError("Next.js terminó durante el arranque; revisar data/runtime/logs/web.log.")
        services["web"] = web
        update_health("web", "RUNNING", pid=web["pid"], owned_by_launcher=web["owned"])

        if listening_pids(8000) and not api_is_quant_os():
            raise RuntimeError("El servicio de API dejó de responder antes de iniciar el recorder.")
        if listening_pids(3000) and not web_is_quant_os():
            raise RuntimeError("El frontend dejó de responder antes de iniciar el recorder.")

        recorder = _spawn([sys.executable, str(ROOT / "scripts" / "run_recorder.py")],
                          cwd=ROOT, env=env, log_name="recorder")
        write_pid(RECORDER_PID, recorder.pid)
        _wait_for(lambda: read_health("supervisor").get("status") in ("RUNNING", "DEGRADED"),
                  recorder, 60, "recorder supervisor")
        if recorder.poll() is not None:
            raise RuntimeError("El recorder supervisor terminó durante el arranque; revisar data/runtime/logs/recorder.log.")
        _wait_for(lambda: read_health("paper_runtime").get("status") in ("RUNNING", "DEGRADED"),
                  recorder, 45, "paper runtime")
        from src.common.runtime_health import runtime_health_snapshot
        pump_paper = runtime_health_snapshot(ROOT)["components"]["pumpfun_paper"]
        warmup_deadline = time.monotonic() + 90
        while pump_paper.get("status") not in ("RUNNING", "DEGRADED", "ERROR", "DISABLED") and \
                recorder.poll() is None and time.monotonic() < warmup_deadline:
            time.sleep(1)
            pump_paper = runtime_health_snapshot(ROOT)["components"]["pumpfun_paper"]
        if POLY_SCRIPT.exists() and _poly_enabled():   # paper en vivo de Polymarket up/down (sin órdenes reales)
            poly = _spawn([sys.executable, str(POLY_SCRIPT)], cwd=ROOT, env=env, log_name="poly_paper")
            poly_started_at = time.monotonic()
            write_pid(POLY_PID, poly.pid)
        update_health("os_launcher", "RUNNING", success=True, api_pid=api["pid"], web_pid=web["pid"],
                      recorder_pid=recorder.pid, poly_paper_pid=poly.pid if poly else None, no_paid_x=not allow_paid_x)
        print(f"OS listo. Web: {WEB_URL} | API: {API_URL}/docs", flush=True)
        print(f"Paper Polymarket up/down: {'corriendo (PID %d)' % poly.pid if poly else 'apagado (config/os_launcher.json)'}", flush=True)
        components = runtime_health_snapshot(ROOT)["components"]
        for name in ("api", "web", "os_launcher", "supervisor", "markets_recorder", "paper_runtime", "pumpfun_recorder", "pumpfun_paper", "leader_paper", "x_watcher"):
            row = components[name]
            print(f"{name}: {row.get('status', 'NEVER_STARTED')}" +
                  (f" (PID {row['pid']})" if row.get("pid") else ""), flush=True)
        print("X: llamadas pagas deshabilitadas por defecto." if not allow_paid_x else "X: habilitado por opción explícita.", flush=True)
        print("Launcher activo en primer plano; usá DETENER_OS.bat para apagarlo ordenadamente.", flush=True)
        while not STOP_OS.exists():
            if api["proc"] is not None and api["proc"].poll() is None and api_is_quant_os():
                update_health("api", "RUNNING", pid=api["pid"], owned_by_launcher=True)
            elif api["proc"] is None and api_is_quant_os():
                update_health("api", "RUNNING", pid=api["pid"], owned_by_launcher=False)
            elif api.get("proc") is not None and api["proc"].poll() is not None:
                update_health("api", "ERROR", error="FastAPI process exited", owned_by_launcher=True)

            if web["proc"] is not None and web["proc"].poll() is None and web_is_quant_os():
                update_health("web", "RUNNING", pid=web["pid"], owned_by_launcher=True)
            elif web["proc"] is None and web_is_quant_os():
                update_health("web", "RUNNING", pid=web["pid"], owned_by_launcher=False)
            elif web.get("proc") is not None and web["proc"].poll() is not None:
                update_health("web", "ERROR", error="Next.js process exited", owned_by_launcher=True)

            if recorder.poll() is not None:
                update_health("supervisor", "ERROR", error="Recorder supervisor process exited")
            if poly is not None and poly.poll() is not None and time.monotonic() - poly_started_at >= 60:
                print(f"Paper Polymarket terminó con código {poly.returncode}; reiniciando.", flush=True)
                poly = _spawn([sys.executable, str(POLY_SCRIPT)], cwd=ROOT, env=env, log_name="poly_paper")
                poly_started_at = time.monotonic()
                write_pid(POLY_PID, poly.pid)
            update_health("os_launcher", "RUNNING", api_pid=api["pid"], web_pid=web["pid"],
                          recorder_pid=recorder.pid, poly_paper_pid=poly.pid if poly else None, no_paid_x=not allow_paid_x)
            time.sleep(5)
        print("Apagado solicitado; esperando cierre ordenado de recorder y workers...", flush=True)
        STOP_RECORDER.write_text("requested_by_os_launcher", encoding="ascii")
        try:
            recorder.wait(timeout=120)
        except subprocess.TimeoutExpired:
            print("Recorder no cerró en 120 s; finalizando el árbol del proceso iniciado por este launcher.", flush=True)
            _stop_owned(recorder, timeout_s=10)
        return 0
    except KeyboardInterrupt:
        print("Interrupción recibida; solicitando cierre ordenado.", flush=True)
        STOP_OS.write_text("keyboard_interrupt", encoding="ascii")
        if recorder is not None and recorder.poll() is None:
            STOP_RECORDER.write_text("requested_by_os_launcher", encoding="ascii")
            try:
                recorder.wait(timeout=120)
            except subprocess.TimeoutExpired:
                _stop_owned(recorder, timeout_s=10)
        return 0
    except Exception as exc:
        update_health("os_launcher", "ERROR", error=f"{type(exc).__name__}: {exc}")
        print(f"OS launcher error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        if recorder is not None and recorder.poll() is None:
            STOP_RECORDER.write_text("startup_failed", encoding="ascii")
            try:
                recorder.wait(timeout=30)
            except subprocess.TimeoutExpired:
                _stop_owned(recorder)
        return 1
    finally:
        if poly is not None:
            _stop_owned(poly)
            POLY_PID.unlink(missing_ok=True)
        if recorder is not None:
            update_health("supervisor", "STOPPED")
            RECORDER_PID.unlink(missing_ok=True)
        for kind, service in (("web", web), ("api", api)):
            if service is None:
                continue
            if service["owned"]:
                _stop_owned(service["proc"])
                update_health(kind, "STOPPED", owned_by_launcher=False)
                service["path"].unlink(missing_ok=True)
            else:
                update_health(kind, "RUNNING", pid=service["pid"], owned_by_launcher=False)
        STOP_RECORDER.unlink(missing_ok=True)
        LAUNCHER_PID.unlink(missing_ok=True)
        update_health("os_launcher", "STOPPED")


def stop(timeout_s: float = 150) -> int:
    pid = active_launcher_pid()
    if pid is None:
        if _stop_orphaned_services():
            print("Procesos huérfanos del launcher anterior apagados tras validar sus PID y comandos.")
            return 0
        print("No hay un supervisor Quant OS activo identificado. No se tocó ningún proceso ni puerto.")
        return 0
    STOP_OS.parent.mkdir(parents=True, exist_ok=True)
    STOP_OS.write_text(f"requested {time.time():.3f}", encoding="ascii")
    print(f"Apagado solicitado al launcher PID {pid}; se detendrán únicamente los procesos que inició.")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not is_this_launcher(pid):
            STOP_OS.unlink(missing_ok=True)
            print("Quant OS apagado ordenadamente.")
            return 0
        time.sleep(1)
    print(f"El launcher PID {pid} sigue activo después de {timeout_s}s; no se terminó ningún proceso por nombre.", file=sys.stderr)
    return 1


def show_status() -> int:
    names = ("api", "web", "os_launcher", "supervisor", "markets_recorder", "paper_runtime",
             "pumpfun_recorder", "pumpfun_paper", "leader_paper", "x_watcher")
    for name in names:
        row = read_health(name)
        status = row.get("status", "NEVER_STARTED")
        pid = row.get("pid")
        print(f"{name}: {status}" + (f" (PID {pid})" if pid else ""))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Start, inspect, or stop the local Quant OS safely.")
    parser.add_argument("action", choices=("start", "stop", "status", "_supervise"))
    parser.add_argument("--allow-paid-x", action="store_true", help="Explicitly allow paid X API calls.")
    args = parser.parse_args()
    if args.action == "start":
        return start(args.allow_paid_x)
    if args.action == "stop":
        return stop()
    if args.action == "status":
        return show_status()
    return _supervise(args.allow_paid_x)


if __name__ == "__main__":
    sys.exit(main())
