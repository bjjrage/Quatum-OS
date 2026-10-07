"""Buyer-10, post-decision entry, fixed sizing, and frozen exits."""

import random

from src.paper.pump_wallet_skill_v1 import (
    ENTRY_SOL,
    FIRST_BUYERS,
    INITIAL_CAPITAL_SOL,
    MAX_HOLD_S,
    MAX_OPEN,
    MAX_WAIT_S,
    STOP_LOSS,
    TAKE_FRAC,
    TRAIL,
    FixedPumpAccount,
    WalletSkillPaper,
)


VS0, VT0 = 30 * 10**9, 1_073_000_000 * 10**6


def _event(mint, user, slot, vsol=VS0, vtok=VT0):
    return {
        "mint": mint,
        "user": user,
        "is_buy": True,
        "sol_amount": 500_000_000,
        "token_amount": 10**12,
        "slot": slot,
        "virtual_sol_reserves": vsol,
        "virtual_token_reserves": vtok,
    }


def _paper_with_goods(root, goods):
    paper = WalletSkillPaper(root=root, rnd=random.Random(0))
    for wallet in goods:
        paper.skill.stats[wallet] = {"matured": 5, "wins": 2}
    paper.on_create({"mint": "M", "user": "DEV", "symbol": "M"}, 1_000.0)
    return paper


def test_signal_is_decided_at_tenth_unique_buyer_and_buyer_eleven_cannot_revise(tmp_path):
    one_good = _paper_with_goods(tmp_path / "one", {"W1"})
    buyers = ["W1", "u2", "u3", "u4", "u5", "u6", "u7", "u8", "u9", "u10"]
    for slot, wallet in enumerate(buyers, 1):
        one_good.on_trade(_event("M", wallet, slot), 1_000.0 + slot)
    assert "M" not in one_good.signaled

    exactly_two = _paper_with_goods(tmp_path / "two", {"W1", "W2"})
    buyers = ["W1", "u2", "u3", "W2", "u5", "u6", "u7", "u8", "u9", "u10"]
    for slot, wallet in enumerate(buyers, 1):
        exactly_two.on_trade(_event("M", wallet, slot), 1_000.0 + slot)
    assert "M" in exactly_two.signaled
    assert exactly_two.accounts["wallet_ladder_v1"].pending_buy["M"]["decision_slot"] == 10

    late = _paper_with_goods(tmp_path / "late", {"W1", "W11"})
    buyers = ["W1", "u2", "u3", "u4", "u5", "u6", "u7", "u8", "u9", "u10"]
    for slot, wallet in enumerate(buyers, 1):
        late.on_trade(_event("M", wallet, slot), 1_000.0 + slot)
    late.on_trade(_event("M", "W11", 11), 1_011.0)
    assert "M" not in late.signaled


def test_duplicate_wallet_does_not_advance_unique_buyer_number(tmp_path):
    paper = _paper_with_goods(tmp_path, {"W1", "W2"})
    sequence = ["W1", "W1", "u2", "u3", "W2", "u5", "u6", "u7", "u8", "u9"]
    for slot, wallet in enumerate(sequence, 1):
        paper.on_trade(_event("M", wallet, slot), 1_000.0 + slot)
    assert len(paper.buyers["M"]) == 9
    assert "M" not in paper.signaled
    paper.on_trade(_event("M", "u10", 11), 1_011.0)
    assert "M" in paper.signaled
    assert paper.accounts["wallet_ladder_v1"].pending_buy["M"]["decision_slot"] == 11


def test_entry_uses_first_trade_after_decision_and_size_is_fixed(tmp_path):
    paper = _paper_with_goods(tmp_path, {"W1", "W2"})
    buyers = ["W1", "u2", "u3", "W2", "u5", "u6", "u7", "u8", "u9", "u10"]
    for slot, wallet in enumerate(buyers, 1):
        paper.on_trade(_event("M", wallet, slot), 1_000.0 + slot)
    paper.on_trade(_event("M", "u11", 11), 1_011.0)

    position = paper.accounts["wallet_ladder_v1"].s["posiciones"]["M"]
    assert position["decision_slot"] == 10
    assert position["entrada_ts"] > position["decision_ts"]
    assert position["demora_s"] > 0
    assert position["tok"] > 0

    account = FixedPumpAccount("wallet_ladder_v1", tmp_path / "sizing")
    assert account.s["capital_inicial"] == INITIAL_CAPITAL_SOL == 20.0
    assert account.s["entry_sol"] == ENTRY_SOL == 0.5
    assert account.s["max_abiertas"] == MAX_OPEN == 30
    account.s["cash"] = 100.0  # prior gains do not change the configured entry size
    account.request_buy("N", 2_000.0)
    account.on_trade("N", VS0, VT0, 2_001.0)
    assert abs(account.s["cash"] - (100.0 - ENTRY_SOL - 0.0005)) < 1e-9


