"""Unit tests for Policy Engine, Portfolio Allocator, and Attribution Engine."""

import pytest
from src.regime.policy_engine import (
    DeterministicPolicyEngine,
    DomainMarketRegime,
    GlobalMacroRegime,
    StrategyRegimeState,
)
from src.portfolio.allocator import PortfolioAllocator
from src.attribution.engine import PerformanceAttributionEngine
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
)


def test_regime_classification_and_ai_metadata_isolation():
    engine = DeterministicPolicyEngine(
        high_vol_annualized_threshold=0.80,
        stressed_vol_annualized_threshold=1.20,
        stressed_spread_bps_threshold=25.0,
    )

    # 1. Normal vol, low spread, upward trend
    state_normal = engine.evaluate_regime(
        annualized_volatility=0.45,
        bid_ask_spread_bps=5.0,
        trend_30d_return=0.10,
        smile_arbitrage_free=True,
        ai_advisory_label="AI says: market is euphoric, go 10x long!",
    )
    assert state_normal.global_macro == GlobalMacroRegime.RISK_ON
    assert state_normal.domain_regime == DomainMarketRegime.NORMAL_VOL
    assert state_normal.capital_allocation_multiplier == 1.0
    assert state_normal.strategy_states["STR-001"] == StrategyRegimeState.ACTIVE
    # AI advisory is preserved as passive commentary but didn't grant extra leverage
    assert state_normal.ai_commentary == "AI says: market is euphoric, go 10x long!"

    # 2. Stressed illiquid regime
    state_stressed = engine.evaluate_regime(
        annualized_volatility=1.40,
        bid_ask_spread_bps=35.0,
        trend_30d_return=-0.15,
        smile_arbitrage_free=True,
    )
    assert state_stressed.global_macro == GlobalMacroRegime.RISK_OFF
    assert state_stressed.domain_regime == DomainMarketRegime.STRESSED_ILLIQUID
    assert state_stressed.capital_allocation_multiplier == 0.25

    # 3. Smile arbitrage breach halts STR-001
    state_arb_fail = engine.evaluate_regime(
        annualized_volatility=0.50,
        bid_ask_spread_bps=5.0,
        trend_30d_return=0.0,
        smile_arbitrage_free=False,
    )
    assert state_arb_fail.strategy_states["STR-001"] == StrategyRegimeState.HALTED


def test_evidence_gated_portfolio_allocator():
    allocator = PortfolioAllocator(
        total_equity_usd=100_000.0,
        max_strategy_allocation_pct=0.40,
        small_live_absolute_cap_usd=5_000.0,
        live_capital_locked=True,
    )

    s_idea = StrategySpec(
        strategy_id="STR-IDEA",
        name="Idea Strat",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.HUMAN,
        stage=StrategyStage.IDEA,
        description="Idea test",
    )
    s_paper = StrategySpec(
        strategy_id="STR-PAPER",
        name="Paper Strat",
        family=StrategyFamily.RELATIVE_VALUE,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.PAPER,
        description="Paper test",
    )
    s_small = StrategySpec(
        strategy_id="STR-SMALL",
        name="Small Live Strat",
        family=StrategyFamily.FUNDING_BASIS,
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.SMALL_LIVE,
        description="Small live test",
        math_foundation_validated=True,
        economic_edge_validated=True,
    )
    s_active1 = StrategySpec(
        strategy_id="STR-ACT-1",
        name="Active Strat 1",
        family=StrategyFamily.RELATIVE_VALUE,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
        description="Active 1 test",
        math_foundation_validated=True,
        economic_edge_validated=True,
    )
    s_active2 = StrategySpec(
        strategy_id="STR-ACT-2",
        name="Active Strat 2",
        family=StrategyFamily.EVENT_NEWS,
        origin=StrategyOrigin.ML,
        stage=StrategyStage.ACTIVE,
        description="Active 2 test",
        math_foundation_validated=True,
        economic_edge_validated=True,
    )

    budgets = allocator.allocate([s_idea, s_paper, s_small, s_active1, s_active2])

    # Zero capital invariants
    assert budgets["STR-IDEA"].allocated_capital_usd == 0.0
    assert budgets["STR-PAPER"].allocated_capital_usd == 0.0

    # Small live capped at $5k
    assert budgets["STR-SMALL"].allocated_capital_usd == 5_000.0

    # Active strategies receive risk-budgeted allocations, capped at 40% ($40,000)
    assert budgets["STR-ACT-1"].allocated_capital_usd <= 40_000.0
    assert budgets["STR-ACT-2"].allocated_capital_usd <= 40_000.0
    assert budgets["STR-ACT-1"].allocated_capital_usd > 0.0

    # Total allocated capital <= total equity
    total_allocated = sum(b.allocated_capital_usd for b in budgets.values())
    assert total_allocated <= 100_000.0

    # Live eligible invariant: because live_capital_locked=True, is_live_eligible is False
    assert budgets["STR-ACT-1"].is_live_eligible is False


def test_performance_attribution_alpha_beta_decomposition():
    attr_engine = PerformanceAttributionEngine(benchmark_symbol="BTC-USDT")

    # Record trade 1: Buy BTC at 60,010 (decision price 60,000, fee 3.0)
    attr_engine.record_trade(
        trade_id="t1",
        strategy_id="STR-001",
        symbol="BTC-USDT",
        side="BUY",
        quantity=0.1,
        decision_price=60_000.0,
        execution_price=60_010.0,
        fee_paid=3.0,
        timestamp_ns=1_000_000_000,
    )

    # Compute attribution: gross PnL = $500, benchmark return = +5%, strategy beta = 0.5, capital = $10,000
    res = attr_engine.compute_attribution(
        strategy_gross_pnls={"STR-001": 500.0},
        market_benchmark_return=0.05,
        strategy_betas={"STR-001": 0.5},
        average_capital_usd={"STR-001": 10_000.0},
    )

    strat_attr = res["STR-001"]
    assert strat_attr.trade_count == 1
    assert strat_attr.gross_pnl_usd == 500.0
    assert strat_attr.total_fees_usd == 3.0
    # Slippage: (60,010 - 60,000) * 0.1 = $1.0
    assert strat_attr.total_slippage_usd == 1.0
    assert strat_attr.implementation_shortfall_usd == 1.0
    # Net PnL = 500 - 3 - 1 = 496.0
    assert strat_attr.net_pnl_usd == 496.0

    # Beta PnL = 0.5 * 0.05 * 10,000 = $250.0
    assert strat_attr.beta_pnl_usd == 250.0
    # Alpha PnL = 496 - 250 = $246.0
    assert strat_attr.alpha_pnl_usd == 246.0
    assert strat_attr.win_rate_pct == 100.0
