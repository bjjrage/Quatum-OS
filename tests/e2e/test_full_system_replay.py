"""
End-to-End System Replay and Adversarial Stress Test Suite.

Validates the full quantitative trading loop:
Synthetic Point-in-Time Data
  -> Feature Engine & Event Detector
  -> Strategy Candidates (STR-001 Relative Value)
  -> Deterministic Policy / Regime Engine
  -> Evidence-Gated Portfolio Allocator
  -> Deterministic Risk Engine (Circuit Breakers, EventCluster, Leverage)
  -> Realistic Paper Broker (Queue, Latency, Slippage, Fees)
  -> Multi-Factor Performance Attribution Engine

Includes Adversarial Stress Scenarios:
1. Flash Crash / Drawdown circuit breaker halt.
2. Extreme spread blowout & liquidity drought.
3. Burst order rate limiter defense against rogue loops.
4. Live capital lockout enforcement.
"""

import pytest
from src.research import (
    SyntheticMarketGenerator,
    FeatureEngine,
    EventDetector,
)
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
)
from src.strategies.factory import SignalDirection
from src.strategies.str001_empirical import STR001RelativeValueAlpha
from src.regime.policy_engine import (
    DeterministicPolicyEngine,
    DomainMarketRegime,
    GlobalMacroRegime,
    StrategyRegimeState,
)
from src.portfolio.allocator import PortfolioAllocator
from src.risk.engine import (
    DeterministicRiskEngine,
    ProposedOrder,
    RiskLimits,
    RiskViolationCode,
)
from src.risk.event_cluster import EventCluster
from src.paper.broker import (
    PaperBroker,
    PaperOrderSide,
    PaperOrderType,
    PaperOrderStatus,
)
from src.attribution.engine import PerformanceAttributionEngine


