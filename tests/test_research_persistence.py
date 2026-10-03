"""Tests for durable experiment registry persistence, parameter fingerprints, and holdout sealing."""

from pathlib import Path
import pytest
from src.research import (
    ExperimentRecord,
    ExperimentRegistry,
    ResearchParameterSet,
    ParameterSetStatus,
    compute_parameter_fingerprint,
    SealedHoldoutManager,
    HoldoutAuditRecord,
    HoldoutViolationError,
)


def test_research_parameter_set_fingerprint_and_immutability():
    """Verify that changing any parameter alters the fingerprint and default status is PROVISIONAL."""
    params_a = {"lookback_candles": 20, "z_threshold": -3.0}
    pset_a = ResearchParameterSet(
        parameter_set_id="param_001",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        parameters=params_a,
    )
    assert pset_a.status == ParameterSetStatus.PROVISIONAL
    assert len(pset_a.config_fingerprint) == 64

    # Parameter change must produce a distinct fingerprint
    params_b = {"lookback_candles": 30, "z_threshold": -3.0}
    pset_b = ResearchParameterSet(
        parameter_set_id="param_002",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        parameters=params_b,
    )
    assert pset_b.config_fingerprint != pset_a.config_fingerprint

    # Tampering with fingerprint causes validation error
    with pytest.raises(ValueError, match="Config fingerprint mismatch"):
        ResearchParameterSet(
            parameter_set_id="param_003",
            strategy_id="STR-002",
            strategy_version="2.0.0",
            parameters=params_a,
            config_fingerprint="tampered_fake_fingerprint",
        )


def test_experiment_registry_durable_persistence_and_trial_count_recovery(tmp_path: Path):
    """Verify that experiments persist to disk and trial_count survives registry restarts."""
    exp_dir = tmp_path / "experiments"
    registry_1 = ExperimentRegistry(storage_dir=exp_dir)

    rec_1 = ExperimentRecord(
        experiment_id="exp_001",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        parameters={"lookback": 20},
        gate_result="FAIL",
        falsification_evidence="Net expectancy below round-trip fee hurdle",
        reasons=["SHARPE_INSUFFICIENT"],
    )
    count_1 = registry_1.record_experiment(rec_1)
    assert count_1 == 1
    assert registry_1.get_trial_count("STR-002") == 1

    rec_2 = ExperimentRecord(
        experiment_id="exp_002",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        parameters={"lookback": 30},
        gate_result="PASS",
    )
    count_2 = registry_1.record_experiment(rec_2)
    assert count_2 == 2
    assert registry_1.get_trial_count("STR-002") == 2

    # Simulate process shutdown and restart on same directory
    registry_2 = ExperimentRegistry(storage_dir=exp_dir)
    assert registry_2.get_trial_count("STR-002") == 2
    loaded_rec_1 = registry_2.get_experiment("exp_001")
    assert loaded_rec_1 is not None
    assert loaded_rec_1.falsification_evidence == "Net expectancy below round-trip fee hurdle"
    assert loaded_rec_1.reasons == ["SHARPE_INSUFFICIENT"]

    # Overwrite must fail
    with pytest.raises(ValueError, match="already exists. Modification is forbidden"):
        registry_2.record_experiment(rec_1)

    # Deletion must fail
    with pytest.raises(RuntimeError, match="Governance Invariant Violated"):
        registry_2.delete_experiment("exp_001")


def test_sealed_holdout_manager_prevents_retuning_and_logs_audit(tmp_path: Path):
    """Verify holdout dataset is sealed and produces immutable audit records."""
    audit_file = tmp_path / "holdout_audits.json"
    manager = SealedHoldoutManager(audit_storage_path=audit_file)

    # 1. First evaluation of STR-002 v2.0.0 on holdout
    record = manager.evaluate_holdout(
        strategy_id="STR-002",
        strategy_version="2.0.0",
        git_sha="git_sha_abc123",
        parameter_set_fingerprint="fp_params_v1",
        hypothesis_description="Post-liquidation altcoin bounce when BTC is flat/up",
        holdout_dataset_bytes_or_hash="dataset_raw_bytes_or_hash_content",
        metrics={"net_sharpe": 1.85, "max_drawdown": -0.042},
    )
    assert record.strategy_version == "2.0.0"
    assert record.audit_id.startswith("holdout_STR-002_2.0.0_")

    # 2. Re-evaluating the SAME strategy version must raise HoldoutViolationError
    with pytest.raises(HoldoutViolationError, match="Holdout dataset is sealed"):
        manager.evaluate_holdout(
            strategy_id="STR-002",
            strategy_version="2.0.0",
            git_sha="git_sha_def456",
            parameter_set_fingerprint="fp_params_v2_tweaked",
            hypothesis_description="Tweaked parameters to improve performance",
            holdout_dataset_bytes_or_hash="dataset_raw_bytes_or_hash_content",
            metrics={"net_sharpe": 2.10},
        )

    # 3. Evaluating a properly BUMPED strategy version succeeds
    record_bumped = manager.evaluate_holdout(
        strategy_id="STR-002",
        strategy_version="2.1.0",
        git_sha="git_sha_def456",
        parameter_set_fingerprint="fp_params_v2_tweaked",
        hypothesis_description="Version bump with orthogonalized factor model",
        holdout_dataset_bytes_or_hash="dataset_raw_bytes_or_hash_content",
        metrics={"net_sharpe": 1.92},
    )
    assert record_bumped.strategy_version == "2.1.0"
    assert len(manager.list_audits_for_strategy("STR-002")) == 2
