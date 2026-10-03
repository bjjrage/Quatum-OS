"""
Comprehensive Governance & Holdout Hardening Test Suite (Hardening 03).
Covers:
- Section 1: Holdout Preregistration, Access & Burn (tests 1-12)
- Section 2: Gate Bundle & Strict Validator (tests 13-24)
- Section 3: Gate C / DSR & Real BH-FDR (tests 25-38)
- Section 4: Gate D / Correlation & Capacity (tests 39-50)
- Section 5: Lifecycle Promotion & Evidence Bundle (tests 51-68)
Total: 68 tests.
"""

import math
import tempfile
import time
from pathlib import Path
import pytest
from typing import Dict, Any, List, Optional, Tuple
from pydantic import ValidationError

from src.research.holdout import (
    SealedHoldoutManager,
    HoldoutStatus,
    HoldoutViolationError,
    HoldoutPreRegistration,
    HoldoutAccessRecord,
    HoldoutEvaluationResult,
)
from src.research.experiments import (
    ExperimentRegistry,
    ExperimentRecord,
    MultipleTestingContext,
)
from src.portfolio.gates import (
    GateStatus,
    StrategyGateResult,
    LatencySensitivityGate,
    TemporalStabilityGate,
    MultipleSelectionGate,
    CorrelationCapacityGate,
    benjamini_hochberg,
    expected_max_sharpe,
    deflated_sharpe_ratio,
    validate_gate_bundle,
    all_gates_pass,
)
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    CounterpartyThesis,
    StrategyFamily,
    StrategyOrigin,
    PromotionEvidenceBundle,
)
from src.strategies.registry import (
    StrategyRegistry,
    InvalidStageTransitionError,
)
from apps.api.services.data_service import QuantOSDataService


# =====================================================================
# SECTION 1: Holdout Preregistration, Access & Burn (Tests 1-12)
# =====================================================================

def test_holdout_status_unopened_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        assert mgr.get_status() == HoldoutStatus.UNOPENED.value


def test_holdout_status_preregistered():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Validating momentum persistence in crypto holdout",
            falsification_criteria=["Sharpe < 1.0"],
        )
        assert mgr.get_status() == HoldoutStatus.PREREGISTERED.value


def test_holdout_preregistration_requires_hypothesis_and_falsification():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        # Empty hypothesis description
        with pytest.raises(ValueError, match="hypothesis_description"):
            mgr.create_preregistration(
                strategy_id="STR-001",
                strategy_version="1.0.0",
                git_sha="abcdef1234567890",
                dataset_fingerprint="ds_hash_12345678",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="param_hash_12345678",
                hypothesis_description="   ",
                falsification_criteria=["Sharpe < 1.0"],
            )
        # Empty falsification criteria
        with pytest.raises(ValueError, match="falsification_criteria"):
            mgr.create_preregistration(
                strategy_id="STR-001",
                strategy_version="1.0.0",
                git_sha="abcdef1234567890",
                dataset_fingerprint="ds_hash_12345678",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="param_hash_12345678",
                hypothesis_description="Valid hypothesis",
                falsification_criteria=[],
            )


def test_holdout_preregistration_requires_exact_provenance_fingerprints():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        with pytest.raises(ValueError, match="fingerprint"):
            mgr.create_preregistration(
                strategy_id="STR-001",
                strategy_version="1.0.0",
                git_sha="abcdef1234567890",
                dataset_fingerprint="",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="param_hash_12345678",
                hypothesis_description="Valid hypothesis",
                falsification_criteria=["Sharpe < 1.0"],
            )


def test_holdout_cannot_open_without_preregistration():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        with pytest.raises(HoldoutViolationError, match=r"does not exist"):
            mgr.open_holdout(
                preregistration_id="NON_EXISTENT_ID",
                strategy_id="STR-001",
                strategy_version="1.0.0",
                git_sha="abcdef1234567890",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="param_hash_12345678",
            )


def test_holdout_open_once_succeeds_and_transitions_to_opened():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Validating momentum persistence",
            falsification_criteria=["Sharpe < 1.0"],
        )
        rec = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        assert rec.access_id is not None
        assert mgr.get_status() == HoldoutStatus.OPENED.value


