import itertools
from types import SimpleNamespace

import pytest

from scripts.os_launcher import parse_listen_pids


def test_parse_netstat_only_returns_listening_pid_for_requested_port():
    sample = """\
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:3000            0.0.0.0:0              LISTENING       1234
  TCP    [::]:8000               [::]:0                 LISTENING       4321
  TCP    127.0.0.1:3000          127.0.0.1:50000        ESTABLISHED     8888
  TCP    0.0.0.0:13000           0.0.0.0:0              LISTENING       9999
"""
    assert parse_listen_pids(sample, 3000) == {1234}
    assert parse_listen_pids(sample, 8000) == {4321}
    assert parse_listen_pids(sample, 5000) == set()


def test_poly_paper_is_a_recognised_owned_service():
    from scripts import os_launcher as L
    cmd = f'"C:\\Python\\python.exe" "{L.POLY_SCRIPT}"'
    assert L._service_command_matches(cmd, "poly_paper")
    assert not L._service_command_matches(cmd, "recorder")
    assert not L._service_command_matches('python other_script.py', "poly_paper")


@pytest.mark.parametrize("poly_exits", [False, True])
def test_poly_paper_start_restart_and_shutdown_use_valid_health_components(tmp_path, monkeypatch, capsys, poly_exits):
    from scripts import os_launcher as L
    from src.common import runtime_health as H

    monkeypatch.setattr(L, "ROOT", tmp_path)
    runtime = tmp_path / "data" / "runtime"
    monkeypatch.setattr(L, "RUNTIME", runtime)
    for name, filename in (("LAUNCHER_PID", "os_launcher.pid"), ("RECORDER_PID", "recorder.pid"),
                           ("POLY_PID", "poly_paper.pid"), ("STOP_OS", "STOP_OS"),
                           ("STOP_RECORDER", "STOP_RECORDER")):
        monkeypatch.setattr(L, name, runtime / filename)
    script = tmp_path / "run_poly_updown_paper.py"
    script.touch()
    monkeypatch.setattr(L, "POLY_SCRIPT", script)
    monkeypatch.setattr(L, "_new_service", lambda kind, env: {
        "proc": None, "pid": 10, "owned": False, "path": runtime / f"{kind}.pid", "signature": lambda: True,
    })
    monkeypatch.setattr(L, "_wait_for", lambda *args: None)
    monkeypatch.setattr(L, "listening_pids", lambda port: set())
    monkeypatch.setattr(L, "api_is_quant_os", lambda: True)
    monkeypatch.setattr(L, "web_is_quant_os", lambda: True)
    monkeypatch.setattr(H, "runtime_health_snapshot", lambda root: {
        "components": {name: {"status": "DISABLED"} for name in H.COMPONENTS},
    })
    clock = itertools.count(step=61)
    monkeypatch.setattr(L.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(L.time, "sleep", lambda seconds: L.STOP_OS.touch())
    spawned = []
    stopped = []

    def spawn(command, **kwargs):
        code = 1 if poly_exits and kwargs["log_name"] == "poly_paper" and len(spawned) == 1 else None
        proc = SimpleNamespace(pid=100 + len(spawned), returncode=code, poll=lambda: code, wait=lambda **kw: 0)
        spawned.append((command, kwargs, proc))
        return proc

    monkeypatch.setattr(L, "_spawn", spawn)
    monkeypatch.setattr(L, "_stop_owned", lambda proc, **kwargs: stopped.append(proc.pid))

    assert L._supervise() == 0
    papers = [(command, kwargs, proc) for command, kwargs, proc in spawned if kwargs["log_name"] == "poly_paper"]
    assert len(papers) == (2 if poly_exits else 1)
    assert all(command == [L.sys.executable, str(script)] for command, _, _ in papers)
    assert papers[-1][2].pid in stopped
    assert not L.POLY_PID.exists() and not L.LAUNCHER_PID.exists()
    health = L.read_health("os_launcher")
    assert health["status"] == "STOPPED" and health["last_error_message_sanitized"] is None
    assert "OS launcher error" not in capsys.readouterr().err


def test_stop_orphaned_poly_paper_does_not_abort_api_cleanup(tmp_path, monkeypatch):
    from scripts import os_launcher as L

    monkeypatch.setattr(L, "ROOT", tmp_path)
    runtime = tmp_path / "data" / "runtime"
    monkeypatch.setattr(L, "RUNTIME", runtime)
    for name, filename in (("POLY_PID", "poly_paper.pid"), ("API_PID", "api.pid"), ("STOP_RECORDER", "STOP_RECORDER")):
        monkeypatch.setattr(L, name, runtime / filename)
    L.write_pid(L.POLY_PID, 101)
    L.write_pid(L.API_PID, 102)
    monkeypatch.setattr(L, "_owned_orphan_pids", lambda: {"poly_paper": 101, "api": 102})
    stopped = []
    monkeypatch.setattr(L, "_terminate_process_tree", lambda pid: stopped.append(pid) or True)

    assert L._stop_orphaned_services() is True
    assert stopped == [101, 102]
    assert not L.POLY_PID.exists() and not L.API_PID.exists()
    assert L.read_health("api")["status"] == "STOPPED"
