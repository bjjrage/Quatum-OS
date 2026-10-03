"""
24-Point Comprehensive Red-Team Attack Matrix for v1.4.1.

Attacks:
1. recorder resume with matching fingerprint
2. recorder resume missing AcceptanceState/import
3. new fingerprint accidental clock carryover
4. BTC DOWN trying to enter STR-002
5. RUNNING_HARD_UP trying to enter
6. hardcoded z-score presented as validated
7. threshold changed without fingerprint change
8. restart ExperimentRegistry and lose trial_count
9. duplicate experiment deletion/edit
10. unknown StrategySpec field silently ignored
11. Tier5 small tradable incorrectly blocked
12. UNTRADABLE asset allowed to execute
13. Monte Carlo using insufficient empirical sample
14. IID Gaussian fallback pretending empirical result
15. sixth prop attempt after five failures
16. new strategy version incorrectly permanently blocked
17. second prop account with ambiguous copy-trading rules
18. same STR-002 exposure split across accounts to evade caps
19. strategy tries to relax Risk hard stop
20. delayed market order fills using stale T0 BBO
21. duplicate execution idempotency key
22. reused holdout after parameter tuning
23. direct ACTIVE/economic_edge_validated injection
24. live capital routing while locked
"""

import pytest
import tempfile
import time
from pathlib import Path
from pydantic import ValidationError

from src.quality.acceptance import RuntimeManifest, AcceptanceState
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyFamily,
    StrategyOrigin,
    CounterpartyThesis,
    StrategyParameterSet,
)
from src.strategies.registry import StrategyRegistry
from src.strategies.str002_v2 import (
    BtcState,
    BtcStateClassifier,
    get_str002_model_variants,
)
from src.portfolio.regime import RegimeSnapshot
from src.quality.tradability import (
    TradabilityTier,
    LiquidityTierPolicy,
)
from src.risk.capital_pockets import (
    PocketType,
    CapitalPocket,
    ManualEvidenceObject,
    MultiAccountEvidenceGate,
    PropRuleProfile,
    TradeSample,
    PropExamMonteCarloSimulator,
    MultiAccountRiskAggregator,
)
from src.risk.engine import DeterministicRiskEngine, RiskLimits, ProposedOrder, RiskViolationCode
from src.risk.event_cluster import EventCluster
from src.research.parameters import ResearchParameterSet
from src.research.experiments import ExperimentRegistry, ExperimentRecord
from src.research.holdout import SealedHoldoutManager, HoldoutViolationError
from src.execution.models import OrderIntent, OrderState, compute_idempotency_key
from src.execution.reconciliation import OrderLifecycleTracker
from src.paper.broker import PaperBroker, PaperOrderSide, PaperOrderType, PaperOrderStatus


# Vector 1: Recorder resume with matching fingerprint
def test_attack_1_recorder_resume_matching_fingerprint():
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_file = Path(temp_dir) / "test_manifest.json"
        m1, resumed1 = RuntimeManifest.resume_or_create(
            manifest_file, pid=123, git_sha="sha1", config_fingerprint="fp-12345"
        )
        assert resumed1 is False
        m1.save(manifest_file)

        m2, resumed2 = RuntimeManifest.resume_or_create(
            manifest_file, pid=456, git_sha="sha1", config_fingerprint="fp-12345"
        )
        assert resumed2 is True
        assert m2.run_id == m1.run_id
        assert m2.started_at_timestamp_ns == m1.started_at_timestamp_ns
        assert m2.started_at_utc == m1.started_at_utc


# Vector 2: Recorder resume missing AcceptanceState/import
def test_attack_2_recorder_resume_missing_import():
    state = AcceptanceState.RUNNING
    assert state.value == "RUNNING"
    assert hasattr(RuntimeManifest, "resume_or_create")