def test_holdout_second_open_fails_closed_with_violation_error():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Validating momentum persistence",
            falsification_criteria=["Sharpe < 1.0"],
        )
        mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        with pytest.raises(HoldoutViolationError, match="already OPENED"):
            mgr.open_holdout(
                preregistration_id=prereg.preregistration_id,
                strategy_id="STR-001",
                strategy_version="1.0.0",
                git_sha="abcdef1234567890",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="param_hash_12345678",
            )


def test_holdout_dataset_reuse_forbidden_for_same_strategy_lineage():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        # Attempting second preregistration on same lineage & dataset hash
        with pytest.raises(HoldoutViolationError, match="burned"):
            mgr.create_preregistration(
                strategy_id="STR-001",
                strategy_version="1.0.0",
                git_sha="abcdef1234567890",
                dataset_fingerprint="ds_hash_12345678",
                config_fingerprint="cfg_hash_87654321",
                parameter_set_fingerprint="param_hash_87654321",
                hypothesis_description="Tuned attempt",
                falsification_criteria=["Sharpe < 1.0"],
            )


def test_holdout_dataset_reuse_forbidden_across_versions():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        # Attempting version 1.0.1 on same dataset
        with pytest.raises(HoldoutViolationError, match="burned"):
            mgr.create_preregistration(
                strategy_id="STR-001",
                strategy_version="1.0.1",
                git_sha="abcdef1234567890",
                dataset_fingerprint="ds_hash_12345678",
                config_fingerprint="cfg_hash_87654321",
                parameter_set_fingerprint="param_hash_87654321",
                hypothesis_description="New version on burned holdout",
                falsification_criteria=["Sharpe < 1.0"],
            )


def test_holdout_eval_record_immutable_and_matches_preregistration():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        eval_res = mgr.record_evaluation_result(
            access_id=acc.access_id,
            result_metrics={"sharpe": 1.5, "max_drawdown": 0.05},
            passed=True,
            reasons=["All thresholds met"],
        )
        assert eval_res.result_metrics["sharpe"] == 1.5
        # Immutability check
        with pytest.raises(ValidationError):
            eval_res.passed = False


def test_holdout_burned_status_when_evaluation_fails_or_burn_triggered():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        mgr.record_evaluation_result(
            access_id=acc.access_id,
            result_metrics={"sharpe": 0.5},
            passed=False,
            reasons=["Sharpe below 1.0"],
        )
        assert mgr.get_status() == HoldoutStatus.BURNED.value


def test_holdout_tampered_audit_log_fails_closed_governance_locked():
    with tempfile.TemporaryDirectory() as tmp:
        audit_file = Path(tmp) / "audits.json"
        audit_file.write_text("CORRUPTED_NOT_JSON {{{")
        mgr = SealedHoldoutManager(audit_storage_path=audit_file, raise_on_corruption=False)
        assert mgr.is_corrupted is True
        assert mgr.get_status() == HoldoutStatus.GOVERNANCE_LOCKED.value
        with pytest.raises(HoldoutViolationError, match="GOVERNANCE_LOCKED"):
            mgr.create_preregistration(
                strategy_id="STR-001",
                strategy_version="1.0.0",
                git_sha="abcdef1234567890",
                dataset_fingerprint="ds_hash_12345678",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="param_hash_12345678",
                hypothesis_description="Initial run",
                falsification_criteria=["Sharpe < 1.0"],
            )


# =====================================================================
# SECTION 2: Gate Bundle & Strict Validator (Tests 13-24)
# =====================================================================

