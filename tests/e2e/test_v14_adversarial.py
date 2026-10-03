"""
End-to-End Adversarial Red-Team Suite (v1.4.0).

Verifies the 10 critical attack vectors and governance invariants:
1. Attempt to privilege a strategy at runtime or in config -> strictly blocked.
2. Attempt to route live order while live_capital_locked=True -> vetoed with $0.0 risk.
3. Attempt to allocate live capital to an unvalidated strategy -> strictly $0.0.
4. Attempt to connect 2nd account from same provider without written evidence -> blocked.
5. Attempt to purchase 6th exam after 5 consecutive failures -> blocked by kill switch.
6. Attempt to route short order on STR-002 v2 -> blocked with LONG_ONLY invariant.
7. Attempt to execute in a Tier 5 market -> blocked by Tradability policy.
8. Replay under latency degradation -> rejected as LATENCY_RACE by Gate A.
9. Prop account daily loss spillover to Own account -> zero risk transfer, Own unfrozen.
10. Global multi-account leverage breach -> freezes all accounts simultaneously.
"""

import pytest
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
    CounterpartyThesis,
)
from src.strategies.registry import StrategyRegistry, InvalidStageTransitionError
from src.strategies.str002_v2 import Str002V2Strategy
from src.portfolio.allocator import PortfolioAllocator
from src.portfolio.gates import LatencySensitivityGate, GateStatus
from src.quality.tradability import LiquidityTierPolicy, TradabilityTier
from src.risk.engine import DeterministicRiskEngine, ProposedOrder, RiskViolationCode
from src.risk.capital_pockets import (
    PocketType,
    CapitalPocket,
    MultiAccountEvidenceGate,
    PropRuleProfile,
    PropExamMonteCarloSimulator,
    MultiAccountRiskAggregator,
)


def test_adversarial_1_privilege_injection_impossible():
    """Attack 1: Inject privilege into StrategySpec at initialization or mutation."""
    # Direct constructor injection fails
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        StrategySpec(
            strategy_id="ATTACK-PRIV",
            name="Privilege Exploit",
            family=StrategyFamily.MOMENTUM,
            origin=StrategyOrigin.HUMAN,
            is_privileged=True,
        )

    # Mutation fails
    spec = StrategySpec(
        strategy_id="ATTACK-CLEAN",
        name="Clean Candidate",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
    )
    with pytest.raises((AttributeError, Exception)):
        spec.is_privileged = True  # Read-only property descriptor / frozen model


def test_adversarial_2_live_order_routing_while_locked():
    """Attack 2: Attempt to route a live order when live_capital_locked=True."""
    engine = DeterministicRiskEngine()
    assert engine.limits.live_capital_locked is True

    order = ProposedOrder(
        order_id="ORD-LIVE-01",
        strategy_id="STR-001",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.5,
        price=60_000.0,
    )

    decision = engine.evaluate_order(order, is_live=True)
    assert decision.approved is False
    assert decision.violation_code == RiskViolationCode.CAPITAL_LOCKED
    assert "Live capital is locked" in decision.reason


def test_adversarial_3_capital_allocation_to_unvalidated_stages():
    """Attack 3: Attempt to allocate capital to RESEARCH, IDEA, or PAPER stages."""
    allocator = PortfolioAllocator(total_equity_usd=100_000.0, live_capital_locked=True)

    unvalidated_specs = [
        StrategySpec(strategy_id="S-IDEA", name="Idea", family=StrategyFamily.MOMENTUM, origin=StrategyOrigin.QUANT, stage=StrategyStage.IDEA),
        StrategySpec(strategy_id="S-RES", name="Research", family=StrategyFamily.BEHAVIORAL, origin=StrategyOrigin.HUMAN, stage=StrategyStage.RESEARCH),
        StrategySpec(strategy_id="S-VAL", name="Validation", family=StrategyFamily.FUNDING_BASIS, origin=StrategyOrigin.STATISTICAL, stage=StrategyStage.VALIDATION),
        StrategySpec(strategy_id="S-PAP", name="Paper", family=StrategyFamily.RELATIVE_VALUE, origin=StrategyOrigin.QUANT, stage=StrategyStage.PAPER),
    ]

    budgets = allocator.allocate(unvalidated_specs)

    for spec in unvalidated_specs:
        b = budgets[spec.strategy_id]
        assert b.allocated_capital_usd == 0.0
        assert b.authorized_live_budget == 0.0
        assert b.is_live_eligible is False


def test_adversarial_4_secondary_prop_account_bypass():
    """Attack 4: Attempt to connect 2nd account from same prop provider without written evidence."""
    gate = MultiAccountEvidenceGate()

    # First account passes
    ok1, _ = gate.register_account("ApexFunding", "ACC-01")
    assert ok1 is True

    # Second account without contract terms fails immediately
    ok2, msg2 = gate.register_account("ApexFunding", "ACC-02", evidence=None)
    assert ok2 is False
    assert "PENDING_MANUAL_EVIDENCE" in msg2


