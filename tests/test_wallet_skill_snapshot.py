"""Restart and incremental-startup certification; persistence must be lossless."""

import inspect

from src.collectors.pumpfun_recorder import PumpfunRecorder
from src.paper.pump_wallet_skill_v1 import WalletSkillPaper


def test_save_and_new_process_restore_canonical_wallet_state(tmp_path):
    first = WalletSkillPaper(root=tmp_path)
    first.skill.on_trade("W", "M", True, 1.0, 100.0)
    first.buyers["M"] = ["W"]
    first.buyer_sets["M"] = {"W"}
    first.signaled.add("M")
    first.save(101.0)

    second = WalletSkillPaper(root=tmp_path)
    assert second.skill.pending == first.skill.pending
    assert second.buyers == first.buyers
    assert second.signaled == first.signaled


def test_corrupt_or_incompatible_snapshot_is_explicitly_rejected(tmp_path):
    paper = WalletSkillPaper(root=tmp_path)
    loader = getattr(paper, "load_bootstrap_snapshot", None)
    assert callable(loader), "There is no bootstrap snapshot loader or invalidation path."
    path = tmp_path / "pump_wallet_skill_v1" / "bootstrap_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{truncated", encoding="utf-8")
    try:
        loader(path)
    except Exception as exc:
        assert "SNAPSHOT_INVALID" in str(exc)
    else:
        raise AssertionError("Corrupt snapshot was accepted silently.")


def test_normal_paper_startup_does_not_replay_full_history():
    source = inspect.getsource(PumpfunRecorder._start_paper)
    assert "paper.warmup" not in source, "Every startup still calls the full historical warmup."
    assert "load_bootstrap_snapshot" in source or "load_checkpoint" in source


def test_recorder_buffers_live_events_while_historical_bootstrap_runs():
    source = inspect.getsource(PumpfunRecorder)
    start = inspect.getsource(PumpfunRecorder._start_paper)
    assert "buffer" in source.lower() or "pending_events" in source.lower(), (
        "Recorder has no live event buffer to bridge the bootstrap cutoff."
    )
    # The paper must be visible (live events buffered) before the history catch-up runs. The catch-up entry
    # point is `paper.bootstrap` because the startup must not call `paper.warmup` (see the test above).
    assert -1 < start.find("self.paper = paper") < start.find("paper.bootstrap"), (
        "Paper becomes visible only after warmup, leaving trades unconsumed during bootstrap."
    )
