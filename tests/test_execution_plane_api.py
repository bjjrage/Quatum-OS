"""Tests for Execution Plane FastAPI endpoints (read-only operational inspection)."""
from fastapi.testclient import TestClient
import pytest

from apps.api.main import app
from src.execution_plane.service import ExecutionPlaneService


@pytest.fixture(autouse=True)
def reset_service():
    ExecutionPlaneService.reset_instance()
    yield
    ExecutionPlaneService.reset_instance()


@pytest.fixture
def client():
    return TestClient(app)


def test_api_execution_status(client):
    res = client.get("/api/execution/status")
    assert res.status_code == 200
    data = res.json()
    assert data["effective_mode"] == "LIVE_LOCKED"
    assert data["live_trading_locked"] is True
    assert data["authorized_live_capital_usd"] == 0.0
    assert data["real_production_orders_sent"] == 0
    assert "safety_invariants" in data
    assert data["safety_invariants"]["risk_veto_override_possible"] is False


def test_api_execution_venues(client):
    res = client.get("/api/execution/venues")
    assert res.status_code == 200
    venues = res.json()
    assert len(venues) == 3
    venue_names = {v["venue"] for v in venues}
    assert venue_names == {"binance_perp", "bybit", "deribit"}
    for v in venues:
        assert v["capabilities"]["live_available"] is False
        assert v["capabilities"]["order_submit"] is False


def test_api_execution_orders_and_fills(client):
    res_orders = client.get("/api/execution/orders")
    assert res_orders.status_code == 200
    assert isinstance(res_orders.json(), list)

    res_fills = client.get("/api/execution/fills")
    assert res_fills.status_code == 200
    assert isinstance(res_fills.json(), list)


def test_api_execution_reconciliation(client):
    res = client.get("/api/execution/reconciliation")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("NOT_CONFIGURED", "UNKNOWN", "HEALTHY", "MISMATCH")
    assert data["live_trading_locked"] is True


def test_api_execution_latency(client):
    res = client.get("/api/execution/latency")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "samples_count" in data


def test_api_execution_credentials_status(client):
    res = client.get("/api/execution/credentials/status")
    assert res.status_code == 200
    data = res.json()
    assert data["withdrawal_permission_required"] is False
    assert data["secrets_exposed"] is False
    # Verify status report contains only variable names, never values
    for v_info in data["venues"].values():
        for env_info in v_info.values():
            assert "api_secret" not in env_info
            assert "client_secret" not in env_info
            assert "secret" not in env_info


def test_api_execution_account_status(client):
    res = client.get("/api/execution/account-status?venue=binance_perp")
    assert res.status_code == 200
    data = res.json()
    assert data["venue"] == "binance_perp"
    assert data["status"] in ("NOT_CONFIGURED", "KNOWN", "UNKNOWN")


def test_api_execution_intents(client):
    res = client.get("/api/execution/intents")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_no_order_submission_endpoints_exist(client):
    # Verify there is NO POST endpoint to submit or place an order
    res_post_order = client.post("/api/execution/order", json={"symbol": "BTCUSDT"})
    assert res_post_order.status_code in (404, 405)

    res_post_submit = client.post("/api/execution/submit", json={"symbol": "BTCUSDT"})
    assert res_post_submit.status_code in (404, 405)

    res_post_orders = client.post("/api/execution/orders", json={"symbol": "BTCUSDT"})
    assert res_post_orders.status_code in (404, 405)