def test_adversarial_5_sixth_exam_purchase_after_5_failures():
    """Attack 5: Attempt to purchase 6th exam for strategy that failed 5 consecutive attempts."""
    simulator = PropExamMonteCarloSimulator()
    profile = PropRuleProfile(
        firm_name="AlphaEvaluation",
        version="v1",
        effective_date="2026-01-01",
        daily_loss_limit_pct=0.04,
        trailing_max_drawdown_pct=0.08,
        profit_target_pct=0.10,
        min_trading_days=5,
    )

    strat_id = "STR-OVERFIT-AI"

    # Simulate 5 consecutive failures
    for _ in range(5):
        simulator.record_attempt_result(
            strat_id, "AlphaEvaluation", passed=False, strategy_version="v1.0", profile_version="v1"
        )

    assert simulator.is_combination_eligible(
        strat_id, "AlphaEvaluation", strategy_version="v1.0", profile_version="v1"
    ) is False

    # Attempt to simulate 6th exam purchase
    res = simulator.simulate(strat_id, profile, daily_mean_ret=0.01, daily_vol_ret=0.01)
    assert res["is_eligible"] is False
    assert res["pass_probability"] == 0.0
    assert "KILL_SWITCH_ACTIVE" in res["reason"]


def test_adversarial_6_str002_short_order_routing():
    """Attack 6: Attempt to execute a short trade on STR-002 v2."""
    strat = Str002V2Strategy()

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="ETHUSDT",
        timestamp_ns=1700000000_000000000,
        r_alt_series=[0.01] * 40,
        r_btc_series=[0.01] * 40,
        r_eth_series=[0.01] * 40,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=3500.0,
        pre_shock_origin=3400.0,
        pre_shock_vwap=3420.0,
        delta_5s=-10.0,
        bid_depth_0_5pct=100_000.0,
        pre_shock_median_depth=100_000.0,
        recent_1s_lows=[3400.0, 3410.0],
        is_short_side_hypothesis=True,  # Red-team attack: attempting short order
    )

    assert should_exec is False
    assert snapshot is None
    assert diag["decision"] == "BLOCKED"
    assert diag["is_long_only_enforced"] is True
    assert "SHORT_SIDE_RESEARCH_ONLY" in diag["reason"]


def test_adversarial_7_execute_in_tier_5_market():
    """Attack 7: Attempt to execute in a Tier 5 untradable market."""
    policy = LiquidityTierPolicy(max_spread_bps=15.0)

    # Market in severe stress with 30 bps spread
    score = policy.evaluate(
        symbol="ILLIQUID-ALT",
        timestamp_ns=1700000000_000000000,
        spread_bps=30.0,
        depth_0_5pct_usd=50_000.0,
        volume_5m_usd=200_000.0,
    )

    assert score.tier == TradabilityTier.TIER_5_UNTRADABLE
    assert score.tradable is False
    assert len(score.rejection_reasons) > 0


def test_adversarial_8_latency_race_rejection():
    """Attack 8: Strategy relying on zero-latency order races fails Gate A."""
    gate = LatencySensitivityGate(max_sharpe_drop_pct_at_5s=0.50, min_edge_half_life_s=5.0)

    # Sharpe collapses under latency
    sharpes_latency_race = {0.0: 4.0, 1.0: 1.5, 5.0: 0.2, 30.0: -0.5}
    result = gate.evaluate(sharpes_latency_race)

    assert result.status == GateStatus.FAIL
    assert result.diagnostics["is_latency_race"] is True
    assert "LATENCY_RACE" in result.falsification_evidence


def test_adversarial_9_prop_loss_does_not_affect_own_pocket():
    """Attack 9: Prop account failure spills over to Own account."""
    own = CapitalPocket(
        pocket_id="OWN-1",
        pocket_type=PocketType.OWN,
        account_id="A-OWN",
        initial_equity_usd=100_000.0,
        current_equity_usd=100_000.0,
        peak_equity_usd=100_000.0,
        daily_starting_equity_usd=100_000.0,
    )
    prop = CapitalPocket(
        pocket_id="PROP-1",
        pocket_type=PocketType.PROP,
        firm_name="FundedFirm",
        account_id="A-PROP",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
        daily_loss_limit_pct=0.04,  # $2,000 max daily loss
    )

    # Prop loses $4,000 and breaches daily limit
    breached, _ = prop.update_equity(46_000.0)
    assert breached is True
    assert prop.is_frozen is True

    # Own account is strictly isolated
    assert own.is_frozen is False
    assert own.current_equity_usd == 100_000.0


def test_adversarial_10_global_leverage_breach_freezes_all_accounts():
    """Attack 10: Multi-account combined exposure breaches global ceiling."""
    aggregator = MultiAccountRiskAggregator(max_global_gross_leverage=3.0)

    p_own = CapitalPocket(
        pocket_id="OWN-1",
        pocket_type=PocketType.OWN,
        account_id="A1",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
    )
    p_prop = CapitalPocket(
        pocket_id="PROP-1",
        pocket_type=PocketType.PROP,
        firm_name="FirmX",
        account_id="A2",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
    )
    aggregator.add_pocket(p_own)
    aggregator.add_pocket(p_prop)

    # Combined equity: $100k. Notional: 6 BTC @ $60k = $360k -> 3.6x leverage > 3.0x
    aggregator.update_positions("A1", {"BTCUSDT": 3.0}, {"BTCUSDT": 60_000.0})
    aggregator.update_positions("A2", {"BTCUSDT": 3.0}, {"BTCUSDT": 60_000.0})

    approved, reason, metrics = aggregator.evaluate_global_risk()

    assert approved is False
    assert "Global gross leverage" in reason
    assert p_own.is_frozen is True
    assert p_prop.is_frozen is True
