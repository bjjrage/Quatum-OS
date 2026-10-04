import subprocess
import time

from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services import git_save as gs


def _repo(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    (tmp_path / "a.txt").write_text("1")
    return tmp_path


def _wait():
    for _ in range(100):
        s = gs.status()
        if s["state"] != "RUNNING":
            return s
        time.sleep(0.05)
    return gs.status()


def test_commits_only_when_tests_pass(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    monkeypatch.setattr(gs, "ROOT", repo)
    real = gs._run
    monkeypatch.setattr(gs, "_run", lambda cmd, timeout=300: subprocess.CompletedProcess(cmd, 0, "5 passed", "")
                        if "pytest" in cmd else real(cmd, timeout))
    gs.start("test save", push=False)
    s = _wait()
    assert s["state"] == "DONE", s
    log = subprocess.run(["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True).stdout
    assert "test save" in log


def test_failing_tests_block_the_commit(tmp_path, monkeypatch):
    repo = _repo(tmp_path)
    monkeypatch.setattr(gs, "ROOT", repo)
    real = gs._run
    monkeypatch.setattr(gs, "_run", lambda cmd, timeout=300: subprocess.CompletedProcess(cmd, 1, "1 failed", "")
                        if "pytest" in cmd else real(cmd, timeout))
    gs.start("should not commit", push=False)
    s = _wait()
    assert s["state"] == "ERROR"
    log = subprocess.run(["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True)
    assert "should not commit" not in log.stdout


def test_endpoint_is_local_only():
    assert TestClient(app, client=("203.0.113.9", 1)).post("/api/system/git/save").status_code == 403
