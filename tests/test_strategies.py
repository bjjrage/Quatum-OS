"""Unit tests for Strategy Domain and Registry with hardened governance invariants."""

import pytest
from src.strategies.models import (
    StrategyOrigin,
    StrategyStage,
    StrategyFamily,
    StrategySpec,
    CounterpartyThesis,
)
from src.strategies.registry import (
    StrategyRegistry,
    DuplicateStrategyError,
    StrategyNotFoundError,
    InvalidStageTransitionError,
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
    """Verify that all 11 lifecycle stages can be represented and transitioned step-by-step."""
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

    thesis = CounterpartyThesis(
        counterparty_type="Informed liquidity takers",
        economic_mechanism="Microstructure inventory imbalance",
        why_trade_now="Execution urgency",
        why_impact_may_be_transient="Inventory rebalancing",
        why_it_may_be_information="Macro news",
        observable_evidence=["Spread widening"],
        falsification_conditions=["Persistent adverse selection"],
    )
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-STAGE-01",
        name="Stage Pipeline Test",
        family="CUSTOM_TEST",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.IDEA,
        counterparty_thesis=thesis,
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
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        StrategySpec(
            strategy_id="STR-PRIV-01",
            name="Attempted Privileged Strategy",
            family="ARBITRAGE",
            origin=StrategyOrigin.HUMAN,
            is_privileged=True,
        )

    registry = create_default_registry()
    strategies = registry.list_all()
    assert len(strategies) == 2
    for s in strategies:
        assert s.is_privileged is False


def test_privilege_cannot_be_injected_via_mutation_or_copy():
    """HARDENING: Invariant 1 - Verify that StrategySpec cannot technically become privileged.

    Tests:
    1. Direct property assignment raises AttributeError.
    2. model_copy(update={'is_privileged': True}) raises ValueError.
    3. object.__setattr__ fails to override descriptor (spec.is_privileged remains False).
    4. Constructor rejects truthy is_privileged.
    """
    spec = StrategySpec(
        strategy_id="STR-HARDEN-01",
        name="Harden Test",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
    )
    assert spec.is_privileged is False

    # 1. Direct attribute mutation must be blocked by read-only property
    with pytest.raises(AttributeError):
        spec.is_privileged = True

    # 2. model_copy update injection must raise ValueError
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        spec.model_copy(update={"is_privileged": True})

    # 3. Descriptor priority prevents even object.__setattr__ from writing to property
    with pytest.raises(AttributeError, match="has no setter"):
        object.__setattr__(spec, "is_privileged", True)
    assert spec.is_privileged is False

    # 4. Constructor injection
    with pytest.raises(ValueError, match="No strategy may be marked privileged"):
        StrategySpec(
            strategy_id="STR-HARDEN-02",
            name="Harden Test 2",
            family="MOMENTUM",
            origin=StrategyOrigin.ML,
            is_privileged=True,
        )


def test_evidence_gated_lifecycle_transitions():
    """HARDENING: Invariant 2 - Verify that strategy lifecycle transitions enforce evidence gates.

    Allowed forward promotion:
      RESEARCH -> VALIDATION
      VALIDATION -> HOLDOUT
      HOLDOUT -> PAPER
      PAPER -> SMALL_LIVE
      SMALL_LIVE -> ACTIVE

    Illegal gate bypasses:
      RESEARCH -> ACTIVE (bypasses validation, holdout, paper, small_live)
      IDEA -> SMALL_LIVE (bypasses research, validation, holdout, paper)
      VALIDATION -> ACTIVE (bypasses holdout, paper, small_live)

    Operational reversibility:
      ACTIVE -> PAUSED
      PAUSED -> ACTIVE

    Kill / archive:
      RESEARCH -> KILLED
      KILLED -> ARCHIVED
      ARCHIVED -> anything (terminal, must be rejected)
    """
    thesis = CounterpartyThesis(
        counterparty_type="Informed liquidity takers",
        economic_mechanism="Microstructure inventory imbalance",
        why_trade_now="Execution urgency",
        why_impact_may_be_transient="Inventory rebalancing",
        why_it_may_be_information="Macro news",
        observable_evidence=["Spread widening"],
        falsification_conditions=["Persistent adverse selection"],
    )
    registry = StrategyRegistry()
    spec = StrategySpec(
        strategy_id="STR-GATE-01",
        name="Gate Test",
        family="RELATIVE_VALUE",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        counterparty_thesis=thesis,
    )
    registry.register(spec)

    # 1. Allowed forward sequence
    registry.update_stage("STR-GATE-01", StrategyStage.VALIDATION)
    assert registry.get("STR-GATE-01").stage == StrategyStage.VALIDATION

    registry.update_stage("STR-GATE-01", StrategyStage.HOLDOUT)
    assert registry.get("STR-GATE-01").stage == StrategyStage.HOLDOUT

    registry.update_stage("STR-GATE-01", StrategyStage.PAPER)
    assert registry.get("STR-GATE-01").stage == StrategyStage.PAPER

    registry.update_stage("STR-GATE-01", StrategyStage.SMALL_LIVE)
    assert registry.get("STR-GATE-01").stage == StrategyStage.SMALL_LIVE

    registry.update_stage("STR-GATE-01", StrategyStage.ACTIVE)
    assert registry.get("STR-GATE-01").stage == StrategyStage.ACTIVE

    # 2. Operational state toggles
    registry.update_stage("STR-GATE-01", StrategyStage.PAUSED)
    assert registry.get("STR-GATE-01").stage == StrategyStage.PAUSED

    registry.update_stage("STR-GATE-01", StrategyStage.ACTIVE)
    assert registry.get("STR-GATE-01").stage == StrategyStage.ACTIVE

    # 3. Illegal gate-skipping tests
    spec_research = StrategySpec(
        strategy_id="STR-GATE-JUMP-1",
        name="Jump 1",
        family="MOMENTUM",
        origin=StrategyOrigin.HUMAN,
        stage=StrategyStage.RESEARCH,
    )
    registry.register(spec_research)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-JUMP-1", StrategyStage.ACTIVE)

    spec_idea = StrategySpec(
        strategy_id="STR-GATE-JUMP-2",
        name="Jump 2",
        family="MOMENTUM",
        origin=StrategyOrigin.STATISTICAL,
        stage=StrategyStage.IDEA,
    )
    registry.register(spec_idea)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-JUMP-2", StrategyStage.SMALL_LIVE)

    spec_validation = StrategySpec(
        strategy_id="STR-GATE-JUMP-3",
        name="Jump 3",
        family="MOMENTUM",
        origin=StrategyOrigin.ML,
        stage=StrategyStage.VALIDATION,
    )
    registry.register(spec_validation)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-JUMP-3", StrategyStage.ACTIVE)

    # 4. Kill and terminal archive paths
    spec_kill = StrategySpec(
        strategy_id="STR-GATE-KILL",
        name="Kill Test",
        family="MOMENTUM",
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
    )
    registry.register(spec_kill)
    registry.update_stage("STR-GATE-KILL", StrategyStage.KILLED)
    assert registry.get("STR-GATE-KILL").stage == StrategyStage.KILLED

    registry.update_stage("STR-GATE-KILL", StrategyStage.ARCHIVED)
    assert registry.get("STR-GATE-KILL").stage == StrategyStage.ARCHIVED

    # ARCHIVED is terminal: any outbound transition must fail
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-KILL", StrategyStage.RESEARCH)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-KILL", StrategyStage.ACTIVE)
    with pytest.raises(InvalidStageTransitionError):
        registry.update_stage("STR-GATE-KILL", StrategyStage.IDEA)


