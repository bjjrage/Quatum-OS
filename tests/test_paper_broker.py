"""Unit tests for Realistic Paper Broker simulation."""

import pytest
from src.paper.broker import (
    PaperBroker,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
)


def test_market_order_fill_with_slippage_and_fee():
    broker = PaperBroker(
        initial_cash_usd=100_000.0,
        simulated_latency_ms=10.0,
        taker_fee_bps=5.0,  # 0.05%
        base_slippage_bps=2.0,  # 0.02%
    )

    bbo = {"best_bid": 60_000.0, "best_ask": 60_010.0, "bid_size": 2.0, "ask_size": 2.0}

    # BUY Market order for 0.5 BTC
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=0.5,
        venue="BINANCE",
        current_time_ns=1_000_000_000,
        current_bbo=bbo,
    )

    assert order.status == PaperOrderStatus.FILLED
    # Base price was ask 60,010.0. Slippage +2 bps = 60,010 * 1.0002 = 60,022.002
    assert order.filled_price > 60_010.0
    assert order.slippage_usd > 0.0
    assert order.fee_paid > 0.0
    assert len(broker.trades) == 1

    summary = broker.get_portfolio_summary({"BTC-USDT": 60_010.0})
    assert summary["positions"]["BTC-USDT"]["quantity"] == 0.5
    assert summary["cash_usd"] < 100_000.0


def test_limit_order_queue_and_fill():
    broker = PaperBroker(
        initial_cash_usd=50_000.0,
        simulated_latency_ms=20.0,
        maker_fee_bps=1.0,  # 0.01%
    )

    bbo = {"best_bid": 59_990.0, "best_ask": 60_000.0, "bid_size": 3.0, "ask_size": 3.0}

    # Place Buy limit at 59,990 (joining the bid)
    t0 = 1_000_000_000
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=1.0,
        limit_price=59_990.0,
        venue="BINANCE",
        current_time_ns=t0,
        current_bbo=bbo,
    )

    assert order.status == PaperOrderStatus.SUBMITTED
    assert order.queue_ahead_volume == 3.0

    # Event 1: Market event before latency delay expires -> does not fill
    trades1 = broker.on_market_event(
        symbol="BTC-USDT",
        best_bid=59_990.0,
        best_ask=60_000.0,
        event_time_ns=t0 + 10_000_000,  # +10ms (< 20ms latency)
        trade_volume=5.0,
    )
    assert len(trades1) == 0
    assert order.status == PaperOrderStatus.SUBMITTED

    # Event 2: After latency, trade volume partially consumes queue (2.0 consumed out of 3.0)
    trades2 = broker.on_market_event(
        symbol="BTC-USDT",
        best_bid=59_990.0,
        best_ask=60_000.0,
        event_time_ns=t0 + 30_000_000,  # +30ms
        trade_volume=2.0,
    )
    assert len(trades2) == 0
    assert order.queue_ahead_volume == 1.0

    # Event 3: Remaining queue consumed -> fills!
    trades3 = broker.on_market_event(
        symbol="BTC-USDT",
        best_bid=59_990.0,
        best_ask=60_000.0,
        event_time_ns=t0 + 40_000_000,
        trade_volume=1.5,
    )
    assert len(trades3) == 1
    assert order.status == PaperOrderStatus.FILLED
    assert order.filled_price == 59_990.0
    assert order.fee_paid == 59_990.0 * 1.0 * (1.0 / 10_000.0)


def test_order_cancellation():
    broker = PaperBroker(initial_cash_usd=100_000.0)
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=1.0,
        limit_price=50_000.0,
        current_time_ns=1_000_000_000,
    )
    assert order.status == PaperOrderStatus.SUBMITTED

    cancelled = broker.cancel_order(order.order_id)
    assert cancelled is True
    assert order.status == PaperOrderStatus.CANCELLED

    # Cancelling again returns False
    assert broker.cancel_order(order.order_id) is False


def test_realized_and_unrealized_pnl():
    broker = PaperBroker(initial_cash_usd=100_000.0, maker_fee_bps=0.0, taker_fee_bps=0.0, base_slippage_bps=0.0)

    # Buy 1 BTC @ 50,000
    broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=1.0,
        current_time_ns=1_000_000_000,
        current_bbo={"best_bid": 50_000.0, "best_ask": 50_000.0},
    )

    # Mark price goes to 55,000 -> unrealized PnL = +$5,000
    summary = broker.get_portfolio_summary({"BTC-USDT": 55_000.0})
    assert summary["unrealized_pnl_usd"] == 5_000.0
    assert summary["total_equity_usd"] == 105_000.0

    # Sell 0.5 BTC @ 56,000 -> realized PnL = 0.5 * (56k - 50k) = +$3,000
    broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.SELL,
        order_type=PaperOrderType.MARKET,
        quantity=0.5,
        current_time_ns=2_000_000_000,
        current_bbo={"best_bid": 56_000.0, "best_ask": 56_000.0},
    )

    summary2 = broker.get_portfolio_summary({"BTC-USDT": 56_000.0})
    assert summary2["positions"]["BTC-USDT"]["quantity"] == 0.5
    assert summary2["positions"]["BTC-USDT"]["realized_pnl"] == 3_000.0
    assert summary2["total_equity_usd"] == 106_000.0
