"""Unit tests for Portfolio Selection Gates (v1.4.0)."""

import pytest
import math
from src.portfolio.gates import (
    GateStatus,
    StrategyGateResult,
    LatencySensitivityGate,
    TemporalStabilityGate,
    MultipleSelectionGate,
    CorrelationCapacityGate,
    all_gates_pass,
)


def test_latency_sensitivity_gate_robust():
    """Verify that strategies with slow decay pass the latency sensitivity gate."""
    gate = LatencySensitivityGate(max_sharpe_drop_pct_at_5s=0.50, min_edge_half_life_s=5.0)

    # Robust strategy: Sharpe 2.5 at 0s, 2.3 at 1s, 2.0 at 5s, 1.5 at 30s
    sharpes = {0.0: 2.5, 1.0: 2.3, 5.0: 2.0, 30.0: 1.5}
    result = gate.evaluate(sharpes)

    assert result.status == GateStatus.PASS
    assert result.diagnostics["is_latency_race"] is False
    assert result.diagnostics["classification"] == "ROBUST_EXECUTION"
    assert result.diagnostics["edge_half_life_s"] > 5.0
    assert result.diagnostics["sharpe_drop_pct_at_5s"] == pytest.approx(0.20, abs=1e-3)
    assert result.falsification_evidence is None


def test_latency_sensitivity_gate_latency_race_rejection():
    """Verify that fast-decaying strategies are flagged as LATENCY_RACE and rejected."""
    gate = LatencySensitivityGate(max_sharpe_drop_pct_at_5s=0.50, min_edge_half_life_s=5.0)

    # Latency race strategy: Sharpe 3.0 at 0s, 1.2 at 1s, 0.3 at 5s, 0.0 at 30s
    sharpes = {0.0: 3.0, 1.0: 1.2, 5.0: 0.3, 30.0: 0.0}
    result = gate.evaluate(sharpes)

    assert result.status == GateStatus.FAIL
    assert result.diagnostics["is_latency_race"] is True
    assert result.diagnostics["classification"] == "LATENCY_RACE"
    assert result.diagnostics["edge_half_life_s"] < 5.0
    assert result.diagnostics["sharpe_drop_pct_at_5s"] == pytest.approx(0.90, abs=1e-3)
    assert "LATENCY_RACE" in result.falsification_evidence


def test_temporal_stability_gate_pass_and_decay():
    """Verify Gate B detects alpha decay and rolling instability."""
    gate = TemporalStabilityGate(min_decay_ratio=0.50, min_positive_rolling_pct=0.75, rolling_window_periods=10)

    # 1. Stable positive returns (80 periods)
    stable_returns = [0.01 + 0.002 * (i % 3) for i in range(80)]
    result_stable = gate.evaluate(stable_returns)
    assert result_stable.status == GateStatus.PASS
    assert result_stable.diagnostics["is_decaying"] is False
    assert result_stable.diagnostics["is_unstable"] is False
    assert result_stable.diagnostics["rolling_positive_pct"] == 1.0

    # 2. Decaying strategy: good early (periods 0..40), zero/negative late (periods 40..80)
    decaying_returns = [0.02 + 0.005 * (i % 2) for i in range(40)] + [-0.005 + 0.002 * (i % 2) for i in range(40)]
    result_decay = gate.evaluate(decaying_returns)
    assert result_decay.status == GateStatus.FAIL
    assert result_decay.diagnostics["is_decaying"] is True
    assert "alpha decay" in result_decay.falsification_evidence.lower()


def test_multiple_selection_gate_dsr_and_trial_count_penalty():
    """Verify Gate C applies Bailey & López de Prado multiple testing correction."""
    gate = MultipleSelectionGate(min_dsr=0.95, max_adjusted_pvalue=0.05)

    # Strategy with Sharpe = 1.2, 100 observations
    # Single trial: should have moderate confidence
    res_1_trial = gate.evaluate(sharpe_ratio=1.2, trial_count=1, sample_length=100)
    # Expected null Sharpe for N=1 is 0.0
    assert res_1_trial.diagnostics["expected_max_null_sharpe"] == 0.0

    # Same strategy evaluated after 200 trials in ExperimentRegistry
    # Null threshold jumps significantly due to max of 200 standard normals
    res_200_trials = gate.evaluate(sharpe_ratio=1.2, trial_count=200, sample_length=100)
    assert res_200_trials.status == GateStatus.FAIL
    assert res_200_trials.diagnostics["expected_max_null_sharpe"] > 1.5
    assert res_200_trials.diagnostics["deflated_sharpe_ratio"] < 0.95
    assert "multiple testing correction" in res_200_trials.falsification_evidence

    # Highly robust strategy with Sharpe = 3.5 surviving 200 trials
    res_exceptional = gate.evaluate(sharpe_ratio=3.5, trial_count=200, sample_length=250)
    assert res_exceptional.status == GateStatus.PASS
    assert res_exceptional.diagnostics["deflated_sharpe_ratio"] >= 0.95


