"""Tests for durable experiment registry persistence, parameter fingerprints, and holdout sealing."""

from pathlib import Path
import pytest
from src.research import (
    ExperimentRecord,
    ExperimentRegistry,
    RegistryIntegrityStatus,
    ExperimentRegistryIntegrityError,
    ResearchParameterSet,
    ParameterSetStatus,
    compute_parameter_fingerprint,
    SealedHoldoutManager,
    HoldoutAuditRecord,
    HoldoutViolationError,
    HoldoutAuditIntegrityError,
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

    # 1. First evaluation of STR-002 v2.0.0 on holdout via canonical governance pipeline
    prereg = manager.create_preregistration(
        strategy_id="STR-002",
        strategy_version="2.0.0",
        git_sha="git_sha_abc123456",
        dataset_fingerprint="dataset_hash_part1_12345678",
        config_fingerprint="config_hash_v1_12345678",
        parameter_set_fingerprint="fp_params_v1_12345678",
        hypothesis_description="Post-liquidation altcoin bounce when BTC is flat/up",
        falsification_criteria=["Sharpe < 1.0"],
        primary_metrics=["sharpe", "max_drawdown"],
        analysis_plan_fingerprint="plan_hash_12345678",
    )
    acc = manager.open_holdout(
        preregistration_id=prereg.preregistration_id,
        strategy_id="STR-002",
        strategy_version="2.0.0",
        git_sha="git_sha_abc123456",
        config_fingerprint="config_hash_v1_12345678",
        parameter_set_fingerprint="fp_params_v1_12345678",
    )
    eval_res = manager.record_evaluation_result(
        access_id=acc.access_id,
        result_metrics={"net_sharpe": 1.85, "max_drawdown": -0.042},
        passed=True,
    )
    assert eval_res.strategy_version == "2.0.0"
    assert eval_res.result_id.startswith("eval_STR-002_2.0.0_")

    # 2. Re-evaluating the SAME strategy version or reopening must raise HoldoutViolationError
    with pytest.raises(HoldoutViolationError):
        manager.open_holdout(
            preregistration_id=prereg.preregistration_id,
            strategy_id="STR-002",
            strategy_version="2.0.0",
            git_sha="git_sha_abc123456",
            config_fingerprint="config_hash_v1_12345678",
            parameter_set_fingerprint="fp_params_v1_12345678",
        )

    # 3. Evaluating a bumped strategy version on the SAME holdout dataset is forbidden (dataset reuse)
    with pytest.raises(HoldoutViolationError, match="Holdout dataset reuse across iterations is forbidden"):
        manager.create_preregistration(
            strategy_id="STR-002",
            strategy_version="2.1.0",
            git_sha="git_sha_def456789",
            dataset_fingerprint="dataset_hash_part1_12345678",
            config_fingerprint="config_hash_v2_12345678",
            parameter_set_fingerprint="fp_params_v2_tweaked",
            hypothesis_description="Version bump with orthogonalized factor model",
            falsification_criteria=["Sharpe < 1.0"],
            primary_metrics=["sharpe", "max_drawdown"],
            analysis_plan_fingerprint="plan_hash_12345678",
        )

    # 4. Evaluating on a fresh holdout partition succeeds
    prereg_fresh = manager.create_preregistration(
        strategy_id="STR-002",
        strategy_version="2.1.0",
        git_sha="git_sha_def456789",
        dataset_fingerprint="dataset_hash_part2_fresh_12345678",
        config_fingerprint="config_hash_v2_12345678",
        parameter_set_fingerprint="fp_params_v2_tweaked",
        hypothesis_description="Version bump with orthogonalized factor model on fresh partition",
        falsification_criteria=["Sharpe < 1.0"],
        primary_metrics=["sharpe", "max_drawdown"],
        analysis_plan_fingerprint="plan_hash_12345678",
    )
    acc_fresh = manager.open_holdout(
        preregistration_id=prereg_fresh.preregistration_id,
        strategy_id="STR-002",
        strategy_version="2.1.0",
        git_sha="git_sha_def456789",
        config_fingerprint="config_hash_v2_12345678",
        parameter_set_fingerprint="fp_params_v2_tweaked",
    )
    eval_fresh = manager.record_evaluation_result(
        access_id=acc_fresh.access_id,
        result_metrics={"net_sharpe": 1.92},
        passed=True,
    )
    assert eval_fresh.strategy_version == "2.1.0"
    assert len(manager.list_audits_for_strategy("STR-002")) == 2

    # 5. Legacy evaluate_holdout is disabled
    with pytest.raises(HoldoutViolationError, match="LEGACY_HOLDOUT_EVALUATION_DISABLED"):
        manager.evaluate_holdout(
            strategy_id="STR-002",
            strategy_version="2.2.0",
            git_sha="git_sha_def456789",
            parameter_set_fingerprint="fp_params_v3",
            hypothesis_description="Legacy call attempt",
            holdout_dataset_bytes_or_hash="dataset_raw_bytes",
            metrics={"net_sharpe": 1.92},
        )


def test_experiment_registry_corruption_fails_closed(tmp_path: Path):
    """
    CRITICAL REQUIREMENT (v1.4.2 Section 7):
    If ANY experiment file is corrupted, the registry must:
    - Set status to CORRUPTED / MANUAL_REPAIR_REQUIRED
    - Raise ExperimentRegistryIntegrityError
    - Refuse to return trial counts or record new experiments
    - Preserve the corrupted file for forensics
    """
    exp_dir = tmp_path / "experiments"
    exp_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write one valid record
    rec_valid = ExperimentRecord(
        experiment_id="exp_valid",
        strategy_id="STR-002",
        strategy_version="2.0.0",
        parameters={"lookback": 20},
    )
    with open(exp_dir / "exp_valid.json", "w", encoding="utf-8") as f:
        f.write(rec_valid.model_dump_json(indent=2))

    # 2. Write one corrupted record
    corrupt_file = exp_dir / "exp_corrupt.json"
    corrupt_file.write_text("{\"corrupted_json\": [unclosed", encoding="utf-8")

    # 3. Initializing registry must fail closed and raise ExperimentRegistryIntegrityError
    with pytest.raises(ExperimentRegistryIntegrityError, match="corruption detected"):
        ExperimentRegistry(storage_dir=exp_dir)

    # 4. Verify corrupted file was NOT deleted or overwritten
    assert corrupt_file.exists()
    assert corrupt_file.read_text(encoding="utf-8") == "{\"corrupted_json\": [unclosed"

    # 5. Quarantine log file was created
    quarantine_file = exp_dir / "quarantine_integrity_log.json"
    assert quarantine_file.exists()

    # 6. Verify an instance marked corrupted refuses operations
    reg = ExperimentRegistry.__new__(ExperimentRegistry)
    reg.storage_dir = exp_dir
    reg._experiments = {}
    reg._strategy_trial_counts = {}
    reg.status = RegistryIntegrityStatus.CORRUPTED
    reg.quarantine_log = []

    with pytest.raises(ExperimentRegistryIntegrityError, match="Cannot return trial count"):
        reg.get_trial_count("STR-002")

    with pytest.raises(ExperimentRegistryIntegrityError, match="Cannot record experiment"):
        reg.record_experiment(rec_valid)


def test_sealed_holdout_audit_corruption_fails_closed(tmp_path: Path):
    """
    CRITICAL REQUIREMENT (v1.4.2 Section 8):
    If holdout audit file is corrupted, SealedHoldoutManager must:
    - NOT initialize to an empty list
    - Set status to corrupted and raise HoldoutAuditIntegrityError
    - Lock holdout dataset against evaluations
    - Preserve corrupted audit log for forensic inspection
    """
    audit_file = tmp_path / "holdout_audits.json"
    manager_init = SealedHoldoutManager(audit_storage_path=audit_file)

    # Record valid evaluation
    prereg = manager_init.create_preregistration(
        strategy_id="STR-002",
        strategy_version="2.0.0",
        git_sha="sha_valid_12345678",
        dataset_fingerprint="dataset_bytes_hash_12345678",
        config_fingerprint="cfg_hash_12345678",
        parameter_set_fingerprint="fp_valid_12345678",
        hypothesis_description="Initial evaluation",
        falsification_criteria=["Sharpe < 1.0"],
        primary_metrics=["sharpe", "max_drawdown"],
        analysis_plan_fingerprint="plan_hash_12345678",
    )
    acc = manager_init.open_holdout(
        preregistration_id=prereg.preregistration_id,
        strategy_id="STR-002",
        strategy_version="2.0.0",
        git_sha="sha_valid_12345678",
        config_fingerprint="cfg_hash_12345678",
        parameter_set_fingerprint="fp_valid_12345678",
    )
    manager_init.record_evaluation_result(
        access_id=acc.access_id,
        result_metrics={"net_sharpe": 1.5},
        passed=True,
    )
    assert audit_file.exists()

    # Corrupt the audit file with invalid JSON garbage
    corrupted_content = "CORRUPTED_NON_JSON_BYTES_X00XFF"
    audit_file.write_text(corrupted_content, encoding="utf-8")

    # Reopening manager must fail closed
    with pytest.raises(HoldoutAuditIntegrityError, match="corrupted"):
        SealedHoldoutManager(audit_storage_path=audit_file)

    # Calling evaluate_holdout on compromised manager must fail closed
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
            hypothesis_description="Attempted bypass",
            holdout_dataset_bytes_or_hash="dataset_bytes",
            metrics={"net_sharpe": 3.0},
        )

    # Corrupted file was preserved
    assert audit_file.read_text(encoding="utf-8") == corrupted_content

