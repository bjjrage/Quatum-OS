"""PRE-PAPER HARDENING 04 — Test Suite: Operational Truth, Persistence & Auth

Validates:
1. Operational truth:
   - Recorder PID alive != feeds healthy; missing feed telemetry -> UNKNOWN / DEGRADED.
   - Known zero remains zero; unknown value != zero; missing clock measurement != zero drift.
   - Reconciliation without external snapshot -> NOT_RUN/UNKNOWN; mismatch exposed; matching -> RECONCILED.
   - Paper class availability != Paper RUNNING; no paper session -> NOT_STARTED.
   - System alerts do not claim paper active or all feeds healthy without evidence.
   - Missing CI evidence -> UNKNOWN; backend exceptions cannot become HEALTHY.
2. Risk authority and kill switch:
   - Kill switch API reflects authority; survives reload; blocks new execution attempts.
3. Persistence & Concurrency:
   - LocalPersistenceBackend expected_hash detection & limit slicing.
   - SupabasePersistenceBackend deterministic pagination >1000 rows (2505 rows mocked),
     stable ordering, no duplicates, no silent truncation.
   - Supabase write race detection via expected_hash.
4. Auth & Secret Sanitization:
   - Protected mutation rejects unauthenticated requests (401/403).
   - Authorized mutation passes with operator token.
   - SSE stream auth enforcement.
   - Secret scrubbing redacts sensitive keys, tokens, and passwords.
5. Invariants:
   - Authorized live capital is strictly USD 0.
   - Live routing locked.
   - Paper operational state is NOT_STARTED by default.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.auth import OperatorPrincipal, require_operator_auth, verify_stream_auth, scrub_secrets
from apps.api.services.data_service import QuantOSDataService
from src.common.operational_truth import OperationalStatus, safe_metric, is_fresh
from src.persistence.backend import (
    LocalPersistenceBackend,
    PersistenceError,
    ImmutableConflictError,
    payload_hash,
    canonical_json,
)
from src.persistence.supabase_backend import SupabasePersistenceBackend, RestTransport
from src.persistence.config import SupabaseConfig
from src.execution_plane.store import ExecutionKillSwitch
from src.execution_plane.models import OrderIntent
from src.risk.engine import DeterministicRiskEngine, RiskLimits, ProposedOrder, RiskViolationCode


# ------------------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------------------

@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def operator_env(monkeypatch):
    monkeypatch.setenv("QUANT_OS_OPERATOR_TOKEN", "test-operator-secret-12345")
    monkeypatch.setenv("QUANT_OS_STREAM_TOKEN", "test-stream-secret-67890")


# ------------------------------------------------------------------------------
# 1. Operational Truth: Zero vs Null & Status Semantics
# ------------------------------------------------------------------------------

def test_safe_metric_preserves_zero_and_null():
    """Known 0.0 remains 0.0; unknown / None remains None."""
    assert safe_metric(0) == 0
    assert safe_metric(0.0) == 0.0
    assert safe_metric(None) is None
    assert safe_metric(123.45) == 123.45


def test_is_fresh_helper():
    """Freshness verification fails closed on missing or unparseable timestamps."""
    assert is_fresh(None, now_s=1000.0) is False
    assert is_fresh(900.0, now_s=1000.0, max_age_s=200.0) is True
    assert is_fresh(500.0, now_s=1000.0, max_age_s=200.0) is False
    assert is_fresh(-1.0, now_s=1000.0) is False


def test_operational_status_enum_values():
    """OperationalStatus enum encapsulates non-binary truth values."""
    assert OperationalStatus.UNKNOWN.value == "UNKNOWN"
    assert OperationalStatus.NOT_STARTED.value == "NOT_STARTED"
    assert OperationalStatus.NOT_RUN.value == "NOT_RUN"
    assert OperationalStatus.NOT_CONFIGURED.value == "NOT_CONFIGURED"
    assert OperationalStatus.MISMATCH.value == "MISMATCH"
    assert OperationalStatus.RECONCILED.value == "RECONCILED"


# ------------------------------------------------------------------------------
# 2. Recorder Operational Truth: PID Alive != Feeds Healthy
# ------------------------------------------------------------------------------

def test_recorder_pid_alive_does_not_mean_feeds_healthy():
    """When recorder PID is active but no manifest or feed telemetry exists,
    feed health must NOT falsely report HEALTHY or 0.0ms clock drift."""
    service = QuantOSDataService()

    # Simulate running process but empty manifest data
    mock_manifest = {
        "run_id": "test_run_1",
        "git_sha": "abc1234",
        "pid": 99999,
        "started_at_timestamp_ns": 1700000000000000000,
    }

    from unittest.mock import mock_open
    with patch.object(service, "_load_latest_quality_report", return_value=None), \
         patch("psutil.pid_exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(mock_manifest))), \
         patch("pathlib.Path.exists", return_value=True):
        status = service.get_recorder_status()

        assert status["is_process_alive"] is True
        assert status["all_feeds_healthy"] is False or status["all_feeds_healthy"] is None
        # Binance has no clock measurement in quality report -> must be None, NOT 0.0
        binance_v = status["venues"].get("binance_perp")
        assert binance_v is not None
        assert binance_v["clock_skew_ms"] is None
        assert binance_v["manifest_health"] == "UNVERIFIED"

        # Required feeds that have no parquet data must be UNKNOWN
        req_feeds = status.get("required_feeds", {})
        assert "binance_perp/trade_ticks" in req_feeds
        assert req_feeds["binance_perp/trade_ticks"]["status"] == "UNKNOWN"


def test_recorder_missing_manifest_fails_closed():
    """When manifest cannot be read, status fails closed to STOPPED/UNKNOWN with no fake data."""
    service = QuantOSDataService()
    with patch("pathlib.Path.exists", return_value=False):
        status = service.get_recorder_status()
        assert status["status"] == "STOPPED"
        assert status["venues"] == {}


# ------------------------------------------------------------------------------
# 3. Paper Trading Truth: Class Availability != Paper RUNNING
# ------------------------------------------------------------------------------

def test_paper_account_not_started_by_default(monkeypatch):
    """When no paper session is active, paper account returns NOT_STARTED with null equity/pnl."""
    monkeypatch.delenv("QUANT_OS_MOCK_MODE", raising=False)
    service = QuantOSDataService()
    account = service.get_paper_account()

    assert account["status"] == "NOT_STARTED"
    assert account["operational_state"] == "NOT_STARTED"
    assert account["initial_cash_usd"] is None
    assert account["cash_usd"] is None
    assert account["equity_usd"] is None
    assert account["realized_pnl_usd"] is None
    assert account["unrealized_pnl_usd"] is None
    assert account["positions"] == []
    assert account["orders"] == []
    assert account["fills"] == []


def test_system_status_alerts_truthful_when_not_started(monkeypatch):
    """System status alerts do not claim paper is actively running or all feeds healthy."""
    monkeypatch.delenv("QUANT_OS_MOCK_MODE", raising=False)
    service = QuantOSDataService()
    sys_status = service.get_system_status()

    assert sys_status["paper_pnl_usd"] is None
    assert any("NOT_STARTED" in alert["message"] for alert in sys_status["system_alerts"])


def test_paper_account_running_when_session_activated():
    """Activating paper session sets status to RUNNING and populates initial cash."""
    service = QuantOSDataService()
    service.paper_session_active = True
    account = service.get_paper_account()

    assert account["status"] in ("RUNNING", "MOCK")
    assert account["cash_usd"] == service.paper_broker.cash_usd
    assert account["equity_usd"] == service.paper_broker.cash_usd


# ------------------------------------------------------------------------------
# 4. Execution Reconciliation Truth
# ------------------------------------------------------------------------------

def test_execution_reconciliation_not_run_by_default():
    """Execution state honestly exposes reconciliation status as NOT_RUN without external feed."""
    service = QuantOSDataService()
    exec_state = service.get_execution_state()

    assert exec_state["reconciliation_status"] == "NOT_RUN"
    assert exec_state["mismatch_detected"] is None
    assert exec_state["drift_usd"] is None


def test_execution_reconciliation_reports_mismatch():
    """When external reconciliation reports mismatch, API accurately propagates it."""
    from src.execution_plane.service import ExecutionPlaneService
    ep_instance = MagicMock()
    ep_instance.get_reconciliation.return_value = {
        "status": "MISMATCH",
        "reconciliation_events_count": 5,
        "latest_event": "drift detected",
    }

    with patch.object(ExecutionPlaneService, "get_instance", return_value=ep_instance):
        service = QuantOSDataService()
        exec_state = service.get_execution_state()
        assert exec_state["reconciliation_status"] == "MISMATCH"
        assert exec_state["mismatch_detected"] is True
        assert exec_state["drift_usd"] is None


# ------------------------------------------------------------------------------
# 5. Persistent Kill Switch Authority & Execution Block
# ------------------------------------------------------------------------------

def test_kill_switch_api_requires_auth(api_client, operator_env):
    """Unauthenticated kill switch mutation is rejected with 401."""
    res = api_client.post("/api/risk/kill-switch/activate", json={"reason": "test emergency"})
    assert res.status_code == 401


def test_kill_switch_api_rejects_invalid_token(api_client, operator_env):
    """Kill switch mutation with invalid token is rejected with 403."""
    res = api_client.post(
        "/api/risk/kill-switch/activate",
        headers={"Authorization": "Bearer wrong-token"},
        json={"reason": "test emergency"}
    )
    assert res.status_code == 403


def test_kill_switch_activation_and_execution_blocking(api_client, operator_env, tmp_path):
    """Activating kill switch updates authority, persists state, blocks execution, and resets cleanly."""
    db_file = tmp_path / "control_plane_test.db"
    backend = LocalPersistenceBackend(db_path=str(db_file))
    ks = ExecutionKillSwitch(backend=backend)

    # Initialize risk engine and link kill switch
    risk_limits = RiskLimits(max_drawdown_limit_pct=0.10, max_gross_leverage=3.0, live_capital_locked=False)
    risk_engine = DeterministicRiskEngine(initial_equity_usd=10000.0, limits=risk_limits)

    service = QuantOSDataService()
    service.execution_kill_switch = ks
    service.risk_engine = risk_engine

    order = ProposedOrder(
        order_id="test_ord_1",
        strategy_id="STR-002",
        symbol="BTC/USDT",
        side="BUY",
        quantity=0.01,
        price=50000.0,
        venue="binance",
    )

    # Before activation: can evaluate and approve order
    decision_before = risk_engine.evaluate_order(order, is_live=False)
    assert decision_before.approved is True

    # Activate GLOBAL kill switch
    service.activate_kill_switch(scope="GLOBAL", actor="TEST_OP", reason="Risk limit breach")
    assert service.risk_engine.kill_switch_active is True

    # After activation: execution MUST fail closed with KILL_SWITCH_ACTIVE
    decision_after = risk_engine.evaluate_order(order, is_live=False)
    assert decision_after.approved is False
    assert decision_after.violation_code == RiskViolationCode.KILL_SWITCH_ACTIVE

    # Risk status API reflects active global kill switch
    status = service.get_risk_status()
    assert status["kill_switch_active"] is True
    assert status["kill_switches"]["GLOBAL"]["active"] is True

    # Verify persistence: reload fresh instance from the same DB
    reloaded_ks = ExecutionKillSwitch(backend=backend)
    assert "GLOBAL" in reloaded_ks.active_scopes()

    # Reset kill switch
    service.reset_kill_switch(scope="GLOBAL", actor="TEST_OP", reason="Operator cleared")
    assert service.risk_engine.kill_switch_active is False
    assert "GLOBAL" not in service.execution_kill_switch.active_scopes()


def test_kill_switch_api_endpoints_end_to_end(api_client, operator_env):
    """End-to-end API activation and reset with valid operator token."""
    headers = {"Authorization": "Bearer test-operator-secret-12345"}

    # Activate via API
    res = api_client.post(
        "/api/risk/kill-switch/activate",
        headers=headers,
        json={"scope": "GLOBAL", "reason": "Operator initiated test"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["kill_switch_active"] is True

    # Check status endpoint
    status_res = api_client.get("/api/risk/status")
    assert status_res.status_code == 200
    assert status_res.json()["kill_switch_active"] is True

    # Reset via API
    reset_res = api_client.post(
        "/api/risk/kill-switch/reset",
        headers=headers,
        json={"scope": "GLOBAL", "reason": "Test cleared"}
    )
    assert reset_res.status_code == 200
    reset_data = reset_res.json()
    assert reset_data["kill_switch_active"] is False


# ------------------------------------------------------------------------------
# 6. LocalPersistenceBackend: Expected Hash Detection & Limit
# ------------------------------------------------------------------------------

def test_local_persistence_expected_hash_concurrency(tmp_path):
    """LocalPersistenceBackend put rejects write if expected_hash mismatches existing record."""
    db_file = tmp_path / "test_concurrency.db"
    backend = LocalPersistenceBackend(db_path=str(db_file))

    # Initial put on mutable table 'event_clusters'
    record1 = {"cluster_id": "c1", "description": "initial_value"}
    backend.put("event_clusters", "c1", record1)
    hash1 = payload_hash(record1)

    # Update with matching expected_hash succeeds
    record2 = {"cluster_id": "c1", "description": "updated_value"}
    res = backend.put("event_clusters", "c1", record2, expected_hash=hash1)
    assert res == "UPDATED"
    hash2 = payload_hash(record2)
    assert hash2 != hash1

    # Update with stale / mismatched expected_hash MUST raise PersistenceError
    record3 = {"cluster_id": "c1", "description": "stale_write"}
    with pytest.raises(PersistenceError, match="Lost update detected"):
        backend.put("event_clusters", "c1", record3, expected_hash="stale_hash_value")


def test_local_persistence_list_limit(tmp_path):
    """LocalPersistenceBackend list respects limit argument without error."""
    db_file = tmp_path / "test_limit.db"
    backend = LocalPersistenceBackend(db_path=str(db_file))

    for i in range(10):
        backend.put("event_clusters", f"c_{i:02d}", {"cluster_id": f"c_{i:02d}", "description": f"desc_{i}"})

    all_rows = backend.list("event_clusters")
    assert len(all_rows) == 10

    limited_rows = backend.list("event_clusters", limit=4)
    assert len(limited_rows) == 4


# ------------------------------------------------------------------------------
# 7. Supabase Persistence Backend: Pagination >1000 Rows & Concurrency
# ------------------------------------------------------------------------------

class MockPaginatedTransport(RestTransport):
    """Mock RestTransport for testing pagination across 2505 rows."""
    def __init__(self, all_rows):
        self.all_rows = all_rows
        self.call_count = 0

    def request(self, method, path, params=None, json_body=None, headers=None):
        self.call_count += 1
        params = params or {}
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", 1000))
        slice_rows = self.all_rows[offset : offset + limit]
        body = [{"payload": r} for r in slice_rows]
        return (200, body)


def test_supabase_pagination_over_1000_rows_deterministic():
    """Deterministic pagination loops over pages without silent 1000-row truncation."""
    total_mock_rows = 2505
    all_mock_data = [{"cluster_id": f"row_{i:05d}", "description": f"data_{i}"} for i in range(total_mock_rows)]

    transport = MockPaginatedTransport(all_mock_data)
    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=transport
    )

    results = backend.list("event_clusters", page_size=1000)

    # Must return all 2505 rows without silent truncation
    assert len(results) == 2505
    assert results[0]["cluster_id"] == "row_00000"
    assert results[-1]["cluster_id"] == f"row_{total_mock_rows - 1:05d}"

    # Verify no duplicates
    unique_ids = {r["cluster_id"] for r in results}
    assert len(unique_ids) == 2505

    # Exactly 3 page fetches: offset 0 (1000), offset 1000 (1000), offset 2000 (505)
    assert transport.call_count == 3


def test_supabase_patch_cas_request_shape():
    """1. Exact PostgREST PATCH CAS request shape (method=PATCH, path, params with pk & data_hash, Prefer header)."""
    captured = []

    class CapturingTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            captured.append({
                "method": method,
                "path": path,
                "params": params,
                "json_body": json_body,
                "headers": headers,
            })
            return (200, [{"cluster_id": "c1", "data_hash": "new_hash_123"}])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=CapturingTransport(),
    )

    data = {"cluster_id": "c1", "name": "cluster_one", "events": [1, 2]}
    res = backend.put("event_clusters", "c1", data, expected_hash="old_hash_000")

    assert res == "UPDATED"
    assert len(captured) == 1
    req = captured[0]
    assert req["method"] == "PATCH"
    assert req["path"] == "/rest/v1/event_clusters"
    assert req["params"] == {"cluster_id": "eq.c1", "data_hash": "eq.old_hash_000"}
    assert req["headers"] == {"Prefer": "return=representation"}
    assert req["json_body"]["cluster_id"] == "c1"
    assert req["json_body"]["payload"] == data
    assert req["json_body"]["data_hash"] == payload_hash(data)


def test_supabase_patch_cas_success():
    """2. Successful CAS: PostgREST returns 1 row representation -> UPDATED."""
    class SuccessTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            return (200, [{"cluster_id": "c1", "payload": json_body["payload"], "data_hash": json_body["data_hash"]}])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=SuccessTransport(),
    )

    res = backend.put("event_clusters", "c1", {"cluster_id": "c1", "v": 2}, expected_hash="h1")
    assert res == "UPDATED"


def test_supabase_patch_cas_zero_rows_conflict():
    """3. Zero-row CAS conflict: 0 rows modified -> raises PersistenceError('CAS_CONFLICT')."""
    class ConflictTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            # PostgREST returns [] when no row matches the filter (e.g. data_hash mismatch)
            return (200, [])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=ConflictTransport(),
    )

    with pytest.raises(PersistenceError, match="CAS_CONFLICT"):
        backend.put("event_clusters", "c1", {"cluster_id": "c1", "v": 2}, expected_hash="wrong_hash")


def test_supabase_patch_cas_no_get_before_patch():
    """4. Zero GET before PATCH: exactly 1 call to transport."""
    calls = []

    class CountingTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            calls.append(method)
            return (200, [{"cluster_id": "c1"}])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=CountingTransport(),
    )

    backend.put("event_clusters", "c1", {"cluster_id": "c1"}, expected_hash="h0")
    assert calls == ["PATCH"]
    assert len(calls) == 1


def test_supabase_patch_cas_updates_projections_atomically():
    """5. Indexed materialized projections updated atomically with payload."""
    sent_payload = None

    class CaptureBodyTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            nonlocal sent_payload
            sent_payload = json_body
            return (200, [json_body])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=CaptureBodyTransport(),
    )

    order_data = {
        "intent_id": "int_100",
        "client_order_id": "cl_100",
        "venue_order_id": "v_ord_100",
        "venue": "BINANCE",
        "symbol": "BTC-USD",
        "state": "FILLED",
        "idempotency_key": "idem_100",
        "custom_meta": "extra",
    }
    backend.put("execution_orders", "int_100", order_data, expected_hash="h_prev")

    assert sent_payload is not None
    assert sent_payload["intent_id"] == "int_100"
    assert sent_payload["client_order_id"] == "cl_100"
    assert sent_payload["venue_order_id"] == "v_ord_100"
    assert sent_payload["venue"] == "BINANCE"
    assert sent_payload["symbol"] == "BTC-USD"
    assert sent_payload["state"] == "FILLED"
    assert sent_payload["idempotency_key"] == "idem_100"
    assert sent_payload["payload"] == order_data
    assert sent_payload["data_hash"] == payload_hash(order_data)


def test_supabase_patch_cas_null_hash_fails_closed():
    """6. NULL hash fails closed: when data_hash is NULL in DB, PATCH with expected_hash returns 0 rows -> CAS_CONFLICT."""
    class NullHashTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            return (200, [])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=NullHashTransport(),
    )

    with pytest.raises(PersistenceError, match="CAS_CONFLICT"):
        backend.put("event_clusters", "c1", {"cluster_id": "c1", "val": 99}, expected_hash="any_hash")


def test_supabase_patch_cas_two_writers_race():
    """7. Two writers race: exactly one gets 1 row and succeeds; second gets 0 rows and raises CAS_CONFLICT."""
    import threading

    class AtomicDbServer:
        def __init__(self):
            self.lock = threading.Lock()
            self.current_hash = "initial_hash_h0"
            self.rows = {"c1": {"cluster_id": "c1", "val": 0, "data_hash": "initial_hash_h0"}}

        def patch(self, pk_val, expected_hash, json_body):
            with self.lock:
                row = self.rows.get(pk_val)
                if row is None or row.get("data_hash") != expected_hash:
                    return (200, [])
                row.update(json_body)
                return (200, [dict(row)])

    server = AtomicDbServer()

    class AtomicTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            if method == "PATCH":
                pk_val = params["cluster_id"].split("eq.")[1]
                expected_hash = params["data_hash"].split("eq.")[1]
                return server.patch(pk_val, expected_hash, json_body)
            return (200, [])

    backend_a = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=AtomicTransport(),
    )
    backend_b = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=AtomicTransport(),
    )

    results = {}
    errors = {}

    def writer_a():
        try:
            res = backend_a.put(
                "event_clusters", "c1",
                {"cluster_id": "c1", "val": 1},
                expected_hash="initial_hash_h0",
            )
            results["A"] = res
        except Exception as e:
            errors["A"] = e

    def writer_b():
        try:
            res = backend_b.put(
                "event_clusters", "c1",
                {"cluster_id": "c1", "val": 2},
                expected_hash="initial_hash_h0",
            )
            results["B"] = res
        except Exception as e:
            errors["B"] = e

    t_a = threading.Thread(target=writer_a)
    t_b = threading.Thread(target=writer_b)
    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()

    # Exactly one writer succeeded and the other got CAS_CONFLICT
    assert ("A" in results and "B" in errors) or ("B" in results and "A" in errors)
    if "A" in results:
        assert results["A"] == "UPDATED"
        assert isinstance(errors["B"], PersistenceError)
        assert "CAS_CONFLICT" in str(errors["B"])
    else:
        assert results["B"] == "UPDATED"
        assert isinstance(errors["A"], PersistenceError)
        assert "CAS_CONFLICT" in str(errors["A"])


def test_supabase_insert_collision_on_mutable_table_raises():
    """8. Insert collision on mutable table with different payload raises INSERT_COLLISION."""
    class CollisionTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            if method == "POST":
                return (409, {"message": "duplicate key value violates unique constraint"})
            if method == "GET":
                existing = {"cluster_id": "c1", "payload": {"cluster_id": "c1", "val": "old_data"}}
                return (200, [existing])
            return (200, [])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=CollisionTransport(),
    )

    with pytest.raises(PersistenceError, match="INSERT_COLLISION"):
        backend.put("event_clusters", "c1", {"cluster_id": "c1", "val": "new_data"})


def test_supabase_immutable_table_rejects_cas_and_overwrite():
    """9. Immutable table CAS or overwrite blocked (ImmutableConflictError)."""
    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=MagicMock(),
    )
    with pytest.raises(ImmutableConflictError, match="append-only; CAS mutation forbidden"):
        backend.put("execution_intents", "intent_1", {"intent_id": "intent_1"}, expected_hash="any_hash")

    class ImmutableConflictTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            if method == "POST":
                return (409, {"message": "duplicate key value violates unique constraint"})
            if method == "GET":
                return (200, [{"intent_id": "intent_1", "payload": {"intent_id": "intent_1", "data": "original"}}])
            return (200, [])

    backend_conflict = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=ImmutableConflictTransport(),
    )
    with pytest.raises(ImmutableConflictError, match="is append-only with a different payload"):
        backend_conflict.put("execution_intents", "intent_1", {"intent_id": "intent_1", "data": "tampered"})


def test_backfill_hash_equals_python_payload_hash():
    """10. Backfill hash equals Python payload_hash(payload)."""
    from scripts.backfill_supabase_data_hash import backfill_data_hashes

    patched_rows = []

    class MockTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            if method == "GET":
                if path == "/rest/v1/event_clusters":
                    return (200, [{"cluster_id": "c1", "payload": {"cluster_id": "c1", "foo": "bar"}, "data_hash": None}])
                return (200, [])
            if method == "PATCH":
                patched_rows.append((path, params, json_body))
                return (200, [json_body])
            return (200, [])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=MockTransport(),
    )

    report = backfill_data_hashes(backend)
    assert report["hashes_backfilled"] >= 1
    assert len(patched_rows) >= 1
    path, params, body = patched_rows[0]
    expected_hash = payload_hash({"cluster_id": "c1", "foo": "bar"})
    assert body["data_hash"] == expected_hash


def test_backfill_mismatch_on_corrupted_existing_hash_stops():
    """11. Backfill mismatch on corrupted existing hash stops immediately (INTEGRITY_FAILURE)."""
    from scripts.backfill_supabase_data_hash import backfill_data_hashes

    class CorruptTransport(RestTransport):
        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            if method == "GET" and path == "/rest/v1/event_clusters":
                return (200, [{"cluster_id": "c1", "payload": {"cluster_id": "c1"}, "data_hash": "corrupted_hash_xyz"}])
            return (200, [])

    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=CorruptTransport(),
    )

    with pytest.raises(PersistenceError, match="INTEGRITY_FAILURE"):
        backfill_data_hashes(backend)


def test_backfill_is_idempotent():
    """12. Backfill is idempotent (second run produces 0 modifications)."""
    from scripts.backfill_supabase_data_hash import backfill_data_hashes

    row_data = {"cluster_id": "c1"}
    h = payload_hash(row_data)

    class ValidTransport(RestTransport):
        def __init__(self):
            self.patch_called = False

        def request(self, method, path, params=None, json_body=None, headers=None, raw_body=None):
            if method == "GET":
                if path == "/rest/v1/event_clusters":
                    return (200, [{"cluster_id": "c1", "payload": row_data, "data_hash": h}])
                return (200, [])
            if method == "PATCH":
                self.patch_called = True
                return (200, [json_body])
            return (200, [])

    transport = ValidTransport()
    backend = SupabasePersistenceBackend(
        config=SupabaseConfig(url="https://test.supabase.co", anon_key="test_anon", service_role_key="test_svc"),
        transport=transport,
    )

    report = backfill_data_hashes(backend)
    assert report["hashes_backfilled"] == 0
    assert report["already_valid"] >= 1
    assert transport.patch_called is False



# ------------------------------------------------------------------------------
# 8. Auth & Secret Hygiene
# ------------------------------------------------------------------------------

def test_require_operator_auth_unconfigured_fails_closed(monkeypatch):
    """When operator auth is unconfigured, require_operator_auth raises 503 AUTH_NOT_CONFIGURED."""
    monkeypatch.delenv("QUANT_OS_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("QUANT_OS_API_KEY", raising=False)
    monkeypatch.delenv("QUANT_OS_TEST_AUTH_OVERRIDE", raising=False)
    with pytest.raises(HTTPException) as excinfo:
        require_operator_auth()
    assert excinfo.value.status_code == 503
    assert "AUTH_NOT_CONFIGURED" in excinfo.value.detail


def test_require_operator_auth_rejects_empty(operator_env):
    """When operator auth is configured, empty credentials returns 401."""
    with pytest.raises(HTTPException) as excinfo:
        require_operator_auth()
    assert excinfo.value.status_code == 401


def test_require_operator_auth_rejects_invalid_token(operator_env):
    """When operator auth is configured, mismatched token returns 403."""
    with pytest.raises(HTTPException) as excinfo:
        require_operator_auth(authorization="Bearer incorrect-token")
    assert excinfo.value.status_code == 403


def test_require_operator_auth_valid(operator_env):
    """require_operator_auth returns OperatorPrincipal without leaking raw token."""
    # Bearer header
    user1 = require_operator_auth(authorization="Bearer test-operator-secret-12345")
    assert isinstance(user1, OperatorPrincipal)
    assert user1.auth_method == "bearer"
    assert len(user1.principal_id) == 12
    assert "test-operator-secret-12345" not in user1.principal_id
    assert "test-operator-secret-12345" not in str(user1)

    # X-API-Key header
    user2 = require_operator_auth(x_api_key="test-operator-secret-12345")
    assert isinstance(user2, OperatorPrincipal)
    assert user2.auth_method == "api_key"
    assert user2.principal_id == user1.principal_id


def test_verify_stream_auth_unconfigured_fails_closed(monkeypatch):
    """When stream auth is unconfigured, verify_stream_auth raises 503 STREAM_AUTH_NOT_CONFIGURED."""
    monkeypatch.delenv("QUANT_OS_STREAM_TOKEN", raising=False)
    monkeypatch.delenv("QUANT_OS_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("QUANT_OS_API_KEY", raising=False)
    monkeypatch.delenv("QUANT_OS_TEST_AUTH_OVERRIDE", raising=False)
    with pytest.raises(HTTPException) as excinfo:
        verify_stream_auth()
    assert excinfo.value.status_code == 503
    assert "STREAM_AUTH_NOT_CONFIGURED" in excinfo.value.detail


def test_verify_stream_auth_enforcement(monkeypatch):
    """Stream auth rejects unauthenticated connections when token is configured."""
    monkeypatch.setenv("QUANT_OS_OPERATOR_TOKEN", "stream-secret-999")
    with pytest.raises(HTTPException) as excinfo:
        verify_stream_auth()
    assert excinfo.value.status_code == 401

    with pytest.raises(HTTPException) as excinfo:
        verify_stream_auth(token="wrong-token")
    assert excinfo.value.status_code == 401

    # Valid token succeeds
    res = verify_stream_auth(token="stream-secret-999")
    assert res is True


def test_scrub_secrets_redacts_sensitive_fields():
    """scrub_secrets sanitizes sensitive keys and bearer token values."""
    raw_payload = {
        "user": "operator",
        "api_key": "my_secret_key_123",
        "password": "super_secret_password",
        "deep": {
            "token": "bearer_jwt_token_here",
            "safe_field": 42.0,
            "private_key": "-----BEGIN PRIVATE KEY-----",
        },
        "list_items": [
            {"secret_value": "pass123"},
            "Bearer sensitive-token-string",
            "normal string"
        ]
    }

    scrubbed = scrub_secrets(raw_payload)

    assert scrubbed["api_key"] == "[REDACTED]"
    assert scrubbed["password"] == "[REDACTED]"
    assert scrubbed["deep"]["token"] == "[REDACTED]"
    assert scrubbed["deep"]["private_key"] == "[REDACTED]"
    assert scrubbed["deep"]["safe_field"] == 42.0
    assert scrubbed["list_items"][0]["secret_value"] == "[REDACTED]"
    assert "[REDACTED]" in scrubbed["list_items"][1]
    assert scrubbed["list_items"][2] == "normal string"


# ------------------------------------------------------------------------------
# 9. Global Invariants: Capital, Routing, and Authority Verification
# ------------------------------------------------------------------------------

def test_global_invariants_strictly_maintained(api_client):
    """Verify global invariants: $0 live capital, live routing locked."""
    res = api_client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["authorized_live_capital_usd"] == 0.0
    assert data["live_trading_locked"] is True

    risk_res = api_client.get("/api/risk/status")
    assert risk_res.status_code == 200
    risk_data = risk_res.json()
    assert risk_data["authorized_live_capital_usd"] == 0.0
    assert risk_data["live_capital_state"] == "CAPITAL_LOCKED"


def test_reconciliation_real_matching_reconciled():
    """When external reconciliation reports HEALTHY matching, API reports RECONCILED/HEALTHY."""
    from src.execution_plane.service import ExecutionPlaneService
    ep_instance = MagicMock()
    ep_instance.get_reconciliation.return_value = {
        "status": "HEALTHY",
        "reconciliation_events_count": 10,
        "latest_event": "all balances and positions match broker snapshot",
    }

    with patch.object(ExecutionPlaneService, "get_instance", return_value=ep_instance):
        service = QuantOSDataService()
        exec_state = service.get_execution_state()
        assert exec_state["reconciliation_status"] == "HEALTHY"
        assert exec_state["mismatch_detected"] is False
        assert exec_state["drift_usd"] == 0.0


def test_system_status_missing_ci_evidence_is_unknown():
    """Missing CI evidence must be UNKNOWN and tests_passing None."""
    service = QuantOSDataService()
    sys_status = service.get_system_status()
    assert sys_status["ci_state"] == "UNKNOWN"
    assert sys_status["tests_passing"] is None
    assert sys_status["tests_failing"] is None


def test_data_service_exception_fails_closed_never_healthy():
    """Backend exception in get_recorder_status fails closed with ERROR, never false HEALTHY."""
    service = QuantOSDataService()
    with patch("pathlib.Path.exists", side_effect=RuntimeError("Disk failure")):
        status = service.get_recorder_status()
        assert status["status"] in ("STOPPED", "ERROR")
        assert status.get("is_process_alive") is not True


def test_scoped_kill_switches_venue_symbol_strategy(tmp_path):
    """Scoped kill switches for VENUE, SYMBOL, and STRATEGY correctly block targeted intents."""
    db_file = tmp_path / "control_plane_scoped_test.db"
    backend = LocalPersistenceBackend(db_path=str(db_file))
    ks = ExecutionKillSwitch(backend=backend)

    # Activate VENUE kill switch for 'deribit'
    ks.activate(scope="VENUE", actor="OPERATOR", reason="Deribit API degrade", target="deribit")
    # Activate SYMBOL kill switch for 'ETH/USDT'
    ks.activate(scope="SYMBOL", actor="OPERATOR", reason="ETH extreme volatility", target="ETH/USDT")
    # Activate STRATEGY kill switch for 'STR-003'
    ks.activate(scope="STRATEGY", actor="OPERATOR", reason="STR-003 decommissioned", target="STR-003")

    scopes = ks.active_scopes()
    assert "VENUE:deribit" in scopes
    assert "SYMBOL:ETH/USDT" in scopes
    assert "STRATEGY:STR-003" in scopes

    # Check blocking
    def _intent(venue, symbol, strategy_id):
        return OrderIntent(
            intent_id="i1",
            client_order_id="c1",
            strategy_id=strategy_id,
            strategy_version="1",
            venue=venue,
            symbol=symbol,
            side="BUY",
            order_type="LIMIT",
            quantity=0.1,
            limit_price=50000.0,
            capital_pocket_id="OWN_MAIN",
            idempotency_key="k1",
            market_data_timestamp_ns=1000,
            decision_timestamp_ns=1000,
            max_signal_age_ms=5000.0,
            created_at_ns=1000,
        )

    assert ks.blocking(_intent("binance", "BTC/USDT", "STR-002")) is None
    assert ks.blocking(_intent("deribit", "BTC/USDT", "STR-002")) == "VENUE:deribit"
    assert ks.blocking(_intent("binance", "ETH/USDT", "STR-002")) == "SYMBOL:ETH/USDT"
    assert ks.blocking(_intent("binance", "SOL/USDT", "STR-003")) == "STRATEGY:STR-003"


def test_stream_endpoint_rejects_unauthorized_token(api_client, operator_env):
    """EventSource SSE stream endpoint rejects connection without valid token when auth is required."""
    res = api_client.get("/api/stream/events?token=invalid_token")
    assert res.status_code == 401


def test_known_zero_drift_vs_unmeasured():
    """Known zero clock drift (0.0ms measured) is strictly distinct from missing measurement (None)."""
    service = QuantOSDataService()
    report_with_zero = {
        "timestamp_integrity": {
            "estimated_clock_offset_ms": 0.0,
            "is_host_clock_skew_detected": False,
        },
        "venue_feeds": {
            "binance_perp": {"total_events": 100, "last_event_received_at_utc": "2026-10-03T12:00:00Z"}
        }
    }
    from unittest.mock import mock_open
    with patch.object(service, "_load_latest_quality_report", return_value=report_with_zero), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps({"run_id": "r1", "pid": 123}))), \
         patch("psutil.pid_exists", return_value=True):
        st = service.get_recorder_status()
        assert st["venues"]["binance_perp"]["clock_skew_ms"] == 0.0
        assert st["venues"]["binance_perp"]["clock_skew_detected"] is False


def test_paper_account_no_fake_pnl_or_positions_unstarted(monkeypatch):
    """When paper is unstarted, no ghost positions or fake zero PnL are reported."""
    monkeypatch.delenv("QUANT_OS_MOCK_MODE", raising=False)
    service = QuantOSDataService()
    acct = service.get_paper_account()
    assert acct["status"] == "NOT_STARTED"
    assert acct["realized_pnl_usd"] is None
    assert acct["unrealized_pnl_usd"] is None
    assert len(acct["positions"]) == 0
    assert len(acct["orders"]) == 0
    assert len(acct["fills"]) == 0


def test_kill_switch_reset_unauthenticated_rejected(api_client, operator_env):
    """Resetting kill switch without credentials returns 401."""
    res = api_client.post("/api/risk/kill-switch/reset", json={"reason": "unauthorized clear"})
    assert res.status_code == 401


def test_kill_switch_reset_invalid_token_rejected(api_client, operator_env):
    """Resetting kill switch with invalid token returns 403."""
    res = api_client.post(
        "/api/risk/kill-switch/reset",
        headers={"Authorization": "Bearer bad-token"},
        json={"reason": "unauthorized clear"}
    )
    assert res.status_code == 403


def test_stream_auth_success(operator_env):
    """Valid stream authorization succeeds without raising HTTPException."""
    assert verify_stream_auth(token="test-stream-secret-67890") is True


def test_execution_kill_switch_blocking_blocks_account_scope(tmp_path):
    """ACCOUNT-scoped kill switch blocks intents targeting that specific account pocket."""
    backend = LocalPersistenceBackend(db_path=str(tmp_path / "ks_acc.db"))
    ks = ExecutionKillSwitch(backend=backend)
    ks.activate(scope="ACCOUNT", actor="RISK_SYSTEM", reason="Pocket margin breached", target="PROP_ALPHA_100K")

    blocked_intent = OrderIntent(
        intent_id="i_acc", client_order_id="c_acc", strategy_id="STR-002", strategy_version="1",
        venue="binance", symbol="BTC/USDT", side="BUY", order_type="LIMIT", quantity=0.1, limit_price=50000.0,
        capital_pocket_id="PROP_ALPHA_100K", idempotency_key="k_acc",
        market_data_timestamp_ns=1000, decision_timestamp_ns=1000, max_signal_age_ms=5000.0, created_at_ns=1000,
    )
    assert ks.blocking(blocked_intent) == "ACCOUNT:PROP_ALPHA_100K"

    allowed_intent = OrderIntent(
        intent_id="i_own", client_order_id="c_own", strategy_id="STR-002", strategy_version="1",
        venue="binance", symbol="BTC/USDT", side="BUY", order_type="LIMIT", quantity=0.1, limit_price=5000.0,
        capital_pocket_id="OWN_MAIN", idempotency_key="k_own",
        market_data_timestamp_ns=1000, decision_timestamp_ns=1000, max_signal_age_ms=5000.0, created_at_ns=1000,
    )
    assert ks.blocking(allowed_intent) is None


def test_kill_switch_api_fails_closed_when_auth_unconfigured(api_client, monkeypatch):
    """When operator auth is unconfigured, kill switch activation returns 503 Service Unavailable."""
    monkeypatch.delenv("QUANT_OS_OPERATOR_TOKEN", raising=False)
    monkeypatch.delenv("QUANT_OS_API_KEY", raising=False)
    monkeypatch.delenv("QUANT_OS_TEST_AUTH_OVERRIDE", raising=False)
    res = api_client.post("/api/risk/kill-switch/activate", json={"reason": "emergency"})
    assert res.status_code == 503
    assert "AUTH_NOT_CONFIGURED" in res.json().get("detail", "")


def test_kill_switch_matrix_all_scopes(tmp_path):
    """ExecutionKillSwitch matrix: GLOBAL, VENUE, ACCOUNT, STRATEGY, SYMBOL + reset + restart persistence."""
    backend = LocalPersistenceBackend(db_path=str(tmp_path / "ks_matrix.db"))
    ks = ExecutionKillSwitch(backend=backend)

    def _intent(venue="binance", acct="OWN_MAIN", strat="STR-002", sym="BTC/USDT"):
        return OrderIntent(
            intent_id="i1", client_order_id="c1", strategy_id=strat, strategy_version="1",
            venue=venue, symbol=sym, side="BUY", order_type="LIMIT", quantity=0.1, limit_price=50000.0,
            capital_pocket_id=acct, idempotency_key="k1",
            market_data_timestamp_ns=1000, decision_timestamp_ns=1000, max_signal_age_ms=5000.0, created_at_ns=1000,
        )

    # 1. VENUE
    ks.activate(scope="VENUE", actor="OP", reason="Deribit outage", target="deribit")
    assert ks.blocking(_intent(venue="deribit")) == "VENUE:deribit"
    assert ks.blocking(_intent(venue="binance")) is None

    # 2. ACCOUNT
    ks.activate(scope="ACCOUNT", actor="OP", reason="Prop pocket breached", target="PROP_ALPHA_100K")
    assert ks.blocking(_intent(acct="PROP_ALPHA_100K")) == "ACCOUNT:PROP_ALPHA_100K"
    assert ks.blocking(_intent(acct="OWN_MAIN")) is None

    # 3. STRATEGY
    ks.activate(scope="STRATEGY", actor="OP", reason="Strategy fault", target="STR-003")
    assert ks.blocking(_intent(strat="STR-003")) == "STRATEGY:STR-003"
    assert ks.blocking(_intent(strat="STR-002")) is None

    # 4. SYMBOL
    ks.activate(scope="SYMBOL", actor="OP", reason="Asset halt", target="ETH/USDT")
    assert ks.blocking(_intent(sym="ETH/USDT")) == "SYMBOL:ETH/USDT"
    assert ks.blocking(_intent(sym="BTC/USDT")) is None

    # 5. GLOBAL
    ks.activate(scope="GLOBAL", actor="OP", reason="System-wide halt")
    assert ks.blocking(_intent()) == "GLOBAL"

    # Reset GLOBAL
    ks.reset(scope="GLOBAL", actor="OP", reason="System resumed")
    assert ks.blocking(_intent(venue="binance", acct="OWN_MAIN", strat="STR-002", sym="BTC/USDT")) is None

    # Restart persistence: verify scopes survive fresh instance
    ks2 = ExecutionKillSwitch(backend=backend)
    active2 = ks2.active_scopes()
    assert "VENUE:deribit" in active2
    assert "ACCOUNT:PROP_ALPHA_100K" in active2
    assert "STRATEGY:STR-003" in active2
    assert "SYMBOL:ETH/USDT" in active2
    assert "GLOBAL" not in active2


def test_router_live_kill_switch_propagation_without_reconstruction(tmp_path):
    """Router and ExecutionPlaneService immediately reflect kill switch activation/reset without reconstruction."""
    from src.execution_plane.adapters.fake import FakeExchangeAdapter
    from src.execution_plane.router import ExecutionRouter, InstrumentRegistry
    from src.execution_plane.models import InstrumentMeta, ExecutionMode
    from src.execution_plane.service import ExecutionPlaneService
    from src.execution_plane.store import ExecutionStore

    backend = LocalPersistenceBackend(db_path=str(tmp_path / "router_ks.db"))
    store = ExecutionStore(backend)

    risk_limits = RiskLimits(max_drawdown_limit_pct=0.10, max_gross_leverage=3.0, live_capital_locked=False)
    risk_engine = DeterministicRiskEngine(initial_equity_usd=10000.0, limits=risk_limits)

    instruments = InstrumentRegistry()
    instruments.register(InstrumentMeta(
        symbol="BTC/USDT",
        venue="sim",
        venue_symbol="BTCUSDT",
        tick_size=0.1,
        step_size=0.001,
        min_qty=0.001,
        min_notional=5.0,
        base_asset="BTC",
        quote_asset="USDT",
        margin_asset="USDT",
    ))
    adapter = FakeExchangeAdapter("sim", "LIVE")

    # Construct router ONCE
    router = ExecutionRouter(
        store=store,
        risk_engine=risk_engine,
        adapters={"sim": adapter},
        instruments=instruments,
        mode=ExecutionMode.PAPER,
        capital_authorizer=lambda p: 10000.0,
        allow_test_adapters=True,
    )

    # ExecutionPlaneService instance on same backend
    eps = ExecutionPlaneService(backend=backend)

    intent = OrderIntent(
        intent_id="i_live_ks", client_order_id="c_live_ks", strategy_id="STR-002", strategy_version="1",
        venue="sim", symbol="BTC/USDT", side="BUY", order_type="LIMIT", quantity=0.1, limit_price=50000.0,
        capital_pocket_id="OWN_MAIN", idempotency_key="k_live_ks",
        market_data_timestamp_ns=1000, decision_timestamp_ns=1000, max_signal_age_ms=5000.0, created_at_ns=1000,
    )

    # Initial state: router unblocked
    assert router._kill_active(intent) is None
    assert eps.get_kill_switches()["active_scopes"] == []

    # Activate kill switch via external kill switch instance on the same backend
    external_ks = ExecutionKillSwitch(backend=backend)
    external_ks.activate(scope="SYMBOL", actor="EXTERNAL_CONTROLLER", reason="Flash crash", target="BTC/USDT")

    # Router WITHOUT reconstruction immediately blocks the intent!
    assert router._kill_active(intent) == "SYMBOL:BTC/USDT"
    # ExecutionPlaneService WITHOUT reconstruction immediately shows active scope!
    assert eps.get_kill_switches()["active_scopes"] == ["SYMBOL:BTC/USDT"]

    # Reset kill switch via external instance
    external_ks.reset(scope="SYMBOL", actor="EXTERNAL_CONTROLLER", reason="Normal volatility resumed", target="BTC/USDT")

    # Router WITHOUT reconstruction immediately unblocks!
    assert router._kill_active(intent) is None
    assert eps.get_kill_switches()["active_scopes"] == []


def test_recorder_status_exposes_uptime_and_data_span_separately():
    """get_recorder_status separates process_uptime_seconds and committed_data_span_seconds without wall-clock READY."""
    import time
    service = QuantOSDataService()
    report = {
        "stream_continuity": {
            "effective_data_span_seconds": 12345.0,
            "all_streams_pass": True,
        },
        "gates": {
            "gate_24h": {"status": "PENDING", "passed": False},
            "gate_72h": {"status": "PENDING", "passed": False},
        },
        "venue_feeds": {},
    }
    from unittest.mock import mock_open
    manifest = {
        "run_id": "r1",
        "pid": 99999,
        "started_at_timestamp_ns": time.time_ns() - int(50000 * 1e9),
    }
    with patch.object(service, "_load_latest_quality_report", return_value=report), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=json.dumps(manifest))), \
         patch("psutil.pid_exists", return_value=True):
        status = service.get_recorder_status()
        assert status["process_uptime_seconds"] >= 49999.0
        assert status["committed_data_span_seconds"] == 12345.0
        assert status["gate_24h_status"] == "PENDING"
        assert status["gate_72h_status"] == "PENDING"
        assert "READY" not in (status["gate_24h_status"], status["gate_72h_status"])


def test_system_status_gates_pass_boolean_from_quality_report():
    """get_system_status derives passed boolean from authoritative quality report (status == PASS)."""
    service = QuantOSDataService()

    # Case 1: Report is PASS
    report_pass = {
        "gates": {
            "gate_24h": {"status": "PASS", "passed": True, "elapsed_seconds": 86450.0},
            "gate_72h": {"status": "PENDING", "passed": False, "elapsed_seconds": 86450.0},
        }
    }
    with patch.object(service, "_load_latest_quality_report", return_value=report_pass), \
         patch.object(service, "get_recorder_status", return_value={"status": "RUNNING", "elapsed_seconds": 86450.0, "gate_24h_status": "PASS", "gate_72h_status": "PENDING"}):
        status = service.get_system_status()
        assert status["gate_24h"]["status"] == "PASS"
        assert status["gate_24h"]["passed"] is True
        assert status["gate_72h"]["status"] == "PENDING"
        assert status["gate_72h"]["passed"] is False

    # Case 2: Report is FAIL
    report_fail = {
        "gates": {
            "gate_24h": {"status": "FAIL", "passed": False, "elapsed_seconds": 90000.0},
            "gate_72h": {"status": "FAIL", "passed": False, "elapsed_seconds": 90000.0},
        }
    }
    with patch.object(service, "_load_latest_quality_report", return_value=report_fail), \
         patch.object(service, "get_recorder_status", return_value={"status": "RUNNING", "elapsed_seconds": 90000.0, "gate_24h_status": "FAIL", "gate_72h_status": "FAIL"}):
        status = service.get_system_status()
        assert status["gate_24h"]["status"] == "FAIL"
        assert status["gate_24h"]["passed"] is False

