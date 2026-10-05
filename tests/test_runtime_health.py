import json
import os
from datetime import datetime, timezone

from src.common.runtime_health import RuntimeHealth, runtime_health_snapshot, sanitize_error


def test_health_persists_minimum_fields_and_sanitizes_secrets(tmp_path):
    h = RuntimeHealth("leader_paper", tmp_path)
    row = h.update("RUNNING", started=True, success=True,
                   error=RuntimeError("Authorization: Bearer abcDEF0123456789SECRET https://host/path?token=secret"))
    saved = json.loads(h.path.read_text())
    assert saved["status"] == "RUNNING"
    assert saved["enabled"] is True
    assert saved["started_at"] and saved["last_heartbeat"] and saved["last_success"]
    assert saved["last_error_type"] == "RuntimeError"
    assert "abcDEF0123456789SECRET" not in json.dumps(saved)
    assert "token=secret" not in json.dumps(saved)
    assert row["last_error_message_sanitized"]


def test_heartbeat_updates_preserve_component_diagnostics(tmp_path):
    health = RuntimeHealth("paper_runtime", tmp_path)
    health.update("DEGRADED", unavailable_accounts={"flujo_v1": "STATE_UNREADABLE"},
                  error=RuntimeError("state cannot be read"))

    refreshed = health.update("DEGRADED", pid=12345)

    assert refreshed["unavailable_accounts"] == {"flujo_v1": "STATE_UNREADABLE"}
    assert refreshed["last_error_type"] == "RuntimeError"


def test_concurrent_runtime_heartbeats_do_not_share_temporary_files(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    health = RuntimeHealth("pumpfun_recorder", tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda _: health.update("RUNNING"), range(40)))

    assert len(rows) == 40
    assert json.loads(health.path.read_text())["status"] == "RUNNING"


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


def test_snapshot_includes_os_services_and_explains_paid_x_disable(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_OS_NO_PAID_X", "1")
    out = runtime_health_snapshot(tmp_path)["components"]
    assert out["api"]["status"] == "NEVER_STARTED"
    assert out["web"]["status"] == "NEVER_STARTED"
    assert out["os_launcher"]["status"] == "NEVER_STARTED"
    assert out["x_watcher"]["status"] == "DISABLED"
    assert out["x_watcher"]["disabled_reason"] == "PAID_CALLS_DISABLED_BY_LAUNCHER"


def test_sanitize_error_strips_authorization_and_query_strings():
    safe = sanitize_error("Authorization: Bearer supersecret123456789 https://x.test/a?api_key=private")
    assert "supersecret123456789" not in safe
    assert "api_key=private" not in safe