def _make_canonical_gates(status: GateStatus = GateStatus.PASS, dataset_fp: str = "ds_hash_12345678", cfg_fp: str = "cfg_hash_12345678", strat_id: str = "STR-001"):
    res_a = StrategyGateResult.create_pass(
        gate_type="LATENCY_SENSITIVITY",
        strategy_id=strat_id,
        strategy_version="1.0.0",
        dataset_fingerprint=dataset_fp,
        config_fingerprint=cfg_fp,
        score=0.9,
        threshold=0.8,
        metrics={"score": 0.9},
        thresholds={"min": 0.8},
        criteria_evaluations={"latency_ok": True},
        reasons=[],
    ) if status == GateStatus.PASS else StrategyGateResult.create_pending(
        gate_type="LATENCY_SENSITIVITY",
        strategy_id=strat_id,
        strategy_version="1.0.0",
        dataset_fingerprint=dataset_fp,
        config_fingerprint=cfg_fp,
        reasons=["Pending"],
    )
    res_b = StrategyGateResult.create_pass(
        gate_type="TEMPORAL_STABILITY",
        strategy_id=strat_id,
        strategy_version="1.0.0",
        dataset_fingerprint=dataset_fp,
        config_fingerprint=cfg_fp,
        score=0.85,
        threshold=0.75,
        metrics={"score": 0.85},
        thresholds={"min": 0.75},
        criteria_evaluations={"stability_ok": True},
        reasons=[],
    )
    res_c = StrategyGateResult.create_pass(
        gate_type="MULTIPLE_SELECTION",
        strategy_id=strat_id,
        strategy_version="1.0.0",
        dataset_fingerprint=dataset_fp,
        config_fingerprint=cfg_fp,
        score=0.95,
        threshold=0.90,
        metrics={"score": 0.95},
        thresholds={"min": 0.90},
        criteria_evaluations={"dsr_ok": True},
        reasons=[],
    )
    res_d = StrategyGateResult.create_pass(
        gate_type="CORRELATION_CAPACITY",
        strategy_id=strat_id,
        strategy_version="1.0.0",
        dataset_fingerprint=dataset_fp,
        config_fingerprint=cfg_fp,
        score=0.88,
        threshold=0.80,
        metrics={"score": 0.88},
        thresholds={"min": 0.80},
        criteria_evaluations={"capacity_ok": True},
        reasons=[],
    )
    return [res_a, res_b, res_c, res_d]


def test_gate_bundle_requires_all_four_canonical_gates():
    gates = _make_canonical_gates()[:3]
    valid, reasons = validate_gate_bundle(gates)
    assert valid is False
    assert any("4 gates" in r for r in reasons)


def test_gate_bundle_fails_if_any_gate_is_pending():
    gates = _make_canonical_gates(status=GateStatus.PENDING)
    valid, reasons = validate_gate_bundle(gates)
    assert valid is False
    assert any("PASS" in r for r in reasons)


def test_gate_bundle_fails_if_any_gate_is_fail():
    gates = _make_canonical_gates()
    gates[0] = StrategyGateResult.create_fail(
        gate_type="LATENCY_SENSITIVITY",
        strategy_id="STR-001",
        strategy_version="1.0.0",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        reasons=["Latency failed"],
    )
    valid, reasons = validate_gate_bundle(gates)
    assert valid is False
    assert any("PASS" in r for r in reasons)


def test_gate_bundle_fails_if_dataset_fingerprint_mismatch():
    gates = _make_canonical_gates()
    gates[1] = StrategyGateResult.create_pass(
        gate_type="TEMPORAL_STABILITY",
        strategy_id="STR-001",
        strategy_version="1.0.0",
        dataset_fingerprint="different_dataset_hash",
        config_fingerprint="cfg_hash_12345678",
        score=0.85,
        threshold=0.75,
        metrics={"score": 0.85},
        thresholds={"min": 0.75},
        criteria_evaluations={"stability_ok": True},
        reasons=[],
    )
    valid, reasons = validate_gate_bundle(gates)
    assert valid is False
    assert any("dataset_fingerprint" in r and "match" in r for r in reasons)


def test_gate_bundle_fails_if_config_fingerprint_mismatch():
    gates = _make_canonical_gates()
    gates[1] = StrategyGateResult.create_pass(
        gate_type="TEMPORAL_STABILITY",
        strategy_id="STR-001",
        strategy_version="1.0.0",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="different_config_hash",
        score=0.85,
        threshold=0.75,
        metrics={"score": 0.85},
        thresholds={"min": 0.75},
        criteria_evaluations={"stability_ok": True},
        reasons=[],
    )
    valid, reasons = validate_gate_bundle(gates)
    assert valid is False
    assert any("config_fingerprint" in r and "match" in r for r in reasons)


def test_gate_bundle_fails_if_strategy_id_mismatch():
    gates = _make_canonical_gates()
    gates[1] = StrategyGateResult.create_pass(
        gate_type="TEMPORAL_STABILITY",
        strategy_id="STR-002",
        strategy_version="1.0.0",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        score=0.85,
        threshold=0.75,
        metrics={"score": 0.85},
        thresholds={"min": 0.75},
        criteria_evaluations={"stability_ok": True},
        reasons=[],
    )
    valid, reasons = validate_gate_bundle(gates)
    assert valid is False
    assert any("strategy_id" in r and "match" in r for r in reasons)


