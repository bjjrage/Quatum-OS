import json
import time
from pathlib import Path
import pytest
from src.quality.acceptance import RuntimeManifest, AcceptanceState


def test_resume_identical_config_preserves_run_and_timestamps(tmp_path: Path):
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
    assert resumed_manifest.last_heartbeat_timestamp_ns >= initial_manifest.last_heartbeat_timestamp_ns


def test_different_config_creates_new_run(tmp_path: Path):
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


def test_corrupt_manifest_fails_safely_starts_fresh(tmp_path: Path):
    manifest_file = tmp_path / "current_run.json"
    manifest_file.write_text("{corrupt json", encoding="utf-8")
    
    new_manifest, resumed = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=3003,
        git_sha="sha_test",
        config_fingerprint="fingerprint_abc",
    )
    
    assert resumed is False
    assert new_manifest.pid == 3003
    assert new_manifest.status == AcceptanceState.RUNNING


def test_missing_manifest_creates_new(tmp_path: Path):
    manifest_file = tmp_path / "non_existent_run.json"
    manifest, resumed = RuntimeManifest.resume_or_create(
        filepath=manifest_file,
        pid=4004,
        git_sha="sha_test",
        config_fingerprint="fingerprint_abc",
    )
    assert resumed is False
    assert manifest.pid == 4004
