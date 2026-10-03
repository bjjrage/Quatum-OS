"""Unit tests for Capital Pockets and Multi-Account Risk Governance."""

import pytest
from src.risk.capital_pockets import (
    PocketType,
    CapitalPocket,
    ManualEvidenceObject,
    MultiAccountEvidenceGate,
    PropRuleProfile,
    PropExamMonteCarloSimulator,
    MultiAccountRiskAggregator,
)


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


def test_multi_account_evidence_gate_enforcement():
    """Verify MultiAccountEvidenceGate allows 1st account, blocks 2nd without written contract evidence."""
    gate = MultiAccountEvidenceGate()

    # 1. First account from 'ApexTrader': permitted immediately
    ok1, msg1 = gate.register_account("ApexTrader", "APEX-ACC-101")
    assert ok1 is True
    assert "approved" in msg1.lower()

    # 2. Second account from 'ApexTrader' with NO evidence: strictly blocked
    ok2, msg2 = gate.register_account("ApexTrader", "APEX-ACC-102", evidence=None)
    assert ok2 is False
    assert "PENDING_MANUAL_EVIDENCE" in msg2

    # 3. Second account with incomplete evidence (< 50 chars or missing flags): rejected
    evidence_bad = ManualEvidenceObject(
        provider_name="ApexTrader",
        account_id="APEX-ACC-102",
        has_signed_contract_terms=True,
        has_documented_scaling_rules=False,  # Missing
        has_cross_account_risk_confirmation=True,
        written_evidence_text="Too short",
        submission_timestamp_utc="2026-10-02T22:00:00Z",
    )
    ok3, msg3 = gate.register_account("ApexTrader", "APEX-ACC-102", evidence=evidence_bad)
    assert ok3 is False
    assert "PENDING_MANUAL_EVIDENCE" in msg3

    # 4. Second account with complete valid evidence: approved
    evidence_good = ManualEvidenceObject(
        provider_name="ApexTrader",
        account_id="APEX-ACC-102",
        has_signed_contract_terms=True,
        has_documented_scaling_rules=True,
        has_cross_account_risk_confirmation=True,
        written_evidence_text=(
            "Contract signed on 2026-10-01. Firm terms Section 4.2 formally permits up to 5 concurrent "
            "evaluation accounts with independent trailing drawdowns. Aggregate exposure limits verified."
        ),
        submission_timestamp_utc="2026-10-02T22:00:00Z",
    )
    ok4, msg4 = gate.register_account("ApexTrader", "APEX-ACC-102", evidence=evidence_good)
    assert ok4 is True
    assert "approved with verified manual evidence" in msg4.lower()


def test_prop_exam_monte_carlo_and_5_attempt_kill_switch():
    """Verify Monte Carlo path simulation and 5-attempt kill switch permanently blocking strategy."""
    simulator = PropExamMonteCarloSimulator()
    profile = PropRuleProfile(
        firm_name="TopTierProp",
        version="2026.1",
        effective_date="2026-01-01",
        daily_loss_limit_pct=0.04,
        trailing_max_drawdown_pct=0.08,
        profit_target_pct=0.08,
        min_trading_days=5,
    )

    strat_id = "STR-PROP-TEST"
    assert simulator.is_strategy_eligible(strat_id, "TopTierProp") is True

    # 1. Run simulation on profitable strategy with good risk profile
    res_good = simulator.simulate(
        strategy_id=strat_id,
        profile=profile,
        daily_mean_ret=0.008,
        daily_vol_ret=0.010,
        n_simulations=200,
        random_seed=42,
    )
    assert res_good["is_eligible"] is True
    assert res_good["pass_probability"] > 0.50

    # 2. Simulate 4 consecutive failures
    for attempt in range(1, 5):
        fails = simulator.record_attempt_result(strat_id, "TopTierProp", passed=False)
        assert fails == attempt
        assert simulator.is_strategy_eligible(strat_id, "TopTierProp") is True

    # 3. 5th consecutive failure triggers KILL SWITCH
    fails_5 = simulator.record_attempt_result(strat_id, "TopTierProp", passed=False)
    assert fails_5 == 5
    assert simulator.is_strategy_eligible(strat_id, "TopTierProp") is False

    # 4. Subsequent simulation or exam purchase is permanently BLOCKED
    res_blocked = simulator.simulate(
        strategy_id=strat_id,
        profile=profile,
        daily_mean_ret=0.01,
        daily_vol_ret=0.01,
        n_simulations=100,
    )
    assert res_blocked["is_eligible"] is False
    assert res_blocked["pass_probability"] == 0.0
    assert "KILL_SWITCH_ACTIVE" in res_blocked["reason"]


def test_aggregate_multi_account_risk_global_breach():
    """Verify RiskAggregator combines exposure and freezes all accounts upon global ceiling breach."""
    aggregator = MultiAccountRiskAggregator(max_global_gross_leverage=3.0)

    p1 = CapitalPocket(
        pocket_id="P1",
        pocket_type=PocketType.OWN,
        account_id="ACC1",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
    )
    p2 = CapitalPocket(
        pocket_id="P2",
        pocket_type=PocketType.PROP,
        firm_name="FirmA",
        account_id="ACC2",
        initial_equity_usd=50_000.0,
        current_equity_usd=50_000.0,
        peak_equity_usd=50_000.0,
        daily_starting_equity_usd=50_000.0,
    )
    aggregator.add_pocket(p1)
    aggregator.add_pocket(p2)

    assert aggregator.total_aggregate_equity() == 100_000.0

    # Positions: ACC1 has 2.0 BTC, ACC2 has 3.0 BTC -> Total 5.0 BTC @ $70,000 = $350,000 Notional
    # Gross leverage = $350k / $100k = 3.5x > 3.0x ceiling!
    aggregator.update_positions("ACC1", {"BTCUSDT": 2.0}, {"BTCUSDT": 70_000.0})
    aggregator.update_positions("ACC2", {"BTCUSDT": 3.0}, {"BTCUSDT": 70_000.0})

    approved, reason, metrics = aggregator.evaluate_global_risk()

    assert approved is False
    assert "Global gross leverage" in reason
    assert metrics["gross_leverage"] == pytest.approx(3.5, abs=1e-2)

    # Invariant: Global breach freezes ALL accounts
    assert p1.is_frozen is True
    assert p2.is_frozen is True
