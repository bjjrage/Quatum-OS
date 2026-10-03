"""Unit tests for Realistic Paper Broker simulation."""

import pytest
from src.paper.broker import (
    PaperBroker,
    PaperOrderSide,
    PaperOrderStatus,
    PaperOrderType,
)


def test_zero_latency_immediate_market_fill():
    """With zero latency, market orders fill immediately against provided BBO."""
    broker = PaperBroker(
        initial_cash_usd=100_000.0,
        simulated_latency_ms=0.0,
        taker_fee_bps=5.0,  # 0.05%
        base_slippage_bps=2.0,  # 0.02%
        enforce_risk_permit=False,
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


def test_delayed_market_order_fills_against_post_latency_market_state():
    """
    CRITICAL REQUIREMENT (v1.4.1 Section 20):
    A market order submitted at T0 with latency must NOT fill using the BBO observed at T0.
    It must evaluate against post-latency market state at T >= T0 + latency.
    """
    latency_ms = 20.0
    latency_ns = int(latency_ms * 1_000_000)
    broker = PaperBroker(
        initial_cash_usd=100_000.0,
        simulated_latency_ms=latency_ms,
        taker_fee_bps=5.0,
        base_slippage_bps=2.0,
        enforce_risk_permit=False,
    )

    t0 = 1_000_000_000
    stale_bbo = {"best_bid": 60_000.0, "best_ask": 60_010.0, "bid_size": 5.0, "ask_size": 5.0}

    # Order submitted at T0
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=1.0,
        current_time_ns=t0,
        current_bbo=stale_bbo,
    )

    # Must NOT be filled immediately with stale BBO!
    assert order.status == PaperOrderStatus.SUBMITTED
    assert order.filled_qty == 0.0
    assert len(broker.trades) == 0

    # Event arrives at T0 + 10ms (latency not yet elapsed) -> must NOT fill
    trades_early = broker.on_market_event(
        symbol="BTC-USDT",
        best_bid=60_020.0,
        best_ask=60_030.0,
        event_time_ns=t0 + (latency_ns // 2),
        ask_size=5.0,
        bid_size=5.0,
    )
    assert len(trades_early) == 0
    assert order.status == PaperOrderStatus.SUBMITTED

    # Event arrives at T0 + 25ms (latency elapsed) with MOVED market price (ask = 60,050)
    post_latency_ask = 60_050.0
    trades_fill = broker.on_market_event(
        symbol="BTC-USDT",
        best_bid=60_040.0,
        best_ask=post_latency_ask,
        event_time_ns=t0 + latency_ns + 5_000_000,
        ask_size=5.0,
        bid_size=5.0,
    )

    assert len(trades_fill) == 1
    assert order.status == PaperOrderStatus.FILLED
    # Must fill against the post-latency ask 60,050 (with slippage), NOT stale 60,010!
    assert order.filled_price >= post_latency_ask
    assert trades_fill[0].is_taker is True
    assert order.fee_paid > 0.0


def test_marketable_limit_classified_as_taker():
    """A limit order crossing the spread must be classified as a taker order and charged taker fees."""
    broker = PaperBroker(
        initial_cash_usd=100_000.0,
        simulated_latency_ms=0.0,
        maker_fee_bps=1.0,  # 0.01%
        taker_fee_bps=5.0,  # 0.05%
        enforce_risk_permit=False,
    )
    bbo = {"best_bid": 60_000.0, "best_ask": 60_010.0, "bid_size": 5.0, "ask_size": 5.0}

    # BUY limit with price 60,015 >= best_ask 60,010 -> crosses book
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=1.0,
        limit_price=60_015.0,
        current_time_ns=1_000_000_000,
        current_bbo=bbo,
    )

    assert order.status == PaperOrderStatus.FILLED
    assert order.is_taker is True
    # Fee paid must reflect taker fee (5 bps), not maker fee (1 bp)
    expected_approx_fee = 1.0 * order.filled_price * (5.0 / 10_000.0)
    assert pytest.approx(order.fee_paid, rel=1e-3) == expected_approx_fee


