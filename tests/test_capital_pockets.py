"""Unit tests for Capital Pockets, Empirical Prop Monte Carlo, and Multi-Account Risk Governance."""

import pytest
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
from src.risk.event_cluster import EventCluster


def test_capital_pockets_isolation_and_selective_freeze():
    """Verify zero risk transfer between OWN and PROP, and selective freeze on daily loss breach."""
    own_pocket = CapitalPocket(
        pocket_id="POCK-OWN-01",
        pocket_type=PocketType.OWN,
        account_id="ACC-OWN-01",
        initial_equity_usd=100_000.0,
        current_equity_usd=100_000.0,
        peak_equity_usd=100_000.0,
        daily_starting_equity_usd=100_000.0,
    )
    prop_pocket = CapitalPocket(
        pocket_id="POCK-PROP-01",
        pocket_type=PocketType.PROP,
        firm_name="AlphaProp",
        account_id="ACC-PROP-01",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
        daily_loss_limit_pct=0.05,  # $2,500 daily loss limit
    )

    # 1. Prop pocket drops by $3,000 (breaches daily limit)
    breached, reason = prop_pocket.update_equity(47_000.0)
    assert breached is True
    assert prop_pocket.is_frozen is True
    assert "daily loss limit" in reason

    # INVARIANT: Zero risk transfer — OWN pocket is completely unaffected and unfrozen
    assert own_pocket.is_frozen is False
    assert own_pocket.current_equity_usd == 100_000.0


def test_multi_account_evidence_gate_explicit_questions():
    """
    Verify MultiAccountEvidenceGate allows 1st account, blocks 2nd without complete written
    contract evidence explicitly confirming multi-account, same-bot, and copy trading policies (v1.4.1 Section 17).
    """
    gate = MultiAccountEvidenceGate()

    # 1. First account from 'ApexTrader': permitted immediately
    ok1, msg1 = gate.register_account("ApexTrader", "APEX-ACC-101")
    assert ok1 is True
    assert "approved" in msg1.lower()

    # 2. Second account with NO evidence: strictly blocked
    ok2, msg2 = gate.register_account("ApexTrader", "APEX-ACC-102", evidence=None)
    assert ok2 is False
    assert "PENDING_MANUAL_EVIDENCE" in msg2

    # 3. Second account where same_bot counts as copy trading (violating policy): rejected
    evidence_ambiguous_copy = ManualEvidenceObject(
        provider_name="ApexTrader",
        account_id="APEX-ACC-102",
        multiple_accounts_allowed=True,
        same_bot_allowed=True,
        same_strategy_allowed=True,
        does_same_bot_count_as_copy_trading=True,  # Ambiguous / counts as prohibited copy trading
        has_signed_contract_terms=True,
        has_documented_scaling_rules=True,
        has_cross_account_risk_confirmation=True,
        written_evidence_text="Terms signed. Scaling documented. Risk verified across all accounts.",
        submission_timestamp_utc="2026-10-02T22:00:00Z",
    )
    ok3, msg3 = gate.register_account("ApexTrader", "APEX-ACC-102", evidence=evidence_ambiguous_copy)
    assert ok3 is False
    assert "PENDING_MANUAL_EVIDENCE" in msg3

    # 4. Second account with complete valid affirmative evidence: approved
    evidence_good = ManualEvidenceObject(
        provider_name="ApexTrader",
        account_id="APEX-ACC-102",
        multiple_accounts_allowed=True,
        same_bot_allowed=True,
        same_strategy_allowed=True,
        does_same_bot_count_as_copy_trading=False,
        shared_account_restrictions="NONE_UP_TO_3_ACCOUNTS",
        cross_account_hedging_policy="DISALLOWED",
        has_signed_contract_terms=True,
        has_documented_scaling_rules=True,
        has_cross_account_risk_confirmation=True,
        written_evidence_text=(
            "Contract signed on 2026-10-01. Firm terms Section 4.2 formally permits up to 5 concurrent "
            "evaluation accounts running identical autonomous EA bots without triggering copy-trading violations."
        ),
        submission_timestamp_utc="2026-10-02T22:00:00Z",
    )
    ok4, msg4 = gate.register_account("ApexTrader", "APEX-ACC-102", evidence=evidence_good)
    assert ok4 is True
    assert "approved with verified manual evidence" in msg4.lower()


