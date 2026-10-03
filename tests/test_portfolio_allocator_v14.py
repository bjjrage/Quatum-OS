"""Unit tests verifying OS Invariant: THE OS DOES NOT SELECT THE BEST BACKTEST."""

import pytest
from src.strategies.models import StrategySpec, StrategyStage, StrategyFamily, StrategyOrigin
from src.portfolio.allocator import PortfolioAllocator, AllocationAction, AllocationBudget


def test_os_does_not_select_best_backtest_winner_take_all():
    """Verify that a strategy with massive backtest Sharpe does not get winner-take-all allocation."""
    allocator = PortfolioAllocator(
        total_equity_usd=100_000.0,
        max_strategy_allocation_pct=0.40,
        live_capital_locked=True,
    )

    strat_high_sharpe = StrategySpec(
        strategy_id="STR-HIGH-SHARPE",
        name="Massive In-Sample Overfit",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.ML,
        stage=StrategyStage.ACTIVE,
        description="High Sharpe in backtest",
        trial_count=150,  # 150 trials run in registry
    )
    strat_modest_sharpe = StrategySpec(
        strategy_id="STR-MODEST-SHARPE",
        name="Modest Solid Edge",
        family=StrategyFamily.FUNDING_BASIS,
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.ACTIVE,
        description="Moderate Sharpe, few trials",
        trial_count=2,
    )

    metrics = {
        "STR-HIGH-SHARPE": {"sharpe": 4.5, "trial_count": 150, "edge_half_life_s": 25.0},
        "STR-MODEST-SHARPE": {"sharpe": 1.8, "trial_count": 2, "edge_half_life_s": 60.0},
    }

    budgets = allocator.allocate(
        strategies=[strat_high_sharpe, strat_modest_sharpe],
        strategy_metrics=metrics,
    )

    # Invariant: Neither strategy gets 100%
    b_high = budgets["STR-HIGH-SHARPE"]
    b_modest = budgets["STR-MODEST-SHARPE"]

    assert b_high.allocated_capital_usd > 0.0
    assert b_modest.allocated_capital_usd > 0.0

    # Invariant: Anti winner-take-all ceiling capped at 40% ($40,000)
    assert b_high.allocated_capital_usd <= 40_000.0
    assert b_modest.allocated_capital_usd <= 40_000.0

    # Invariant: High trial count receives severe estimation uncertainty discount
    assert b_high.uncertainty_discount < b_modest.uncertainty_discount

    # Both are live locked ($0.0 live risk)
    assert b_high.authorized_live_budget == 0.0
    assert b_modest.authorized_live_budget == 0.0


def test_capacity_and_latency_margin_constraints():
    """Verify capital sizing is constrained by liquidity depth and latency margins."""
    allocator = PortfolioAllocator(total_equity_usd=100_000.0, live_capital_locked=True)

    strat_illiquid = StrategySpec(
        strategy_id="STR-ILLIQUID",
        name="Microcap Alt Reversal",
        family=StrategyFamily.BEHAVIORAL,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
    )
    strat_fast_decay = StrategySpec(
        strategy_id="STR-FAST-DECAY",
        name="Near-Latency Race",
        family=StrategyFamily.STATISTICAL_ARBITRAGE,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
    )

    # STR-ILLIQUID: 5m volume is only $50,000 -> 1% capacity cap is $500
    # STR-FAST-DECAY: edge half-life is 7.0s -> close to 5s threshold -> discounted
    metrics = {
        "STR-ILLIQUID": {"avg_5m_volume_usd": 50_000.0, "edge_half_life_s": 30.0},
        "STR-FAST-DECAY": {"avg_5m_volume_usd": 5_000_000.0, "edge_half_life_s": 7.0},
    }

    budgets = allocator.allocate(
        strategies=[strat_illiquid, strat_fast_decay],
        strategy_metrics=metrics,
    )

    # Illiquid strategy capped at $500 capacity
    assert budgets["STR-ILLIQUID"].allocated_capital_usd <= 500.0
    assert budgets["STR-ILLIQUID"].capacity_cap_usd == 500.0

    # Fast decay strategy receives latency margin discount
    assert budgets["STR-FAST-DECAY"].latency_margin_discount < 1.0


