"""Backend truth invariants in DEFAULT mode (no QUANT_OS_MOCK_MODE): no fixtures presented as real."""
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _default_mode(monkeypatch):
    monkeypatch.delenv("QUANT_OS_MOCK_MODE", raising=False)


def _j(path):
    r = client.get(path)
    assert r.status_code == 200, path
    return r.json()


def test_default_has_no_fictional_prop_or_100k_capital():
    assert _j("/api/prop/profiles") == []
    assert _j("/api/prop/compliance") == []
    cap = _j("/api/capital-pockets")
    ids = {p["pocket_id"]: p for p in cap["pockets"]}
    assert set(ids) == {"OWN_MAIN"}
    own = ids["OWN_MAIN"]
    assert own["initial_equity_usd"] == own["current_equity_usd"] == 2000.0
    assert own["state_kind"] == "HYPOTHETICAL"
    assert cap["authorized_live_capital_usd"] == 0.0
    assert cap["data_source"] == "CONFIG"
    assert "AlphaFunding" not in str(cap)


def test_default_no_fictional_risk_audit_or_market_rows():
    assert _j("/api/risk/decisions") == []
    risk = _j("/api/risk/status")
    assert risk["recent_decisions"] == []
    assert risk["current_equity_usd"] == 2000.0
    assert risk["data_source"] == "LOCAL_RUNTIME"
    assert _j("/api/audit") == []
    m = _j("/api/markets/tradability")
    assert m["status"] == "NOT_AVAILABLE" and m["markets"] == []

def test_default_paper_is_labelled_simulation_not_own_capital():
    p = _j("/api/paper/account")
    assert p["data_source"] == "PAPER_SIMULATION"
    assert p["is_own_capital"] is False
    assert p["initial_cash_usd"] != 100000.0


def test_default_attribution_not_zero():
    a = _j("/api/attribution")
    assert a["status"] == "NOT_AVAILABLE" and a["net_pnl_usd"] is None


def test_default_system_status_no_hardcoded_metrics_or_stale_sha():
    s = _j("/api/system/status")
    assert s["tests_passing"] is None and s["tests_failing"] is None
    assert s["ci_state"] == "UNKNOWN"
    assert s["failed_gates"] is None
    assert s["data_source"] == "REAL_RUNTIME" and s["mock_mode"] is False
    assert s["live_trading_locked"] is True and s["authorized_live_capital_usd"] == 0.0
    ci = _j("/api/system/ci")
    assert ci["passing_tests"] is None and ci["failing_tests"] is None and ci["status"] == "UNKNOWN"


def test_git_sha_unresolved_is_unknown(tmp_path, monkeypatch):
    from apps.api.services.data_service import QuantOSDataService
    import subprocess

    def boom(*a, **k):
        raise OSError("no git")
    monkeypatch.setattr(subprocess, "run", boom)
    assert QuantOSDataService(root_dir=tmp_path)._get_git_sha() == "UNKNOWN"


def test_str002_never_exceeds_100pct_sizing():
    blob = str(_j("/api/strategies/str002/specialized"))
    assert "120%" not in blob

def test_mock_mode_labels_fixtures(monkeypatch):
    monkeypatch.setenv("QUANT_OS_MOCK_MODE", "1")
    cap = _j("/api/capital-pockets")
    assert cap["data_source"] == "MOCK" and cap["is_fixture"] is True and cap["status"] == "MOCK"
    for prof in _j("/api/prop/profiles"):
        assert prof["data_source"] == "MOCK" and prof["is_fixture"] is True
    assert _j("/api/markets/tradability")["status"] == "MOCK"
