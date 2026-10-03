"""Quantitative portfolio performance metrics and drawdown analytics."""
import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .engine import SimulatedTrade, OrderSide


class BacktestPerformanceReport(BaseModel):
    """Structured performance report for a backtest or paper run."""
    initial_equity: float
    final_equity: float
    total_net_pnl: float
    total_return_pct: float
    annualized_sharpe: float
    annualized_sortino: float
    max_drawdown_pct: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    expectancy_per_trade: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_fees_paid: float
    turnover: float


def calc_performance_metrics(
    equity_curve: List[float],
    trades: List[SimulatedTrade],
    annualize_factor: float = math.sqrt(252 * 24 * 60),  # Minute bars by default
) -> BacktestPerformanceReport:
    """Calculate institutional-grade performance and drawdown metrics."""
    if not equity_curve:
        equity_curve = [100_000.0]

    initial_eq = equity_curve[0]
    final_eq = equity_curve[-1]
    net_pnl = round(final_eq - initial_eq, 2)
    tot_return_pct = round(((final_eq - initial_eq) / initial_eq) * 100.0, 4)

    # Returns series
    returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]
        curr = equity_curve[i]
        if prev > 0:
            returns.append((curr - prev) / prev)
        else:
            returns.append(0.0)

    # Sharpe & Sortino
    sharpe = 0.0
    sortino = 0.0
    if len(returns) >= 2:
        mean_ret = sum(returns) / len(returns)
        var = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(var) if var > 1e-12 else 0.0

        if std > 1e-9:
            sharpe = round((mean_ret / std) * annualize_factor, 2)

        # Downside deviation for Sortino
        downside_sq = [min(0.0, r) ** 2 for r in returns]
        downside_std = math.sqrt(sum(downside_sq) / len(downside_sq)) if downside_sq else 0.0
        if downside_std > 1e-9:
            sortino = round((mean_ret / downside_std) * annualize_factor, 2)

    # Max Drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    max_dd_pct = round(max_dd * 100.0, 2)
    calmar = round(tot_return_pct / max_dd_pct, 2) if max_dd_pct > 0.001 else 0.0

    # Trade statistics
    total_trades = len(trades)
    total_fees = round(sum(t.fee_paid for t in trades), 2)
    turnover = round(sum(t.price * t.quantity for t in trades), 2)

    # Match trades into roundtrips
    # Simple pairing heuristic for per-trade expectancy:
    wins = 0
    losses = 0
    gross_profits = 0.0
    gross_losses = 0.0

    # Calculate trade PnLs
    # Group by symbol
    sym_trades: Dict[str, List[SimulatedTrade]] = {}
    for t in trades:
        sym_trades.setdefault(t.symbol, []).append(t)

    for sym, t_list in sym_trades.items():
        inv = 0.0
        cost_basis = 0.0
        for t in t_list:
            if t.side == OrderSide.BUY:
                inv += t.quantity
                cost_basis += t.price * t.quantity
            else:
                if inv > 0:
                    avg_cost = cost_basis / inv
                    pnl = (t.price - avg_cost) * min(inv, t.quantity) - t.fee_paid
                    if pnl > 0:
                        wins += 1
                        gross_profits += pnl
                    else:
                        losses += 1
                        gross_losses += abs(pnl)
                    inv = max(0.0, inv - t.quantity)

    win_rate = round(wins / (wins + losses), 4) if (wins + losses) > 0 else 0.0
    profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 1e-9 else (99.0 if gross_profits > 0 else 0.0)
    expectancy = round((gross_profits - gross_losses) / (wins + losses), 2) if (wins + losses) > 0 else 0.0

    return BacktestPerformanceReport(
        initial_equity=initial_eq,
        final_equity=final_eq,
        total_net_pnl=net_pnl,
        total_return_pct=tot_return_pct,
        annualized_sharpe=sharpe,
        annualized_sortino=sortino,
        max_drawdown_pct=max_dd_pct,
        calmar_ratio=calmar,
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy_per_trade=expectancy,
        total_trades=total_trades,
        winning_trades=wins,
        losing_trades=losses,
        total_fees_paid=total_fees,
        turnover=turnover,
    )
