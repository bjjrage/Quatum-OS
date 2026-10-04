import pytest
from src.execution_plane.authority import ExecutionAuthorizationSigner
from src.execution_plane.models import ExecutionMode
from src.risk.engine import RiskDecision


def _permit(qty=10.0, px=0.5):
    s = ExecutionAuthorizationSigner()
    p = s.mint(kind="SUBMIT", venue="paper", mode=ExecutionMode.PAPER, client_order_id="c1",
               intent_id="i1", symbol="BTCUSDT", side="BUY", risk_decision=RiskDecision(approved=True, reason="t"),
               max_quantity=qty, limit_price=px, current_time_ns=1, validity_window_ns=0)
    return s, p


def test_permit_rejects_larger_quantity_than_authorized():
    s, p = _permit()
    with pytest.raises(PermissionError, match="quantity"):
        s.verifier.verify(p, "paper", expected_quantity=1000.0, expected_limit_price=0.5)


def test_permit_rejects_different_price():
    s, p = _permit()
    with pytest.raises(PermissionError, match="price"):
        s.verifier.verify(p, "paper", expected_quantity=10.0, expected_limit_price=0.9)


def test_permit_accepts_exact_and_smaller_quantity():
    s, p = _permit()
    s.verifier.verify(p, "paper", expected_quantity=10.0, expected_limit_price=0.5)
    s2, p2 = _permit()
    s2.verifier.verify(p2, "paper", expected_quantity=4.0, expected_limit_price=0.5)


def test_tampering_with_bound_quantity_breaks_signature():
    import dataclasses
    s, p = _permit()
    forged = object.__new__(type(p))
    for f in dataclasses.fields(p):
        object.__setattr__(forged, f.name, getattr(p, f.name))
    object.__setattr__(forged, "max_quantity", 1e9)
    with pytest.raises(PermissionError, match="signature"):
        s.verifier.verify(forged, "paper", expected_quantity=1e9, expected_limit_price=0.5)


def test_health_is_not_a_constant(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from apps.api.main import app
    r = TestClient(app).get("/api/health").json()
    assert r["status"] in ("HEALTHY", "DEGRADED")
    assert "checks" in r and "recorder" in r["checks"] and "data_dir_writable" in r["checks"]
