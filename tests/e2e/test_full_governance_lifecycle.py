"""
End-to-End Test: Proving the complete evidence-gated governance lifecycle.

Proves:
Candidate Strategy
→ Registry RESEARCH
→ Counterparty Thesis
→ ExperimentRegistry
→ Backtest
→ Portfolio Gates
→ VALIDATION
→ Frozen Holdout
→ HOLDOUT result
→ PAPER
→ Regime/Policy
→ Portfolio Allocation
→ Risk Engine
→ Execution Intent & Idempotency Key
→ Paper Fill against post-latency market state
→ Position Ledger
→ Performance Attribution
→ Lifecycle Progression

Invariants:
- Zero Live Capital ($0 live capital).
- No direct injection of ACTIVE + economic_edge_validated=True.
- No capital allocated before eligibility.
- Every threshold and gate is fully auditable.
"""

import pytest
import tempfile
import time
from pathlib import Path

from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    CounterpartyThesis,
    StrategyFamily,
    StrategyOrigin,
    StrategyRuleEvidence,
    StrategyParameterSet,
)
from src.strategies.registry import StrategyRegistry
from src.research.experiments import ExperimentRegistry, ExperimentRecord
from src.research.parameters import ResearchParameterSet
from src.research.holdout import SealedHoldoutManager, HoldoutViolationError
from src.portfolio.gates import (
    StrategyGateResult,
    GateStatus,
    LatencySensitivityGate,
    TemporalStabilityGate,
)
from src.portfolio.regime import RegimeSnapshot
from src.strategies.str002_v2 import BtcState
from src.portfolio.allocator import PortfolioAllocator
from src.risk.engine import DeterministicRiskEngine, RiskLimits, ProposedOrder
from src.risk.event_cluster import EventCluster
from src.execution.models import OrderIntent, OrderState, compute_idempotency_key
from src.execution.reconciliation import OrderLifecycleTracker
from src.paper.broker import PaperBroker, PaperOrderSide, PaperOrderType, PaperOrderStatus
from src.attribution.engine import PerformanceAttributionEngine