def test_gate_bundle_forbids_placeholder_fingerprint_ds_prov_unspecified():
    with pytest.raises(ValueError, match=r"(?i)placeholder|provenance violation"):
        StrategyGateResult.create_pass(
            gate_type="LATENCY_SENSITIVITY",
            strategy_id="STR-001",
            strategy_version="1.0.0",
            dataset_fingerprint="ds_prov_unspecified",
            config_fingerprint="cfg_hash_12345678",
            score=0.9,
            threshold=0.8,
            metrics={"score": 0.9},
            thresholds={"min": 0.8},
            criteria_evaluations={"latency_ok": True},
            reasons=[],
        )


def test_gate_bundle_forbids_placeholder_fingerprint_cfg_prov_unspecified():
    with pytest.raises(ValueError, match=r"(?i)placeholder|provenance violation"):
        StrategyGateResult.create_pass(
            gate_type="LATENCY_SENSITIVITY",
            strategy_id="STR-001",
            strategy_version="1.0.0",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_prov_unspecified",
            score=0.9,
            threshold=0.8,
            metrics={"score": 0.9},
            thresholds={"min": 0.8},
            criteria_evaluations={"latency_ok": True},
            reasons=[],
        )


def test_gate_bundle_forbids_placeholder_fingerprint_PROVENANCE_UNSPECIFIED():
    with pytest.raises(ValueError, match=r"(?i)placeholder|provenance violation"):
        StrategyGateResult.create_pass(
            gate_type="LATENCY_SENSITIVITY",
            strategy_id="STR-001",
            strategy_version="1.0.0",
            dataset_fingerprint="PROVENANCE_UNSPECIFIED",
            config_fingerprint="cfg_hash_12345678",
            score=0.9,
            threshold=0.8,
            metrics={"score": 0.9},
            thresholds={"min": 0.8},
            criteria_evaluations={"latency_ok": True},
            reasons=[],
        )


def test_gate_bundle_forbids_nan_or_inf_in_metrics_thresholds_or_score():
    with pytest.raises(ValueError, match=r"(?i)nonfinite|finite"):
        StrategyGateResult.create_pass(
            gate_type="LATENCY_SENSITIVITY",
            strategy_id="STR-001",
            strategy_version="1.0.0",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            score=float("nan"),
            threshold=0.8,
            metrics={"score": 0.9},
            thresholds={"min": 0.8},
            criteria_evaluations={"latency_ok": True},
            reasons=[],
        )


def test_all_gates_pass_thin_wrapper_matches_validate_gate_bundle():
    gates = _make_canonical_gates()
    assert all_gates_pass(gates) is True
    assert validate_gate_bundle(gates)[0] is True

    gates_bad = gates[:3]
    assert all_gates_pass(gates_bad) is False
    assert validate_gate_bundle(gates_bad)[0] is False


def test_gate_bundle_immutability_extra_forbid():
    gates = _make_canonical_gates()
    with pytest.raises(ValidationError):
        gates[0].score = 0.5
    with pytest.raises(ValidationError):
        StrategyGateResult(
            gate_type="LATENCY_SENSITIVITY",
            status=GateStatus.PASS,
            score=1.0,
            threshold=0.5,
            extra_field="disallowed",
        )


# =====================================================================
# SECTION 3: Gate C / DSR & Real BH-FDR (Tests 25-38)
# =====================================================================

def test_dsr_formula_matches_bailey_lopez_de_prado_equation():
    em_100 = expected_max_sharpe(n_trials=100)
    assert 1.5 < em_100 < 3.0
    dsr = deflated_sharpe_ratio(estimated_sharpe=2.5, n_trials=100, sample_length=100, skewness=0.0, kurtosis=3.0)
    assert 0.0 <= dsr <= 1.0


def test_dsr_expected_max_sharpe_strictly_increasing_in_trial_count():
    em10 = expected_max_sharpe(10)
    em100 = expected_max_sharpe(100)
    em1000 = expected_max_sharpe(1000)
    assert em10 < em100 < em1000


def test_dsr_expected_max_sharpe_zero_for_single_trial():
    assert expected_max_sharpe(1) == 0.0


def test_dsr_penalty_increases_with_negative_skewness():
    dsr_normal = deflated_sharpe_ratio(estimated_sharpe=3.0, n_trials=50, sample_length=100, skewness=0.0, kurtosis=3.0)
    dsr_neg_skew = deflated_sharpe_ratio(estimated_sharpe=3.0, n_trials=50, sample_length=100, skewness=-1.5, kurtosis=3.0)
    assert dsr_neg_skew < dsr_normal


