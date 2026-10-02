"""Unit tests for Strategy Domain and Registry."""

import pytest
from src.strategies.models import (
    StrategyOrigin,
    StrategyStage,
    StrategyFamily,
    StrategySpec,
)
from src.strategies.registry import (
    StrategyRegistry,
    DuplicateStrategyError,
    StrategyNotFoundError,
    get_seed_str_001,
    get_seed_str_002,
    create_default_registry,
)


def test_register_valid_strategy():
    """Verify registration and retrieval of a valid strategy specification."""
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-TEST-01",
        name="StatArb Pairs",
        family=StrategyFamily.STATISTICAL_ARBITRAGE.value,
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.IDEA,
        description="Cointegration-based pairs trading on perpetual futures.",
    )
    registry.register(spec)
    retrieved = registry.get("STR-TEST-01")
    assert retrieved.strategy_id == "STR-TEST-01"
    assert retrieved.name == "StatArb Pairs"
    assert retrieved.family == StrategyFamily.STATISTICAL_ARBITRAGE.value
    assert retrieved.origin == StrategyOrigin.STATISTICAL
    assert retrieved.stage == StrategyStage.IDEA


def test_reject_duplicate_strategy_id():
    """Verify that registering an existing strategy ID raises DuplicateStrategyError."""
    registry = StrategyRegistry()
    spec1 = StrategySpec(
        strategy_id="STR-DUP-01",
        name="First Strategy",
        family=StrategyFamily.MOMENTUM.value,
        origin=StrategyOrigin.QUANT,
    )
    spec2 = StrategySpec(
        strategy_id="STR-DUP-01",
        name="Duplicate Strategy",
        family=StrategyFamily.MEAN_REVERSION.value,
        origin=StrategyOrigin.ML,
    )
    registry.register(spec1)
    with pytest.raises(DuplicateStrategyError, match="STR-DUP-01"):
        registry.register(spec2)


def test_represent_all_lifecycle_stages():
    """Verify that all 11 lifecycle stages can be represented and transitioned."""
    expected_stages = [
        StrategyStage.IDEA,
        StrategyStage.RESEARCH,
        StrategyStage.VALIDATION,
        StrategyStage.HOLDOUT,
        StrategyStage.PAPER,
        StrategyStage.SMALL_LIVE,
        StrategyStage.ACTIVE,
        StrategyStage.REDUCED,
        StrategyStage.PAUSED,
        StrategyStage.KILLED,
        StrategyStage.ARCHIVED,
    ]
    assert len(expected_stages) == 11
    
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-STAGE-01",
        name="Stage Pipeline Test",
        family=StrategyFamily.QUANT.value if hasattr(StrategyFamily, "QUANT") else "CUSTOM_TEST",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.IDEA,
    )
    registry.register(spec)
    
    for stage in expected_stages:
        registry.update_stage("STR-STAGE-01", stage)
        assert registry.get("STR-STAGE-01").stage == stage


def test_represent_all_strategy_origins():
    """Verify that all 5 strategy origins can be represented without restriction."""
    expected_origins = [
        StrategyOrigin.HUMAN,
        StrategyOrigin.QUANT,
        StrategyOrigin.STATISTICAL,
        StrategyOrigin.ML,
        StrategyOrigin.AI_RESEARCH,
    ]
    assert len(expected_origins) == 5
    
    registry = StrategyRegistry()
    for origin in expected_origins:
        s_id = f"STR-ORIGIN-{origin.value}"
        spec = StrategySpec(
            strategy_id=s_id,
            name=f"Strategy from {origin.value}",
            family=StrategyFamily.CROSS_MARKET.value,
            origin=origin,
            stage=StrategyStage.RESEARCH,
        )
        registry.register(spec)
        assert registry.get(s_id).origin == origin


def test_register_arbitrary_future_strategy_family():
    """Verify that arbitrary un-enumerated strategy families can be registered dynamically."""
    registry = StrategyRegistry()
    custom_families = [
        "LLM_SENTIMENT_BREAKOUT",
        "CROSS_CHAIN_BRIDGE_ARBITRAGE",
        "MEV_AUCTION_RECOVERY",
        "LIQUID_STAKING_BASIS",
    ]
    for fam in custom_families:
        s_id = f"STR-{fam[:10]}"
        spec = StrategySpec(
            strategy_id=s_id,
            name=f"Custom Family {fam}",
            family=fam,
            origin=StrategyOrigin.AI_RESEARCH,
            stage=StrategyStage.IDEA,
        )
        registry.register(spec)
        assert registry.get(s_id).family == fam


def test_str_001_behaves_like_normal_registry_entry():
    """Verify STR-001 (Seed Line A) is an ordinary, non-privileged registry entry."""
    spec = get_seed_str_001()
    assert spec.strategy_id == "STR-001"
    assert spec.name == "Polymarket x Deribit Relative Value"
    assert spec.origin == StrategyOrigin.QUANT
    assert spec.stage == StrategyStage.RESEARCH
    assert spec.math_foundation_validated is True
    assert spec.economic_edge_validated is False
    assert spec.is_privileged is False

    registry = StrategyRegistry()
    registry.register(spec)
    assert registry.get("STR-001") == spec


def test_str_002_behaves_like_normal_registry_entry():
    """Verify STR-002 (Seed Line B) is an ordinary, non-privileged registry entry."""
    spec = get_seed_str_002()
    assert spec.strategy_id == "STR-002"
    assert spec.name == "Impulse / Overshoot / Short-Horizon Retracement"
    assert spec.origin == StrategyOrigin.HUMAN
    assert spec.stage == StrategyStage.RESEARCH
    assert spec.math_foundation_validated is False
    assert spec.economic_edge_validated is False
    assert spec.is_privileged is False

    registry = StrategyRegistry()
    registry.register(spec)
    assert registry.get("STR-002") == spec


def test_origin_creates_no_privileged_behavior():
    """Verify that no strategy origin confers special privileges, and attempting to privilege any fails."""
    # Attempting to set is_privileged=True must raise ValueError
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        StrategySpec(
            strategy_id="STR-PRIV-01",
            name="Attempted Privileged Strategy",
            family="ARBITRAGE",
            origin=StrategyOrigin.HUMAN,
            is_privileged=True,
        )

    # Human, Quant, ML all have identical structure and permissions
    registry = create_default_registry()
    strategies = registry.list_all()
    assert len(strategies) == 2
    for s in strategies:
        assert s.is_privileged is False


def test_registry_has_no_execution_authority():
    """Verify non-negotiable governance: StrategyRegistry has strictly zero execution authority."""
    registry = StrategyRegistry()
    assert registry.has_execution_authority() is False
    
    # Assert registry does not have order placement or trading execution methods
    forbidden_methods = [
        "execute_trade",
        "place_order",
        "submit_order",
        "allocate_capital",
        "connect_broker",
    ]
    for method in forbidden_methods:
        assert not hasattr(registry, method), f"Registry illegally exposes '{method}'!"


def test_strategy_not_found_raises():
    """Verify StrategyNotFoundError on missing strategy."""
    registry = StrategyRegistry()
    with pytest.raises(StrategyNotFoundError):
        registry.get("STR-NONEXISTENT")
