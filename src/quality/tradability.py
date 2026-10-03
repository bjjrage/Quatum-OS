"""
Tradability Score and Liquidity Tier Execution Policy.

Core Invariants:
1. Every market evaluated for execution must have a point-in-time TradabilityScore.
2. Distinct taxonomy separates Tier 5 (Marginal liquidity, tradable with strict size limits)
   from UNTRADABLE (fails minimum criteria entirely, zero orders, zero risk).
3. Hard integrity failures (manifest invalid, clock skew, spread blowout, book depletion)
   strictly result in UNTRADABLE (tradable=False).
"""

from __future__ import annotations

from enum import IntEnum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TradabilityTier(IntEnum):
    """Execution tradability tiers based on microstructure liquidity and data integrity."""
    TIER_1_LARGE_CAP = 1
    TIER_2_MID_CAP = 2
    TIER_3_SMALL_CAP = 3
    TIER_4_MICRO_CAP = 4
    TIER_5_SMALL_TRADABLE = 5   # Marginal liquidity, tradable with strict size limits
    UNTRADABLE = 6              # Fails minimum criteria entirely (zero orders, zero risk)

    # Backward compatibility aliases
    TIER_1_EXCELLENT = 1
    TIER_2_GOOD = 2
    TIER_3_ACCEPTABLE = 3
    TIER_4_MARGINAL = 4
    TIER_5_UNTRADABLE = 6


class TradabilityScore(BaseModel):
    """Point-in-time tradability score and tier classification for a target instrument."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    timestamp_ns: int
    spread_bps: float
    depth_0_5pct_usd: float
    volume_5m_usd: float
    clock_sync_offset_ms: float
    manifest_valid: bool
    tier: TradabilityTier
    tradable: bool
    max_position_usd: Optional[float] = None
    limit_orders_only: bool = False
    rejection_reasons: List[str] = Field(default_factory=list)


TradabilityEvaluationResult = TradabilityScore


class LiquidityTierPolicy:
    """Evaluates instrument liquidity, market microstructure, and system integrity to assign tiers.
    
    Hard Invariants for UNTRADABLE:
    - Bid-Ask Spread > max_spread_bps
    - Bid/Ask Depth within 0.5% < min_depth_0_5pct_usd
    - 5-Minute Volume < min_volume_5m_usd
    - Clock Skew > max_clock_skew_ms
    - Manifest validity == False
    """

    def __init__(
        self,
        max_spread_bps: float = 15.0,
        min_depth_0_5pct_usd: float = 25_000.0,
        min_volume_5m_usd: float = 100_000.0,
        max_clock_skew_ms: float = 500.0,
        require_valid_manifest: bool = True,
        tier5_max_position_usd: float = 5_000.0,
    ):
        self.max_spread_bps = max_spread_bps
        self.min_depth_0_5pct_usd = min_depth_0_5pct_usd
        self.min_volume_5m_usd = min_volume_5m_usd
        self.max_clock_skew_ms = max_clock_skew_ms
        self.require_valid_manifest = require_valid_manifest
        self.tier5_max_position_usd = tier5_max_position_usd

    def evaluate(
        self,
        symbol: str,
        timestamp_ns: int,
        spread_bps: float,
        depth_0_5pct_usd: float,
        volume_5m_usd: float,
        clock_sync_offset_ms: float = 0.0,
        manifest_valid: bool = True,
    ) -> TradabilityScore:
        """Assign point-in-time TradabilityTier and enforce execution safety."""
        rejection_reasons: List[str] = []

        # Check hard violations that immediately force UNTRADABLE (tradable=False)
        if spread_bps > self.max_spread_bps:
            rejection_reasons.append(
                f"Spread ({spread_bps:.1f} bps) exceeds ceiling ({self.max_spread_bps:.1f} bps)."
            )

        if depth_0_5pct_usd < self.min_depth_0_5pct_usd:
            rejection_reasons.append(
                f"Book depth within 0.5% (${depth_0_5pct_usd:,.0f}) below minimum (${self.min_depth_0_5pct_usd:,.0f})."
            )

        if volume_5m_usd < self.min_volume_5m_usd:
            rejection_reasons.append(
                f"5-minute volume (${volume_5m_usd:,.0f}) below minimum threshold (${self.min_volume_5m_usd:,.0f})."
            )

        if abs(clock_sync_offset_ms) > self.max_clock_skew_ms:
            rejection_reasons.append(
                f"Clock sync offset ({abs(clock_sync_offset_ms):.1f} ms) exceeds limit ({self.max_clock_skew_ms:.1f} ms)."
            )

        if self.require_valid_manifest and not manifest_valid:
            rejection_reasons.append("Storage manifest validity check failed or missing.")

        if rejection_reasons:
            return TradabilityScore(
                symbol=symbol,
                timestamp_ns=timestamp_ns,
                spread_bps=spread_bps,
                depth_0_5pct_usd=depth_0_5pct_usd,
                volume_5m_usd=volume_5m_usd,
                clock_sync_offset_ms=clock_sync_offset_ms,
                manifest_valid=manifest_valid,
                tier=TradabilityTier.UNTRADABLE,
                tradable=False,
                rejection_reasons=rejection_reasons,
            )

        # Graduated tier scoring when no hard rejection occurs
        if spread_bps <= 2.0 and depth_0_5pct_usd >= 250_000.0 and volume_5m_usd >= 1_000_000.0:
            tier = TradabilityTier.TIER_1_LARGE_CAP
            max_pos = None
            limit_only = False
        elif spread_bps <= 5.0 and depth_0_5pct_usd >= 100_000.0 and volume_5m_usd >= 500_000.0:
            tier = TradabilityTier.TIER_2_MID_CAP
            max_pos = None
            limit_only = False
        elif spread_bps <= 10.0 and depth_0_5pct_usd >= 50_000.0 and volume_5m_usd >= 250_000.0:
            tier = TradabilityTier.TIER_3_SMALL_CAP
            max_pos = None
            limit_only = False
        elif spread_bps <= 12.0 and depth_0_5pct_usd >= 35_000.0 and volume_5m_usd >= 150_000.0:
            tier = TradabilityTier.TIER_4_MICRO_CAP
            max_pos = None
            limit_only = False
        else:
            # Tier 5: Marginal liquidity, tradable with strict size limits and limit-only execution
            tier = TradabilityTier.TIER_5_SMALL_TRADABLE
            max_pos = self.tier5_max_position_usd
            limit_only = True

        return TradabilityScore(
            symbol=symbol,
            timestamp_ns=timestamp_ns,
            spread_bps=spread_bps,
            depth_0_5pct_usd=depth_0_5pct_usd,
            volume_5m_usd=volume_5m_usd,
            clock_sync_offset_ms=clock_sync_offset_ms,
            manifest_valid=manifest_valid,
            tier=tier,
            tradable=True,
            max_position_usd=max_pos,
            limit_orders_only=limit_only,
            rejection_reasons=[],
        )
