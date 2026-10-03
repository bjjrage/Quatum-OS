import json
import time
from pathlib import Path
import pytest
from src.quality.acceptance import (
    RuntimeManifest,
    AcceptanceState,
    AcceptanceContinuityState,
    RecorderContinuityError,
)


def test_missing_manifest_creates_new(tmp_path: Path):
    """CASE A: Missing manifest starts fresh new run."""
    manifest_file = tmp_path / "non_existent_run.json"
    manifest, resumed = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=4004,
        git_sha="sha_test",
        config_fingerprint="fingerprint_abc",
    )
    assert resumed is False
    assert manifest.pid == 4004
    assert manifest.continuity_state == AcceptanceContinuityState.NEW_RUN
    assert manifest.continuity_reason == "FRESH_INITIALIZATION"


def test_resume_identical_config_preserves_run_and_timestamps(tmp_path: Path):
    """CASE B: Identical config fingerprint preserves run_id and start timestamps."""
    manifest_file = tmp_path / "current_run.json"
    initial_manifest, resumed = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=1001,
        git_sha="sha_initial_123",
        config_fingerprint="fingerprint_abc",
        venues=["deribit", "binance", "polymarket"],
    )
    assert not resumed
    initial_manifest.save(manifest_file)
    
    initial_run_id = initial_manifest.run_id
    initial_started_at = initial_manifest.started_at_utc
    initial_started_ns = initial_manifest.started_at_timestamp_ns
    
    time.sleep(0.01)
    
    # Simulate restart with same fingerprint but new PID and new git commit
    resumed_manifest, resumed = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=2002,
        git_sha="sha_new_456",
        config_fingerprint="fingerprint_abc",
    )
    
    assert resumed is True
    assert resumed_manifest.run_id == initial_run_id
    assert resumed_manifest.started_at_utc == initial_started_at
    assert resumed_manifest.started_at_timestamp_ns == initial_started_ns
    assert resumed_manifest.pid == 2002
    assert resumed_manifest.git_sha == "sha_new_456"
    assert resumed_manifest.status == AcceptanceState.RUNNING
    assert resumed_manifest.continuity_state == AcceptanceContinuityState.VALID
    assert resumed_manifest.last_heartbeat_timestamp_ns >= initial_manifest.last_heartbeat_timestamp_ns


def test_different_config_creates_new_run(tmp_path: Path):
    """CASE C: Different config fingerprint creates explicit new run with CONFIG_CHANGED."""
    manifest_file = tmp_path / "current_run.json"
    initial_manifest, _ = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=1001,
        git_sha="sha_initial_123",
        config_fingerprint="fingerprint_original",
    )
    initial_manifest.save(manifest_file)
    
    # Restart with different config fingerprint
    new_manifest, resumed = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=2002,
        git_sha="sha_initial_123",
        config_fingerprint="fingerprint_different",
    )
    
    assert resumed is False
    assert new_manifest.run_id != initial_manifest.run_id
    assert new_manifest.config_fingerprint == "fingerprint_different"
    assert new_manifest.continuity_state == AcceptanceContinuityState.CONFIG_CHANGED
    assert "CONFIG_FINGERPRINT_CHANGED" in new_manifest.continuity_reason
    assert new_manifest.previous_run_id == initial_manifest.run_id


def test_corrupt_manifest_fails_closed_raises_error(tmp_path: Path):
    """CASE D: Corrupted JSON manifest must raise RecorderContinuityError, NEVER reset clock silently."""
    manifest_file = tmp_path / "current_run.json"
    manifest_file.write_text("{corrupt json syntax", encoding="utf-8")
    
    with pytest.raises(RecorderContinuityError, match="failed integrity parsing"):
        RuntimeManifest.resume_or_create(
            filepath=manifest_file,
            pid=3003,
            git_sha="sha_test",
            config_fingerprint="fingerprint_abc",
            fail_closed=True,
        )


def test_partial_json_fails_closed_raises_error(tmp_path: Path):
    """CASE D: Partial truncated JSON raises RecorderContinuityError."""
    manifest_file = tmp_path / "current_run.json"
    manifest_file.write_text('{"run_id": "run_incomplete"', encoding="utf-8")
    
    with pytest.raises(RecorderContinuityError):
        RuntimeManifest.resume_or_create(
            filepath=manifest_file,
            pid=3003,
            git_sha="sha_test",
            config_fingerprint="fingerprint_abc",
        )


def test_invalid_pydantic_schema_fails_closed_raises_error(tmp_path: Path):
    """CASE D: Valid JSON but missing mandatory schema fields raises RecorderContinuityError."""
    manifest_file = tmp_path / "current_run.json"
    # Missing started_at_timestamp_ns, pid, etc.
    manifest_file.write_text(json.dumps({"run_id": "r1", "random_field": "val"}), encoding="utf-8")
    
    with pytest.raises(RecorderContinuityError):
        RuntimeManifest.resume_or_create(
            filepath=manifest_file,
            pid=3003,
            git_sha="sha_test",
            config_fingerprint="fingerprint_abc",
        )


def test_corrupted_manifest_non_raising_mode_returns_broken(tmp_path: Path):
    """Non-raising inspection mode returns AcceptanceContinuityState.BROKEN and preserves evidence."""
    manifest_file = tmp_path / "current_run.json"
    manifest_file.write_text("{garbled data}", encoding="utf-8")
    
    manifest, resumed = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=5005,
        git_sha="sha_test",
        config_fingerprint="fp1",
        fail_closed=False,
    )
    assert resumed is False
    assert manifest.continuity_state == AcceptanceContinuityState.BROKEN
    assert "RecorderContinuityError" in manifest.continuity_reason
    assert manifest.recovery_evidence == "{garbled data}"