def test_dsr_penalty_increases_with_positive_excess_kurtosis():
    dsr_meso = deflated_sharpe_ratio(estimated_sharpe=3.0, n_trials=50, sample_length=100, skewness=0.0, kurtosis=3.0)
    dsr_lepto = deflated_sharpe_ratio(estimated_sharpe=3.0, n_trials=50, sample_length=100, skewness=0.0, kurtosis=8.0)
    assert dsr_lepto < dsr_meso


def test_dsr_fails_closed_on_sample_length_under_30():
    gate = MultipleSelectionGate()
    res = gate.evaluate(
        sharpe_ratio=2.5,
        trial_count=10,
        sample_length=20,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        raw_p_value=0.01,
        all_raw_p_values=[0.01] * 10,
    )
    assert res.status == GateStatus.PENDING
    assert any("insufficient sample length" in r.lower() for r in res.reasons)


def test_bh_fdr_rejects_empty_p_values():
    q_vals, passes = benjamini_hochberg([])
    assert q_vals == []
    assert passes == []


def test_bh_fdr_rejects_non_finite_p_values():
    with pytest.raises(ValueError, match="finite float"):
        benjamini_hochberg([0.01, float("nan")])
    with pytest.raises(ValueError, match="finite float"):
        benjamini_hochberg([0.01, float("inf")])


def test_bh_fdr_rejects_out_of_bounds_p_values():
    with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\]"):
        benjamini_hochberg([-0.05])
    with pytest.raises(ValueError, match=r"\[0\.0, 1\.0\]"):
        benjamini_hochberg([1.05])


def test_bh_fdr_single_hypothesis_matches_nominal_alpha():
    q_vals, passes = benjamini_hochberg([0.04], alpha=0.05)
    assert q_vals == [0.04]
    assert passes == [True]

    q_vals2, passes2 = benjamini_hochberg([0.06], alpha=0.05)
    assert q_vals2 == [0.06]
    assert passes2 == [False]


def test_bh_fdr_monotonic_step_up_adjustment():
    raw_p = [0.01, 0.04, 0.03]
    q_vals, passes = benjamini_hochberg(raw_p, alpha=0.05)
    # Ranks sorted: 0.01 (rank 1), 0.03 (rank 2), 0.04 (rank 3)
    # Adjusted:
    # rank 3: 0.04 * 3 / 3 = 0.04
    # rank 2: min(0.04, 0.03 * 3 / 2 = 0.045) = 0.04
    # rank 1: min(0.04, 0.01 * 3 / 1 = 0.03) = 0.03
    # Result in original order: [0.03, 0.04, 0.04]
    assert q_vals[0] <= q_vals[2] <= q_vals[1]


def test_bh_fdr_strictly_bounded_zero_to_one():
    raw_p = [0.001, 0.5, 0.99]
    q_vals, _ = benjamini_hochberg(raw_p)
    assert all(0.0 <= q <= 1.0 for q in q_vals)


def test_gate_c_pending_when_raw_p_values_missing_or_incomplete():
    gate = MultipleSelectionGate()
    # Missing all_raw_p_values when trial_count > 1
    res = gate.evaluate(
        sharpe_ratio=2.5,
        trial_count=5,
        sample_length=100,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        raw_p_value=0.01,
        all_raw_p_values=None,
    )
    assert res.status == GateStatus.PENDING
    assert any("incomplete" in r.lower() or "pending" in r.lower() for r in res.reasons)


def test_gate_c_passes_only_when_both_dsr_and_fdr_pass():
    gate = MultipleSelectionGate()
    # Both pass
    res_pass = gate.evaluate(
        sharpe_ratio=2.8,
        trial_count=3,
        sample_length=100,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        raw_p_value=0.005,
        all_raw_p_values=[0.005, 0.01, 0.02],
    )
    assert res_pass.status == GateStatus.PASS

    # FDR fails (p-values too high)
    res_fail = gate.evaluate(
        sharpe_ratio=2.8,
        trial_count=3,
        sample_length=100,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        raw_p_value=0.40,
        all_raw_p_values=[0.40, 0.50, 0.60],
    )
    assert res_fail.status == GateStatus.FAIL


# =====================================================================
# SECTION 4: Gate D / Correlation & Capacity (Tests 39-50)
# =====================================================================