def test_partial_fill_and_depth_exhaustion():
    """Orders larger than available book depth must fill partially."""
    broker = PaperBroker(
        initial_cash_usd=200_000.0,
        simulated_latency_ms=0.0,
        taker_fee_bps=5.0,
        base_slippage_bps=2.0,
        enforce_risk_permit=False,
    )

    bbo = {"best_bid": 60_000.0, "best_ask": 60_010.0, "bid_size": 5.0, "ask_size": 1.5}

    # Want 3.0 BTC, but available depth at ask is only 1.5 BTC
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=3.0,
        current_time_ns=1_000_000_000,
        current_bbo=bbo,
    )

    assert order.status == PaperOrderStatus.PARTIALLY_FILLED
    assert order.filled_qty == 1.5

    # Subsequent market event brings more liquidity
    trades2 = broker.on_market_event(
        symbol="BTC-USDT",
        best_bid=60_015.0,
        best_ask=60_020.0,
        event_time_ns=1_050_000_000,
        ask_size=2.0,
        bid_size=2.0,
    )

    assert len(trades2) == 1
    assert order.status == PaperOrderStatus.FILLED
    assert order.filled_qty == 3.0


def test_limit_order_queue_and_fill():
    broker = PaperBroker(
        initial_cash_usd=50_000.0,
        simulated_latency_ms=20.0,
        maker_fee_bps=1.0,  # 0.01%
        enforce_risk_permit=False,
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


def test_order_cancellation_and_replace():
    broker = PaperBroker(initial_cash_usd=100_000.0, simulated_latency_ms=10.0, enforce_risk_permit=False)
    t0 = 1_000_000_000
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.LIMIT,
        quantity=1.0,
        limit_price=50_000.0,
        current_time_ns=t0,
    )
    assert order.status == PaperOrderStatus.SUBMITTED

    # Replace order
    t1 = t0 + 5_000_000
    new_order = broker.replace_order(
        order_id=order.order_id,
        new_quantity=2.0,
        new_limit_price=50_500.0,
        current_time_ns=t1,
    )
    assert order.status == PaperOrderStatus.CANCELLED
    assert new_order.status == PaperOrderStatus.SUBMITTED
    assert new_order.quantity == 2.0
    assert new_order.limit_price == 50_500.0
    assert new_order.available_at_ns == t1 + broker.latency_ns


def test_realized_and_unrealized_pnl():
    broker = PaperBroker(
        initial_cash_usd=100_000.0,
        simulated_latency_ms=0.0,
        maker_fee_bps=0.0,
        taker_fee_bps=0.0,
        base_slippage_bps=0.0,
        enforce_risk_permit=False,
    )

    # Buy 1 BTC @ 50,000
    broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=1.0,
        current_time_ns=1_000_000_000,
        current_bbo={"best_bid": 50_000.0, "best_ask": 50_000.0, "ask_size": 10.0, "bid_size": 10.0},
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
        current_bbo={"best_bid": 56_000.0, "best_ask": 56_000.0, "ask_size": 10.0, "bid_size": 10.0},
    )

    summary2 = broker.get_portfolio_summary({"BTC-USDT": 56_000.0})
    assert summary2["positions"]["BTC-USDT"]["quantity"] == 0.5
    assert summary2["positions"]["BTC-USDT"]["realized_pnl"] == 3_000.0
    assert summary2["total_equity_usd"] == 106_000.0


def test_paper_broker_blocks_direct_order_without_risk_permit():
    """Default PaperBroker must strictly reject any order submitted without valid risk permit."""
    broker = PaperBroker()  # Default enforce_risk_permit=True
    with pytest.raises(PermissionError, match="Pre-trade Risk permit is mandatory"):
        broker.submit_order(
            symbol="BTC-USDT",
            side=PaperOrderSide.BUY,
            order_type=PaperOrderType.MARKET,
            quantity=0.1,
            current_bbo={"best_bid": 60_000.0, "best_ask": 60_010.0},
        )


def test_paper_broker_accepts_valid_permit():
    """PaperBroker accepts order when valid approved permit is provided."""
    from tests.helpers.auth import create_test_signer_and_verifier, issue_permit
    from src.execution_plane.models import ExecutionMode

    signer, verifier = create_test_signer_and_verifier()
    broker = PaperBroker(simulated_latency_ms=0.0, verifier=verifier)
    permit = issue_permit(
        kind="SUBMIT",
        venue="paper",
        client_order_id="test_ord_1",
        symbol="BTC-USDT",
        mode=ExecutionMode.PAPER,
        authorized_live_capital_usd=0.0,
        risk_approved=True,
        issued_ns=1_000_000_000,
        signer=signer,
    )
    bbo = {"best_bid": 60_000.0, "best_ask": 60_010.0, "bid_size": 5.0, "ask_size": 5.0}
    order = broker.submit_order(
        symbol="BTC-USDT",
        side=PaperOrderSide.BUY,
        order_type=PaperOrderType.MARKET,
        quantity=0.1,
        current_bbo=bbo,
        permit=permit,
    )
    assert order.status == PaperOrderStatus.FILLED
