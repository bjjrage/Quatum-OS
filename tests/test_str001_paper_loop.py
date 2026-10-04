import pytest
from src.shadow.str001_paper import Str001PaperTrader

T0 = 1_760_000_000_000_000_000


def rec(mid="m1", action="BUY_YES", bid=0.40, ask=0.42, und="BTC"):
    entry = ask if action == "BUY_YES" else 1.0 - bid
    return {"status": "PRICED", "action": action, "market_id": mid, "yes_token_id": f"tok-{mid}",
            "underlying": und, "ts_utc": f"2026-10-04T00:00:{mid[-1]}0Z", "entry_price": entry,
            "quote": {"bid": bid, "ask": ask, "bid_size": 500.0, "ask_size": 500.0, "ts_ns": T0}}


@pytest.fixture
def t(tmp_path):
    return Str001PaperTrader(out_dir=tmp_path, initial_cash_usd=10_000.0, notional_per_trade_usd=50.0,
                             clock_ns=lambda: T0 + 1_000_000)


def test_buy_yes_fills_through_router_and_settles_win(t):
    e = t.on_decision(rec())
    assert e["state"] in ("FILLED", "PARTIALLY_FILLED"), e
    assert t.broker.positions["tok-m1"].quantity > 0
    cash_after_entry = t.broker.cash_usd
    qty = t.broker.positions["tok-m1"].quantity
    pnl = t.settle("m1", 1)
    assert pnl == pytest.approx((1.0 - 0.42) * qty)
    assert pnl > 0 and t.broker.cash_usd > cash_after_entry


def test_buy_yes_loses_when_resolves_no(t):
    t.on_decision(rec())
    qty = t.broker.positions["tok-m1"].quantity
    pnl = t.settle("m1", 0)
    assert pnl == pytest.approx(-0.42 * qty)


def test_buy_no_wins_when_resolves_no(t):
    e = t.on_decision(rec(action="BUY_NO", bid=0.60, ask=0.62))
    assert e["state"] in ("FILLED", "PARTIALLY_FILLED"), e
    assert "tok-m1:NO" in t.broker.positions
    assert t.settle("m1", 0) > 0


def test_no_second_position_in_same_market_and_underlying_cap(t):
    t.on_decision(rec("m1"))
    assert t.on_decision(rec("m1")) is None
    t.max_per_und = 1
    assert t.on_decision(rec("m2"))["reason"] == "MAX_PER_UNDERLYING"


def test_non_signals_are_ignored(t):
    r = rec(); r["action"] = "NONE"
    assert t.on_decision(r) is None


def test_orders_logged(t, tmp_path):
    t.on_decision(rec())
    assert (tmp_path / "paper_orders.jsonl").exists()