def test_full_governance_lifecycle_end_to_end():
    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = Path(temp_dir)
        exp_dir = base_dir / "experiments"
        holdout_audit_file = base_dir / "holdouts" / "audits.json"

        # -------------------------------------------------------------
        # STEP 1: Candidate Strategy Registration in RESEARCH stage
        # -------------------------------------------------------------
        registry = StrategyRegistry()

        thesis = CounterpartyThesis(
            counterparty_type="Urgent liquidity demander paying premium on crypto-event mispricings",
            economic_mechanism="Structural cross-market inventory imbalance and latency clearing frictions",
            why_trade_now="Stop cascade and margin calls require immediate liquidity execution",
            why_impact_may_be_transient="Temporary order book depletion that refills as passive makers replenish depth",
            why_it_may_be_information="Fundamental network level regime breaks or systemic insolvencies",
            falsification_conditions=[
                "Half-life of reversion exceeds 5 minutes",
                "Spread widening exceeds 30 bps",
                "Post-fill slippage exceeds 10 bps",
            ],
        )

        spec = StrategySpec(
            strategy_id="STR-GOV-001",
            name="Cross Venue Relative Value Alpha",
            family=StrategyFamily.RELATIVE_VALUE,
            origin=StrategyOrigin.QUANT,
            stage=StrategyStage.RESEARCH,
            economic_edge_validated=False,
            parameters={"threshold_z": 2.5, "lookback_window": 100},
            counterparty_thesis=thesis,
            metadata={"risk_budget_bps": 50.0, "tags": ["relative_value", "cross_venue"]},
        )

        registry.register(spec)
        registered_spec = registry.get(spec.strategy_id)
        assert registered_spec.stage == StrategyStage.RESEARCH
        assert registered_spec.economic_edge_validated is False

        # Attempting direct creation of ACTIVE + economic_edge_validated=True MUST FAIL
        with pytest.raises(ValueError, match=r"directly as ACTIVE"):
            bad_spec = StrategySpec(
                strategy_id="STR-ILLEGAL-001",
                name="Illegal Active Strategy",
                family=StrategyFamily.RELATIVE_VALUE,
                origin=StrategyOrigin.QUANT,
                stage=StrategyStage.ACTIVE,
                economic_edge_validated=True,
                parameters={},
                counterparty_thesis=thesis,
            )
            registry.register(bad_spec)

        # -------------------------------------------------------------
        # STEP 2: Parameter Fingerprinting & Durable Experimentation
        # -------------------------------------------------------------
        param_set = ResearchParameterSet(
            parameter_set_id="params-001",
            strategy_id=spec.strategy_id,
            strategy_version="1.0.0",
            parameters={"threshold_z": 2.5, "lookback_window": 100},
        )
        assert len(param_set.fingerprint) == 64

        exp_registry = ExperimentRegistry(storage_dir=exp_dir)
        rec = ExperimentRecord(
            experiment_id="exp-001",
            strategy_id=spec.strategy_id,
            strategy_version="1.0.0",
            config_fingerprint=param_set.fingerprint,
            result_metrics={"sharpe": 2.1, "max_drawdown": 0.04, "profit_factor": 1.8},
            cost_model_version="v1.4_conservative",
        )
        trial_count = exp_registry.record_experiment(rec)
        assert trial_count == 1
        assert exp_registry.get_trial_count(spec.strategy_id) == 1

        # -------------------------------------------------------------
        # STEP 3: Portfolio Gates Auditing (Provisional research thresholds)
        # -------------------------------------------------------------
        lat_gate = LatencySensitivityGate()
        lat_result = lat_gate.evaluate(
            sharpes_by_delay={0.0: 2.1, 1.0: 2.05, 5.0: 2.0, 30.0: 1.8},
            strategy_id=spec.strategy_id,
            strategy_version="1.0.0",
            config_fingerprint=param_set.fingerprint,
        )
        assert lat_result.status == GateStatus.PASS
        assert lat_result.threshold_is_provisional is True
        assert lat_result.parameter_fingerprint == param_set.fingerprint

        temp_gate = TemporalStabilityGate(rolling_window_periods=20)
        daily_returns = [0.005 + (0.002 if i % 2 == 0 else -0.001) for i in range(100)]
        temp_result = temp_gate.evaluate(
            daily_returns,
            strategy_id=spec.strategy_id,
            strategy_version="1.0.0",
            config_fingerprint=param_set.fingerprint,
        )
        assert temp_result.status == GateStatus.PASS

        # Promote stage to VALIDATION
        registry.update_stage(spec.strategy_id, StrategyStage.VALIDATION)
        val_spec = registry.get(spec.strategy_id)
        assert val_spec.stage == StrategyStage.VALIDATION

        # -------------------------------------------------------------
        # STEP 4: Sealed Holdout Evaluation
        # -------------------------------------------------------------
        holdout_mgr = SealedHoldoutManager(audit_storage_path=holdout_audit_file)
        audit_record = holdout_mgr.evaluate_holdout(
            strategy_id=spec.strategy_id,
            strategy_version="1.0.0",
            git_sha="git-test-commit-sha",
            parameter_set_fingerprint=param_set.fingerprint,
            hypothesis_description="Out of sample holdout validation across September 2026",
            holdout_dataset_bytes_or_hash="dataset-sha256-btc-sample-202610",
            metrics={"sharpe": 1.85, "max_drawdown": 0.05, "total_return": 0.12},
        )
        assert audit_record.audit_id is not None
        assert audit_record.result_metrics["sharpe"] == 1.85

        # Re-tuning with the same holdout is strictly forbidden
        with pytest.raises(HoldoutViolationError):
            holdout_mgr.evaluate_holdout(
                strategy_id=spec.strategy_id,
                strategy_version="1.0.0",
                git_sha="git-test-commit-sha",
                parameter_set_fingerprint="different_tuned_fingerprint",
                hypothesis_description="Tuned parameters on same holdout",
                holdout_dataset_bytes_or_hash="dataset-sha256-btc-sample-202610",
                metrics={"sharpe": 2.5},
            )

        # -------------------------------------------------------------
        # STEP 5: Promotion to PAPER Stage (Capital = $0 live, virtual paper only)
        # -------------------------------------------------------------
        registry.update_stage(spec.strategy_id, StrategyStage.HOLDOUT)
        registry.update_stage(spec.strategy_id, StrategyStage.PAPER)
        paper_spec = registry.get(spec.strategy_id)
        assert paper_spec.stage == StrategyStage.PAPER
        assert paper_spec.economic_edge_validated is False

        # -------------------------------------------------------------
        # STEP 6: Macro Regime & Portfolio Allocation
        # -------------------------------------------------------------
        regime = RegimeSnapshot(
            snapshot_id="reg-001",
            timestamp_ns=1_000_000_000,
            btc_regime_state=BtcState.FLAT.value,
            btc_realized_vol_5m=0.0012,
            btc_momentum_zscore=0.45,
            spread_state="NORMAL",
            volatility_regime="MEDIUM",
            liquidity_tier="TIER_1",
            cluster_risk_level="LOW",
        )

        allocator = PortfolioAllocator(
            total_equity_usd=100_000.0,
            max_strategy_allocation_pct=0.30,
            live_capital_locked=True,
        )

        # Register cluster
        btc_cluster = EventCluster(
            cluster_id="BTC_DIRECTIONAL",
            description="BTC directional exposure",
            max_gross_exposure_usd=50_000.0,
            max_net_exposure_usd=50_000.0,
            stress_loss_limit_usd=15_000.0,
            member_weights={"BTC-USDT": 1.0},
        )

        budgets = allocator.allocate(
            strategies=[paper_spec],
            strategy_metrics={paper_spec.strategy_id: {"sharpe": 1.85, "trial_count": 1, "edge_half_life_s": 60.0}},
        )
        assert paper_spec.strategy_id in budgets
        assert budgets[paper_spec.strategy_id].allocated_capital_usd == 0.0
        assert budgets[paper_spec.strategy_id].authorized_live_budget == 0.0
        assert budgets[paper_spec.strategy_id].is_live_eligible is False
        assert budgets[paper_spec.strategy_id].paper_budget_usd == 10_000.0
        allocated_paper_capital = budgets[paper_spec.strategy_id].paper_budget_usd

        # -------------------------------------------------------------
        # STEP 7: Risk Engine Evaluation ($0 Live Capital Invariant)
        # -------------------------------------------------------------
        risk_engine = DeterministicRiskEngine(
            initial_equity_usd=100_000.0,
            limits=RiskLimits(live_capital_locked=True),
        )
        risk_engine.register_event_cluster(btc_cluster)

        proposed = ProposedOrder(
            order_id="ord-lifecycle-001",
            strategy_id=paper_spec.strategy_id,
            symbol="BTC-USDT",
            side="BUY",
            quantity=0.2,
            price=60_000.0,
            venue="BINANCE",
            timestamp_s=time.time(),
        )

        # Physical Check 1: LIVE order MUST BE REJECTED because live_capital_locked=True
        live_decision = risk_engine.evaluate_order(proposed, is_live=True)
        assert live_decision.approved is False
        assert live_decision.violation_code.value == "CAPITAL_LOCKED"

        # Physical Check 2: PAPER order is approved
        paper_decision = risk_engine.evaluate_order(proposed, is_live=False)
        assert paper_decision.approved is True

        # -------------------------------------------------------------
        # STEP 8: Execution Domain Contracts & Lifecycle Tracking
        # -------------------------------------------------------------
        idem_key = compute_idempotency_key(
            strategy_id=paper_spec.strategy_id,
            order_intent_id="intent-001",
            round_trip_index=0,
            timestamp_bucket=100_000,
        )

        intent = OrderIntent(
            order_intent_id="intent-001",
            strategy_id=paper_spec.strategy_id,
            symbol=proposed.symbol,
            side=proposed.side,
            order_type="MARKET",
            quantity=proposed.quantity,
            venue=proposed.venue,
            idempotency_key=idem_key,
        )

        tracker = OrderLifecycleTracker()
        tracker.track_order(intent)
        assert tracker.get_state(intent.order_intent_id) == OrderState.SUBMITTED

        tracker.transition_to(intent.order_intent_id, OrderState.ROUTED)
        assert tracker.get_state(intent.order_intent_id) == OrderState.ROUTED

        tracker.transition_to(intent.order_intent_id, OrderState.ACKNOWLEDGED)
        assert tracker.get_state(intent.order_intent_id) == OrderState.ACKNOWLEDGED

        # -------------------------------------------------------------
        # STEP 9: Realistic Paper Broker Fill (Post-Latency Execution)
        # -------------------------------------------------------------
        broker = PaperBroker(
            initial_cash_usd=100_000.0,
            simulated_latency_ms=20.0,  # 20ms transit latency
            taker_fee_bps=5.0,
            base_slippage_bps=2.0,
        )

        t0 = 1_000_000_000
        client_bbo = {"best_bid": 60_000.0, "best_ask": 60_010.0, "bid_size": 2.0, "ask_size": 2.0}

        order = broker.submit_order(
            symbol=intent.symbol,
            side=PaperOrderSide.BUY,
            order_type=PaperOrderType.MARKET,
            quantity=intent.quantity,
            venue=intent.venue,
            current_time_ns=t0,
            current_bbo=client_bbo,
            permit=paper_decision,
        )

        # INVARIANT: Market order does NOT fill using stale T0 quote!
        assert order.status == PaperOrderStatus.SUBMITTED
        assert order.filled_qty == 0.0

        # Post-latency event arrives at T0 + 25ms with price ask = 60,020.0
        post_latency_ask = 60_020.0
        trades = broker.on_market_event(
            symbol=intent.symbol,
            best_bid=60_010.0,
            best_ask=post_latency_ask,
            event_time_ns=t0 + 25_000_000,
            ask_size=5.0,
            bid_size=5.0,
        )

        assert len(trades) == 1
        assert order.status == PaperOrderStatus.FILLED
        assert order.filled_price >= post_latency_ask
        assert order.fee_paid > 0.0

        # Update execution tracker to FILLED
        tracker.transition_to(intent.order_intent_id, OrderState.FILLED)
        assert tracker.get_state(intent.order_intent_id) == OrderState.FILLED

        # -------------------------------------------------------------
        # STEP 10: Performance Attribution
        # -------------------------------------------------------------
        attribution = PerformanceAttributionEngine(benchmark_symbol="BTC-USDT")
        attribution.record_trade(
            trade_id=trades[0].trade_id,
            strategy_id=paper_spec.strategy_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=trades[0].quantity,
            decision_price=proposed.price,
            execution_price=trades[0].price,
            fee_paid=trades[0].fee,
            timestamp_ns=trades[0].timestamp_ns,
        )

        summary = attribution.compute_attribution(
            strategy_gross_pnls={paper_spec.strategy_id: 150.0},
            market_benchmark_return=0.015,
            strategy_betas={paper_spec.strategy_id: 0.5},
            average_capital_usd={paper_spec.strategy_id: allocated_paper_capital},
        )
        assert paper_spec.strategy_id in summary
        report = summary[paper_spec.strategy_id]
        assert report.strategy_id == paper_spec.strategy_id
        assert report.net_pnl < report.gross_pnl  # Reflects execution drag and fees

        # Final invariant check: Even after successful paper run, economic edge is NOT validated
        final_spec = registry.get(spec.strategy_id)
        assert final_spec.economic_edge_validated is False
        assert final_spec.stage == StrategyStage.PAPER