def test_exit_thresholds_and_priority_are_frozen(tmp_path):
    assert STOP_LOSS == -0.50
    assert TAKE_FRAC == 0.50
    assert TRAIL == 0.35
    assert MAX_WAIT_S == 7200
    assert MAX_HOLD_S == 21600

    account = FixedPumpAccount("wallet_ladder_v1", tmp_path)
    account.request_buy("M", 0.0)
    account.on_trade("M", VS0, VT0, 1.0)
    k = VS0 * VT0
    high_vs = int(VS0 * 1.6)
    high_vt = k // high_vs
    account.on_trade("M", high_vs, high_vt, 2.0)
    assert account.pending_sell["M"][1:] == ("2x", 0.5)
    account.on_trade("M", high_vs, high_vt, 3.0)
    assert account.s["posiciones"]["M"]["tomado"]

    peak_vs = int(VS0 * 2.2)
    account.on_trade("M", peak_vs, k // peak_vs, 4.0)
    drawdown_vs = int(VS0 * 1.7)
    account.on_trade("M", drawdown_vs, k // drawdown_vs, 5.0)
    assert account.pending_sell["M"][1] == "trailing -35%"


def test_pre_two_x_stop_loss_is_minus_fifty_percent(tmp_path):
    account = FixedPumpAccount("wallet_ladder_v1", tmp_path)
    account.request_buy("M", 0.0)
    account.on_trade("M", VS0, VT0, 1.0)
    account.on_trade("M", VS0 // 3, VT0 * 3, 2.0)
    assert account.pending_sell["M"][1] == "stop -50%"
    account.on_trade("M", VS0 // 3, VT0 * 3, 3.0)
    assert account.s["cerradas"][-1]["motivo"] == "stop -50%"


def test_two_hour_timeout_and_six_hour_max_hold(tmp_path):
    timeout = FixedPumpAccount("wallet_ladder_v1", tmp_path / "timeout")
    timeout.request_buy("M", 0.0)
    timeout.on_trade("M", VS0, VT0, 1.0)
    timeout.tick(1.0 + MAX_WAIT_S, {"M": [VS0, VT0, 1.0]})
    assert timeout.pending_sell["M"][1] == "no llego a 2x en 2h"
    timeout.on_trade("M", VS0, VT0, 1.0 + MAX_WAIT_S + 1)
    assert timeout.s["cerradas"][-1]["motivo"] == "no llego a 2x en 2h"

    # If an unscaled position is first ticked at 6h, the earlier 2h no-2x
    # condition has priority, as encoded by the existing if/elif rule order.
    priority = FixedPumpAccount("wallet_ladder_v1", tmp_path / "priority")
    priority.request_buy("M", 0.0)
    priority.on_trade("M", VS0, VT0, 1.0)
    priority.tick(1.0 + MAX_HOLD_S, {"M": [VS0, VT0, 1.0]})
    assert priority.pending_sell["M"][1] == "no llego a 2x en 2h"

    held = FixedPumpAccount("wallet_ladder_v1", tmp_path / "held")
    held.request_buy("M", 0.0)
    held.on_trade("M", VS0, VT0, 1.0)
    k = VS0 * VT0
    high_vs = int(VS0 * 1.6)
    high_vt = k // high_vs
    held.on_trade("M", high_vs, high_vt, 2.0)
    held.on_trade("M", high_vs, high_vt, 3.0)
    held.tick(1.0 + MAX_HOLD_S, {"M": [high_vs, high_vt, 1.0]})
    assert held.pending_sell["M"][1] == "tope 6h"
    held.on_trade("M", high_vs, high_vt, 1.0 + MAX_HOLD_S + 1)
    assert held.s["cerradas"][-1]["motivo"] == "tope 6h"
