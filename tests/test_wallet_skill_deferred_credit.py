"""Certification tests for the frozen WALLET_SKILL_V1 observation rules."""

from src.paper.pump_wallet_skill_v1 import (
    EVAL_HORIZON_S,
    GOOD_MIN_HIT_RATE,
    GOOD_MIN_MATURED,
    WalletSkillBook,
)


def test_good_wallet_thresholds_and_pending_do_not_count():
    book = WalletSkillBook()
    book.stats["four-perfect"] = {"matured": 4, "wins": 4}
    book.stats["five-two-wins"] = {"matured": 5, "wins": 2}
    book.stats["five-one-win"] = {"matured": 5, "wins": 1}
    book.on_trade("pending", "unmatured-token", True, 1.0, 100.0)

    assert GOOD_MIN_MATURED == 5
    assert GOOD_MIN_HIT_RATE == 0.35
    assert not book.is_good("four-perfect")
    assert book.is_good("five-two-wins")  # 2/5 = 40%
    assert not book.is_good("five-one-win")
    assert book.snapshot("pending")["matured"] == 0
    assert not book.is_good("pending")


def test_winner_and_loser_are_credited_symmetrically_at_two_hours():
    book = WalletSkillBook()
    t0 = 10_000.0
    book.on_trade("winner", "WIN", True, 1.0, t0)
    book.on_trade("other", "WIN", True, 2.1, t0 + 1)
    book.on_trade("loser", "LOSS", True, 1.0, t0)

    assert book.snapshot("winner")["matured"] == 0
    assert book.snapshot("loser")["matured"] == 0
    assert book.mature(t0 + EVAL_HORIZON_S - 1) == 0
    assert book.snapshot("winner")["matured"] == 0
    assert book.snapshot("loser")["matured"] == 0

    assert book.mature(t0 + EVAL_HORIZON_S) == 2
    assert book.snapshot("winner")["matured"] == 1
    assert book.snapshot("winner")["wins_2x"] == 1
    assert book.snapshot("loser")["matured"] == 1
    assert book.snapshot("loser")["wins_2x"] == 0


def test_current_observation_cannot_make_wallet_good_before_maturity():
    book = WalletSkillBook()
    book.stats["W"] = {"matured": 4, "wins": 4}
    book.on_trade("W", "CURRENT", True, 1.0, 100.0)
    book.on_trade("other", "CURRENT", True, 3.0, 101.0)

    assert not book.is_good("W")
    assert book.snapshot("W")["matured"] == 4
    book.mature(100.0 + EVAL_HORIZON_S)
    assert book.is_good("W")
