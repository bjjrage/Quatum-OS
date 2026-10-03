"""Backtesting, Execution Simulation, and Validation Engine."""
from .engine import DeterministicBacktestEngine, SimulatedOrder, OrderSide, OrderType, OrderStatus, SimulatedTrade
from .metrics import calc_performance_metrics, BacktestPerformanceReport
from .validation import purged_walk_forward_splits, benjamini_hochberg_fdr, holm_bonferroni_correction

__all__ = [
    "DeterministicBacktestEngine",
    "SimulatedOrder",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "SimulatedTrade",
    "calc_performance_metrics",
    "BacktestPerformanceReport",
    "purged_walk_forward_splits",
    "benjamini_hochberg_fdr",
    "holm_bonferroni_correction",
]