def test_prop_monte_carlo_insufficient_sample_returns_pending():
    """
    CRITICAL REQUIREMENT (v1.4.1 Section 14):
    If empirical data is insufficient (< 30 trades), simulator must return
    status = PENDING / INSUFFICIENT_DATA and NEVER fake an empirical pass with IID Gaussian returns.
    """
    simulator = PropExamMonteCarloSimulator()
    profile = PropRuleProfile(
        provider_id="TopTierProp",
        version="v1.0",
        daily_loss_limit_pct=0.04,
        trailing_max_drawdown_pct=0.08,
        profit_target_pct=0.08,
        min_trading_days=5,
    )

    # 1. Zero trades -> PENDING / INSUFFICIENT_DATA
    res_empty = simulator.simulate(
        strategy_id="STR-002",
        profile=profile,
        trades=[],
    )
    assert res_empty["status"] == "PENDING / INSUFFICIENT_DATA"
    assert res_empty["is_eligible"] is False
    assert res_empty["pass_probability"] == 0.0

    # 2. Only 15 trades (< 30 minimum) -> PENDING / INSUFFICIENT_DATA
    few_trades = [
        TradeSample(
            trade_id=f"trd-{i}",
            timestamp_ns=1_000_000_000 * i,
            net_return=0.01,
            pnl_usd=100.0,
            mfe_usd=200.0,
            mae_usd=50.0,
            holding_time_s=300.0,
        )
        for i in range(15)
    ]
    res_few = simulator.simulate(
        strategy_id="STR-002",
        profile=profile,
        trades=few_trades,
    )
    assert res_few["status"] == "PENDING / INSUFFICIENT_DATA"
    assert res_few["is_eligible"] is False
    assert "Insufficient empirical trade sample" in res_few["reason"]


def test_prop_monte_carlo_empirical_block_bootstrap_reproducible():
    """Verify empirical block bootstrap simulation produces consistent results with fixed seed."""
    simulator = PropExamMonteCarloSimulator()
    profile = PropRuleProfile(
        provider_id="TopTierProp",
        version="v1.0",
        daily_loss_limit_pct=0.04,
        trailing_max_drawdown_pct=0.08,
        profit_target_pct=0.08,
        min_trading_days=5,
    )

    # Generate 50 realistic trade samples
    trades = []
    for i in range(50):
        # 60% win rate with positive edge
        ret = 0.015 if (i % 5 != 0) else -0.018
        trades.append(
            TradeSample(
                trade_id=f"trd-{i}",
                timestamp_ns=1_000_000_000 * i,
                net_return=ret,
                pnl_usd=ret * 100_000,
                mfe_usd=abs(ret) * 150_000,
                mae_usd=abs(ret) * 50_000 if ret < 0 else 20_000,
                holding_time_s=600.0,
            )
        )

    res1 = simulator.simulate(
        strategy_id="STR-002",
        profile=profile,
        trades=trades,
        n_simulations=100,
        random_seed=12345,
    )
    res2 = simulator.simulate(
        strategy_id="STR-002",
        profile=profile,
        trades=trades,
        n_simulations=100,
        random_seed=12345,
    )

    assert res1["status"] == "COMPLETED"
    assert res1["is_eligible"] is True
    # Reproducibility test with fixed seed
    assert res1["pass_probability"] == res2["pass_probability"]
    assert res1["failure_probability"] == res2["failure_probability"]
    assert "mean" in res1["max_drawdown_distribution"]
    assert "mean" in res1["final_equity_distribution"]


def test_prop_5_attempt_kill_switch_version_keying():
    """
    CRITICAL REQUIREMENT (v1.4.1 Section 15):
    Kill switch must be keyed by (strategy_version, prop_rule_profile_version, provider).
    STR-002 v2.0 failing 5 times must be blocked.
    STR-002 v2.1 must NOT be permanently poisoned by v2.0 failures.
    """
    simulator = PropExamMonteCarloSimulator()
    provider = "ApexTrader"
    profile_v1 = "v1.0"

    strat_id = "STR-002"
    v2_0 = "v2.0"
    v2_1 = "v2.1"

    # 1. v2.0 fails 4 times -> still eligible
    for i in range(1, 5):
        fails = simulator.record_attempt_result(
            strat_id, provider, passed=False, strategy_version=v2_0, profile_version=profile_v1
        )
        assert fails == i
        assert simulator.is_combination_eligible(strat_id, provider, v2_0, profile_v1) is True

    # 2. 5th failure blocks v2.0
    fails_5 = simulator.record_attempt_result(
        strat_id, provider, passed=False, strategy_version=v2_0, profile_version=profile_v1
    )
    assert fails_5 == 5
    assert simulator.is_combination_eligible(strat_id, provider, v2_0, profile_v1) is False

    # 3. 6th attempt on v2.0 is blocked by simulator
    profile_obj = PropRuleProfile(provider_id=provider, version=profile_v1)
    res_blocked = simulator.simulate(
        strategy_id=strat_id,
        strategy_version=v2_0,
        profile=profile_obj,
        trades=[],
    )
    assert res_blocked["status"] == "BLOCKED"
    assert res_blocked["is_eligible"] is False
    assert "RETURN_TO_RESEARCH_REVIEW" in res_blocked["action"]

    # 4. INVARIANT: v2.1 is NOT permanently poisoned! It has a clean 0-failure record
    assert simulator.is_combination_eligible(strat_id, provider, v2_1, profile_v1) is True