def test_event_cluster_aggregate_exposure_cap():
    """Verify that multiple strategies on the same EventCluster do not breach cluster limits."""
    allocator = PortfolioAllocator(
        total_equity_usd=100_000.0,
        max_strategy_allocation_pct=0.40,
        max_cluster_allocation_pct=0.30,  # Max 30% ($30k) in any single cluster
        live_capital_locked=True,
    )

    s1 = StrategySpec(
        strategy_id="STR-BTC-1",
        name="BTC Momentum",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
    )
    s2 = StrategySpec(
        strategy_id="STR-BTC-2",
        name="BTC Basis",
        family=StrategyFamily.FUNDING_BASIS,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
    )

    event_clusters = {
        "STR-BTC-1": ["CRYPTO_SYSTEMIC_BTC"],
        "STR-BTC-2": ["CRYPTO_SYSTEMIC_BTC"],
    }

    budgets = allocator.allocate(
        strategies=[s1, s2],
        event_clusters=event_clusters,
    )

    # Combined allocation to CRYPTO_SYSTEMIC_BTC must not exceed $30,000 (30%)
    total_btc_cluster = budgets["STR-BTC-1"].allocated_capital_usd + budgets["STR-BTC-2"].allocated_capital_usd
    assert total_btc_cluster <= 30_001.0


def test_live_capital_locked_invariant_always_zero():
    """Verify strict invariant: authorized_live_budget is ALWAYS 0.0 when capital is locked."""
    allocator_locked = PortfolioAllocator(total_equity_usd=100_000.0, live_capital_locked=True)
    allocator_unlocked = PortfolioAllocator(total_equity_usd=100_000.0, live_capital_locked=False)

    strat = StrategySpec(
        strategy_id="STR-LIVE-TEST",
        name="Live Test Strat",
        family=StrategyFamily.RELATIVE_VALUE,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
    )

    budgets_locked = allocator_locked.allocate([strat])
    assert budgets_locked["STR-LIVE-TEST"].is_live_eligible is False
    assert budgets_locked["STR-LIVE-TEST"].authorized_live_budget == 0.0
    assert budgets_locked["STR-LIVE-TEST"].allocated_capital_usd > 0.0
    assert budgets_locked["STR-LIVE-TEST"].paper_budget_usd > 0.0

    budgets_unlocked = allocator_unlocked.allocate([strat])
    assert budgets_unlocked["STR-LIVE-TEST"].is_live_eligible is True
    assert budgets_unlocked["STR-LIVE-TEST"].authorized_live_budget > 0.0


def test_allocation_actions_governance():
    """Verify AllocationAction states (SCALE, REDUCE, PAUSE, KILL)."""
    allocator = PortfolioAllocator(total_equity_usd=100_000.0)

    s_active = StrategySpec(
        strategy_id="STR-ACT",
        name="Active Strat",
        family=StrategyFamily.MOMENTUM,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.ACTIVE,
    )
    s_reduced = StrategySpec(
        strategy_id="STR-RED",
        name="Reduced Strat",
        family=StrategyFamily.BEHAVIORAL,
        origin=StrategyOrigin.HUMAN,
        stage=StrategyStage.REDUCED,
    )
    s_paused = StrategySpec(
        strategy_id="STR-PAUSE",
        name="Paused Strat",
        family=StrategyFamily.STATISTICAL_ARBITRAGE,
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.PAUSED,
    )
    s_killed = StrategySpec(
        strategy_id="STR-KILL",
        name="Killed Strat",
        family=StrategyFamily.ON_CHAIN,
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.KILLED,
    )

    budgets = allocator.allocate([s_active, s_reduced, s_paused, s_killed])

    assert budgets["STR-ACT"].action == AllocationAction.SCALE
    assert budgets["STR-RED"].action == AllocationAction.REDUCE
    assert budgets["STR-PAUSE"].action == AllocationAction.PAUSE
    assert budgets["STR-KILL"].action == AllocationAction.KILL
