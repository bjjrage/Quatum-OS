"""
Tradability Score and Liquidity Tier 5 Execution Policy.

Invariant:
Every market evaluated for execution must have a point-in-time TradabilityScore.
If a market is evaluated as TIER_5_UNTRADABLE, strategies MUST NOT execute any order
even if the alpha signal is active.
"""

from __future__ import annotations

from enum import IntEnum
from typing import List, Optional
from pydantic import BaseModel, Field


class TradabilityTier(IntEnum):
    """Execution tradability tiers based on microstructure liquidity and data integrity."""
    TIER_1_EXCELLENT = 1
    TIER_2_GOOD = 2
    TIER_3_ACCEPTABLE = 3
    TIER_4_MARGINAL = 4
    TIER_5_UNTRADABLE = 5  # Strictly blocked from execution


class TradabilityScore(BaseModel):
    """Point-in-time tradability score and tier classification for a target instrument."""
    symbol: str
    timestamp_ns: int
    spread_bps: float
    depth_0_5pct_usd: float
    volume_5m_usd: float
    clock_sync_offset_ms: float
    manifest_valid: bool
    tier: TradabilityTier
    tradable: bool
    rejection_reasons: List[str] = Field(default_factory=list)


class LiquidityTierPolicy:
    """Evaluates instrument liquidity, market microstructure, and system integrity to assign tiers.
    
    Hard Invariants for TIER 5 (UNTRADABLE):
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
    ):
        self.max_spread_bps = max_spread_bps
        self.min_depth_0_5pct_usd = min_depth_0_5pct_usd
        self.min_volume_5m_usd = min_volume_5m_usd
        self.max_clock_skew_ms = max_clock_skew_ms
        self.require_valid_manifest = require_valid_manifest

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

        # Check hard violations that immediately force Tier 5
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
                tier=TradabilityTier.TIER_5_UNTRADABLE,
                tradable=False,
                rejection_reasons=rejection_reasons,
            )

        # Graduated tier scoring when no hard rejection occurs
        if spread_bps <= 2.0 and depth_0_5pct_usd >= 250_000.0 and volume_5m_usd >= 1_000_000.0:
            tier = TradabilityTier.TIER_1_EXCELLENT
        elif spread_bps <= 5.0 and depth_0_5pct_usd >= 100_000.0 and volume_5m_usd >= 500_000.0:
            tier = TradabilityTier.TIER_2_GOOD
        elif spread_bps <= 10.0 and depth_0_5pct_usd >= 50_000.0 and volume_5m_usd >= 250_000.0:
            tier = TradabilityTier.TIER_3_ACCEPTABLE
        else:
            tier = TradabilityTier.TIER_4_MARGINAL

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
            rejection_reasons=[],
        )