def test_aggregate_multi_account_risk_strategy_and_eventcluster():
    """
    CRITICAL REQUIREMENT (v1.4.1 Section 18):
    Risk Aggregator must aggregate exposure across accounts by:
    - strategy_id (e.g. STR-002 in Own + Prop A + Prop B)
    - EventCluster (e.g. crypto directional stress)
    """
    aggregator = MultiAccountRiskAggregator(
        max_global_gross_leverage=4.0,
        max_global_single_asset_pct=0.50,
        max_global_strategy_pct=0.40,  # Max 40% in single strategy
    )

    p_own = CapitalPocket(
        pocket_id="P_OWN",
        pocket_type=PocketType.OWN,
        account_id="ACC_OWN",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
    )
    p_prop1 = CapitalPocket(
        pocket_id="P_PROP1",
        pocket_type=PocketType.PROP,
        firm_name="PropFirmA",
        account_id="ACC_PROP1",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
    )
    aggregator.add_pocket(p_own)
    aggregator.add_pocket(p_prop1)

    # Register EventCluster
    cluster = EventCluster(
        cluster_id="CRYPTO_DIRECTIONAL",
        description="Crypto directional futures",
        max_gross_exposure_usd=60_000.0,  # $60,000 max cluster cap
        max_net_exposure_usd=60_000.0,
        stress_loss_limit_usd=20_000.0,
        member_weights={"BTCUSDT": 1.0, "ETHUSDT": 1.0},
    )
    aggregator.register_event_cluster(cluster)

    assert aggregator.total_aggregate_equity() == 100_000.0

    # Test 1: Strategy Concentration Breach
    # STR-002 is run in ACC_OWN ($25k notional) and ACC_PROP1 ($25k notional) = $50k total (50% > 40% cap)
    aggregator.update_positions(
        account_id="ACC_OWN",
        positions={"BTCUSDT": 0.35},
        mark_prices={"BTCUSDT": 70_000.0, "ETHUSDT": 3_500.0},
        strategy_allocations={"ACC_OWN": {"STR-002": {"BTCUSDT": 0.35}}},  # ~$24,500
    )
    aggregator.update_positions(
        account_id="ACC_PROP1",
        positions={"BTCUSDT": 0.35},
        mark_prices={"BTCUSDT": 70_000.0, "ETHUSDT": 3_500.0},
        strategy_allocations={"ACC_PROP1": {"STR-002": {"BTCUSDT": 0.35}}},  # ~$24,500 -> Total $49,000 (49% > 40%)
    )

    approved1, reason1, metrics1 = aggregator.evaluate_global_risk()
    assert approved1 is False
    assert "strategy 'STR-002'" in reason1
    assert "breaches maximum strategy concentration" in reason1

    # Test 2: EventCluster Gross Exposure Breach
    # Rebalance strategy to be compliant (within 40%), but cluster exposure exceeds $60k
    aggregator.max_global_strategy_pct = 0.80  # relax strategy cap
    # ACC_OWN: 0.5 BTC ($35k), ACC_PROP1: 10 ETH ($35k) -> Total $70k > $60k cluster cap
    aggregator.update_positions(
        account_id="ACC_OWN",
        positions={"BTCUSDT": 0.5},
        mark_prices={"BTCUSDT": 70_000.0, "ETHUSDT": 3_500.0},
        strategy_allocations={"ACC_OWN": {"STR-001": {"BTCUSDT": 0.5}}},
    )
    aggregator.update_positions(
        account_id="ACC_PROP1",
        positions={"ETHUSDT": 10.0},
        mark_prices={"BTCUSDT": 70_000.0, "ETHUSDT": 3_500.0},
        strategy_allocations={"ACC_PROP1": {"STR-002": {"ETHUSDT": 10.0}}},
    )

    approved2, reason2, metrics2 = aggregator.evaluate_global_risk()
    assert approved2 is False
    assert "EventCluster exposure for 'CRYPTO_DIRECTIONAL'" in reason2
    assert "$70,000.00" in reason2
