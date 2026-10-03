"""Unit tests for Deterministic Risk Engine and EventCluster aggregation."""

import pytest
from src.risk.engine import (
    DeterministicRiskEngine,
    ProposedOrder,
    RiskLimits,
    RiskViolationCode,
)
from src.risk.event_cluster import EventCluster


def test_live_capital_strictly_locked():
    engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(live_capital_locked=True),
    )
    order = ProposedOrder(
        order_id="ord-001",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.1,
        price=60_000.0,
    )

    decision_paper = engine.evaluate_order(order, is_live=False)
    assert decision_paper.approved is True

    decision_live = engine.evaluate_order(order, is_live=True)
    assert decision_live.approved is False
    assert decision_live.violation_code == RiskViolationCode.CAPITAL_LOCKED


def test_kill_switch_veto_and_reset():
    engine = DeterministicRiskEngine(initial_equity_usd=100_000.0)
    order = ProposedOrder(
        order_id="ord-002",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.1,
        price=60_000.0,
    )

    engine.trigger_kill_switch("Market anomaly detected on Polymarket")
    decision = engine.evaluate_order(order, is_live=False)
    assert decision.approved is False
    assert decision.violation_code == RiskViolationCode.KILL_SWITCH_ACTIVE

    engine.reset_kill_switch()
    decision_after = engine.evaluate_order(order, is_live=False)
    assert decision_after.approved is True


def test_drawdown_circuit_breaker_allows_only_derisking():
    engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(max_drawdown_limit_pct=0.10),
    )
    # Peak is 100k, equity drops to 89k (11% drawdown > 10% limit)
    engine.update_portfolio_state(
        equity_usd=89_000.0,
        positions={"BTC-USDT": 1.0},
        mark_prices={"BTC-USDT": 60_000.0},
    )

    # Trying to buy more BTC (increase risk) -> REJECT
    buy_more = ProposedOrder(
        order_id="ord-buy",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.5,
        price=60_000.0,
    )
    dec_buy = engine.evaluate_order(buy_more)
    assert dec_buy.approved is False
    assert dec_buy.violation_code == RiskViolationCode.MAX_DRAWDOWN_EXCEEDED

    # Trying to open a new position ETH -> REJECT
    buy_new = ProposedOrder(
        order_id="ord-new",
        strategy_id="STR-001",
        symbol="ETH-USDT",
        side="BUY",
        quantity=1.0,
        price=3_000.0,
    )
    dec_new = engine.evaluate_order(buy_new)
    assert dec_new.approved is False
    assert dec_new.violation_code == RiskViolationCode.MAX_DRAWDOWN_EXCEEDED

    # Selling existing BTC (reducing risk) -> APPROVE
    sell_close = ProposedOrder(
        order_id="ord-sell",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="SELL",
        quantity=0.5,
        price=60_000.0,
    )
    dec_sell = engine.evaluate_order(sell_close)
    assert dec_sell.approved is True


def test_single_asset_concentration_cap():
    engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(max_single_position_pct=0.25),  # max $25,000 per asset
    )
    # 0.5 BTC @ $60,000 = $30,000 > $25,000
    big_order = ProposedOrder(
        order_id="ord-conc",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.5,
        price=60_000.0,
    )
    dec = engine.evaluate_order(big_order)
    assert dec.approved is False
    assert dec.violation_code == RiskViolationCode.SINGLE_ASSET_CONCENTRATION_EXCEEDED

    # 0.3 BTC @ $60,000 = $18,000 <= $25,000 -> APPROVE
    ok_order = ProposedOrder(
        order_id="ord-ok",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.3,
        price=60_000.0,
    )
    dec_ok = engine.evaluate_order(ok_order)
    assert dec_ok.approved is True


