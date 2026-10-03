"""Pre-Paper Hardening 01c — Final Risk-Authority Closure.

Authoritative invariant: the ONLY operational route to a valid ExecutionAuthorization is
Strategy -> OrderIntent -> ExecutionRouter -> DeterministicRiskEngine -> RiskDecision
-> ExecutionRouter/ExecutionAuthorizationSigner -> ExecutionAuthorization -> PaperBroker.

No supported production API outside ExecutionRouter / ExecutionAuthorizationSigner may
mint an authorization, and PaperBroker is a verify-only consumer (it never converts a
RiskDecision / boolean into an authorization by itself).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.execution_plane.authority import (
    ExecutionAuthorization,
    ExecutionAuthorizationSigner,
    ExecutionAuthorizationVerifier,
)
from src.execution_plane.models import ExecutionMode, OrderIntent, OrderState
from src.paper.broker import PaperBroker, PaperOrderSide, PaperOrderType
from src.risk.engine import RiskDecision


T0 = 1_700_000_000_000_000_000  # ns


# --------------------------------------------------------------------------- helpers

def _paper_router(tmp_path, latency_ms: float = 0.0, risk_limits=None):
    from src.execution_plane.router import ExecutionRouter, InstrumentRegistry
    from src.execution_plane.security import CredentialProvider
    from src.execution_plane.store import ExecutionStore
    from src.execution_plane.telemetry import ClockMonitor
    from src.persistence.backend import LocalPersistenceBackend
    from src.risk.engine import DeterministicRiskEngine, RiskLimits

    t = [T0]
    backend = LocalPersistenceBackend(tmp_path / "cp.db")
    store = ExecutionStore(backend)
    risk = DeterministicRiskEngine(
        initial_equity_usd=1_000_000.0,
        limits=risk_limits or RiskLimits(live_capital_locked=False, max_orders_per_window=1000),
    )
    reg = InstrumentRegistry()
    broker = PaperBroker(simulated_latency_ms=latency_ms)
    router = ExecutionRouter(
        store, risk, {}, reg, mode=ExecutionMode.PAPER,
        capital_authorizer=lambda p: 0.0, credentials=CredentialProvider({}),
        paper_broker=broker, clock_monitor=ClockMonitor(clock_ns=lambda: t[0]),
        clock_ns=lambda: t[0], sleep=lambda s: None, allow_test_adapters=True,
    )
    return router, broker, t


def _intent(n: int = 1, symbol: str = "BTCUSDT", venue: str = "paper",
            qty: float = 0.1, price: float = 100.0, side: str = "BUY") -> OrderIntent:
    return OrderIntent(
        intent_id=f"paper-01c-{n}", strategy_id="STR-T", strategy_version="1",
        capital_pocket_id="pocket-1", venue=venue, symbol=symbol, side=side,
        order_type="LIMIT", quantity=qty, limit_price=price,
        market_data_timestamp_ns=T0 - 1_000_000, decision_timestamp_ns=T0 - 1_000_000 + n,
        max_signal_age_ms=1000.0, created_at_ns=T0,
    )


def _wired_broker():
    signer = ExecutionAuthorizationSigner()
    return signer, PaperBroker(simulated_latency_ms=0.0, verifier=signer.verifier)


# --------------------------------------------------------------------------- A

class TestRawRiskDecisionBypass:
    def test_broker_rejects_approved_risk_decision_object(self):
        """PaperBroker.submit_order(permit=RiskDecision(approved=True)) MUST REJECT."""
        signer = ExecutionAuthorizationSigner()
        broker = PaperBroker(simulated_latency_ms=0.0, verifier=signer.verifier)
        decision = RiskDecision(approved=True)
        with pytest.raises(PermissionError, match="ExecutionAuthorization"):
            broker.submit_order(
                symbol="BTCUSDT", side=PaperOrderSide.BUY, order_type=PaperOrderType.MARKET,
                quantity=0.1, venue="paper", current_time_ns=T0,
                current_bbo={"best_bid": 99.0, "best_ask": 100.0, "bid_size": 5.0, "ask_size": 5.0},
                permit=decision,
            )
        assert broker.orders == {}

    def test_broker_rejects_unapproved_risk_decision_object(self):
        signer = ExecutionAuthorizationSigner()
        broker = PaperBroker(simulated_latency_ms=0.0, verifier=signer.verifier)
        decision = RiskDecision(approved=False, reason="vetoed")
        with pytest.raises(PermissionError):
            broker.submit_order(
                symbol="BTCUSDT", side=PaperOrderSide.BUY, order_type=PaperOrderType.MARKET,
                quantity=0.1, venue="paper", current_time_ns=T0, permit=decision,
            )
        assert broker.orders == {}

    def test_broker_without_verifier_fails_closed(self):
        broker = PaperBroker(simulated_latency_ms=0.0)  # no verifier wired
        signer = ExecutionAuthorizationSigner()
        auth = signer.mint(kind="SUBMIT", venue="paper", mode=ExecutionMode.PAPER,
                           symbol="BTCUSDT", side="BUY", risk_decision=RiskDecision(approved=True),
                           current_time_ns=T0)
        with pytest.raises(PermissionError, match="Verifier is not configured"):
            broker.submit_order(
                symbol="BTCUSDT", side=PaperOrderSide.BUY, order_type=PaperOrderType.MARKET,
                quantity=0.1, venue="paper", current_time_ns=T0, permit=auth,
            )
        assert broker.orders == {}


# --------------------------------------------------------------------------- B

class TestPublicMintBypass:
    def test_broker_exposes_no_mint_capability(self):
        b = PaperBroker(simulated_latency_ms=0.0)
        assert not hasattr(b, "mint")
        assert not hasattr(b, "authorizer")
        assert not hasattr(b, "signer")
        assert isinstance(b.verifier, ExecutionAuthorizationVerifier) or b.verifier is None
        if b.verifier is not None:
            assert not hasattr(b.verifier, "mint")

    def test_verifier_class_has_no_mint(self):
        assert not hasattr(ExecutionAuthorizationVerifier, "mint")

    def test_broker_rejects_signer_construction(self):
        signer = ExecutionAuthorizationSigner()
        with pytest.raises(TypeError):
            PaperBroker(verifier=signer)  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            PaperBroker(authorizer=signer)  # type: ignore[call-arg]

    def test_authorization_cannot_be_forged_by_construction(self):
        with pytest.raises(PermissionError):
            ExecutionAuthorization(
                kind="SUBMIT", venue="paper", client_order_id="x", mode=ExecutionMode.PAPER,
                authorized_live_capital_usd=0.0, risk_approved=True, issued_ns=T0,
            )


# --------------------------------------------------------------------------- C

class TestIssuePermitRemoved:
    def test_production_base_exposes_no_bypass_helpers(self):
        import src.execution_plane.adapters.base as base

        for name in ("issue_permit", "mint_test_authorization", "ExecutionAuthorizer", "get_default"):
            assert not hasattr(base, name), f"production API must not expose {name}"

    def test_issue_permit_import_fails(self):
        with pytest.raises(ImportError):
            from src.execution_plane.adapters.base import issue_permit  # noqa: F401

    def test_mint_helper_import_fails(self):
        with pytest.raises(ImportError):
            from src.execution_plane.adapters.base import mint_test_authorization  # noqa: F401


# --------------------------------------------------------------------------- D

class TestHelperLeakage:
    def test_helpers_not_importable_from_production_modules(self):
        import src.execution_plane.adapters.base as base
        import src.paper.broker as broker_mod

        for mod in (base, broker_mod):
            assert not hasattr(mod, "mint_test_authorization")
            assert not hasattr(mod, "issue_permit")

    def test_production_never_imports_test_helpers(self):
        root = Path(__file__).resolve().parents[1] / "src"
        offenders = [
            str(p) for p in root.rglob("*.py")
            if "tests.helpers" in p.read_text(encoding="utf-8") or "tests/helpers" in p.read_text(encoding="utf-8")
        ]
        assert offenders == [], f"production imports test helpers: {offenders}"

    def test_helpers_module_is_test_only(self):
        from tests.helpers import auth as h

        assert hasattr(h, "mint_test_authorization")
        assert hasattr(h, "issue_permit")


# --------------------------------------------------------------------------- E / F

class TestRouterAuthorityPath:
    def test_router_success_mints_and_broker_accepts(self, tmp_path):
        router, broker, _ = _paper_router(tmp_path)
        rec = router.submit(_intent())
        assert rec.state is OrderState.ACKNOWLEDGED
        assert getattr(rec, "risk_decision", None) is not None and rec.risk_decision.approved
        assert len(broker.orders) == 1

    def test_risk_reject_generates_no_authorization(self, tmp_path):
        from src.risk.engine import RiskLimits

        # Case 1: engine kill switch blocks before any minting.
        router, broker, _ = _paper_router(tmp_path)
        router.risk.trigger_kill_switch("01c drill")
        rec = router.submit(_intent())
        assert rec.state in (OrderState.RISK_REJECTED, OrderState.REJECTED)
        assert "KILL_SWITCH" in rec.reason
        assert len(broker.orders) == 0
        assert len(router.signer.verifier._consumed_nonces) == 0

        # Case 2: DeterministicRiskEngine vetoes the order itself -> RISK_REJECTED,
        # no authorization minted, broker never touched.
        tiny = RiskLimits(live_capital_locked=False, max_orders_per_window=1000,
                          max_single_position_pct=1e-9)
        router2, broker2, _ = _paper_router(tmp_path, risk_limits=tiny)
        rec2 = router2.submit(_intent(n=2))
        assert rec2.state is OrderState.RISK_REJECTED
        assert rec2.risk_decision is not None and not rec2.risk_decision.approved
        assert len(broker2.orders) == 0
        assert len(router2.signer.verifier._consumed_nonces) == 0


# --------------------------------------------------------------------------- G

class TestWrongIntent:
    def test_authorization_for_intent_a_rejected_with_b(self, tmp_path):
        from src.paper.broker import PaperBroker as PB

        router, broker, _ = _paper_router(tmp_path)

        class SpyBroker(PB):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.seen = []

            def submit_order(self, *a, **k):
                self.seen.append(k.get("permit"))
                return super().submit_order(*a, **k)

        spy = SpyBroker(simulated_latency_ms=0.0)
        router.paper_broker = spy
        rec_a = router.submit(_intent(n=1, symbol="BTCUSDT"))
        assert rec_a.state is OrderState.ACKNOWLEDGED
        assert len(spy.seen) == 1 and spy.seen[0] is not None

        with pytest.raises(PermissionError, match="Authorization symbol mismatch"):
            spy.submit_order(
                symbol="ETHUSDT", side=PaperOrderSide.BUY, order_type=PaperOrderType.MARKET,
                quantity=0.1, venue="paper", current_time_ns=T0, permit=spy.seen[0],
            )
        assert len(spy.orders) == 1  # only intent A's order exists


# --------------------------------------------------------------------------- H / I / J

class TestPreservedTokenProperties:
    def test_replay_still_rejected(self):
        signer, broker = _wired_broker()
        auth = signer.mint(kind="SUBMIT", venue="paper", mode=ExecutionMode.PAPER,
                           symbol="BTCUSDT", side="BUY",
                           risk_decision=RiskDecision(approved=True), current_time_ns=T0,
                           validity_window_ns=10_000_000_000)
        broker.submit_order(symbol="BTCUSDT", side=PaperOrderSide.BUY,
                            order_type=PaperOrderType.MARKET, quantity=0.1,
                            venue="paper", current_time_ns=T0, permit=auth)
        with pytest.raises(PermissionError, match="already consumed"):
            broker.submit_order(symbol="BTCUSDT", side=PaperOrderSide.BUY,
                                order_type=PaperOrderType.MARKET, quantity=0.1,
                                venue="paper", current_time_ns=T0 + 1, permit=auth)

    def test_expiry_still_rejected(self):
        signer, broker = _wired_broker()
        auth = signer.mint(kind="SUBMIT", venue="paper", mode=ExecutionMode.PAPER,
                           symbol="BTCUSDT", side="BUY",
                           risk_decision=RiskDecision(approved=True), current_time_ns=T0,
                           validity_window_ns=1_000_000_000)
        with pytest.raises(PermissionError, match="expired"):
            broker.submit_order(symbol="BTCUSDT", side=PaperOrderSide.BUY,
                                order_type=PaperOrderType.MARKET, quantity=0.1,
                                venue="paper", current_time_ns=T0 + 2_000_000_000, permit=auth)

    def test_tamper_still_rejected(self):
        signer, broker = _wired_broker()
        auth = signer.mint(kind="SUBMIT", venue="paper", mode=ExecutionMode.PAPER,
                           symbol="BTCUSDT", side="BUY",
                           risk_decision=RiskDecision(approved=True), current_time_ns=T0)
        tampered = ExecutionAuthorization(
            kind=auth.kind, venue=auth.venue, client_order_id=auth.client_order_id,
            mode=auth.mode, authorized_live_capital_usd=auth.authorized_live_capital_usd,
            risk_approved=auth.risk_approved, issued_ns=auth.issued_ns,
            intent_id=auth.intent_id, symbol="ETHUSDT", side=auth.side,
            risk_decision_id=auth.risk_decision_id,
            risk_decision_fingerprint=auth.risk_decision_fingerprint,
            expires_at_ns=auth.expires_at_ns, nonce=auth.nonce,
            signature=auth.signature, _issuer=auth._issuer,
        )
        with pytest.raises(PermissionError, match="invalid cryptographic signature"):
            broker.submit_order(symbol="ETHUSDT", side=PaperOrderSide.BUY,
                                order_type=PaperOrderType.MARKET, quantity=0.1,
                                venue="paper", current_time_ns=T0, permit=tampered)


# --------------------------------------------------------------------------- §5 import policy

_FORBIDDEN_MINT_TOKENS = (
    "ExecutionAuthorizationSigner",
    "ExecutionAuthorizer",
    "issue_permit",
    "mint_test_authorization",
)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class TestImportPolicy:
    def test_strategies_cannot_mint(self):
        root = Path(__file__).resolve().parents[1] / "src" / "strategies"
        for p in sorted(root.rglob("*.py")):
            text = _read(p)
            for tok in _FORBIDDEN_MINT_TOKENS:
                assert tok not in text, f"{p} must not reference {tok}"
            assert ".mint(" not in text, f"{p} must not call mint()"

    def test_paper_cannot_mint(self):
        root = Path(__file__).resolve().parents[1] / "src" / "paper"
        for p in sorted(root.rglob("*.py")):
            text = _read(p)
            for tok in _FORBIDDEN_MINT_TOKENS:
                assert tok not in text, f"{p} must not reference {tok}"
            assert ".mint(" not in text, f"{p} must not call mint()"
            assert "RiskDecision(" not in text, f"{p} must not construct/consume RiskDecision"
            assert "src.risk" not in text, f"{p} must not depend on the risk engine"

    def test_adapters_cannot_mint(self):
        root = Path(__file__).resolve().parents[1] / "src" / "execution_plane" / "adapters"
        for p in sorted(root.rglob("*.py")):
            text = _read(p)
            for tok in _FORBIDDEN_MINT_TOKENS:
                assert tok not in text, f"{p} must not reference {tok}"
            assert ".mint(" not in text, f"{p} must not call mint()"

    def test_only_router_and_authority_mint(self):
        root = Path(__file__).resolve().parents[1] / "src"
        minters = sorted(
            str(p) for p in root.rglob("*.py")
            if ".mint(" in _read(p) or "def mint(" in _read(p)
        )
        allowed = {
            str(root / "execution_plane" / "router.py"),
            str(root / "execution_plane" / "authority.py"),
        }
        assert set(minters) == allowed, f"unexpected mint capability holders: {minters}"

    def test_signer_only_in_router_and_authority(self):
        root = Path(__file__).resolve().parents[1] / "src"
        holders = sorted(
            str(p) for p in root.rglob("*.py") if "ExecutionAuthorizationSigner" in _read(p)
        )
        allowed = {
            str(root / "execution_plane" / "router.py"),
            str(root / "execution_plane" / "authority.py"),
        }
        assert set(holders) == allowed, f"unexpected signer holders: {holders}"