# Vector 3: New fingerprint accidental clock carryover
def test_attack_3_new_fingerprint_no_clock_carryover():
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest_file = Path(temp_dir) / "test_manifest.json"
        m1, _ = RuntimeManifest.resume_or_create(
            manifest_file, pid=123, git_sha="sha1", config_fingerprint="fp-old"
        )
        m1.save(manifest_file)

        m2, resumed2 = RuntimeManifest.resume_or_create(
            manifest_file, pid=456, git_sha="sha1", config_fingerprint="fp-new"
        )
        assert resumed2 is False
        assert m2.run_id != m1.run_id
        assert m2.config_fingerprint == "fp-new"


# Vector 4: BTC DOWN trying to enter STR-002
def test_attack_4_btc_down_blocks_str002():
    state = BtcStateClassifier.classify(
        ret_1m=-0.0005, ret_5m=-0.0015, ret_15m=-0.002, btc_realized_vol_5m=0.001
    )
    assert state == BtcState.DOWN
    allowed, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(state, z_score=-3.5)
    assert allowed is False
    assert sizing == 0.0


# Vector 5: RUNNING_HARD_UP trying to enter STR-002
def test_attack_5_running_hard_up_blocks_str002():
    state = BtcStateClassifier.classify(
        ret_1m=0.002, ret_5m=0.005, ret_15m=0.008, btc_realized_vol_5m=0.001
    )
    assert state == BtcState.RUNNING_HARD_UP
    allowed, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(state, z_score=-3.5)
    assert allowed is False
    assert sizing == 0.0


# Vector 6: Hardcoded z-score presented as validated
def test_attack_6_hardcoded_zscore_not_presented_as_validated():
    variants = get_str002_model_variants()
    m0 = next(v for v in variants if v["variant_id"] == "M0")
    assert m0["status"] == "UNVALIDATED"


# Vector 7: Threshold changed without fingerprint change
def test_attack_7_threshold_change_changes_fingerprint():
    p1 = ResearchParameterSet(
        parameter_set_id="p1", strategy_id="STR-002", strategy_version="2.0", parameters={"z_entry": 2.0}
    )
    p2 = ResearchParameterSet(
        parameter_set_id="p2", strategy_id="STR-002", strategy_version="2.0", parameters={"z_entry": 2.05}
    )
    assert p1.fingerprint != p2.fingerprint


# Vector 8: Restart ExperimentRegistry and lose trial_count
def test_attack_8_restart_experiment_registry_retains_trial_count():
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = Path(temp_dir)
        reg1 = ExperimentRegistry(storage_dir=storage)
        rec1 = ExperimentRecord(
            experiment_id="exp-1",
            strategy_id="STR-001",
            strategy_version="1.0",
            result_metrics={"sharpe": 1.5},
        )
        rec2 = ExperimentRecord(
            experiment_id="exp-2",
            strategy_id="STR-001",
            strategy_version="1.0",
            result_metrics={"sharpe": 1.7},
        )
        reg1.record_experiment(rec1)
        reg1.record_experiment(rec2)
        assert reg1.get_trial_count("STR-001") == 2

        # Restart in new instance
        reg2 = ExperimentRegistry(storage_dir=storage)
        assert reg2.get_trial_count("STR-001") == 2


# Vector 9: Duplicate experiment deletion/edit
def test_attack_9_duplicate_experiment_deletion_forbidden():
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = Path(temp_dir)
        reg = ExperimentRegistry(storage_dir=storage)
        rec = ExperimentRecord(
            experiment_id="exp-1",
            strategy_id="STR-001",
            strategy_version="1.0",
            result_metrics={"sharpe": 1.5},
        )
        reg.record_experiment(rec)
        # Attempting to record identical experiment_id raises ValueError
        with pytest.raises(ValueError, match="already exists"):
            reg.record_experiment(rec)

        # Deleting experiment is forbidden
        with pytest.raises(RuntimeError, match="cannot be deleted"):
            reg.delete_experiment("exp-1")