def test_str_002_thesis_and_dimensions_preserved():
    """HARDENING: Invariant 3 - Verify STR-002 thesis preserves original behavioral overshoot hypothesis.

    Verifies that:
    1. Thesis is defined as extreme price impulses normalized by prior volatility.
    2. Orderbook information is documented as a feature, not the definition.
    3. Informative move vs Forced liquidity move distinction is formally documented.
    """
    spec = get_seed_str_002()

    expected_thesis = (
        "Extreme short-horizon price impulses, normalized by prior volatility, "
        "may exhibit an exploitable overshoot followed by retracement."
    )
    assert expected_thesis in spec.description
    assert spec.metadata["thesis"] == expected_thesis

    # Check move types
    assert "informative_move" in spec.metadata["move_types"]
    assert "forced_liquidity_move" in spec.metadata["move_types"]

    # Check research dimensions
    dimensions = spec.metadata["research_dimensions"]
    assert "impulse_magnitude" in dimensions
    assert "prior_realized_volatility" in dimensions
    assert "forward_return" in dimensions
    assert "retracement_ratio" in dimensions
    assert "mfe" in dimensions
    assert "mae" in dimensions
    assert "time_to_retracement" in dimensions
    assert "forced_liquidations" in dimensions

    # Verify feature note
    assert "Orderbook information is an evaluation feature" in spec.metadata["feature_notes"]


def test_registry_has_no_execution_authority():
    """Verify non-negotiable governance: StrategyRegistry has strictly zero execution authority."""
    registry = StrategyRegistry()
    assert registry.has_execution_authority() is False

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
