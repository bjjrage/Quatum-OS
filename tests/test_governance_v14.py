"""Unit tests for v1.4 Governance: Counterparty Thesis, Rule Evidence, and Experiment Registry."""

import pytest
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
    CounterpartyThesis,
    CounterpartyThesisStatus,
    StrategyRuleEvidence,
    StrategyRuleEvidenceStatus,
)
from src.strategies.registry import (
    StrategyRegistry,
    InvalidStageTransitionError,
    create_default_registry,
    create_extended_registry,
    get_seed_str_001,
    get_seed_str_002,
    get_seed_str_003,
    get_seed_pump_fun_copy,
)
from src.research.experiments import ExperimentRecord, ExperimentRegistry


def test_counterparty_thesis_mandatory_for_validation():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="TEST-001",
        name="Test Candidate",
        family=StrategyFamily.MOMENTUM.value,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=None,  # No counterparty thesis
    )
    registry.register(spec)

    # Attempt to promote RESEARCH -> VALIDATION without thesis -> Must fail!
    with pytest.raises(InvalidStageTransitionError) as exc_info:
        registry.update_stage("TEST-001", StrategyStage.VALIDATION)
    assert "Counterparty thesis is missing, incomplete, or lacks falsification conditions" in str(exc_info.value)

    # Attach incomplete thesis (missing falsification conditions)
    incomplete_thesis = CounterpartyThesis(
        counterparty_type="Retail flow",
        economic_mechanism="FOMO",
        why_trade_now="Urgency",
        why_impact_may_be_transient="Rebound",
        why_it_may_be_information="Hacks",
        falsification_conditions=[],  # Empty!
    )
    spec_incomplete = spec.model_copy(update={"counterparty_thesis": incomplete_thesis})
    registry._strategies["TEST-001"] = spec_incomplete

    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("TEST-001", StrategyStage.VALIDATION)

    # Attach complete thesis
    complete_thesis = CounterpartyThesis(
        counterparty_type="Retail liquidity demanders",
        economic_mechanism="Microstructure imbalance",
        why_trade_now="Stop loss executions",
        why_impact_may_be_transient="Transient order flow exhaustion",
        why_it_may_be_information="Regulatory announcements",
        falsification_conditions=["Net expectancy is negative after fees"],
        evidence_status=CounterpartyThesisStatus.RESEARCH_HYPOTHESIS,
    )
    spec_complete = spec.model_copy(update={"counterparty_thesis": complete_thesis})
    registry._strategies["TEST-001"] = spec_complete

    # Now promotion to VALIDATION succeeds!
    registry.update_stage("TEST-001", StrategyStage.VALIDATION)
    assert registry.get("TEST-001").stage == StrategyStage.VALIDATION


def test_rule_evidence_provenance_defaults():
    spec_str002 = get_seed_str_002()
    assert spec_str002.metadata["execution_mode"] == "LONG_ONLY"
    assert spec_str002.metadata["short_side"] == "RESEARCH_ONLY"

    # All manual rules must start as INTUITION_UNVALIDATED
    assert len(spec_str002.rules_evidence) >= 5
    for rule in spec_str002.rules_evidence:
        assert rule.status == StrategyRuleEvidenceStatus.INTUITION_UNVALIDATED
        assert rule.strategy_id == "STR-002"


def test_experiment_registry_trial_counting_and_deletion_prevention():
    exp_reg = ExperimentRegistry()

    # Record 3 experiments for STR-002
    for i in range(3):
        rec = ExperimentRecord(
            experiment_id=f"exp-str002-v1-{i}",
            strategy_id="STR-002",
            parameters={"threshold_z": 2.0 + (0.5 * i)},
            gate_result="FAIL" if i < 2 else "PASS",
        )
        count = exp_reg.record_experiment(rec)
        assert count == i + 1

    assert exp_reg.get_trial_count("STR-002") == 3
    assert len(exp_reg.list_experiments_for_strategy("STR-002")) == 3

    # Attempting to delete an experiment to hide a failure is forbidden
    with pytest.raises(RuntimeError) as exc_info:
        exp_reg.delete_experiment("exp-str002-v1-0")
    assert "Governance Invariant Violated: Experiments cannot be deleted" in str(exc_info.value)


def test_seed_registry_v14_completeness():
    reg = create_extended_registry()
    all_strats = reg.list_all()
    strat_ids = {s.strategy_id for s in all_strats}

    assert "STR-001" in strat_ids
    assert "STR-002" in strat_ids
    assert "STR-003" in strat_ids
    assert "STR-PUMP-COPY" in strat_ids

    # None have execution authority or live capital
    assert reg.has_execution_authority() is False
    for s in all_strats:
        assert s.is_privileged is False
        assert s.counterparty_thesis is not None
        assert len(s.counterparty_thesis.falsification_conditions) > 0
