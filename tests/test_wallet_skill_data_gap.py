"""Certification contract for known gaps during a wallet's 2h observation."""

from src.paper.pump_wallet_skill_v1 import WalletSkillBook


def test_known_gap_excludes_observation_from_wins_losses_and_denominator():
    book = WalletSkillBook()
    register_gap = getattr(book, "register_data_gap", None)
    assert callable(register_gap), (
        "WalletSkillBook has no persisted known-gap input; it cannot classify an "
        "observation as UNOBSERVABLE_DATA_GAP."
    )

    book.on_trade("W", "M", True, 1.0, 100.0)
    register_gap("M", 100.0 + 300.0, 100.0 + 600.0)
    book.on_trade("X", "M", True, 2.5, 200.0)
    book.mature(100.0 + 7200.0)

    row = book.snapshot("W")
    assert row["matured"] == 0
    assert row["wins_2x"] == 0
    assert row["losses"] == 0
    assert row["unobservable_gap"] == 1
