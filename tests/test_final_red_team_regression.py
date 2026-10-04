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


def test_operator_new_run_explicit_flag_creates_new_run_and_archives_old(tmp_path):
    import json
    p = tmp_path / "current_run.json"
    hist = tmp_path / "history"
    # Even if heartbeat is completely fresh (would have resumed under normal restart)
    old = _seed(p, 2)
    new = RuntimeManifest.start_operator_new_run(
        filepath=p,
        pid=2,
        git_sha="y",
        config_fingerprint="fp",
        history_dir=hist,
    )
    assert new.run_id != old.run_id
    assert new.previous_run_id == old.run_id
    assert new.continuity_state == AcceptanceContinuityState.NEW_RUN
    assert new.continuity_reason == "OPERATOR_CONFIRMED_CONTINUITY_GAP"

    # Verify old manifest was immutably archived into history
    archived_file = hist / f"{old.run_id}.json"
    assert archived_file.exists()
    with open(archived_file, "r", encoding="utf-8") as f:
        archived_data = json.load(f)
    assert archived_data["run_id"] == old.run_id
    assert archived_data["git_sha"] == "x"


def test_operator_new_run_idempotent_archive_identical(tmp_path):
    p = tmp_path / "current_run.json"
    hist = tmp_path / "history"
    old = _seed(p, 2)
    hist.mkdir(parents=True, exist_ok=True)
    archived_file = hist / f"{old.run_id}.json"
    # Pre-populate archive with identical content
    with open(archived_file, "w", encoding="utf-8") as f:
        f.write(old.model_dump_json(indent=2))

    new = RuntimeManifest.start_operator_new_run(
        filepath=p,
        pid=3,
        git_sha="z",
        config_fingerprint="fp",
        history_dir=hist,
    )
    assert new.run_id != old.run_id
    assert new.previous_run_id == old.run_id


def test_operator_new_run_archive_collision_different_content_raises(tmp_path):
    import pytest
    from src.quality.acceptance import RecorderContinuityError
    p = tmp_path / "current_run.json"
    hist = tmp_path / "history"
    old = _seed(p, 2)
    hist.mkdir(parents=True, exist_ok=True)
    archived_file = hist / f"{old.run_id}.json"
    # Pre-populate archive with conflicting content
    conflicting = RuntimeManifest.create_new(pid=999, git_sha="diff", config_fingerprint="diff_fp")
    conflicting.run_id = old.run_id  # same run_id but different contents
    with open(archived_file, "w", encoding="utf-8") as f:
        f.write(conflicting.model_dump_json(indent=2))

    with pytest.raises(RecorderContinuityError, match="Archive collision"):
        RuntimeManifest.start_operator_new_run(
            filepath=p,
            pid=3,
            git_sha="z",
            config_fingerprint="fp",
            history_dir=hist,
        )


def test_operator_new_run_without_existing_manifest(tmp_path):
    p = tmp_path / "does_not_exist.json"
    hist = tmp_path / "history"
    new = RuntimeManifest.start_operator_new_run(
        filepath=p,
        pid=10,
        git_sha="initial",
        config_fingerprint="fp",
        history_dir=hist,
    )
    assert new.previous_run_id is None
    assert new.continuity_state == AcceptanceContinuityState.NEW_RUN
    assert new.continuity_reason == "FRESH_INITIALIZATION"
    assert p.exists()


def test_operator_new_run_corrupted_manifest_fails_closed(tmp_path):
    import pytest
    from src.quality.acceptance import RecorderContinuityError
    p = tmp_path / "corrupted.json"
    p.write_text("NOT_VALID_JSON", encoding="utf-8")
    hist = tmp_path / "history"

    with pytest.raises(RecorderContinuityError, match="corrupted"):
        RuntimeManifest.start_operator_new_run(
            filepath=p,
            pid=10,
            git_sha="initial",
            config_fingerprint="fp",
            history_dir=hist,
        )

