from src.research.exam_sim import RULES, simulate
from src.research.hyro_rules import (
    RULES_STATUS,
    TWO_STEP_RULES,
    daily_floor,
    daily_loss_breached,
    max_loss_breached,
    position_loss_breached,
    profit_distribution_counted_pnl,
    qualifying_utc_trading_days,
)


def test_daily_drawdown_fixed_and_trailing_boundaries():
    floor = daily_floor(10_000, 10_000, 0.05)
    assert floor == 9_500
    assert daily_loss_breached(floor, 10_000, 10_000, 0.05, mode="fixed") is False
    assert daily_loss_breached(floor - 0.01, 10_000, 10_000, 0.05, mode="fixed") is True
    assert daily_loss_breached(floor + 0.01, 10_000, 10_000, 0.05, mode="fixed") is False
    assert daily_loss_breached(9_999, 10_000, 10_000, mode=None) is None
    assert daily_loss_breached(9_999, 10_000, 10_000, mode="trailing", intraday_peak_equity=10_500) is True


def test_overall_and_position_loss_boundaries():
    assert max_loss_breached(9_000, 10_000) is False
    assert max_loss_breached(8_999.99, 10_000) is True
    assert max_loss_breached(9_000.01, 10_000) is False
    assert position_loss_breached(-300, 10_000) is False
    assert position_loss_breached(-300.01, 10_000) is True
    assert position_loss_breached(-299.99, 10_000) is False


def test_profit_distribution_caps_positive_days_and_counts_losses_in_full():
    assert profit_distribution_counted_pnl([600, -50, 200], phase_target=1_000) == 550
    assert profit_distribution_counted_pnl([400], phase_target=1_000) == 400
    assert profit_distribution_counted_pnl([400.01], phase_target=1_000) == 400
    assert profit_distribution_counted_pnl([-400], phase_target=1_000) == -400


def test_valid_days_use_closed_trade_thresholds_and_utc_dates():
    trades = [
        {"notional_usd": 500, "realized_pnl_before_fees_usd": 5, "closed_at": "2026-10-01T23:30:00-04:00"},
        {"notional_usd": 500, "realized_pnl_before_fees_usd": -5, "closed_at": "2026-10-02T03:45:00Z"},
        {"notional_usd": 500, "realized_pnl_before_fees_usd": -10, "closed_at": "2026-10-06T12:00:00Z"},
        {"notional_usd": 500, "realized_pnl_before_fees_usd": -5, "closed_at": "2026-10-07T12:00:00Z"},
        {"notional_usd": 499.99, "realized_pnl_before_fees_usd": 10, "closed_at": "2026-10-03T12:00:00Z"},
        {"notional_usd": 500, "realized_pnl_before_fees_usd": 4.99, "closed_at": "2026-10-04T12:00:00Z"},
        {"notional_usd": 500, "realized_pnl_before_fees_usd": 10, "closed_at": "2026-10-05T12:00:00"},
        {"notional_usd": 500, "realized_pnl_before_fees_usd": 10, "closed_at": "not-a-date"},
        {"notional_usd": 500, "realized_pnl_before_fees_usd": 10},
    ]
    assert qualifying_utc_trading_days(trades, 10_000) == {"2026-10-02", "2026-10-06", "2026-10-07"}


def test_exam_outputs_remain_explicitly_model_only_until_account_rules_are_known():
    assert RULES_STATUS == "RULES_UNVERIFIED"
    assert TWO_STEP_RULES["status"] == "RULES_UNVERIFIED"
    row = simulate([0.01] * 20, RULES["HyroTrader_2F"], 1, n=10, block=2, max_days=50)
    assert row["rules_status"] == "RULES_UNVERIFIED"
    assert "target_hit_pct_model_only" in row
    assert "target_hit_pct" not in row
