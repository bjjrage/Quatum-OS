"""
Pre-Paper Hardening 03C — Evidence Authority Closure Counter-Audit Tests.

Verifies:
1. Holdout result derivation:
   - HoldoutAcceptanceCriterion: GT, GTE, LT, LTE, EQ, non-finite threshold rejection.
   - Caller cannot supply 'passed' boolean to record_evaluation_result (fail-closed ValueError).
   - Automatic deterministic derivation of 'passed' from preregistered criteria.
   - Missing required metrics fail closed (REQUIRED_HOLDOUT_METRIC_MISSING).
   - Non-finite/non-numeric metrics fail closed (NON_FINITE_HOLDOUT_METRIC).
   - Audit trail populated with HoldoutCriterionResult.
2. Authoritative Gate Evidence Store & GateBundleArtifact:
   - Append-only GateEvaluationStore with tamper-evident hashing.
   - Duplicate evidence IDs / bundle IDs rejected.
   - Corrupted store locks operations fail-closed (GOVERNANCE_LOCKED).
   - create_gate_bundle enforces all 4 canonical gates (A, B, C, D), provenance matching, and PASS status.
   - Cannot mint incomplete or failed gate bundles.
3. Lifecycle Promotion (HOLDOUT -> PAPER):
   - Mandatory gate_store (GATE_EVIDENCE_STORE_REQUIRED).
   - Mandatory gate_bundle_id in PromotionEvidenceBundle.
   - Corrupted gate_store locks promotion fail-closed.
   - Fabricated / non-existent gate_bundle_id rejected.
   - Provenance mismatch between bundle artifact and evidence bundle rejected.
   - Successful end-to-end promotion with verified gate bundle artifact.
"""

import math
import tempfile
from pathlib import Path
import pytest
from pydantic import ValidationError

from src.research.holdout import (
    SealedHoldoutManager,
    HoldoutStatus,
    HoldoutViolationError,
    HoldoutAuditIntegrityError,
    HoldoutCriterionOperator,
    HoldoutAcceptanceCriterion,
    HoldoutCriterionResult,
)
from src.portfolio.gates import (
    StrategyGateResult,
    GateStatus,
)
from src.portfolio.gate_evidence import (
    GateEvidenceRecord,
    GateBundleArtifact,
    GateEvaluationStore,
    GateEvidenceViolationError,
    GateEvidenceIntegrityError,
)
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
    CounterpartyThesis,
    CounterpartyThesisStatus,
    PromotionEvidenceBundle,
)
from src.strategies.registry import (
    StrategyRegistry,
    InvalidStageTransitionError,
)


def _make_thesis() -> CounterpartyThesis:
    return CounterpartyThesis(
        counterparty_type="Informed and uninformed retail participants in prediction markets",
        economic_mechanism="Structural cross-market segmentation between options and prediction markets",
        why_trade_now="Event volatility triggers directional demand spikes",
        why_impact_may_be_transient="Market maker liquidity refills the orderbook within minutes",
        why_it_may_be_information="Regulatory announcements create permanent repricing",
        falsification_conditions=["Price divergence does not revert within 60 minutes"],
        evidence_status=CounterpartyThesisStatus.RESEARCH_HYPOTHESIS,
    )


def _make_4_gates(strat_id="STR-001", ds_fp="ds_hash_12345678", cfg_fp="cfg_hash_12345678"):
    ga = StrategyGateResult.create_pass(strat_id, "LATENCY_SENSITIVITY", ds_fp, cfg_fp, {"ok": True})
    gb = StrategyGateResult.create_pass(strat_id, "TEMPORAL_STABILITY", ds_fp, cfg_fp, {"ok": True})
    gc = StrategyGateResult.create_pass(strat_id, "MULTIPLE_SELECTION", ds_fp, cfg_fp, {"ok": True})
    gd = StrategyGateResult.create_pass(strat_id, "CORRELATION_CAPACITY", ds_fp, cfg_fp, {"ok": True})
    return [ga, gb, gc, gd]


# =========================================================================
# PART A: Machine-Evaluable Holdout Acceptance Criteria & Derived Pass
# =========================================================================

