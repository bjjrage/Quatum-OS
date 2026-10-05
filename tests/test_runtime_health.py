import json
import os
from datetime import datetime, timezone

from src.common.runtime_health import RuntimeHealth, runtime_health_snapshot, sanitize_error


def test_health_persists_minimum_fields_and_sanitizes_secrets(tmp_path):
    h = RuntimeHealth("leader_paper", tmp_path)
    row = h.update("RUNNING", started=True, success=True,
                   error=RuntimeError("api_key=abcDEF0123456789SECRET https://host/path?token=secret"))
    saved = json.loads(h.path.read_text())
    assert saved["status"] == "RUNNING"
    assert saved["enabled"] is True
    assert saved["started_at"] and saved["last_heartbeat"] and saved["last_success"]
    assert saved["last_error_type"] == "RuntimeError"
    assert "abcDEF0123456789SECRET" not in json.dumps(saved)
    assert "token=secret" not in json.dumps(saved)
    assert row["last_error_message_sanitized"]


def test_snapshot_reports_never_started_disabled_and_dead_process(tmp_path):
    cfg = tmp_path / "config" / "pumpfun.json"
    cfg.parent.mkdir()
    cfg.write_text('{"enabled": false, "x_enabled": false}')
    RuntimeHealth("paper_runtime", tmp_path).update("RUNNING", started=True, pid=99999999)
    out = runtime_health_snapshot(tmp_path)["components"]
    assert out["supervisor"]["status"] == "NEVER_STARTED"
    assert out["pumpfun_recorder"]["status"] == "DISABLED"
    assert out["x_watcher"]["status"] == "DISABLED"
    assert out["paper_runtime"]["status"] == "STOPPED"


def test_sanitize_error_strips_authorization_and_query_strings():
    safe = sanitize_error("Authorization: Bearer supersecret123456789 https://x.test/a?api_key=private")
    assert "supersecret123456789" not in safe
    assert "api_key=private" not in safe
