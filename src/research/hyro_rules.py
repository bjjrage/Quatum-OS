"""Versioned HyroTrader rule facts and boundary helpers for research simulations.

The market-facing simulator remains RULES_UNVERIFIED because account drawdown mode,
trade-level qualifying days, and manually reviewed position-loss rules are not inputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

RULE_VERSION = "HYRO_TWO_STEP_2026-10-05"
VERIFIED_AT = "2026-10-05"
RULES_STATUS = "RULES_UNVERIFIED"
SOURCE_URLS = {
    "targets": "https://www.hyrotrader.com/faq/getting-started/how-to-start/",
    "daily_drawdown": "https://www.hyrotrader.com/faq/rules/how-is-the-5-daily-drawdown-calculated/",
    "drawdown_modes": "https://www.hyrotrader.com/faq/rules/what-is-the-difference-between-standard-trailing-and-swing-fixed-daily-drawdown/",
    "profit_distribution": "https://www.hyrotrader.com/faq/trading-restrictions/i-have-one-trading-day-that-exceeds-the-profit-distribution-rule-what-happens-now/",
    "minimum_days": "https://www.hyrotrader.com/faq/evaluation-process/minimum-trading-days/",
    "position_loss": "https://www.hyrotrader.com/faq/rules/what-is-the-maximum-loss-per-trade-rule/",
    "leverage": "https://www.hyrotrader.com/faq/platform/what-leverage-can-i-use/",
    "trading_rules": "https://www.hyrotrader.com/trading-rules/",
}

TWO_STEP_RULES: Dict[str, Any] = {
    "rule_version": RULE_VERSION,
    "verified_at": VERIFIED_AT,
    "status": RULES_STATUS,
    "source_urls": SOURCE_URLS,
    "phases": [
        {"name": "Challenge", "target_pct": 0.10, "daily_loss_pct": 0.05,
         "max_loss_pct": 0.10, "minimum_valid_days": 5},
        {"name": "Verification", "target_pct": 0.05, "daily_loss_pct": 0.05,
         "max_loss_pct": 0.10, "minimum_valid_days": 5},
    ],
    "profit_distribution_cap_pct_of_phase_target": 0.40,
    "valid_day_min_trade_notional_pct_initial": 0.05,
    "valid_day_min_positive_pnl_pct_trade_notional_before_fees": 0.01,
    "max_realized_loss_per_position_pct_initial": 0.03,
    "max_realized_loss_rule_review": "MANUAL",
    "platform_max_leverage": "UP_TO_100X_DEPENDS_ON_PLATFORM_AND_PAIR",
    "daily_drawdown_mode": None,
    "daily_drawdown_mode_status": "ACCOUNT_OPTION_UNVERIFIED",
    "trade_level_inputs_available_to_daily_simulator": False,
    "time_limit_days": None,
    "max_inactivity_days": 30,
    "prohibited_instruments": ["spot", "USDC perpetuals", "COIN-M futures", "options"],
    "low_cap_coin_max_exposure_pct_initial": 0.05,
}


def daily_floor(initial_balance: float, start_day_equity: float, daily_loss_pct: float = 0.05) -> float:
    return float(start_day_equity) - float(initial_balance) * float(daily_loss_pct)


def daily_loss_breached(current_equity: float, initial_balance: float, start_day_equity: float,
                        daily_loss_pct: float = 0.05, mode: Optional[str] = None,
                        intraday_peak_equity: Optional[float] = None) -> Optional[bool]:
    """Return None until fixed/swing or standard/trailing mode is known for the account."""
    if mode is None:
        return None
    if mode == "fixed":
        floor = daily_floor(initial_balance, start_day_equity, daily_loss_pct)
    elif mode == "trailing":
        peak = start_day_equity if intraday_peak_equity is None else max(start_day_equity, intraday_peak_equity)
        floor = daily_floor(initial_balance, peak, daily_loss_pct)
    else:
        raise ValueError("mode must be 'fixed', 'trailing', or None")
    return float(current_equity) < floor  # official FAQ says the rule breaches below the floor


def max_loss_breached(current_equity: float, initial_balance: float, max_loss_pct: float = 0.10) -> bool:
    return float(current_equity) < float(initial_balance) * (1.0 - float(max_loss_pct))


def profit_distribution_counted_pnl(day_net_pnls: Iterable[float], phase_target: float,
                                    cap_fraction: float = 0.40) -> float:
    """Positive days count only up to the cap; negative net days count in full."""
    cap = float(phase_target) * float(cap_fraction)
    return sum(min(float(pnl), cap) if float(pnl) > 0 else float(pnl) for pnl in day_net_pnls)


def position_loss_breached(realized_pnl_usd: float, initial_balance: float,
                           max_loss_pct: float = 0.03) -> bool:
    return float(realized_pnl_usd) < -float(initial_balance) * float(max_loss_pct)


def qualifying_utc_trading_days(trades: Iterable[Dict[str, Any]], initial_balance: float) -> set[str]:
    """Distinct UTC close dates with at least one rule-qualifying closed trade."""
    min_notional = float(initial_balance) * 0.05
    valid: set[str] = set()
    for trade in trades:
        try:
            notional = abs(float(trade["notional_usd"]))
            pnl = float(trade["realized_pnl_before_fees_usd"])
            close_raw = str(trade["closed_at"])
            close_dt = datetime.fromisoformat(close_raw.replace("Z", "+00:00"))
            if close_dt.tzinfo is None:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        if notional >= min_notional and pnl >= notional * 0.01:
            valid.add(close_dt.astimezone(timezone.utc).date().isoformat())
    return valid