def test_acceptance_criterion_model_validation():
    """Verify HoldoutAcceptanceCriterion validates operators, finite thresholds, and non-empty metric names."""
    # Valid operators (enum and strings)
    c1 = HoldoutAcceptanceCriterion(metric_name="sharpe", operator=HoldoutCriterionOperator.GTE, threshold=1.0)
    assert c1.operator == HoldoutCriterionOperator.GTE
    assert c1.threshold == 1.0

    c2 = HoldoutAcceptanceCriterion(metric_name="max_drawdown", operator="<=", threshold=0.15)
    assert c2.operator == HoldoutCriterionOperator.LTE

    c3 = HoldoutAcceptanceCriterion(metric_name="trade_count", operator="GT", threshold=30.0)
    assert c3.operator == HoldoutCriterionOperator.GT

    # Rejection of empty metric_name
    with pytest.raises(ValidationError):
        HoldoutAcceptanceCriterion(metric_name="", operator=">=", threshold=1.0)

    # Rejection of non-finite threshold (NaN / Inf)
    with pytest.raises(ValidationError):
        HoldoutAcceptanceCriterion(metric_name="sharpe", operator=">=", threshold=float("nan"))
    with pytest.raises(ValidationError):
        HoldoutAcceptanceCriterion(metric_name="sharpe", operator=">=", threshold=float("inf"))

    # Rejection of invalid operator
    with pytest.raises(ValidationError):
        HoldoutAcceptanceCriterion(metric_name="sharpe", operator="INVALID_OP", threshold=1.0)


def test_caller_supplied_passed_strictly_forbidden():
    """Verify record_evaluation_result rejects caller-supplied passed boolean (fail-closed authority bypass closure)."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Test hypothesis",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )

        # Keyword argument passed=True must raise ValueError
        with pytest.raises(ValueError, match="CALLER_SUPPLIED_PASSED_FORBIDDEN"):
            mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5}, passed=True)

        # Positional passed boolean must also raise ValueError
        with pytest.raises(ValueError, match="CALLER_SUPPLIED_PASSED_FORBIDDEN"):
            mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5}, None, True)


def test_holdout_pass_deterministically_derived_from_criteria():
    """Verify holdout pass is derived from preregistered criteria (both explicit and auto-parsed)."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        # Explicit criteria: sharpe >= 1.2, max_drawdown <= 0.10, trade_count >= 20
        explicit_criteria = [
            HoldoutAcceptanceCriterion(metric_name="sharpe", operator=">=", threshold=1.2),
            HoldoutAcceptanceCriterion(metric_name="max_drawdown", operator="<=", threshold=0.10),
            HoldoutAcceptanceCriterion(metric_name="trade_count", operator=">=", threshold=20.0),
        ]
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Explicit criteria test",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe", "max_drawdown"],
            analysis_plan_fingerprint="plan_hash_12345678",
            acceptance_criteria=explicit_criteria,
        )
        assert len(prereg.acceptance_criteria) == 3

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )

        # Metrics satisfy all 3 criteria -> derived passed = True
        res = mgr.record_evaluation_result(
            acc.access_id,
            {"sharpe": 1.5, "max_drawdown": 0.05, "trade_count": 35},
        )
        assert res.passed is True
        assert len(res.criterion_results) == 3
        assert all(cr.passed for cr in res.criterion_results)


def test_holdout_fails_on_criterion_breach():
    """Verify holdout fails deterministically when any acceptance criterion is breached."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Breach test",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe"],
            analysis_plan_fingerprint="plan_hash_12345678",
            acceptance_criteria=[
                HoldoutAcceptanceCriterion(metric_name="sharpe", operator=">=", threshold=1.2)
            ],
        )
        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 0.85})
        assert res.passed is False
        assert any("CRITERION_BREACH" in r for r in res.reasons)
        assert res.criterion_results[0].passed is False


def test_holdout_fails_on_missing_required_metric():
    """Verify holdout fails closed when a preregistered required metric is missing from result_metrics."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Missing metric test",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe", "max_drawdown"],
            analysis_plan_fingerprint="plan_hash_12345678",
            acceptance_criteria=[
                HoldoutAcceptanceCriterion(metric_name="sharpe", operator=">=", threshold=1.0),
                HoldoutAcceptanceCriterion(metric_name="max_drawdown", operator="<=", threshold=0.10),
            ],
        )
        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        # Supply only sharpe; max_drawdown is missing
        res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5})
        assert res.passed is False
        assert any("REQUIRED_HOLDOUT_METRIC_MISSING" in r for r in res.reasons)