def test_end_to_end_replay_pipeline():
    """Complete integrated pipeline run from synthetic ticks to attribution."""
    # 1. Market Data Generation
    generator = SyntheticMarketGenerator(seed=12345)
    ticks = generator.generate_bbo_series(
        symbol="BTCUSDT",
        initial_price=60_000.0,
        num_ticks=50,
        volatility_bps=5.0,
    )
    assert len(ticks) == 50

    prices = [t["ask_price"] for t in ticks]
    timestamps = [t["ts_exchange_ns"] for t in ticks]

    # 2. Features and Events
    spread_bps = FeatureEngine.calc_spread_bps(ticks[-1]["bid_price"], ticks[-1]["ask_price"])
    assert spread_bps > 0.0

    detector = EventDetector(vol_lookback_bars=10, impulse_threshold_z=1.5, min_return_bps=1.0)
    events = detector.detect_impulses(prices, timestamps, symbol="BTCUSDT")

    # 3. Policy / Regime Engine
    policy_engine = DeterministicPolicyEngine()
    current_regime = policy_engine.evaluate_regime(
        annualized_volatility=0.45,
        bid_ask_spread_bps=spread_bps,
        trend_30d_return=0.03,
        smile_arbitrage_free=True,
    )
    assert current_regime.capital_allocation_multiplier == 1.0

    # 4. Portfolio Allocator
    str001_spec = StrategySpec(
        strategy_id="STR-001",
        name="Polymarket Deribit Relative Value",
        family=StrategyFamily.RELATIVE_VALUE,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
        description="Relative value digital options",
        math_foundation_validated=True,
        economic_edge_validated=True,
    )
    allocator = PortfolioAllocator(total_equity_usd=100_000.0, live_capital_locked=True)
    budgets = allocator.allocate([str001_spec], regime=current_regime)
    allocated_usd = budgets["STR-001"].allocated_capital_usd
    assert allocated_usd > 0.0

    # 5. Risk Engine Setup
    risk_engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(
            max_drawdown_limit_pct=0.10,
            max_gross_leverage=2.0,
            max_single_position_pct=0.30,
            live_capital_locked=True,
        ),
    )
    btc_cluster = EventCluster(
        cluster_id="BTC_DIRECTIONAL",
        description="BTC exposure cluster",
        max_gross_exposure_usd=60_000.0,
        max_net_exposure_usd=60_000.0,
        stress_loss_limit_usd=20_000.0,
        member_weights={"BTC-USDT": 1.0},
    )
    risk_engine.register_event_cluster(btc_cluster)

    # 6. Strategy Signal Generation (STR-001)
    pipeline_str001 = STR001RelativeValueAlpha(min_edge_bps=100.0)
    market_data = {
        "symbol": "BTC-USDT",
        "polymarket_mid_price": 0.42,  # Underpriced vs RN ~0.49
        "deribit_forward_price": 60_000.0,
        "strike_price": 60_000.0,
        "time_to_expiry_years": 0.1,
        "implied_volatility": 0.55,
        "dsigma_dK": -0.000005,
    }
    signal = pipeline_str001.generate_signal(market_data, current_ts_ns=int(timestamps[-1]))
    assert signal is not None
    assert signal.strategy_id == "STR-001"
    assert signal.direction == SignalDirection.LONG

    # 7. Proposed Order Evaluation by Risk Engine
    latest_tick = ticks[-1]
    curr_price = float(latest_tick["ask_price"])
    target_qty = 0.2  # 0.2 BTC @ 60k = $12,000 <= $30,000 single cap

    proposed_order = ProposedOrder(
        order_id="ord-e2e-001",
        strategy_id=signal.strategy_id,
        symbol="BTC-USDT",
        side="BUY" if signal.direction == SignalDirection.LONG else "SELL",
        quantity=target_qty,
        price=curr_price,
        venue="BINANCE",
        timestamp_s=latest_tick["ts_exchange_ns"] / 1e9,
    )

    risk_decision = risk_engine.evaluate_order(proposed_order, is_live=False)
    assert risk_decision.approved is True

    # 8. Execution through Realistic Paper Broker
    paper_broker = PaperBroker(
        initial_cash_usd=100_000.0,
        simulated_latency_ms=10.0,
        taker_fee_bps=5.0,
        base_slippage_bps=2.0,
    )
    bbo = {
        "best_bid": float(latest_tick["bid_price"]),
        "best_ask": float(latest_tick["ask_price"]),
        "bid_size": float(latest_tick["bid_size"]),
        "ask_size": float(latest_tick["ask_size"]),
    }

    paper_order = paper_broker.submit_order(
        symbol=proposed_order.symbol,
        side=PaperOrderSide.BUY if proposed_order.side == "BUY" else PaperOrderSide.SELL,
        order_type=PaperOrderType.MARKET,
        quantity=proposed_order.quantity,
        venue=proposed_order.venue,
        current_time_ns=int(latest_tick["ts_exchange_ns"]),
        current_bbo=bbo,
        permit=risk_decision,
    )

    # Deliver order after transit latency
    paper_broker.on_market_event(
        symbol=proposed_order.symbol,
        best_bid=bbo["best_bid"],
        best_ask=bbo["best_ask"],
        event_time_ns=int(latest_tick["ts_exchange_ns"]) + paper_broker.latency_ns,
        ask_size=bbo["ask_size"],
        bid_size=bbo["bid_size"],
    )

    assert paper_order.status == PaperOrderStatus.FILLED
    assert paper_order.filled_price is not None
    assert paper_order.fee_paid > 0.0

    # 9. Performance Attribution
    attribution_engine = PerformanceAttributionEngine(benchmark_symbol="BTC-USDT")
    attribution_engine.record_trade(
        trade_id="trd-e2e-001",
        strategy_id=str001_spec.strategy_id,
        symbol=proposed_order.symbol,
        side=proposed_order.side,
        quantity=proposed_order.quantity,
        decision_price=curr_price,
        execution_price=paper_order.filled_price,
        fee_paid=paper_order.fee_paid,
        timestamp_ns=int(latest_tick["ts_exchange_ns"]),
    )

    attr = attribution_engine.compute_attribution(
        strategy_gross_pnls={"STR-001": 250.0},
        market_benchmark_return=0.02,
        strategy_betas={"STR-001": 0.4},
        average_capital_usd={"STR-001": allocated_usd},
    )

    assert "STR-001" in attr
    assert attr["STR-001"].total_fees_usd == paper_order.fee_paid
    assert attr["STR-001"].implementation_shortfall_usd > 0.0
    assert attr["STR-001"].alpha_pnl_usd != 0.0