# Vector 10: Unknown StrategySpec field silently ignored
def test_attack_10_unknown_strategyspec_field_rejected():
    thesis = CounterpartyThesis(
        counterparty_type="retail",
        economic_mechanism="latency",
        why_trade_now="chasing",
        why_impact_may_be_transient="reversion",
        why_it_may_be_information="news",
        falsification_conditions=["adverse move"],
    )
    with pytest.raises(ValidationError):
        StrategySpec(
            strategy_id="STR-HACK",
            name="Hack",
            family=StrategyFamily.RELATIVE_VALUE,
            origin=StrategyOrigin.QUANT,
            stage=StrategyStage.RESEARCH,
            parameters={},
            counterparty_thesis=thesis,
            backdoor_leverage_multiplier=999,  # Unknown extra field
        )


# Vector 11: Tier5 small tradable incorrectly blocked
def test_attack_11_tier5_small_tradable_allowed_with_cap():
    policy = LiquidityTierPolicy(
        max_spread_bps=15.0,
        min_depth_0_5pct_usd=25_000.0,
        min_volume_5m_usd=100_000.0,
        tier5_max_position_usd=5_000.0,
    )
    score_t5 = policy.evaluate(
        symbol="MARGINAL_ALT",
        timestamp_ns=1700000000_000000000,
        spread_bps=14.0,
        depth_0_5pct_usd=28_000.0,
        volume_5m_usd=120_000.0,
        clock_sync_offset_ms=10.0,
        manifest_valid=True,
    )
    assert score_t5.tier == TradabilityTier.TIER_5_SMALL_TRADABLE
    assert score_t5.tradable is True
    assert score_t5.max_position_usd == 5_000.0
    assert score_t5.limit_orders_only is True


# Vector 12: UNTRADABLE asset allowed to execute
def test_attack_12_untradable_asset_strictly_blocked():
    policy = LiquidityTierPolicy(max_spread_bps=15.0)
    score_untradable = policy.evaluate(
        symbol="ILLIQUID_ALT",
        timestamp_ns=1700000000_000000000,
        spread_bps=45.0,  # Blowout spread > 15 bps
        depth_0_5pct_usd=5_000.0,
        volume_5m_usd=20_000.0,
    )
    assert score_untradable.tier == TradabilityTier.TIER_5_UNTRADABLE
    assert score_untradable.tradable is False
    assert score_untradable.max_position_usd is None or score_untradable.max_position_usd == 0.0


# Vector 13: Monte Carlo using insufficient empirical sample
def test_attack_13_monte_carlo_insufficient_sample():
    simulator = PropExamMonteCarloSimulator()
    profile = PropRuleProfile(provider_id="Alpha")
    res = simulator.simulate("STR-002", profile, trades=[])
    assert res["status"] == "PENDING / INSUFFICIENT_DATA"
    assert res["is_eligible"] is False
    assert res["pass_probability"] == 0.0


# Vector 14: IID Gaussian fallback pretending empirical result
def test_attack_14_iid_gaussian_fallback_rejected():
    simulator = PropExamMonteCarloSimulator()
    profile = PropRuleProfile(provider_id="Alpha")
    res = simulator.simulate("STR-002", profile, daily_mean_ret=0.05, daily_vol_ret=0.01)
    assert res["status"] == "PENDING / INSUFFICIENT_DATA"
    assert res["pass_probability"] == 0.0
    assert "Gaussian IID fallback strictly forbidden" in res["reason"]


# Vector 15: Sixth prop attempt after five failures
def test_attack_15_sixth_prop_attempt_blocked():
    simulator = PropExamMonteCarloSimulator()
    for _ in range(5):
        simulator.record_attempt_result(
            "STR-002", "PropCo", passed=False, strategy_version="v2.0", profile_version="v1.0"
        )

    profile = PropRuleProfile(provider_id="PropCo", version="v1.0")
    res = simulator.simulate("STR-002", profile, strategy_version="v2.0", trades=[])
    assert res["status"] == "BLOCKED"
    assert res["is_eligible"] is False
    assert "KILL_SWITCH_ACTIVE" in res["reason"]


