"""Unit tests for Backtest Engine, Performance Metrics, and Walk-Forward Validation."""
import math
import pytest

from src.backtest.engine import DeterministicBacktestEngine, OrderSide, OrderType, OrderStatus
from src.backtest.metrics import calc_performance_metrics
from src.backtest.validation import purged_walk_forward_splits, benjamini_hochberg_fdr, holm_bonferroni_correction


def test_deterministic_backtest_market_orders_and_fees() -> None:
    """Engine executes market orders with slippage, taker fee, and deterministic accounting."""
    engine = DeterministicBacktestEngine(
        initial_cash=100_000.0,
        maker_fee_bps=1.0,
        taker_fee_bps=4.0,
        slippage_bps=2.0,
        fill_latency_ns=0,
    )

    t0 = 1_000_000_000_000_000

    # Market Buy 1.0 BTC at ask 60,000.0
    # Expected fill price: 60,000 * (1 + 0.0002) = 60,012.0
    # Expected fee: 60,012 * 0.0004 = 24.0048
    ord1 = engine.submit_order(
        symbol="BTCUSDT",
        venue="binance_perp",
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=1.0,
        current_ts_ns=t0,
    )
    trades1 = engine.on_market_tick("BTCUSDT", bid_price=59990.0, ask_price=60000.0, current_ts_ns=t0)

    assert len(trades1) == 1
    assert ord1.status == OrderStatus.FILLED
    assert math.isclose(ord1.filled_price, 60012.0, rel_tol=1e-5)
    assert engine.positions["BTCUSDT"] == 1.0
    assert engine.cash < 40000.0

    # Market Sell 1.0 BTC at bid 65,000.0
    # Expected fill: 65,000 * (1 - 0.0002) = 64,987.0
    ord2 = engine.submit_order(
        symbol="BTCUSDT",
        venue="binance_perp",
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        quantity=1.0,
        current_ts_ns=t0 + 1_000_000,
    )
    trades2 = engine.on_market_tick("BTCUSDT", bid_price=65000.0, ask_price=65010.0, current_ts_ns=t0 + 1_000_000)

    assert len(trades2) == 1
    assert engine.positions["BTCUSDT"] == 0.0
    assert engine.cash > 104000.0  # Profitable roundtrip net of fees


def test_deterministic_backtest_limit_orders() -> None:
    """Limit orders only fill when market crosses limit price."""
    engine = DeterministicBacktestEngine(initial_cash=50_000.0, fill_latency_ns=0)
    t0 = 1_000_000_000

    # Limit Buy at 50.0
    ord1 = engine.submit_order(
        symbol="SOLUSDT",
        venue="binance_perp",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=10.0,
        limit_price=50.0,
        current_ts_ns=t0,
    )

    # Market at 55.0 / 56.0 -> Order remains pending
    t1 = engine.on_market_tick("SOLUSDT", bid_price=55.0, ask_price=56.0, current_ts_ns=t0 + 100)
    assert len(t1) == 0
    assert ord1.status == OrderStatus.PENDING

    # Market drops to 49.0 / 50.0 -> Order fills at limit price 50.0
    t2 = engine.on_market_tick("SOLUSDT", bid_price=49.0, ask_price=50.0, current_ts_ns=t0 + 200)
    assert len(t2) == 1
    assert ord1.status == OrderStatus.FILLED
    assert ord1.filled_price == 50.0


def test_performance_metrics_calculation() -> None:
    """Performance metrics correctly calculate Sharpe, Sortino, Drawdown, and Win Rate."""
    # Monotonically increasing equity curve
    equity = [100_000.0, 101_000.0, 102_500.0, 102_000.0, 104_000.0, 105_000.0]
    
    from src.backtest.engine import SimulatedTrade
    trades = [
        SimulatedTrade("1", "o1", "BTC", "binance", OrderSide.BUY, 60000.0, 1.0, 24.0, 1),
        SimulatedTrade("2", "o2", "BTC", "binance", OrderSide.SELL, 65000.0, 1.0, 26.0, 2),
    ]

    metrics = calc_performance_metrics(equity, trades)
    assert metrics.total_return_pct == 5.0
    assert metrics.total_net_pnl == 5000.0
    assert metrics.annualized_sharpe > 0.0
    assert metrics.max_drawdown_pct > 0.0
    assert metrics.win_rate == 1.0
    assert metrics.profit_factor > 1.0


def test_purged_walk_forward_splits() -> None:
    """Walk forward splits enforce purge and embargo gaps between folds."""
    splits = purged_walk_forward_splits(
        n_samples=100,
        train_size=40,
        test_size=10,
        purge_size=5,
        embargo_size=5,
        step_size=10,
    )
    assert len(splits) >= 4
    for sp in splits:
        assert len(sp.train_indices) == 40
        assert len(sp.test_indices) == 10
        # No overlap between train and test
        assert set(sp.train_indices).isdisjoint(set(sp.test_indices))
        # Purge gap of 5 between train end and test start
        train_max = max(sp.train_indices)
        test_min = min(sp.test_indices)
        assert test_min - train_max - 1 == 5


def test_multiple_testing_corrections() -> None:
    """FDR and Holm-Bonferroni control false discovery rate across multiple candidate tests."""
    # 10 candidate strategies: 2 strong signals (p < 0.001), 8 noise (p > 0.10)
    p_vals = [0.0001, 0.0005, 0.12, 0.25, 0.38, 0.45, 0.60, 0.72, 0.85, 0.95]

    sig_fdr, thresh = benjamini_hochberg_fdr(p_vals, alpha=0.05)
    assert sig_fdr[0] is True
    assert sig_fdr[1] is True
    assert all(sig is False for sig in sig_fdr[2:])

    sig_holm = holm_bonferroni_correction(p_vals, alpha=0.05)
    assert sig_holm[0] is True
    assert sig_holm[1] is True
    assert all(sig is False for sig in sig_holm[2:])
