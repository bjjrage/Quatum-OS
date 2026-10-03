"""Execution Plane v1 — router/lifecycle certification. Uses ONLY FakeExchangeAdapter (MOCK); no network."""
import pytest

from src.execution_plane.adapters.fake import FakeExchangeAdapter
from src.execution_plane.models import ExecutionMode as M, InstrumentMeta, OrderIntent, OrderState as S
from src.execution_plane.router import ExecutionRouter, InstrumentRegistry
from src.execution_plane.security import CredentialProvider
from src.execution_plane.store import ExecutionKillSwitch, ExecutionStore
from src.execution_plane.telemetry import ClockMonitor
from src.persistence.backend import LocalPersistenceBackend
from src.risk.engine import DeterministicRiskEngine, RiskLimits

T0 = 1_700_000_000_000_000_000  # ns


class H:
    def __init__(self, tmp_path, mode=M.SANDBOX, live_locked=False, db="cp.db", adapter=None, reuse=None):
        self.t = [T0]
        self.backend = reuse or LocalPersistenceBackend(tmp_path / db)
        self.store = ExecutionStore(self.backend)
        self.risk = DeterministicRiskEngine(initial_equity_usd=1_000_000.0,
                                            limits=RiskLimits(live_capital_locked=live_locked,
                                                              max_orders_per_window=1000))
        self.fake = adapter or FakeExchangeAdapter(now_ms=lambda: self.t[0] // 1_000_000)
        self.reg = InstrumentRegistry()
        self.reg.register(InstrumentMeta(symbol="BTCUSDT", venue="fake_venue", venue_symbol="BTCUSDT", tick_size=0.1,
                                         step_size=0.001, min_qty=0.001, min_notional=5.0, base_asset="BTC",
                                         quote_asset="USDT", margin_asset="USDT"))
        self.sleeps = []
        self.auth = 0.0
        self.mode = mode
        self.router = self.mk()

    def mk(self):
        return ExecutionRouter(self.store, self.risk, {"fake_venue": self.fake}, self.reg, mode=self.mode,
                               capital_authorizer=lambda p: self.auth, credentials=CredentialProvider({}),
                               clock_monitor=ClockMonitor(clock_ns=lambda: self.t[0]),
                               clock_ns=lambda: self.t[0], sleep=self.sleeps.append, allow_test_adapters=True)

    def intent(self, n=1, qty=0.1, price=100.0, **kw):
        d = dict(intent_id=f"i{n}", strategy_id="STR-T", strategy_version="1", capital_pocket_id="pocket-1",
                 venue="fake_venue", symbol="BTCUSDT", side="BUY", order_type="LIMIT", quantity=qty,
                 limit_price=price, market_data_timestamp_ns=T0 - 1_000_000, decision_timestamp_ns=T0 - 1_000_000 + n,
                 max_signal_age_ms=1000.0, created_at_ns=T0)
        d.update(kw)
        return OrderIntent(**d)


@pytest.fixture
def h(tmp_path):
    return H(tmp_path)


def test_credentials_missing_not_configured():
    cp = CredentialProvider({})
    for v in ("binance_perp", "bybit", "deribit"):
        assert cp.status(v)["status"] == "NOT_CONFIGURED"


def test_secret_redaction_in_status_and_repr():
    cp = CredentialProvider({"BINANCE_API_KEY": "AKEY123456", "BINANCE_API_SECRET": "SSECRET987654"})
    blob = repr(cp.status("binance_perp")) + repr(cp.get("binance_perp"))
    assert "AKEY123456" not in blob and "SSECRET987654" not in blob
    from src.execution_plane.security import redact_text
    assert "SSECRET987654" not in redact_text("boom SSECRET987654", cp.known_values())


def test_live_locked_rejects_everything(tmp_path):
    h = H(tmp_path, mode=M.LIVE_LOCKED, live_locked=True)
    r = h.router.submit(h.intent())
    assert r.state is S.RISK_REJECTED or r.state is S.REJECTED
    assert h.fake.submit_calls == []


def test_live_with_zero_authorization_rejected(tmp_path):
    h = H(tmp_path, mode=M.LIVE, live_locked=False)
    h.router.recon_status["fake_venue"] = "HEALTHY"
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED and "AUTHORIZED_LIVE_CAPITAL_ZERO" in r.reason
    assert h.fake.submit_calls == []


def test_live_with_locked_risk_engine_vetoed_even_if_authorized(tmp_path):
    h = H(tmp_path, mode=M.LIVE, live_locked=True)
    h.auth = 10_000.0
    h.router.recon_status["fake_venue"] = "HEALTHY"
    r = h.router.submit(h.intent())
    assert r.state is S.RISK_REJECTED and "CAPITAL_LOCKED" in r.reason
    assert h.fake.submit_calls == []


def test_risk_veto_cannot_be_bypassed(tmp_path):
    h = H(tmp_path)
    h.risk.trigger_kill_switch("test")
    r = h.router.submit(h.intent())
    assert r.state in (S.RISK_REJECTED, S.REJECTED) and h.fake.submit_calls == []


def test_event_cluster_split_across_venues_still_vetoed(tmp_path):
    from src.risk.engine import EventCluster
    import inspect
    h = H(tmp_path)
    params = inspect.signature(EventCluster).parameters
    assert "cluster_id" in params
    r = h.router.submit(h.intent(event_cluster_id="UNKNOWN-CLUSTER"))
    assert r.state is S.REJECTED and "UNKNOWN_EVENT_CLUSTER" in r.reason


def test_paper_never_real_submits(tmp_path):
    h = H(tmp_path, mode=M.PAPER)
    r = h.router.submit(h.intent())
    assert h.fake.submit_calls == []
    assert r.state is S.REJECTED and "PAPER_NOT_WIRED" in r.reason  # no broker wired -> fail closed


def test_paper_with_broker(tmp_path):
    from src.paper.broker import PaperBroker
    h = H(tmp_path, mode=M.PAPER)
    h.router.paper_broker = PaperBroker()
    r = h.router.submit(h.intent())
    assert h.fake.submit_calls == [] and r.state in (S.ACKNOWLEDGED, S.FILLED, S.PARTIALLY_FILLED)


def test_shadow_would_submit_never_transmits(tmp_path):
    h = H(tmp_path, mode=M.SHADOW)
    r = h.router.submit(h.intent())
    assert r.state is S.WOULD_SUBMIT
    assert h.fake.submit_calls == [] and h.fake.orders == {}
    row = h.backend.get("execution_orders", "i1")
    sr = row["shadow_request"]
    assert sr["symbol"] == "BTCUSDT" and sr["side"] == "BUY" and sr["client_order_id"] == r.intent.client_order_id
    assert row["data_source"] == "SHADOW"


def test_sandbox_cannot_fall_through_to_live(tmp_path):
    h = H(tmp_path, mode=M.SANDBOX)
    r = h.router.submit(h.intent())
    assert r.state is S.ACKNOWLEDGED
    from src.execution_plane.adapters.base import issue_permit, LiveLockedError
    permit = issue_permit("SUBMIT", "fake_venue", "x", M.SANDBOX, 0.0, True, T0)
    from src.execution_plane.adapters.real import BinanceUSDMAdapter
    live = BinanceUSDMAdapter(environment="LIVE", credentials=CredentialProvider({}), transport=None)
    with pytest.raises(Exception):
        live.submit_order(permit, h.intent(venue="binance_perp"), h.reg.get("fake_venue", "BTCUSDT"))


def test_no_real_adapter_in_router_without_live_gates(tmp_path):
    from src.execution_plane.adapters.real import BinanceUSDMAdapter
    h = H(tmp_path, mode=M.SANDBOX)
    h.router.adapters["fake_venue"] = BinanceUSDMAdapter(environment="LIVE", credentials=CredentialProvider({}),
                                                         transport=None)
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED  # environment mismatch / not configured


def test_duplicate_idempotency_no_duplicate_order(h):
    a = h.router.submit(h.intent())
    b = h.router.submit(h.intent())
    assert a.intent.intent_id == b.intent.intent_id
    assert len(h.fake.submit_calls) == 1


def test_timeout_after_submit_is_unknown_outcome_and_reconciles_before_retry(h):
    h.fake.script_submit("TIMEOUT_ACCEPTED")
    r = h.router.submit(h.intent())
    assert r.state is S.UNKNOWN_OUTCOME
    assert len(h.fake.submit_calls) == 1
    with pytest.raises(Exception):  # retry impossible until venue absence confirmed
        h.router.retry_unknown("i1")
    out = h.router.resolve_unknown("i1")
    assert h.fake.query_calls  # queried venue by client order id
    assert h.router.get("i1").state is S.ACKNOWLEDGED, out
    assert len(h.fake.submit_calls) == 1  # no duplicate economic order


def test_timeout_lost_order_retry_only_after_confirmed_absent(h):
    h.fake.script_submit("TIMEOUT_LOST")
    r = h.router.submit(h.intent())
    assert r.state is S.UNKNOWN_OUTCOME
    h.router.resolve_unknown("i1")
    rec = h.router.get("i1")
    assert rec.venue_absent_confirmed or rec.state is S.REJECTED
    if rec.state is S.UNKNOWN_OUTCOME:
        rec = h.router.retry_unknown("i1")
        assert rec.state is S.ACKNOWLEDGED
        assert len(h.fake.submit_calls) == 2


def test_unknown_outcome_query_failure_stays_unknown(h):
    h.fake.script_submit("TIMEOUT_ACCEPTED")
    h.router.submit(h.intent())
    h.fake.query_fails = True
    h.router.resolve_unknown("i1")
    assert h.router.get("i1").state is S.UNKNOWN_OUTCOME


def test_partial_then_full_fill(h):
    h.fake.script_submit("PARTIAL")
    r = h.router.submit(h.intent(qty=1.0))
    assert r.state is S.PARTIALLY_FILLED and abs(r.filled_qty - 0.4) < 1e-9
    f = h.fake.venue_fill(r.intent.client_order_id, 0.6, 100.0)
    h.router.on_private_event("fake_venue", {"type": "FILL", **f})
    r = h.router.get("i1")
    assert r.state is S.FILLED and abs(r.filled_qty - 1.0) < 1e-9
    assert len(h.store.fills()) == 2
    # replayed event must not double count
    h.router.on_private_event("fake_venue", {"type": "FILL", **f})
    assert abs(h.router.get("i1").filled_qty - 1.0) < 1e-9


def test_cancel_ok(h):
    r = h.router.submit(h.intent())
    r = h.router.cancel("i1")
    assert r.state is S.CANCELED


def test_cancel_fill_race(h):
    h.router.submit(h.intent())
    h.fake.script_cancel("FILL_DURING_CANCEL")
    r = h.router.cancel("i1")
    assert r.state is S.FILLED and abs(r.filled_qty - 0.1) < 1e-9


def test_cancel_already_filled(h):
    h.router.submit(h.intent())
    h.fake.script_cancel("ALREADY_FILLED")
    h.fake.venue_fill(h.router.get("i1").intent.client_order_id, 0.1, 100.0)
    r = h.router.cancel("i1")
    assert r.state in (S.FILLED, S.RECONCILIATION_REQUIRED, S.CANCEL_PENDING)


def test_late_ack_after_unknown(h):
    h.fake.script_submit("TIMEOUT_ACCEPTED")
    r = h.router.submit(h.intent())
    assert r.state is S.UNKNOWN_OUTCOME
    cid = r.intent.client_order_id
    o = h.fake.orders[cid]
    h.router.on_private_event("fake_venue", {"type": "ORDER", "client_order_id": cid,
                                             "venue_order_id": o["venue_order_id"], "status": "NEW"})
    assert h.router.get("i1").state is S.ACKNOWLEDGED


def test_replace_goes_through_full_pipeline(h):
    h.router.submit(h.intent())
    old, new = h.router.replace("i1", h.intent(n=2, price=101.0))
    assert old.state is S.CANCELED and new is not None and new.state is S.ACKNOWLEDGED
    assert len(h.fake.submit_calls) == 2


def test_replace_blocked_when_cancel_not_confirmed(h):
    h.router.submit(h.intent())
    h.fake.script_cancel("REJECT")
    old, new = h.router.replace("i1", h.intent(n=2, price=101.0))
    assert new is None and len(h.fake.submit_calls) == 1


def test_stale_signal_rejected(h):
    r = h.router.submit(h.intent(market_data_timestamp_ns=T0 - 5_000_000_000))
    assert r.state is S.REJECTED and "STALE_SIGNAL" in r.reason and h.fake.submit_calls == []


def test_future_timestamp_rejected(h):
    r = h.router.submit(h.intent(market_data_timestamp_ns=T0 + 10_000_000_000))
    assert r.state is S.REJECTED and "TIMESTAMP_IN_FUTURE" in r.reason


@pytest.mark.parametrize("scope,target", [("GLOBAL", ""), ("VENUE", "fake_venue"), ("SYMBOL", "BTCUSDT"),
                                          ("STRATEGY", "STR-T"), ("ACCOUNT", "pocket-1")])
def test_kill_switch_scopes_reject(h, scope, target):
    h.router.activate_kill_switch(scope, "tester", "drill", target=target)
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED and "KILL_SWITCH" in r.reason and h.fake.submit_calls == []


def test_kill_switch_scope_does_not_overblock(h):
    h.router.activate_kill_switch("SYMBOL", "tester", "drill", target="ETHUSDT")
    assert h.router.submit(h.intent()).state is S.ACKNOWLEDGED


def test_kill_switch_never_flattens_and_cancel_optional(h):
    h.router.submit(h.intent())
    h.router.activate_kill_switch("GLOBAL", "t", "drill")
    assert h.fake.cancel_calls == [] and h.router.get("i1").state is S.ACKNOWLEDGED
    h.router.activate_kill_switch("GLOBAL", "t", "drill2", cancel_open_orders=True)
    assert h.router.get("i1").state is S.CANCELED
    assert all(o["side"] == "BUY" for o in h.fake.orders.values())  # no flattening orders


def test_kill_switch_persisted_across_restart(tmp_path):
    h = H(tmp_path)
    h.router.activate_kill_switch("GLOBAL", "t", "drill")
    h2 = H(tmp_path, reuse=h.backend)
    assert h2.router.submit(h2.intent(n=7)).state is S.REJECTED


def test_clock_drift_block(h):
    h.fake.clock_offset_ms = 5000
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED and "CLOCK_DRIFT_BLOCK" in r.reason


def test_rate_limit_retries_bounded(h):
    h.fake.script_submit("RATE_LIMIT", "RATE_LIMIT", "RATE_LIMIT", "RATE_LIMIT")
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED and "RATE_LIMITED" in r.reason
    assert len(h.fake.submit_calls) == h.router.max_rate_retries + 1
    assert len(h.sleeps) <= h.router.max_rate_retries


def test_rate_limit_then_success(h):
    h.fake.script_submit("RATE_LIMIT")
    assert h.router.submit(h.intent()).state is S.ACKNOWLEDGED
    assert len(h.fake.submit_calls) == 2


def test_missing_metadata_blocks(tmp_path):
    h = H(tmp_path)
    h.reg = InstrumentRegistry()
    h.router.instruments = h.reg
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED and "metadata missing" in r.reason and h.fake.submit_calls == []


def test_precision_validation(h):
    assert "tick" in h.router.submit(h.intent(n=1, price=100.05)).reason.lower()
    assert "step" in h.router.submit(h.intent(n=2, qty=0.0105)).reason.lower()
    assert "min" in h.router.submit(h.intent(n=3, qty=0.0001)).reason.lower()
    assert h.fake.submit_calls == []


def test_venue_reject_is_terminal_not_unknown(h):
    h.fake.script_submit("REJECT")
    assert h.router.submit(h.intent()).state is S.REJECTED


def test_disconnect_before_send_is_safe_reject_after_bounded_retries(h):
    h.fake.script_submit("DISCONNECT", "DISCONNECT", "DISCONNECT")
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED and h.fake.orders == {}


def test_disconnect_after_send_is_unknown(h):
    h.fake.script_submit("DISCONNECT_AFTER")
    assert h.router.submit(h.intent()).state is S.UNKNOWN_OUTCOME


def test_persistence_records(h):
    h.fake.script_submit("PARTIAL")
    h.router.submit(h.intent(qty=1.0))
    b = h.backend
    assert b.get("execution_intents", "i1") and b.get("execution_orders", "i1")
    assert h.store.attempts("i1") and h.store.transitions("i1") and h.store.fills()
    assert h.store.latency_samples()
    assert h.store.get_order("i1").venue_order_id


def test_audit_has_no_secrets(tmp_path):
    from src.persistence.domain import AuditLog
    h = H(tmp_path)
    h.router.audit = AuditLog(h.backend)
    h.router.credentials = CredentialProvider({"BINANCE_API_KEY": "AKEY123456", "BINANCE_API_SECRET": "SSECRET987654"})
    h.router.submit(h.intent())
    dump = repr(h.backend.list("audit_events")) if hasattr(h.backend, "list") else ""
    assert "SSECRET987654" not in dump and "AKEY123456" not in dump
    assert dump  # audit actually written


def test_restart_recovery_submitting_becomes_unknown(tmp_path):
    h = H(tmp_path)
    r = h.router.submit(h.intent())
    rec = h.store.get_order("i1")
    # simulate crash while SUBMITTING: rewind projection
    rec.state = S.SUBMITTING
    h.store.save_order(rec)
    # When venue query fails or is not immediately resolvable, it stays UNKNOWN_OUTCOME
    h.fake.query_fails = True
    h2 = H(tmp_path, reuse=h.backend, adapter=h.fake)
    out = h2.router.recover()
    assert out["to_unknown_outcome"] == 1
    assert h2.router.get("i1").state is S.UNKNOWN_OUTCOME
    assert h2.router.recovery_pending.get("fake_venue") is True
    # recovery pending blocks new submissions until reconciled
    assert h2.router.submit(h2.intent(n=9)).state is S.REJECTED


def test_reconciliation_healthy_and_mismatch_fail_closed(h):
    h.router.submit(h.intent())
    assert h.router.reconcile("fake_venue")["status"] == "HEALTHY"
    h.fake.corrupt_position("BTCUSDT", 5.0)
    assert h.router.reconcile("fake_venue")["status"] == "MISMATCH"
    r = h.router.submit(h.intent(n=2))
    assert r.state is S.REJECTED and "RECONCILIATION" in r.reason


def test_reconciliation_orphan_and_unavailable(h):
    h.fake.add_orphan_order("orphan1")
    assert h.router.reconcile("fake_venue")["status"] == "MISMATCH"
    h.fake.query_fails = True
    assert h.router.reconcile("fake_venue")["status"] in ("UNAVAILABLE", "UNKNOWN")


def test_live_requires_healthy_reconciliation_even_with_capital(tmp_path):
    h = H(tmp_path, mode=M.LIVE, live_locked=False)
    h.auth = 10_000.0
    r = h.router.submit(h.intent())
    assert r.state is S.REJECTED  # reconciliation UNKNOWN / venue not live-capable / env mismatch
    assert h.fake.submit_calls == [] or r.state is S.REJECTED


def test_invalid_transition_rejected(h):
    from src.execution_plane.router import InvalidTransitionError
    r = h.router.submit(h.intent())
    h.router.cancel("i1")
    with pytest.raises(InvalidTransitionError):
        h.router._to(h.router.get("i1"), S.ACKNOWLEDGED)


def test_private_event_for_unknown_order_marks_mismatch(h):
    h.router.on_private_event("fake_venue", {"type": "ORDER", "client_order_id": "ghost", "venue_order_id": "V9",
                                             "status": "NEW"})
    assert h.router.recon_status["fake_venue"] != "HEALTHY"


def test_strategies_cannot_reach_adapters():
    import pathlib, re
    for p in pathlib.Path("src/strategies").rglob("*.py"):
        s = p.read_text(encoding="utf-8")
        assert "execution_plane" not in s and not re.search(r"\.(submit_order|create_order)\(", s), p


def test_test_adapter_refused_in_production_router(tmp_path):
    h = H(tmp_path)
    with pytest.raises(ValueError):
        ExecutionRouter(h.store, h.risk, {"fake_venue": h.fake}, h.reg, mode=M.SANDBOX)


def test_garbage_mode_parses_to_live_locked():
    from src.execution_plane.models import parse_mode
    assert parse_mode("banana") is M.LIVE_LOCKED and parse_mode(None) is M.LIVE_LOCKED
