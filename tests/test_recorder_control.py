from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.services import recorder_control as rc

c = TestClient(app)


def test_start_refuses_when_already_running(monkeypatch):
    monkeypatch.setattr(rc, "is_running", lambda: True)
    monkeypatch.setattr(rc, "_pid", lambda: 4242)
    r = c.post("/api/recorder/start").json()
    assert r["state"] == "ALREADY_RUNNING" and r["ok"] is False


def test_stop_when_not_running_is_noop(monkeypatch):
    monkeypatch.setattr(rc, "is_running", lambda: False)
    monkeypatch.setattr(rc, "_supervisor_pid", lambda: 0)
    assert c.post("/api/recorder/stop").json()["state"] == "ALREADY_STOPPED"


def test_stop_uses_supervisor_when_manifest_is_unreadable(monkeypatch, tmp_path):
    monkeypatch.setattr(rc, "RUNTIME", tmp_path)
    monkeypatch.setattr(rc, "STOP_FILE", tmp_path / "STOP_RECORDER")
    monkeypatch.setattr(rc, "is_running", lambda: False)
    monkeypatch.setattr(rc, "_supervisor_pid", lambda: 4242)

    class Supervisor:
        def __init__(self):
            self.checks = 0
            self.terminated = False

        def is_running(self):
            self.checks += 1
            return self.checks == 1

        def terminate(self):
            self.terminated = True

    supervisor = Supervisor()
    monkeypatch.setattr(rc.psutil, "Process", lambda pid: supervisor)
    monkeypatch.setattr(rc.time, "sleep", lambda seconds: None)

    result = rc.stop(grace_s=3.0)

    assert result["state"] == "STOPPED_CLEANLY"
    assert not supervisor.terminated
    assert not rc.STOP_FILE.exists()


def test_non_local_caller_is_rejected():
    r = TestClient(app, client=("203.0.113.9", 1234)).post("/api/recorder/stop")
    assert r.status_code == 403


def test_stop_is_graceful_via_stop_file(monkeypatch, tmp_path):
    monkeypatch.setattr(rc, "RUNTIME", tmp_path)
    monkeypatch.setattr(rc, "STOP_FILE", tmp_path / "STOP_RECORDER")
    alive = {"v": True}
    monkeypatch.setattr(rc, "is_running", lambda: alive["v"])
    monkeypatch.setattr(rc, "_pid", lambda: 999999)
    import psutil
    monkeypatch.setattr(psutil, "pid_exists", lambda pid: (alive["v"] and (rc.STOP_FILE.exists() is False)) or False)
    out = rc.stop(grace_s=3.0)
    assert out["state"] == "STOPPED_CLEANLY"