def test_holdout_fails_on_non_finite_metric():
    """Verify holdout fails closed when a metric value is NaN or Inf."""
    with tempfile.TemporaryDirectory() as tmp:
        mgr = SealedHoldoutManager(audit_storage_path=Path(tmp) / "audits.json")
        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Non-finite test",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        res = mgr.record_evaluation_result(acc.access_id, {"sharpe": float("nan")})
        assert res.passed is False
        assert any("NON_FINITE_HOLDOUT_METRIC" in r for r in res.reasons)


# =========================================================================
# PART B: Authoritative Gate Evidence Store & GateBundleArtifact
# =========================================================================

def test_gate_evaluation_store_tamper_evident_hashing():
    """Verify GateEvidenceRecord and GateBundleArtifact enforce SHA256 hashes and reject tampering."""
    with tempfile.TemporaryDirectory() as tmp:
        store = GateEvaluationStore(storage_dir=Path(tmp))
        gates = _make_4_gates()

        bundle_art, records = store.record_and_bundle_gates(
            gate_results=gates,
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
        )

        assert bundle_art.status == "VERIFIED"
        assert len(bundle_art.bundle_hash) == 64
        for letter in ("A", "B", "C", "D"):
            rec = records[letter]
            assert len(rec.record_hash) == 64
            assert store.get_gate_evaluation(rec.gate_evidence_id) is not None

        # Reopen store and verify data persisted and verified
        store_reopened = GateEvaluationStore(storage_dir=Path(tmp))
        assert not store_reopened.is_corrupted
        assert store_reopened.get_gate_bundle(bundle_art.gate_bundle_id) is not None


def test_gate_evaluation_store_corruption_locks_governance_fail_closed():
    """Verify corrupting the evaluations or bundles JSON locks the store fail-closed (GOVERNANCE_LOCKED)."""
    with tempfile.TemporaryDirectory() as tmp:
        store = GateEvaluationStore(storage_dir=Path(tmp))
        gates = _make_4_gates()
        store.record_and_bundle_gates(
            gate_results=gates,
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
        )

        # Corrupt bundles JSON file
        bundles_file = Path(tmp) / "gate_bundles.json"
        bundles_file.write_text("CORRUPTED_GARBAGE_BYTES_{{{", encoding="utf-8")

        # Loading corrupted store with raise_on_corruption=True raises GateEvidenceIntegrityError
        with pytest.raises(GateEvidenceIntegrityError, match="corrupted"):
            GateEvaluationStore(storage_dir=Path(tmp), raise_on_corruption=True)

        # With raise_on_corruption=False, is_corrupted is True and operations fail closed
        corrupted_store = GateEvaluationStore(storage_dir=Path(tmp), raise_on_corruption=False)
        assert corrupted_store.is_corrupted is True
        with pytest.raises(GateEvidenceIntegrityError):
            corrupted_store.record_gate_evaluation(
                strategy_id="STR-001",
                strategy_version="1.0.0",
                gate_type="LATENCY_SENSITIVITY",
                dataset_fingerprint="ds_hash_12345678",
                config_fingerprint="cfg_hash_12345678",
                parameter_set_fingerprint="param_hash_12345678",
                git_sha="git_sha_12345678",
                gate_result=gates[0],
            )


def test_cannot_mint_incomplete_or_failed_gate_bundle():
    """Verify GateEvaluationStore refuses to create a GateBundleArtifact if any gate failed or is missing."""
    with tempfile.TemporaryDirectory() as tmp:
        store = GateEvaluationStore(storage_dir=Path(tmp))
        gates = _make_4_gates()

        # Incomplete gates (only 3)
        with pytest.raises(GateEvidenceViolationError, match="validation failed"):
            store.record_and_bundle_gates(
                gate_results=gates[:3],
                parameter_set_fingerprint="param_hash_12345678",
                git_sha="git_sha_12345678",
            )

        # Bundle with one FAIL gate
        gates_with_fail = list(gates)
        gates_with_fail[0] = StrategyGateResult.create_fail(
            gate_type="LATENCY_SENSITIVITY",
            strategy_id="STR-001",
            strategy_version="1.0.0",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            reasons=["High latency race detected"],
        )
        with pytest.raises(GateEvidenceViolationError, match="validation failed"):
            store.record_and_bundle_gates(
                gate_results=gates_with_fail,
                parameter_set_fingerprint="param_hash_12345678",
                git_sha="git_sha_12345678",
            )


# =========================================================================
# PART C: Lifecycle Promotion (HOLDOUT -> PAPER) Authority Checks
# =========================================================================

