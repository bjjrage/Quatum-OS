"""Final pre-paper red-team regression: recorder restart after a long outage."""
import time

from src.quality.acceptance import (
    RESUME_MAX_HEARTBEAT_AGE_SECONDS,
    AcceptanceContinuityState,
    RuntimeManifest,
)


def _seed(path, age_s):
    m = RuntimeManifest.create_new(pid=1, git_sha="x", config_fingerprint="fp")
    m.last_heartbeat_timestamp_ns = time.time_ns() - int(age_s * 1e9)
    m.save(path)
    return m


def test_resume_after_long_outage_starts_new_identifiable_run(tmp_path):
    p = tmp_path / "current_run.json"
    old = _seed(p, RESUME_MAX_HEARTBEAT_AGE_SECONDS + 3600)
    new, resumed = RuntimeManifest.resume_or_create(p, pid=2, git_sha="x", config_fingerprint="fp")
    assert resumed is False
    assert new.run_id != old.run_id
    assert new.previous_run_id == old.run_id
    assert new.continuity_state == AcceptanceContinuityState.NEW_RUN
    assert "CONTINUITY_GAP" in new.continuity_reason
    assert new.elapsed_seconds() < 60  # outage is not counted as elapsed run time


def test_resume_after_short_restart_keeps_run(tmp_path):
    p = tmp_path / "current_run.json"
    old = _seed(p, 5)
    new, resumed = RuntimeManifest.resume_or_create(p, pid=2, git_sha="x", config_fingerprint="fp")
    assert resumed is True and new.run_id == old.run_id
    assert new.continuity_state == AcceptanceContinuityState.VALID