def test_gross_leverage_ceiling():
    engine = DeterministicRiskEngine(
        initial_equity_usd=50_000.0,
        limits=RiskLimits(max_gross_leverage=2.0, max_single_position_pct=1.0),  # max gross $100,000
    )
    # Existing position $80,000
    engine.update_portfolio_state(
        equity_usd=50_000.0,
        positions={"BTC-USDT": 1.0},
        mark_prices={"BTC-USDT": 80_000.0},
    )

    # Order adding $30,000 brings gross to $110,000 (leverage 2.2x > 2.0x) -> REJECT
    leverage_order = ProposedOrder(
        order_id="ord-lev",
        strategy_id="STR-001",
        symbol="ETH-USDT",
        side="BUY",
        quantity=10.0,
        price=3_000.0,
    )
    dec = engine.evaluate_order(leverage_order)
    assert dec.approved is False
    assert dec.violation_code == RiskViolationCode.GROSS_LEVERAGE_EXCEEDED


def test_event_cluster_limits():
    engine = DeterministicRiskEngine(initial_equity_usd=200_000.0)
    # Cluster for BTC ecosystem with gross limit $50k
    btc_cluster = EventCluster(
        cluster_id="BTC_ECOSYSTEM",
        description="Bitcoin exposure cluster",
        max_gross_exposure_usd=50_000.0,
        max_net_exposure_usd=50_000.0,
        stress_loss_limit_usd=15_000.0,
        stress_factor=0.30,
        member_weights={"BTC-USDT": 1.0, "WBTC-USDT": 1.0},
    )
    engine.register_event_cluster(btc_cluster)

    # Order 1: 0.5 BTC @ $60k = $30k -> ok
    ord1 = ProposedOrder(
        order_id="ord-c1",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.5,
        price=60_000.0,
    )
    dec1 = engine.evaluate_order(ord1)
    assert dec1.approved is True

    # Record position
    engine.update_portfolio_state(
        equity_usd=200_000.0,
        positions={"BTC-USDT": 0.5},
        mark_prices={"BTC-USDT": 60_000.0, "WBTC-USDT": 60_000.0},
    )

    # Order 2: 0.5 WBTC @ $60k = $30k -> cluster gross would be $60k > $50k limit -> REJECT
    ord2 = ProposedOrder(
        order_id="ord-c2",
        strategy_id="STR-001",
        symbol="WBTC-USDT",
        side="BUY",
        quantity=0.5,
        price=60_000.0,
    )
    dec2 = engine.evaluate_order(ord2)
    assert dec2.approved is False
    assert dec2.violation_code == RiskViolationCode.EVENT_CLUSTER_LIMIT_EXCEEDED


def test_burst_rate_limiter():
    engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(max_orders_per_window=3, rate_limit_window_seconds=1.0),
    )
    base_time = 1000.0

    for i in range(3):
        ord_i = ProposedOrder(
            order_id=f"burst-{i}",
            strategy_id="STR-001",
            symbol="BTC-USDT",
            side="BUY",
            quantity=0.01,
            price=60_000.0,
            timestamp_s=base_time + 0.1 * i,
        )
        dec = engine.evaluate_order(ord_i, current_time_s=ord_i.timestamp_s)
        assert dec.approved is True

    # 4th order within same window -> REJECT
    ord_overflow = ProposedOrder(
        order_id="burst-overflow",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.01,
        price=60_000.0,
        timestamp_s=base_time + 0.5,
    )
    dec_overflow = engine.evaluate_order(ord_overflow, current_time_s=ord_overflow.timestamp_s)
    assert dec_overflow.approved is False
    assert dec_overflow.violation_code == RiskViolationCode.BURST_RATE_LIMIT_EXCEEDED

    # Order after window expires -> APPROVE
    ord_future = ProposedOrder(
        order_id="burst-future",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.01,
        price=60_000.0,
        timestamp_s=base_time + 2.0,
    )
    dec_future = engine.evaluate_order(ord_future, current_time_s=ord_future.timestamp_s)
    assert dec_future.approved is True