def test_adversarial_flash_crash_circuit_breaker():
    """Adversarial Test 1: 40% flash crash triggers max drawdown circuit breaker."""
    risk_engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(max_drawdown_limit_pct=0.10),
    )

    # Initial position: 1.0 BTC @ 60,000
    risk_engine.update_portfolio_state(
        equity_usd=100_000.0,
        positions={"BTC-USDT": 1.0},
        mark_prices={"BTC-USDT": 60_000.0},
    )

    # Sudden flash crash: BTC drops to 36,000 (-40%), portfolio equity drops to 76,000 (24% drawdown)
    risk_engine.update_portfolio_state(
        equity_usd=76_000.0,
        positions={"BTC-USDT": 1.0},
        mark_prices={"BTC-USDT": 36_000.0},
    )
    assert risk_engine.current_drawdown_pct() == 0.24

    # Rogue attempt to buy more during crash (increase risk)
    rogue_buy = ProposedOrder(
        order_id="rogue-buy-dip",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.5,
        price=36_000.0,
    )
    dec_buy = risk_engine.evaluate_order(rogue_buy)
    assert dec_buy.approved is False
    assert dec_buy.violation_code == RiskViolationCode.MAX_DRAWDOWN_EXCEEDED

    # Legitimate de-risking order: Sell 1.0 BTC to cut losses -> Must be allowed!
    close_sell = ProposedOrder(
        order_id="close-position",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="SELL",
        quantity=1.0,
        price=36_000.0,
    )
    dec_sell = risk_engine.evaluate_order(close_sell)
    assert dec_sell.approved is True


def test_adversarial_spread_blowout_regime_shift():
    """Adversarial Test 2: Severe spread blowout & broken smile shuts down STR-001."""
    policy_engine = DeterministicPolicyEngine(
        stressed_vol_annualized_threshold=1.20,
        stressed_spread_bps_threshold=25.0,
    )

    regime = policy_engine.evaluate_regime(
        annualized_volatility=1.35,
        bid_ask_spread_bps=80.0,  # 80 bps blowout
        trend_30d_return=-0.12,
        smile_arbitrage_free=False,  # Deribit smile breached butterfly arbitrage
    )

    assert regime.domain_regime == DomainMarketRegime.STRESSED_ILLIQUID
    assert regime.global_macro == GlobalMacroRegime.RISK_OFF
    assert regime.capital_allocation_multiplier == 0.25
    assert regime.strategy_states["STR-001"] == StrategyRegimeState.HALTED


def test_adversarial_burst_order_injection():
    """Adversarial Test 3: Runaway strategy submits 30 orders in 100ms."""
    risk_engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(max_orders_per_window=10, rate_limit_window_seconds=1.0),
    )

    t0 = 10_000.0
    approved_count = 0
    rejected_count = 0

    for i in range(30):
        ord_burst = ProposedOrder(
            order_id=f"burst-{i}",
            strategy_id="STR-002",
            symbol="BTC-USDT",
            side="BUY",
            quantity=0.01,
            price=60_000.0,
            timestamp_s=t0 + (i * 0.003),  # every 3ms
        )
        dec = risk_engine.evaluate_order(ord_burst, current_time_s=ord_burst.timestamp_s)
        if dec.approved:
            approved_count += 1
        else:
            rejected_count += 1
            assert dec.violation_code == RiskViolationCode.BURST_RATE_LIMIT_EXCEEDED

    assert approved_count == 10
    assert rejected_count == 20


def test_adversarial_live_execution_lock_enforcement():
    """Adversarial Test 4: Live order execution unconditionally rejected while capital locked."""
    risk_engine = DeterministicRiskEngine(
        initial_equity_usd=100_000.0,
        limits=RiskLimits(live_capital_locked=True),
    )

    live_order = ProposedOrder(
        order_id="live-ord-001",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.1,
        price=60_000.0,
    )

    # Submitting with is_live=True
    dec = risk_engine.evaluate_order(live_order, is_live=True)
    assert dec.approved is False
    assert dec.violation_code == RiskViolationCode.CAPITAL_LOCKED
