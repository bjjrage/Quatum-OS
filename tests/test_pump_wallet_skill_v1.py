import random

from src.paper.pump_paper import FEE
from src.paper.pump_wallet_skill_v1 import (
    ENTRY_SOL,
    FIRST_BUYERS,
    GOOD_MIN_HIT_RATE,
    GOOD_MIN_MATURED,
    INITIAL_CAPITAL_SOL,
    MAX_OPEN,
    EVAL_HORIZON_S,
    FixedPumpAccount,
    WalletSkillBook,
    WalletSkillPaper,
)

VS0, VT0 = 30 * 10**9, 1_073_000_000 * 10**6


def _ev(mint, user, buy, slot, vs=VS0, vt=VT0):
    return {
        "mint": mint,
        "user": user,
        "is_buy": buy,
        "sol_amount": 500_000_000,
        "token_amount": 10**12,
        "slot": slot,
        "virtual_sol_reserves": vs,
        "virtual_token_reserves": vt,
    }


def test_wallet_skill_rules_are_frozen():
    assert GOOD_MIN_MATURED == 5
    assert GOOD_MIN_HIT_RATE == 0.35
    assert EVAL_HORIZON_S == 7200
    assert FIRST_BUYERS == 10
    assert INITIAL_CAPITAL_SOL == 20.0
    assert ENTRY_SOL == 0.5
    assert MAX_OPEN == 30
    assert FEE == 0.0125


def test_deferred_credit_never_credits_winner_or_failure_early():
    b = WalletSkillBook()
    b.on_trade("W", "M1", True, 1.0, 100.0)
    b.on_trade("X", "M1", True, 2.1, 200.0)  # M1 already reached >2x
    assert b.snapshot("W")["matured"] == 0
    b.mature(100.0 + EVAL_HORIZON_S - 1)
    assert b.snapshot("W")["matured"] == 0
    b.mature(100.0 + EVAL_HORIZON_S)
    assert b.snapshot("W")["matured"] == 1
    assert b.snapshot("W")["wins_2x"] == 1

    b.on_trade("W", "M2", True, 1.0, 10_000.0)
    b.mature(10_000.0 + EVAL_HORIZON_S - 1)
    assert b.snapshot("W")["matured"] == 1
    b.mature(10_000.0 + EVAL_HORIZON_S)
    assert b.snapshot("W")["matured"] == 2
    assert b.snapshot("W")["wins_2x"] == 1


def test_current_token_cannot_make_wallet_good():
    b = WalletSkillBook()
    b.stats["W"] = {"matured": 4, "wins": 4}
    b.on_trade("W", "CURRENT", True, 1.0, 100.0)
    b.on_trade("X", "CURRENT", True, 3.0, 101.0)
    assert not b.is_good("W")
    b.mature(100.0 + EVAL_HORIZON_S)
    assert b.is_good("W")


def test_signal_fires_at_buyer_10_and_entry_is_next_trade(tmp_path):
    p = WalletSkillPaper(root=tmp_path, rnd=random.Random(0))
    p.skill.stats["GOOD_A"] = {"matured": 5, "wins": 2}
    p.skill.stats["GOOD_B"] = {"matured": 5, "wins": 2}
    buyers = ["GOOD_A", "u2", "u3", "GOOD_B", "u5", "u6", "u7", "u8", "u9", "u10"]
    now = 1_000_000.0
    p.on_create({"mint": "M", "user": "DEV", "creator": "DEV", "symbol": "M"}, now)
    for i, user in enumerate(buyers[:9]):
        p.on_trade(_ev("M", user, True, i + 1), now + i + 1)
    assert "M" not in p.signaled
    p.on_trade(_ev("M", buyers[9], True, 10), now + 10)
    assert "M" in p.signaled
    assert "M" in p.accounts["wallet_ladder_v1"].pending_buy
    assert "M" not in p.accounts["wallet_ladder_v1"].s["posiciones"]
    p.on_trade(_ev("M", "u11", True, 11), now + 11)
    assert "M" in p.accounts["wallet_ladder_v1"].s["posiciones"]
    pos = p.accounts["wallet_ladder_v1"].s["posiciones"]["M"]
    assert pos["decision_slot"] == 10
    assert pos["demora_s"] > 0


def test_fixed_account_never_compounds_entry_size(tmp_path):
    a = FixedPumpAccount("wallet_ladder_v1", tmp_path)
    assert a.s["capital_inicial"] == 20.0
    assert a.s["entry_sol"] == 0.5
    a.s["cash"] = 100.0
    a.request_buy("A", 1.0)
    assert a.pending_buy["A"]