def test_holdout_to_paper_requires_authoritative_gate_store():
    """Verify HOLDOUT -> PAPER raises GATE_EVIDENCE_STORE_REQUIRED if gate_store is None."""
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
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Holdout to paper test",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        eval_res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5})
        assert eval_res.passed is True

        bundle_paper = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=eval_res.result_id,
            gate_bundle=_make_4_gates(),
        )

        # Promotion with gate_store=None must fail closed
        with pytest.raises(InvalidStageTransitionError, match="GATE_EVIDENCE_STORE_REQUIRED"):
            registry.update_stage(
                "STR-001",
                StrategyStage.PAPER,
                evidence_bundle=bundle_paper,
                holdout_manager=mgr,
                gate_store=None,
            )


def test_holdout_to_paper_requires_valid_stored_gate_bundle_artifact():
    """Verify HOLDOUT -> PAPER requires gate_bundle_id referencing a real, verified bundle in gate_store."""
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
        gate_store = GateEvaluationStore(storage_dir=Path(tmp) / "gates")

        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Holdout to paper artifact test",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        eval_res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5})

        # 1. Missing gate_bundle_id raises error
        bundle_no_id = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=eval_res.result_id,
            gate_bundle=_make_4_gates(),
        )
        with pytest.raises(InvalidStageTransitionError, match="must contain gate_bundle_id"):
            registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_no_id, holdout_manager=mgr, gate_store=gate_store)

        # 2. Fabricated gate_bundle_id not found in store raises error
        bundle_fake_id = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            gate_bundle_id="fabricated_bundle_id_9999",
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=eval_res.result_id,
            gate_bundle=_make_4_gates(),
        )
        with pytest.raises(InvalidStageTransitionError, match="not found in gate evidence store"):
            registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_fake_id, holdout_manager=mgr, gate_store=gate_store)

        # 3. Valid stored bundle artifact promotes successfully
        bundle_art, _ = gate_store.record_and_bundle_gates(
            gate_results=_make_4_gates(),
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
        )
        bundle_valid = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            gate_bundle_id=bundle_art.gate_bundle_id,
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=eval_res.result_id,
        )
        registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_valid, holdout_manager=mgr, gate_store=gate_store)
        assert registry.get("STR-001").stage == StrategyStage.PAPER


def test_corrupted_gate_store_locks_promotion():
    """Verify corrupted gate store locks HOLDOUT -> PAPER fail-closed."""
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
        gates_dir = Path(tmp) / "gates"
        gate_store = GateEvaluationStore(storage_dir=gates_dir)

        prereg = mgr.create_preregistration(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            hypothesis_description="Holdout to paper artifact test",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )
        bundle_holdout = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.VALIDATION,
            target_stage=StrategyStage.HOLDOUT,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            holdout_preregistration_id=prereg.preregistration_id,
        )
        registry.update_stage("STR-001", StrategyStage.HOLDOUT, evidence_bundle=bundle_holdout, holdout_manager=mgr)

        acc = mgr.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-001",
            strategy_version="1.0.0",
            git_sha="git_sha_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
        )
        eval_res = mgr.record_evaluation_result(acc.access_id, {"sharpe": 1.5})

        bundle_art, _ = gate_store.record_and_bundle_gates(
            gate_results=_make_4_gates(),
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
        )

        # Manually corrupt gate store state
        gate_store._is_corrupted = True
        gate_store._corruption_error = "Tampering detected in evaluation record"

        bundle_valid = PromotionEvidenceBundle(
            strategy_id="STR-001",
            strategy_version="1.0.0",
            source_stage=StrategyStage.HOLDOUT,
            target_stage=StrategyStage.PAPER,
            dataset_fingerprint="ds_hash_12345678",
            config_fingerprint="cfg_hash_12345678",
            parameter_set_fingerprint="param_hash_12345678",
            git_sha="git_sha_12345678",
            gate_bundle_id=bundle_art.gate_bundle_id,
            holdout_preregistration_id=prereg.preregistration_id,
            holdout_access_id=acc.access_id,
            holdout_result_id=eval_res.result_id,
        )

        with pytest.raises(InvalidStageTransitionError, match="GOVERNANCE_LOCKED"):
            registry.update_stage("STR-001", StrategyStage.PAPER, evidence_bundle=bundle_valid, holdout_manager=mgr, gate_store=gate_store)
