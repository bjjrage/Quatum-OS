"""Idempotency checks for replayed observations and paper signals."""

from src.paper.pump_wallet_skill_v1 import EVAL_HORIZON_S, WalletSkillBook, WalletSkillPaper


def test_replayed_event_after_restart_does_not_create_a_second_observation(tmp_path):
    first = WalletSkillPaper(root=tmp_path)
    first.skill.on_trade("W", "M", True, 1.0, 100.0)
    first.save(101.0)

    restarted = WalletSkillPaper(root=tmp_path)
    restarted.skill.on_trade("W", "M", True, 1.0, 100.0)
    restarted.skill.mature(100.0 + EVAL_HORIZON_S)
    restarted.skill.on_trade("W", "M", True, 1.0, 100.0)

    assert restarted.skill.snapshot("W")["matured"] == 1
    assert ("W", "M") not in restarted.skill.pending


def test_same_pending_event_is_idempotent_within_one_process():
    book = WalletSkillBook()
    book.on_trade("W", "M", True, 1.0, 100.0)
    book.on_trade("W", "M", True, 1.0, 100.0)
    assert len(book.pending) == 1