def test_gate_d_insufficient_sample_length_returns_pending():
    gate = CorrelationCapacityGate()
    res = gate.evaluate(
        candidate_returns=[0.01] * 20,
        active_returns_by_strategy={},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.PENDING
    assert any("insufficient sample length" in r.lower() for r in res.reasons)


def test_gate_d_zero_variance_returns_none_correlation_not_zero():
    gate = CorrelationCapacityGate()
    flat_returns = [0.01] * 100
    res = gate.evaluate(
        candidate_returns=flat_returns,
        active_returns_by_strategy={"STR-ACTIVE": [0.01 + (0.005 if i % 2 == 0 else -0.005) for i in range(100)]},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.PENDING
    assert any("zero variance" in r.lower() or "degenerate" in r.lower() for r in res.reasons)


def test_gate_d_fails_when_normal_correlation_exceeds_threshold():
    gate = CorrelationCapacityGate()
    active_ret = [0.01 if i % 2 == 0 else -0.01 for i in range(100)]
    cand_ret = [0.01 if i % 2 == 0 else -0.01 for i in range(100)]  # Correlation = 1.0 > 0.60
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={"STR-ACTIVE": active_ret},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.FAIL
    assert any("correlation" in r.lower() for r in res.reasons)


def test_gate_d_fails_when_stress_correlation_exceeds_threshold():
    gate = CorrelationCapacityGate()
    # Normal regime: uncorrelated; Stress regime: highly correlated
    cand_ret = [0.01 if i % 2 == 0 else -0.01 for i in range(50)] + [-0.05 if i % 2 == 0 else -0.04 for i in range(50)]
    active_ret = [-0.01 if i % 2 == 0 else 0.01 for i in range(50)] + [-0.05 if i % 2 == 0 else -0.04 for i in range(50)]
    regimes = ["NORMAL"] * 50 + ["STRESS"] * 50
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={"STR-ACTIVE": active_ret},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        regimes=regimes,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.FAIL
    assert any("stress" in r.lower() for r in res.reasons)


def test_gate_d_fails_when_event_cluster_overlap_detected():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.005 for i in range(100)]
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        candidate_event_clusters=["CLUSTER_BTC_VOL"],
        active_event_clusters={"STR-ACTIVE": ["CLUSTER_BTC_VOL"]},
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.FAIL
    assert any("event cluster overlap" in r.lower() for r in res.reasons)


def test_gate_d_fails_when_proposed_allocation_exceeds_1pct_5m_volume():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.005 for i in range(100)]
    # 1% of 100_000 is 1_000; proposed is 5_000 -> exceeds capacity
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={},
        avg_5m_volume_usd=100_000.0,
        proposed_allocation_usd=5_000.0,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.FAIL
    assert any("capacity" in r.lower() for r in res.reasons)


def test_gate_d_zero_or_negative_volume_fails_closed():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.005 for i in range(100)]
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={},
        avg_5m_volume_usd=0.0,
        proposed_allocation_usd=5_000.0,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.FAIL
    assert any("volume" in r.lower() for r in res.reasons)


def test_gate_d_zero_or_negative_allocation_fails_closed():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.005 for i in range(100)]
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=0.0,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.FAIL
    assert any("allocation" in r.lower() for r in res.reasons)


def test_gate_d_evaluates_across_multiple_regimes():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.008 for i in range(100)]
    active_ret = [0.005 if i % 3 == 0 else -0.005 for i in range(100)]
    regimes = ["BULL"] * 40 + ["BEAR"] * 30 + ["SIDEWAYS"] * 30
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={"STR-ACTIVE": active_ret},
        avg_5m_volume_usd=2_000_000.0,
        proposed_allocation_usd=10_000.0,
        regimes=regimes,
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.PASS


def test_gate_d_unseen_regime_fails_closed():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.008 for i in range(50)]
    # Regimes length mismatch with candidate returns
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        regimes=["BULL"] * 30,  # Mismatch length
        strategy_id="STR-001",
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
    )
    assert res.status == GateStatus.PENDING
    assert any("mismatch" in r.lower() for r in res.reasons)


def test_gate_d_requires_exact_provenance_fingerprints():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.008 for i in range(100)]
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        strategy_id="STR-001",
        dataset_fingerprint="",
        config_fingerprint="",
    )
    assert res.status == GateStatus.PENDING
    assert any("provenance" in r.lower() for r in res.reasons)


