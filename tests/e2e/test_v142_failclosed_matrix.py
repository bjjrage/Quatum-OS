"""
Red-Team Fail-Closed Matrix (v1.4.2 Invariant Verification).

24 dedicated adversarial tests proving that:
UNKNOWN != SAFE
CORRUPTED != EMPTY
MISSING != PASS
UNVERIFIED != ALLOWED

Every failure scenario must FAIL CLOSED:
(BLOCK, PENDING, CONTINUITY_BROKEN, MANUAL_REVIEW_REQUIRED, raises integrity error).
Zero silent recovery. Zero clean-state fallback after losing auditable state.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from src.quality.acceptance import (
    RuntimeManifest,
    RecorderContinuityError,
    AcceptanceContinuityState,
)
from src.risk.capital_pockets import (
    PropRuleProfile,
    PropProfileVerificationStatus,
    PropExamMonteCarloSimulator,
    TradeSample,
)
from src.research.experiments import (
    ExperimentRegistry,
    ExperimentRegistryIntegrityError,
    RegistryIntegrityStatus,
    ExperimentRecord,
)
from src.research.holdout import (
    SealedHoldoutManager,
    HoldoutAuditIntegrityError,
    HoldoutAuditRecord,
)
from src.portfolio.gates import (
    StrategyGateResult,
    GateStatus,
)
from src.strategies.models import (
    CounterpartyThesis,
    StrategySpec,
    StrategyOrigin,
    StrategyFamily,
)


# ============================================================================
# Category 1: Continuous Recorder State Integrity (Vectors 1 - 3)
# ============================================================================

def test_vector_01_corrupt_manifest_json_raises_recorder_continuity_error(tmp_path: Path):
    """Vector 1: Malformed / corrupted manifest JSON must raise RecorderContinuityError."""
    manifest_path = tmp_path / "runtime_manifest.json"
    manifest_path.write_text("{ corrupt json: [not valid", encoding="utf-8")

    with pytest.raises(RecorderContinuityError, match="failed integrity parsing"):
        RuntimeManifest.resume_or_create(
            filepath=manifest_path,
            pid=3003,
            git_sha="sha_test",
            config_fingerprint="fingerprint_abc",
            fail_closed=True,
        )


def test_vector_02_truncated_manifest_json_raises_recorder_continuity_error(tmp_path: Path):
    """Vector 2: Truncated / partial manifest JSON must raise RecorderContinuityError."""
    manifest_path = tmp_path / "runtime_manifest.json"
    manifest_path.write_text('{"run_id": "run_incomplete', encoding="utf-8")

    with pytest.raises(RecorderContinuityError, match="failed integrity parsing"):
        RuntimeManifest.resume_or_create(
            filepath=manifest_path,
            pid=3003,
            git_sha="sha_test",
            config_fingerprint="fingerprint_abc",
            fail_closed=True,
        )


def test_vector_03_invalid_schema_manifest_raises_recorder_continuity_error(tmp_path: Path):
    """Vector 3: Valid JSON with missing/invalid required fields must raise RecorderContinuityError."""
    manifest_path = tmp_path / "runtime_manifest.json"
    manifest_path.write_text(json.dumps({"invalid_field": 12345}), encoding="utf-8")

    with pytest.raises(RecorderContinuityError, match="failed integrity parsing"):
        RuntimeManifest.resume_or_create(
            filepath=manifest_path,
            pid=3003,
            git_sha="sha_test",
            config_fingerprint="fingerprint_abc",
            fail_closed=True,
        )


# ============================================================================
# Category 2: Prop Firm Verification & Attempt Isolation (Vectors 4 - 7)
# ============================================================================

def _make_dummy_trades(count: int = 40) -> list[TradeSample]:
    return [
        TradeSample(
            trade_id=f"T_{i}",
            timestamp_ns=1700000000000000000 + i * 1_000_000_000,
            net_return=0.01,
            pnl_usd=100.0,
            mfe_usd=150.0,
            mae_usd=-50.0,
            holding_time_s=300.0,
        )
        for i in range(count)
    ]


def test_vector_04_unverified_prop_profile_simulation_returns_blocked():
    """Vector 4: Unverified prop profile must return status='BLOCKED_UNVERIFIED_PROFILE'."""
    unverified_profile = PropRuleProfile(
        provider_id="FIRMX",
        firm_name="Firm X",
        version="v1.0",
        verification_status=PropProfileVerificationStatus.PENDING,
    )
    simulator = PropExamMonteCarloSimulator()
    dummy_trades = _make_dummy_trades(40)
    res = simulator.simulate(
        strategy_id="STR-002",
        profile=unverified_profile,
        trades=dummy_trades,
    )
    assert res["status"] == "BLOCKED_UNVERIFIED_PROFILE"
    assert "unverified or unusable" in res["reason"]


def test_vector_05_unverified_prop_profile_not_eligible_for_paid_exam():
    """Vector 5: Unverified prop profile must strictly set eligible_for_paid_exam=False."""
    unverified_profile = PropRuleProfile(
        provider_id="FIRMX",
        firm_name="Firm X",
        version="v1.0",
        verification_status=PropProfileVerificationStatus.PENDING,
    )
    assert unverified_profile.is_usable_for_exam()[0] is False

    simulator = PropExamMonteCarloSimulator()
    dummy_trades = _make_dummy_trades(40)
    res = simulator.simulate(
        strategy_id="STR-002",
        profile=unverified_profile,
        trades=dummy_trades,
    )
    assert res["eligible_for_paid_exam"] is False


def test_vector_06_prop_attempt_tuple_collision_isolated_by_version():
    """Vector 6: Prop attempt tracking must be strictly isolated by (strategy_id, version, provider, profile_version)."""
    simulator = PropExamMonteCarloSimulator()

    # 5 fails on (STR-002, APEX, strategy_version=1.0.0, profile_version=v1.0)
    for _ in range(5):
        simulator.record_attempt_result(
            strategy_id="STR-002",
            provider_id="APEX",
            passed=False,
            strategy_version="1.0.0",
            profile_version="v1.0",
        )

    assert simulator.is_combination_eligible("STR-002", "APEX", strategy_version="1.0.0", profile_version="v1.0") is False

    # (STR-002, APEX, strategy_version=1.0.0, profile_version=v2.0) has 0 attempts -> eligible
    assert simulator.is_combination_eligible("STR-002", "APEX", strategy_version="1.0.0", profile_version="v2.0") is True


def test_vector_07_prop_attempt_five_fails_on_v1_does_not_poison_v2():
    """Vector 7: 5 failed attempts on strategy v1.0.0 must NOT poison strategy v2.0.0."""
    simulator = PropExamMonteCarloSimulator()

    for _ in range(5):
        simulator.record_attempt_result(
            strategy_id="STR-002",
            provider_id="TOPSTEP",
            passed=False,
            strategy_version="1.0.0",
            profile_version="v1.0",
        )

    assert simulator.is_combination_eligible("STR-002", "TOPSTEP", strategy_version="1.0.0", profile_version="v1.0") is False

    # Strategy v2.0.0 is isolated and clean
    assert simulator.is_combination_eligible("STR-002", "TOPSTEP", strategy_version="2.0.0", profile_version="v1.0") is True


# ============================================================================
# Category 3: Experiment Registry Persistence Integrity (Vectors 8 - 10)
# ============================================================================

def test_vector_08_corrupt_experiment_file_marks_registry_corrupted(tmp_path: Path):
    """Vector 8: Any corrupted experiment record in storage raises ExperimentRegistryIntegrityError upon initialization."""
    reg_dir = tmp_path / "experiments"
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "bad_exp.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(ExperimentRegistryIntegrityError, match="corruption detected"):
        ExperimentRegistry(storage_dir=reg_dir)


def test_vector_09_partial_experiment_json_blocks_new_trial_registration(tmp_path: Path):
    """Vector 9: Corrupted experiment storage blocks recording with ExperimentRegistryIntegrityError."""
    reg_dir = tmp_path / "experiments"
    reg_dir.mkdir(parents=True, exist_ok=True)
    (reg_dir / "incomplete.json").write_text('{"experiment_id": "partial', encoding="utf-8")

    with pytest.raises(ExperimentRegistryIntegrityError):
        ExperimentRegistry(storage_dir=reg_dir)

    # Corrupted instance refuses record_experiment
    reg = ExperimentRegistry.__new__(ExperimentRegistry)
    reg.storage_dir = reg_dir
    reg._experiments = {}
    reg._strategy_trial_counts = {}
    reg.status = RegistryIntegrityStatus.CORRUPTED
    reg.quarantine_log = []

    rec = ExperimentRecord(
        experiment_id="exp_new",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        parameters={"lookback": 20},
    )
    with pytest.raises(ExperimentRegistryIntegrityError, match="Cannot record experiment"):
        reg.record_experiment(rec)


def test_vector_10_corrupt_registry_get_trial_count_raises_never_returns_zero(tmp_path: Path):
    """Vector 10: Corrupted registry must NEVER return trial_count=0; it must raise ExperimentRegistryIntegrityError."""
    reg_dir = tmp_path / "experiments"
    reg_dir.mkdir(parents=True, exist_ok=True)

    reg = ExperimentRegistry.__new__(ExperimentRegistry)
    reg.storage_dir = reg_dir
    reg._experiments = {}
    reg._strategy_trial_counts = {}
    reg.status = RegistryIntegrityStatus.CORRUPTED
    reg.quarantine_log = []

    with pytest.raises(ExperimentRegistryIntegrityError, match="Cannot return trial count"):
        reg.get_trial_count("STR-002")


# ============================================================================
# Category 4: Sealed Holdout Audit Integrity (Vectors 11 - 12)
# ============================================================================

def test_vector_11_corrupt_holdout_audit_file_raises_integrity_error(tmp_path: Path):
    """Vector 11: Corrupted holdout audit file must raise HoldoutAuditIntegrityError upon audit check."""
    audit_file = tmp_path / "holdout_audit.json"
    audit_file.write_text("{ corrupted audit log", encoding="utf-8")

    with pytest.raises(HoldoutAuditIntegrityError, match="corrupted"):
        SealedHoldoutManager(audit_storage_path=audit_file)


def test_vector_12_corrupt_holdout_audit_locks_evaluate_holdout(tmp_path: Path):
    """Vector 12: Corrupted holdout audit file strictly locks evaluate_holdout and refuses evaluation."""
    audit_file = tmp_path / "holdout_audit.json"
    audit_file.write_text("corrupted content", encoding="utf-8")

    with pytest.raises(HoldoutAuditIntegrityError, match="corrupted"):
        SealedHoldoutManager(audit_storage_path=audit_file)

    compromised_mgr = SealedHoldoutManager.__new__(SealedHoldoutManager)
    compromised_mgr.audit_storage_path = audit_file
    compromised_mgr._audits = []
    compromised_mgr._is_corrupted = True
    compromised_mgr._corruption_error = "Corrupted by attacker"

    with pytest.raises(HoldoutAuditIntegrityError, match="Holdout dataset access is strictly locked"):
        compromised_mgr.evaluate_holdout(
            strategy_id="STR-002",
            strategy_version="2.0.0",
            git_sha="sha_exploit",
            parameter_set_fingerprint="fp_exploit",
            hypothesis_description="Exploit",
            holdout_dataset_bytes_or_hash="bytes",
            metrics={"net_sharpe": 1.5},
        )


# ============================================================================
# Category 5: StrategyGateResult Invariant Enforcement (Vectors 13 - 18)
# ============================================================================

def test_vector_13_strategy_gate_pass_with_falsification_evidence_rejected():
    """Vector 13: StrategyGateResult cannot declare status=PASS with falsification_evidence."""
    with pytest.raises(ValueError, match="cannot declare status=PASS with falsification_evidence"):
        StrategyGateResult(
            strategy_id="STR-001",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"latency_ok": True},
            falsification_evidence="Simulated race detected",
        )


def test_vector_14_strategy_gate_pass_with_reasons_rejected():
    """Vector 14: StrategyGateResult cannot declare status=PASS with non-empty reasons."""
    with pytest.raises(ValueError, match="cannot declare status=PASS with non-empty reasons"):
        StrategyGateResult(
            strategy_id="STR-001",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"latency_ok": True},
            reasons=["Failed temporal split"],
        )


def test_vector_15_strategy_gate_pass_with_empty_criteria_evaluations_rejected():
    """Vector 15: StrategyGateResult with status=PASS requires non-empty criteria_evaluations."""
    with pytest.raises(ValueError, match="status=PASS requires non-empty criteria_evaluations"):
        StrategyGateResult(
            strategy_id="STR-001",
            gate_type="TEMPORAL",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={},
        )


def test_vector_16_strategy_gate_pass_with_false_criteria_evaluation_rejected():
    """Vector 16: StrategyGateResult cannot declare status=PASS when any criteria evaluation is False."""
    with pytest.raises(ValueError, match="status=PASS cannot contain False criteria evaluations"):
        StrategyGateResult(
            strategy_id="STR-001",
            gate_type="MULTIPLE_SELECTION",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"dsr_significant": False, "pvalue_ok": True},
        )


def test_vector_17_strategy_gate_empty_dataset_fingerprint_rejected():
    """Vector 17: StrategyGateResult with empty dataset_fingerprint must be rejected (provenance violation)."""
    with pytest.raises(ValueError, match="Provenance violation"):
        StrategyGateResult(
            strategy_id="STR-001",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="",
            config_fingerprint="cfg_fp",
            criteria_evaluations={"ok": True},
        )


def test_vector_18_strategy_gate_empty_config_fingerprint_rejected():
    """Vector 18: StrategyGateResult with empty config_fingerprint must be rejected (provenance violation)."""
    with pytest.raises(ValueError, match="Provenance violation"):
        StrategyGateResult(
            strategy_id="STR-001",
            gate_type="LATENCY",
            status=GateStatus.PASS,
            dataset_fingerprint="ds_fp",
            config_fingerprint="",
            criteria_evaluations={"ok": True},
        )


# ============================================================================
# Category 6: Core Model Immutability Audit (Vectors 19 - 24)
# ============================================================================

def test_vector_19_mutation_attempt_on_strategy_gate_result_raises():
    """Vector 19: Mutation attempt on StrategyGateResult must raise."""
    res = StrategyGateResult.create_pass(
        strategy_id="STR-001",
        gate_type="GATE_A",
        dataset_fingerprint="ds_fp",
        config_fingerprint="cfg_fp",
        criteria_evaluations={"ok": True},
    )
    with pytest.raises(Exception):
        res.status = GateStatus.FAIL


def test_vector_20_mutation_attempt_on_prop_rule_profile_raises():
    """Vector 20: Mutation attempt on PropRuleProfile must raise."""
    profile = PropRuleProfile(
        provider_id="TOPSTEP",
        version="v1.0",
        verification_status=PropProfileVerificationStatus.PENDING,
    )
    with pytest.raises(Exception):
        profile.verification_status = PropProfileVerificationStatus.VERIFIED


def test_vector_21_mutation_attempt_on_experiment_record_raises():
    """Vector 21: Mutation attempt on ExperimentRecord must raise."""
    record = ExperimentRecord(
        experiment_id="exp_001",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        parameters={"lookback": 20},
    )
    with pytest.raises(Exception):
        record.strategy_version = "3.0.0"


def test_vector_22_mutation_attempt_on_holdout_audit_record_raises(tmp_path: Path):
    """Vector 22: Mutation attempt on HoldoutAuditRecord must raise."""
    audit = HoldoutAuditRecord(
        audit_id="audit_test_001",
        opened_by="SYSTEM_RESEARCH_GATE",
        timestamp_ns=1000,
        timestamp_utc="2026-10-03T12:00:00Z",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        git_sha="git_sha_abc123",
        parameter_set_fingerprint="fp_params_v1",
        hypothesis_description="Post-liquidation altcoin bounce",
        holdout_dataset_hash="dataset_raw_bytes",
        result_metrics={"net_sharpe": 1.5},
    )
    with pytest.raises(Exception):
        audit.strategy_version = "2.1.0"


def test_vector_23_mutation_attempt_on_counterparty_thesis_raises():
    """Vector 23: Mutation attempt on CounterpartyThesis must raise."""
    thesis = CounterpartyThesis(
        counterparty_type="Urgent Hedgers",
        economic_mechanism="Structural Imbalance",
        why_trade_now="Forced liquidation",
        why_impact_may_be_transient="Order book replenishes",
        why_it_may_be_information="Fundamental hack",
        falsification_conditions=["Expectancy < fees"],
    )
    with pytest.raises(Exception):
        thesis.counterparty_type = "Modified Hedgers"


def test_vector_24_mutation_attempt_on_strategy_spec_raises():
    """Vector 24: Mutation attempt on StrategySpec must raise."""
    spec = StrategySpec(
        strategy_id="STR-002",
        name="Impulse Reversal",
        family=StrategyFamily.BEHAVIORAL,
        origin=StrategyOrigin.HUMAN,
    )
    with pytest.raises(Exception):
        spec.name = "Tampered Name"