# Vector 16: New strategy version incorrectly permanently blocked
def test_attack_16_new_strategy_version_not_permanently_blocked():
    simulator = PropExamMonteCarloSimulator()
    for _ in range(5):
        simulator.record_attempt_result(
            "STR-002", "PropCo", passed=False, strategy_version="v2.0", profile_version="v1.0"
        )

    assert simulator.is_combination_eligible("STR-002", "PropCo", "v2.0", "v1.0") is False
    # v2.1 has fresh record
    assert simulator.is_combination_eligible("STR-002", "PropCo", "v2.1", "v1.0") is True


# Vector 17: Second prop account with ambiguous copy-trading rules
def test_attack_17_second_prop_account_ambiguous_copy_rules():
    gate = MultiAccountEvidenceGate()
    gate.register_account("PropCo", "ACC-1")

    evidence = ManualEvidenceObject(
        provider_name="PropCo",
        account_id="ACC-2",
        multiple_accounts_allowed=True,
        same_bot_allowed=True,
        same_strategy_allowed=True,
        does_same_bot_count_as_copy_trading=True,  # Violates policy
        has_signed_contract_terms=True,
        has_documented_scaling_rules=True,
        has_cross_account_risk_confirmation=True,
        written_evidence_text="Contract signed with full verification of rules and terms.",
    )
    ok, msg = gate.register_account("PropCo", "ACC-2", evidence=evidence)
    assert ok is False
    assert "PENDING_MANUAL_EVIDENCE" in msg


# Vector 18: Same STR-002 exposure split across accounts to evade caps
def test_attack_18_same_strategy_split_across_accounts():
    aggregator = MultiAccountRiskAggregator(max_global_strategy_pct=0.30, max_global_single_asset_pct=0.80)
    eq = 50_000.0
    p1 = CapitalPocket(
        pocket_id="P1",
        pocket_type=PocketType.OWN,
        account_id="A1",
        initial_equity_usd=eq,
        current_equity_usd=eq,
        peak_equity_usd=eq,
        daily_starting_equity_usd=eq,
    )
    p2 = CapitalPocket(
        pocket_id="P2",
        pocket_type=PocketType.PROP,
        account_id="A2",
        initial_equity_usd=eq,
        current_equity_usd=eq,
        peak_equity_usd=eq,
        daily_starting_equity_usd=eq,
    )
    aggregator.add_pocket(p1)
    aggregator.add_pocket(p2)

    # ACC 1: $20k in STR-002, ACC 2: $20k in STR-002 -> Total $40k = 40% > 30% cap!
    aggregator.update_positions(
        "A1",
        {"BTCUSDT": 0.285},
        {"BTCUSDT": 70_000.0},
        strategy_allocations={"A1": {"STR-002": {"BTCUSDT": 0.285}}},
    )
    aggregator.update_positions(
        "A2",
        {"BTCUSDT": 0.285},
        {"BTCUSDT": 70_000.0},
        strategy_allocations={"A2": {"STR-002": {"BTCUSDT": 0.285}}},
    )

    approved, reason, _ = aggregator.evaluate_global_risk()
    assert approved is False
    assert "breaches maximum strategy concentration" in reason


# Vector 19: Strategy tries to relax Risk hard stop
def test_attack_19_strategy_cannot_relax_risk_hard_stop():
    engine = DeterministicRiskEngine(initial_equity_usd=100_000.0)
    engine.trigger_kill_switch("CRITICAL_CIRCUIT_BREAKER")

    order = ProposedOrder(
        order_id="ord-bad",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.1,
        price=60_000.0,
    )
    decision = engine.evaluate_order(order, is_live=False)
    assert decision.approved is False
    assert decision.violation_code == RiskViolationCode.KILL_SWITCH_ACTIVE


