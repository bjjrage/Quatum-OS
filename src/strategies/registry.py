"""Strategy Registry: central inventory and lifecycle state tracker for candidate strategies.

Core Governance Rules:
1. NO STRATEGY IS PRIVILEGED BY ORIGIN.
2. The Strategy Registry is purely declarative: it has ZERO execution authority.
3. Duplicate strategy IDs are strictly rejected.
"""

from typing import Dict, List, Optional
from src.strategies.models import (
    StrategySpec,
    StrategyStage,
    StrategyOrigin,
    StrategyFamily,
)


class DuplicateStrategyError(Exception):
    """Raised when registering a strategy ID that already exists."""
    pass


class StrategyNotFoundError(Exception):
    """Raised when querying a strategy ID that does not exist."""
    pass


class StrategyRegistry:
    """In-memory declarative registry of all strategy candidates across lifecycle stages."""

    def __init__(self) -> None:
        self._strategies: Dict[str, StrategySpec] = {}

    def register(self, spec: StrategySpec) -> None:
        """Register a new strategy specification.
        
        Args:
            spec: Validated StrategySpec
            
        Raises:
            DuplicateStrategyError: If a strategy with the same ID already exists.
        """
        if spec.strategy_id in self._strategies:
            raise DuplicateStrategyError(
                f"Strategy with ID '{spec.strategy_id}' is already registered."
            )
        self._strategies[spec.strategy_id] = spec

    def get(self, strategy_id: str) -> StrategySpec:
        """Retrieve a strategy specification by ID."""
        if strategy_id not in self._strategies:
            raise StrategyNotFoundError(f"Strategy '{strategy_id}' not found in registry.")
        return self._strategies[strategy_id]

    def list_all(self) -> List[StrategySpec]:
        """Return all registered strategy specifications in registration order."""
        return list(self._strategies.values())

    def list_by_stage(self, stage: StrategyStage) -> List[StrategySpec]:
        """Filter strategies by lifecycle stage."""
        return [s for s in self._strategies.values() if s.stage == stage]

    def list_by_family(self, family: str) -> List[StrategySpec]:
        """Filter strategies by family name."""
        return [s for s in self._strategies.values() if s.family == family]

    def list_by_origin(self, origin: StrategyOrigin) -> List[StrategySpec]:
        """Filter strategies by origin."""
        return [s for s in self._strategies.values() if s.origin == origin]

    def update_stage(self, strategy_id: str, new_stage: StrategyStage) -> None:
        """Update the lifecycle stage of a registered strategy."""
        spec = self.get(strategy_id)
        updated = spec.model_copy(update={"stage": new_stage})
        self._strategies[strategy_id] = updated

    @staticmethod
    def has_execution_authority() -> bool:
        """Non-negotiable architectural invariant:
        The Strategy Registry is purely metadata and inventory.
        It has ZERO execution authority, cannot place orders, and cannot touch capital.
        """
        return False


def get_seed_str_001() -> StrategySpec:
    """Return standard specification for Seed Research Program STR-001."""
    return StrategySpec(
        strategy_id="STR-001",
        name="Polymarket x Deribit Relative Value",
        family=StrategyFamily.RELATIVE_VALUE.value,
        origin=StrategyOrigin.QUANT,
        stage=StrategyStage.RESEARCH,
        description="Cross-market relative value between Polymarket binary contracts and Deribit options.",
        math_foundation_validated=True,
        economic_edge_validated=False,
        is_privileged=False,
        metadata={"seed_program": "Line A", "reference_market": "BTC/ETH"},
    )


def get_seed_str_002() -> StrategySpec:
    """Return standard specification for Seed Research Program STR-002."""
    return StrategySpec(
        strategy_id="STR-002",
        name="Impulse / Overshoot / Short-Horizon Retracement",
        family=StrategyFamily.BEHAVIORAL.value,
        origin=StrategyOrigin.HUMAN,
        stage=StrategyStage.RESEARCH,
        description="Microstructure overshoot and mean-reversion following high-velocity orderbook imbalances.",
        math_foundation_validated=False,
        economic_edge_validated=False,
        is_privileged=False,
        metadata={"seed_program": "Line B", "reference_market": "Binance USD(S)-M"},
    )


def create_default_registry() -> StrategyRegistry:
    """Factory creating a StrategyRegistry populated with the initial seed research programs."""
    registry = StrategyRegistry()
    registry.register(get_seed_str_001())
    registry.register(get_seed_str_002())
    return registry
