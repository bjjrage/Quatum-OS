"""
Regime and Policy Engine.

Hierarchical regime classification:
1. Global Macro (RISK_ON, RISK_OFF, NEUTRAL)
2. Domain Regime (LOW_VOL, HIGH_VOL, STRESSED, ILLIQUID)
3. Strategy Regime (e.g., ACTIVE, DORMANT, DEFENSIVE)

Governance Invariant:
AI/LLM inputs are strictly informational labeling metadata with zero autonomous execution authority.
All regime state transitions and allocation multipliers are purely deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Dict, Any, List, Optional


class GlobalMacroRegime(str, Enum):
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"


class DomainMarketRegime(str, Enum):
    LOW_VOL = "LOW_VOL"
    NORMAL_VOL = "NORMAL_VOL"
    HIGH_VOL = "HIGH_VOL"
    STRESSED_ILLIQUID = "STRESSED_ILLIQUID"


class StrategyRegimeState(str, Enum):
    ACTIVE = "ACTIVE"
    REDUCED_SIZE = "REDUCED_SIZE"
    HALTED = "HALTED"


@dataclass
class RegimeState:
    global_macro: GlobalMacroRegime
    domain_regime: DomainMarketRegime
    strategy_states: Dict[str, StrategyRegimeState]
    capital_allocation_multiplier: float  # 0.0 to 1.0 multiplier applied to portfolio risk
    metadata: Dict[str, Any] = field(default_factory=dict)
    ai_commentary: Optional[str] = None  # Advisory metadata only


class DeterministicPolicyEngine:
    """
    Classifies market regime from quantitative signals and determines
    risk scaling multipliers.
    """

    def __init__(
        self,
        high_vol_annualized_threshold: float = 0.80,    # 80% ann vol = high vol
        stressed_vol_annualized_threshold: float = 1.20, # 120% ann vol = stressed
        stressed_spread_bps_threshold: float = 25.0,    # 25 bps bid-ask spread = illiquid
    ):
        self.high_vol_threshold = high_vol_annualized_threshold
        self.stressed_vol_threshold = stressed_vol_annualized_threshold
        self.stressed_spread_threshold = stressed_spread_bps_threshold

    def evaluate_regime(
        self,
        annualized_volatility: float,
        bid_ask_spread_bps: float,
        trend_30d_return: float,
        smile_arbitrage_free: bool = True,
        ai_advisory_label: Optional[str] = None,
    ) -> RegimeState:
        """
        Pure deterministic classification.
        ai_advisory_label is captured in metadata but cannot override classification.
        """
        # 1. Global Macro
        if trend_30d_return > 0.05:
            macro = GlobalMacroRegime.RISK_ON
        elif trend_30d_return < -0.05:
            macro = GlobalMacroRegime.RISK_OFF
        else:
            macro = GlobalMacroRegime.NEUTRAL

        # 2. Domain Regime
        if annualized_volatility >= self.stressed_vol_threshold or bid_ask_spread_bps >= self.stressed_spread_threshold:
            domain = DomainMarketRegime.STRESSED_ILLIQUID
            multiplier = 0.25
        elif annualized_volatility >= self.high_vol_threshold:
            domain = DomainMarketRegime.HIGH_VOL
            multiplier = 0.50
        elif annualized_volatility <= 0.30:
            domain = DomainMarketRegime.LOW_VOL
            multiplier = 1.00
        else:
            domain = DomainMarketRegime.NORMAL_VOL
            multiplier = 1.00

        # Adjust for macro
        if macro == GlobalMacroRegime.RISK_OFF:
            multiplier = min(multiplier, 0.50)

        # 3. Strategy specific states
        strategy_states = {}

        # STR-001 (Relative value / Deribit smile)
        if not smile_arbitrage_free:
            strategy_states["STR-001"] = StrategyRegimeState.HALTED
        elif domain == DomainMarketRegime.STRESSED_ILLIQUID:
            strategy_states["STR-001"] = StrategyRegimeState.REDUCED_SIZE
        else:
            strategy_states["STR-001"] = StrategyRegimeState.ACTIVE

        # STR-002 (Forced liquidation event study)
        # Flourishes in high vol / dislocations, dormant in low vol
        if domain in (DomainMarketRegime.HIGH_VOL, DomainMarketRegime.STRESSED_ILLIQUID):
            strategy_states["STR-002"] = StrategyRegimeState.ACTIVE
        elif domain == DomainMarketRegime.LOW_VOL:
            strategy_states["STR-002"] = StrategyRegimeState.REDUCED_SIZE
        else:
            strategy_states["STR-002"] = StrategyRegimeState.ACTIVE

        return RegimeState(
            global_macro=macro,
            domain_regime=domain,
            strategy_states=strategy_states,
            capital_allocation_multiplier=multiplier,
            metadata={
                "annualized_vol": annualized_volatility,
                "spread_bps": bid_ask_spread_bps,
                "trend_30d": trend_30d_return,
                "smile_valid": smile_arbitrage_free,
            },
            ai_commentary=ai_advisory_label,
        )