# Vector 20: Delayed market order fills using stale T0 BBO
def test_attack_20_delayed_market_order_does_not_fill_stale_t0_quote():
    broker = PaperBroker(initial_cash_usd=100_000.0, simulated_latency_ms=20.0, enforce_risk_permit=False)
    t0 = 1_000_000_000
    stale_bbo = {"best_bid": 60_000.0, "best_ask": 60_010.0, "ask_size": 2.0, "bid_size": 2.0}

    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=1.0,
        current_time_ns=t0,
        current_bbo=stale_bbo,
    )

    # Order must NOT be filled at T0 with stale ask 60,010.0
    assert order.status == PaperOrderStatus.SUBMITTED
    assert order.filled_qty == 0.0

    # Market moves to 60,050.0 at T0 + 25ms
    broker.on_market_event("BTC-USDT", best_bid=60_040.0, best_ask=60_050.0, event_time_ns=t0 + 25_000_000)
    assert order.status == PaperOrderStatus.FILLED
    assert order.filled_price >= 60_050.0


# Vector 21: Duplicate execution idempotency key
def test_attack_21_duplicate_execution_idempotency_key():
    tracker = OrderLifecycleTracker()
    key = "idem-unique-12345"
    intent1 = OrderIntent(
        order_intent_id="int-1",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        venue="BINANCE",
        side="BUY",
        order_type="MARKET",
        quantity=1.0,
        idempotency_key=key,
    )
    tracker.track_order(intent1)

    intent2 = OrderIntent(
        order_intent_id="int-1",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        venue="BINANCE",
        side="BUY",
        order_type="MARKET",
        quantity=1.0,
        idempotency_key=key,
    )
    with pytest.raises(ValueError, match="already tracked"):
        tracker.track_order(intent2)


# Vector 22: Reused holdout after parameter tuning
def test_attack_22_reused_holdout_after_parameter_tuning():
    with tempfile.TemporaryDirectory() as temp_dir:
        audit_file = Path(temp_dir) / "audits.json"
        mgr = SealedHoldoutManager(audit_storage_path=audit_file)
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="sha1_valid_hash",
            dataset_fingerprint="dataset-1-hash-12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="fp-initial",
            hypothesis_description="Initial holdout evaluation",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe", "max_drawdown"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="sha1_valid_hash",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="fp-initial",
        )
        mgr.record_evaluation_result(
            access_id=acc.access_id,
            result_metrics={"sharpe": 1.5},
        )
        with pytest.raises(HoldoutViolationError):
            mgr.create_preregistration(
                strategy_id="STR-001",
                strategy_version="1.0.1",
                git_sha="sha1_valid_hash",
                dataset_fingerprint="dataset-1-hash-12345678",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="fp-tuned",
                hypothesis_description="Tuned parameters on same holdout",
                falsification_criteria=["Sharpe < 1.0"],
                primary_metrics=["sharpe", "max_drawdown"],
                analysis_plan_fingerprint="plan_hash_12345678",
            )


# Vector 23: Direct ACTIVE/economic_edge_validated injection
def test_attack_23_direct_active_validated_injection_rejected():
    registry = StrategyRegistry()
    thesis = CounterpartyThesis(
        counterparty_type="retail",
        economic_mechanism="latency",
        why_trade_now="chasing",
        why_impact_may_be_transient="reversion",
        why_it_may_be_information="news",
        falsification_conditions=["adverse move"],
    )
    spec = StrategySpec(
        strategy_id="STR-BYPASS",
        name="Bypass",
        family=StrategyFamily.RELATIVE_VALUE,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
        economic_edge_validated=True,
        counterparty_thesis=thesis,
    )
    with pytest.raises(ValueError, match=r"directly as ACTIVE"):
        registry.register(spec)


# Vector 24: Live capital routing while locked
def test_attack_24_live_capital_routing_blocked_while_locked():
    engine = DeterministicRiskEngine(limits=RiskLimits(live_capital_locked=True))
    order = ProposedOrder(
        order_id="ord-live",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.1,
        price=60_000.0,
    )
    decision = engine.evaluate_order(order, is_live=True)
    assert decision.approved is False
    assert decision.violation_code == RiskViolationCode.CAPITAL_LOCKED
    assert "Live capital is locked" in decision.reason