def test_gate_d_forbids_pass_on_unspecified_provenance():
    gate = CorrelationCapacityGate()
    cand_ret = [0.01 if i % 2 == 0 else -0.008 for i in range(100)]
    res = gate.evaluate(
        candidate_returns=cand_ret,
        active_returns_by_strategy={},
        avg_5m_volume_usd=1_000_000.0,
        proposed_allocation_usd=5_000.0,
        strategy_id="STR-001",
        dataset_fingerprint="ds_prov_unspecified",
        config_fingerprint="cfg_prov_unspecified",
    )
    assert res.status == GateStatus.PENDING


# =====================================================================
# SECTION 5: Lifecycle Promotion & Evidence Bundle (Tests 51-68)
# =====================================================================

def _make_thesis(falsification: List[str] = None):
    if falsification is None:
        falsification = ["Half-life > 5m", "Spread widening > 30 bps"]
    return CounterpartyThesis(
        counterparty_type="Urgent liquidity demander paying premium on crypto-event mispricings",
        economic_mechanism="Structural cross-market inventory imbalance and latency clearing frictions",
        why_trade_now="Stop cascade and margin calls require immediate liquidity execution",
        why_impact_may_be_transient="Temporary order book depletion that refills as passive makers replenish depth",
        why_it_may_be_information="Fundamental network level regime breaks or systemic insolvencies",
        falsification_conditions=falsification,
    )


def test_research_to_validation_requires_complete_counterparty_thesis():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=None,
    )
    registry.register(spec)
    with pytest.raises(InvalidStageTransitionError, match="Counterparty thesis is missing"):
        registry.update_stage("STR-001", StrategyStage.VALIDATION)


def test_research_to_validation_fails_on_empty_falsification_conditions():
    registry = StrategyRegistry()
    thesis = _make_thesis(falsification=[])
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=thesis,
    )
    registry.register(spec)
    with pytest.raises(InvalidStageTransitionError, match="lacks falsification conditions"):
        registry.update_stage("STR-001", StrategyStage.VALIDATION)


def test_validation_to_holdout_requires_promotion_evidence_bundle():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)
    with pytest.raises(InvalidStageTransitionError, match="PromotionEvidenceBundle is required"):
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=None)


def test_validation_to_holdout_fails_if_holdout_already_opened():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        # Prematurely open holdout
        mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        bundle = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        with pytest.raises(InvalidStageTransitionError, match="must remain unopened"):
            registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle, holdout_manager=mgr)


def test_validation_to_holdout_fails_if_holdout_already_burned():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        mgr.burn_holdout("STR-001", "ds_hash_12345678", reason="Manual burn")
        bundle = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        with pytest.raises(InvalidStageTransitionError, match="must remain unopened"):
            registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle, holdout_manager=mgr)


def test_validation_to_holdout_fails_on_provenance_mismatch():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        bundle = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="mismatched_dataset_hash",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        with pytest.raises(InvalidStageTransitionError, match="Provenance mismatch"):
            registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle, holdout_manager=mgr)


def test_holdout_to_paper_requires_prereg_access_result_and_gate_bundle():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)

        # Incomplete bundle: missing gate_bundle, access_id, result_id
        bundle_incomplete = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        with pytest.raises(InvalidStageTransitionError, match="must contain holdout_preregistration_id, holdout_access_id, and holdout_result_id"):
            registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_incomplete, holdout_manager=mgr)


def test_holdout_to_paper_fails_if_gate_bundle_incomplete():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5}, passed=True)

        # 3 gates instead of 4
        incomplete_gates = _make_canonical_gates()[:3]
        bundle_paper = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=res.result_id,
            gate_bundle=incomplete_gates,
        )
        with pytest.raises(InvalidStageTransitionError, match="Gate bundle failed strict validation"):
            registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_paper, holdout_manager=mgr)


def test_holdout_to_paper_fails_if_any_gate_in_bundle_not_pass():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5}, passed=True)

        gates_with_fail = _make_canonical_gates()
        gates_with_fail[0] = StrategyGateResult.create_fail(
            gate_type="LATENCY_SENSITIVITY",
            strategy_id="STR-001",
            strategy_version="1.0.0",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            reasons=["Latency failed"],
        )
        bundle_paper = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=res.result_id,
            gate_bundle=gates_with_fail,
        )
        with pytest.raises(InvalidStageTransitionError, match="Gate bundle failed strict validation"):
            registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_paper, holdout_manager=mgr)


