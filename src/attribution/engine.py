"""
Performance Attribution and Multi-Factor PnL Decomposition Engine.

Decomposes portfolio and strategy returns into:
- Gross Trade PnL
- Alpha (idiosyncratic excess return)
- Beta (market systematic drift)
- Execution Drag:
  - Exchange Fees (maker/taker)
  - Execution Slippage (market impact / delay)
  - Implementation Shortfall (decision price vs execution price)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class TradeExecutionRecord:
    trade_id: str
    strategy_id: str
    symbol: str
    side: str
    quantity: float
    decision_price: float
    execution_price: float
    fee_paid: float
    timestamp_ns: int


@dataclass
class StrategyAttribution:
    strategy_id: str
    gross_pnl_usd: float = 0.0
    net_pnl_usd: float = 0.0
    alpha_pnl_usd: float = 0.0
    beta_pnl_usd: float = 0.0
    total_fees_usd: float = 0.0
    total_slippage_usd: float = 0.0
    implementation_shortfall_usd: float = 0.0
    trade_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0

    @property
    def win_rate_pct(self) -> float:
        return (self.winning_trades / self.trade_count * 100.0) if self.trade_count > 0 else 0.0

    @property
    def fee_drag_pct(self) -> float:
        return (self.total_fees_usd / abs(self.gross_pnl_usd) * 100.0) if abs(self.gross_pnl_usd) > 0 else 0.0


class PerformanceAttributionEngine:
    """
    Decomposes strategy and portfolio PnL across alpha, beta, and execution frictions.
    """

    def __init__(self, benchmark_symbol: str = "BTC-USDT"):
        self.benchmark_symbol = benchmark_symbol
        self.records: List[TradeExecutionRecord] = []

    def record_trade(
        self,
        trade_id: str,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: float,
        decision_price: float,
        execution_price: float,
        fee_paid: float,
        timestamp_ns: int,
    ) -> TradeExecutionRecord:
        record = TradeExecutionRecord(
            trade_id=trade_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            decision_price=decision_price,
            execution_price=execution_price,
            fee_paid=fee_paid,
            timestamp_ns=timestamp_ns,
        )
        self.records.append(record)
        return record

    def compute_attribution(
        self,
        strategy_gross_pnls: Dict[str, float],
        market_benchmark_return: float = 0.0,
        strategy_betas: Optional[Dict[str, float]] = None,
        average_capital_usd: Optional[Dict[str, float]] = None,
    ) -> Dict[str, StrategyAttribution]:
        """
        Compute full attribution breakdown per strategy.
        """
        attributions: Dict[str, StrategyAttribution] = {}
        betas = strategy_betas or {}
        capitals = average_capital_usd or {}

        # Aggregate trade-level frictions
        for rec in self.records:
            attr = attributions.setdefault(rec.strategy_id, StrategyAttribution(strategy_id=rec.strategy_id))
            attr.trade_count += 1
            attr.total_fees_usd += rec.fee_paid

            # Implementation shortfall: (exec_price - decision_price) * qty for buy, opposite for sell
            if rec.side == "BUY":
                shortfall = (rec.execution_price - rec.decision_price) * rec.quantity
            else:
                shortfall = (rec.decision_price - rec.execution_price) * rec.quantity

            attr.implementation_shortfall_usd += max(0.0, shortfall)
            attr.total_slippage_usd += abs(rec.execution_price - rec.decision_price) * rec.quantity

        # Merge with gross PnL and decompose into Alpha vs Beta
        for strat_id, gross_pnl in strategy_gross_pnls.items():
            attr = attributions.setdefault(strat_id, StrategyAttribution(strategy_id=strat_id))
            attr.gross_pnl_usd = gross_pnl
            attr.net_pnl_usd = gross_pnl - attr.total_fees_usd - attr.total_slippage_usd

            # Beta PnL = Beta * Benchmark_Return * Average_Capital
            beta = betas.get(strat_id, 0.0)
            capital = capitals.get(strat_id, 10_000.0)
            beta_pnl = beta * market_benchmark_return * capital
            attr.beta_pnl_usd = beta_pnl

            # Alpha is the residual net return after market beta
            attr.alpha_pnl_usd = attr.net_pnl_usd - beta_pnl

            if attr.net_pnl_usd > 0:
                attr.winning_trades = max(1, attr.winning_trades)
            elif attr.net_pnl_usd < 0:
                attr.losing_trades = max(1, attr.losing_trades)

        return attributions
