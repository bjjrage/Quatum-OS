"""Strategy domain models and lifecycle specifications for Trading / Quant OS.

Core Governance Rule:
NO STRATEGY IS PRIVILEGED BY ORIGIN.
Human hypotheses, quantitative research, statistical discovery, ML-discovered signals
and AI-assisted research hypotheses must compete under the exact same evidence gates.
Origin is metadata. Origin is NOT evidence.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class StrategyOrigin(str, Enum):
    """Origin of a strategy candidate. Metadata only - confers zero privilege."""
    HUMAN = "HUMAN"
    QUANT = "QUANT"
    STATISTICAL = "STATISTICAL"
    ML = "ML"
    AI_RESEARCH = "AI_RESEARCH"


class StrategyStage(str, Enum):
    """Lifecycle stages through evidence-gated promotion pipeline."""
    IDEA = "IDEA"
    RESEARCH = "RESEARCH"
    VALIDATION = "VALIDATION"
    HOLDOUT = "HOLDOUT"
    PAPER = "PAPER"
    SMALL_LIVE = "SMALL_LIVE"
    ACTIVE = "ACTIVE"
    REDUCED = "REDUCED"
    PAUSED = "PAUSED"
    KILLED = "KILLED"
    ARCHIVED = "ARCHIVED"


class StrategyFamily(str, Enum):
    """Core recognized strategy families. Arbitrary custom families are also supported."""
    RELATIVE_VALUE = "RELATIVE_VALUE"
    CROSS_MARKET = "CROSS_MARKET"
    FUNDING_BASIS = "FUNDING_BASIS"
    STATISTICAL_ARBITRAGE = "STATISTICAL_ARBITRAGE"
    CROSS_ASSET = "CROSS_ASSET"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    BEHAVIORAL = "BEHAVIORAL"
    VOLATILITY = "VOLATILITY"
    OPTIONS = "OPTIONS"
    EVENT_NEWS = "EVENT_NEWS"
    LIQUIDITY_MICROSTRUCTURE = "LIQUIDITY_MICROSTRUCTURE"
    MARKET_MAKING = "MARKET_MAKING"
    ML_ALPHA = "ML_ALPHA"
    REGIME_SPECIFIC = "REGIME_SPECIFIC"
    PREDICTION_MARKETS = "PREDICTION_MARKETS"
    CUSTOM = "CUSTOM"


class StrategySpec(BaseModel):
    """Specification and registration record of a strategy candidate.
    
    Contains metadata, origin, lifecycle stage, and empirical validation flags.
    No execution authority is granted by this specification.
    """
    strategy_id: str = Field(..., description="Unique strategy identifier (e.g. STR-001)")
    name: str = Field(..., description="Descriptive human-readable strategy name")
    family: str = Field(..., description="Strategy family classification")
    origin: StrategyOrigin = Field(..., description="Discovery source / origin (metadata only)")
    stage: StrategyStage = Field(default=StrategyStage.IDEA, description="Current lifecycle stage")
    description: str = Field(default="", description="Detailed thesis and hypothesis description")
    math_foundation_validated: bool = Field(
        default=False, 
        description="Whether mathematical foundations are validated"
    )
    economic_edge_validated: bool = Field(
        default=False, 
        description="Whether out-of-sample economic edge is empirically validated"
    )
    is_privileged: bool = Field(
        default=False, 
        description="Non-negotiable invariant: Always False. No strategy is privileged."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Arbitrary strategy-specific metadata"
    )

    def __init__(self, **data: Any):
        super().__init__(**data)
        # Enforce non-negotiable invariant: no strategy may be privileged
        if self.is_privileged:
            raise ValueError("Core Governance Invariant Violated: No strategy may be marked privileged.")