def test_correlation_capacity_gate():
    """Verify Gate D enforces correlation ceilings and 1% 5m volume capacity."""
    gate = CorrelationCapacityGate(
        max_normal_correlation=0.60,
        max_stress_correlation=0.70,
        max_capacity_volume_pct=0.01,
    )

    n = 50
    # Candidate returns
    cand_returns = [0.01 * (1 if i % 2 == 0 else -1) for i in range(n)]

    # 1. Orthogonal active strategy, well within capacity
    active_returns_ortho = {"STR-001": [0.01 * (1 if i % 3 == 0 else -1) for i in range(n)]}
    result_clean = gate.evaluate(
        candidate_returns=cand_returns,
        active_returns_by_strategy=active_returns_ortho,
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,  # 5,000 <= 1% of 1,000,000 (10,000)
    )
    assert result_clean.status == GateStatus.PASS

    # 2. Capacity exceeded: proposed $25,000 on $1,000,000 5m volume (cap $10,000)
    result_cap_fail = gate.evaluate(
        candidate_returns=cand_returns,
        active_returns_by_strategy=active_returns_ortho,
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=25_000.0,
    )
    assert result_cap_fail.status == GateStatus.FAIL
    assert "exceeds 1% 5m volume capacity" in result_cap_fail.falsification_evidence

    # 3. High correlation failure: identical returns
    active_returns_high_corr = {"STR-002": list(cand_returns)}
    result_corr_fail = gate.evaluate(
        candidate_returns=cand_returns,
        active_returns_by_strategy=active_returns_high_corr,
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
    )
    assert result_corr_fail.status == GateStatus.FAIL
    assert "breaches threshold" in result_corr_fail.falsification_evidence


def test_all_gates_pass_orchestrator():
    """Verify all_gates_pass helper requires all gates to be PASS."""
    passing_result = StrategyGateResult.create_pass(
        strategy_id="STR-001",
        strategy_version="1.0.0",
        gate_type="Gate A",
        dataset_fingerprint="ds_test_fp",
        config_fingerprint="cfg_test_fp",
        criteria_evaluations={"passed": True},
        score=0.9,
        threshold=0.5,
    )
    failing_result = StrategyGateResult.create_fail(
        strategy_id="STR-001",
        strategy_version="1.0.0",
        gate_type="Gate B",
        dataset_fingerprint="ds_test_fp",
        config_fingerprint="cfg_test_fp",
        score=0.3,
        threshold=0.5,
        reasons=["Failed decay"],
        falsification_evidence="Failed decay",
    )

    assert all_gates_pass({"A": passing_result}) is True
    assert all_gates_pass({"A": passing_result, "B": failing_result}) is False
    assert all_gates_pass({}) is False
    # Test list input and PENDING status
    pending_result = StrategyGateResult.create_pending(
        strategy_id="STR-001",
        strategy_version="1.0.0",
        gate_type="Gate C",
        dataset_fingerprint="ds_test_fp",
        config_fingerprint="cfg_test_fp",
        score=0.0,
        threshold=0.5,
        reasons=["Pending additional historical bars."],
    )
    assert all_gates_pass([passing_result]) is True
    assert all_gates_pass([passing_result, pending_result]) is False


def test_strategy_gate_result_audit_contract():
    """Verify StrategyGateResult enforces audit invariants and rejects illegal PASS."""
    # 1. Reject status=PASS with falsification evidence
    with pytest.raises(ValueError, match="cannot declare status=PASS with falsification_evidence"):
        StrategyGateResult(
            strategy_id="STR-002",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"passed": True},
            falsification_evidence="Failed half-life",
        )

    # 2. Reject status=PASS with reasons
    with pytest.raises(ValueError, match="cannot declare status=PASS with non-empty reasons"):
        StrategyGateResult(
            strategy_id="STR-002",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"passed": True},
            reasons=["Failed"],
        )

    # 3. Reject status=PASS with empty criteria_evaluations
    with pytest.raises(ValueError, match="status=PASS requires non-empty criteria_evaluations"):
        StrategyGateResult(
            strategy_id="STR-002",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={},
        )

    # 4. Reject status=PASS with False criteria evaluation
    with pytest.raises(ValueError, match="status=PASS cannot contain False criteria evaluations"):
        StrategyGateResult(
            strategy_id="STR-002",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"dsr_significant": False},
        )

    # 5. Reject empty provenance
    with pytest.raises(ValueError, match="Provenance violation"):
        StrategyGateResult(
            strategy_id="STR-002",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"passed": True},
        )

    # 6. Complete auditable record on FAIL
    fail_res = StrategyGateResult.create_fail(
        strategy_id="STR-002",
        strategy_version="2.0.0",
        gate_type="LATENCY_SENSITIVITY",
        dataset_fingerprint="ds_fp",
        config_fingerprint="cfg_fp",
        metrics={"decay_at_5s": 0.25, "edge_half_life_s": 2.1},
        thresholds={"max_sharpe_drop_pct_at_5s": 0.50, "min_edge_half_life_s": 5.0},
        reasons=["Edge half-life 2.1s < 5.0s"],
    )
    assert fail_res.falsification_evidence == "Edge half-life 2.1s < 5.0s"
    assert len(fail_res.evaluated_at) > 0
    assert fail_res.metrics["decay_at_5s"] == 0.25

    # 7. Immutability: mutation must raise
    with pytest.raises(Exception):
        fail_res.status = GateStatus.PASS


def test_latency_gate_operational_stack_budget():
    """Verify LatencySensitivityGate incorporates the operational execution stack's observed latency."""
    # Stack with slow p99 latency: 2500ms * 2.0 safety margin = 5.0s budget
    gate = LatencySensitivityGate(
        max_sharpe_drop_pct_at_5s=0.50,
        min_edge_half_life_s=3.0,
        observed_p99_latency_ms=2500.0,
        latency_safety_margin_multiplier=2.0,
    )

    # Strategy with 4.0s half-life: would pass min_edge_half_life_s=3.0,
    # but FAILS because operational stack needs 5.0s
    sharpes = {0.0: 2.0, 1.0: 1.8, 4.0: 1.0, 5.0: 0.8, 30.0: 0.2}
    result = gate.evaluate(sharpes)

    assert result.status == GateStatus.FAIL
    assert result.metrics["operational_budget_s"] == 5.0
    assert result.metrics["edge_half_life_s"] < 5.0
    assert "LATENCY_RACE" in result.falsification_evidence