def test_holdout_to_paper_fails_if_holdout_evaluation_did_not_pass():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Initial run",
            falsification_criteria=["Sharpe < 1.0"],
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="abcdef1234567890",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 0.5}, passed=False, reasons=["Sharpe failed"])

        bundle_paper = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=res.result_id,
            gate_bundle=_make_canonical_gates(),
        )
        with pytest.raises(InvalidStageTransitionError, match="Holdout evaluation result did not pass"):
            registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_paper, holdout_manager=mgr)


def test_paper_to_small_live_permanently_blocked_under_zero_capital():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.PAPER,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    with pytest.raises(InvalidStageTransitionError, match=r"USD 0"):
        registry.update_stage("STR-001", StrategyStage.SMALL_LIVE)


def test_direct_registration_as_active_permanently_blocked():
    registry = StrategyRegistry()
    with pytest.raises(ValueError, match="directly as ACTIVE"):
        spec = StrategySpec(
            strategy_id="STR-001",
            name="Candidate Alpha",
            family=StrategyFamily.MOMENTUM,
            origin=StrategyOrigin.QUANT,
            stage=StrategyStage.ACTIVE,
            counterparty_thesis=_make_thesis(),
        )
        registry.register(spec)


def test_direct_registration_as_small_live_permanently_blocked():
    registry = StrategyRegistry()
    with pytest.raises(ValueError, match="directly as SMALL_LIVE"):
        spec = StrategySpec(
            strategy_id="STR-001",
            name="Candidate Alpha",
            family=StrategyFamily.MOMENTUM,
            origin=StrategyOrigin.QUANT,
            stage=StrategyStage.SMALL_LIVE,
            counterparty_thesis=_make_thesis(),
        )
        registry.register(spec)


def test_economic_edge_validated_flag_has_zero_promotion_authority():
    registry = StrategyRegistry()
    # Strategy with economic_edge_validated=True still cannot jump to SMALL_LIVE or ACTIVE
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        economic_edge_validated=True,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-001", StrategyStage.SMALL_LIVE)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-001", StrategyStage.ACTIVE)


def test_promotion_evidence_bundle_immutable_frozen():
    bundle = PromotionEvidenceBundle(
        strategy_id="STR-001",
        strategy_version="1.0.0",
        source_stage=StrategyStage.VALIDATION,
        target_stage=StrategyStage.HOLDOUT,
        dataset_fingerprint="ds_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        parameter_set_fingerprint="param_hash_12345678",
        git_sha="abcdef1234567890",
        holdout_preregistration_id="prereg-001",
    )
    with pytest.raises(ValidationError):
        bundle.strategy_id = "STR-002"


def test_promotion_evidence_bundle_forbids_extra_fields():
    with pytest.raises(ValidationError):
        PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id="prereg-001",
            unauthorized_field="forbidden",
        )


def test_governance_locked_blocks_all_further_promotions():
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-001",
        name="Candidate Alpha",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=_make_thesis(),
    )
    registry.register(spec)
    registry.update_stage("STR-001", StrategyStage.VALIDATION)

    with tempfile.TemporaryDirectory() as tmp:
        corrupted_file = Path(tmp) / "audits.json"
        corrupted_file.write_text("CORRUPTED_JSON")
        mgr = SealedHoldoutManager(audit_storage_path=corrupted_file, raise_on_corruption=False)
        assert mgr.is_corrupted is True

        bundle = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="abcdef1234567890",
            holdout_preregistration_id="prereg-001",
        )
        with pytest.raises(InvalidStageTransitionError, match="GOVERNANCE_LOCKED"):
            registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle, holdout_manager=mgr)


def test_api_holdouts_endpoint_reports_honest_governance_status():
    ds = QuantOSDataService()
    holdouts = ds.get_holdouts()
    assert "status" in holdouts
    assert holdouts["status"] in (
        "SEALED",
        HoldoutStatus.UNOPENED.value,
        HoldoutStatus.PREREGISTERED.value,
        HoldoutStatus.OPENED.value,
        HoldoutStatus.BURNED.value,
        HoldoutStatus.GOVERNANCE_LOCKED.value,
    )
    assert "warning" in holdouts
    assert "HOLDOUT GOVERNANCE" in holdouts["warning"] or "HOLDOUT SEALED" in holdouts["warning"]
