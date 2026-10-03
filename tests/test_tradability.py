"""Unit tests for TradabilityScore and Liquidity Tier 5 Execution Policy."""

import pytest
from src.quality.tradability import (
    TradabilityTier,
    TradabilityScore,
    LiquidityTierPolicy,
)


def test_tradability_policy_graduated_tiers():
    """Verify tier assignment when liquidity conditions are good."""
    policy = LiquidityTierPolicy()

    # Tier 1 Excellent: tight spread, deep book, high volume
    score_t1 = policy.evaluate(
        symbol="BTCUSDT",
        timestamp_ns=1700000000_000000000,
        spread_bps=1.0,
        depth_0_5pct_usd=500_000.0,
        volume_5m_usd=2_000_000.0,
        clock_sync_offset_ms=5.0,
        manifest_valid=True,
    )
    assert score_t1.tier == TradabilityTier.TIER_1_EXCELLENT
    assert score_t1.tradable is True
    assert len(score_t1.rejection_reasons) == 0

    # Tier 3 Acceptable: moderate spread, modest depth
    score_t3 = policy.evaluate(
        symbol="DOGEUSDT",
        timestamp_ns=1700000000_000000000,
        spread_bps=7.5,
        depth_0_5pct_usd=75_000.0,
        volume_5m_usd=300_000.0,
        clock_sync_offset_ms=20.0,
        manifest_valid=True,
    )
    assert score_t3.tier == TradabilityTier.TIER_3_ACCEPTABLE
    assert score_t3.tradable is True


def test_tradability_policy_tier_5_hard_rejections():
    """Verify each condition that immediately forces Tier 5 (Untradable)."""
    policy = LiquidityTierPolicy(
        max_spread_bps=15.0,
        min_depth_0_5pct_usd=25_000.0,
        min_volume_5m_usd=100_000.0,
        max_clock_skew_ms=500.0,
        require_valid_manifest=True,
    )

    # 1. Spread blowout > 15.0 bps
    s_spread = policy.evaluate(
        symbol="ALTUSDT",
        timestamp_ns=1700000000_000000000,
        spread_bps=22.0,
        depth_0_5pct_usd=100_000.0,
        volume_5m_usd=500_000.0,
    )
    assert s_spread.tier == TradabilityTier.TIER_5_UNTRADABLE
    assert s_spread.tradable is False
    assert any("Spread" in r for r in s_spread.rejection_reasons)

    # 2. Book depth depleted < $25k
    s_depth = policy.evaluate(
        symbol="ALTUSDT",
        timestamp_ns=1700000000_000000000,
        spread_bps=5.0,
        depth_0_5pct_usd=12_000.0,
        volume_5m_usd=500_000.0,
    )
    assert s_depth.tier == TradabilityTier.TIER_5_UNTRADABLE
    assert s_depth.tradable is False
    assert any("depth" in r.lower() for r in s_depth.rejection_reasons)

    # 3. Clock skew > 500 ms
    s_clock = policy.evaluate(
        symbol="ALTUSDT",
        timestamp_ns=1700000000_000000000,
        spread_bps=5.0,
        depth_0_5pct_usd=50_000.0,
        volume_5m_usd=500_000.0,
        clock_sync_offset_ms=650.0,
    )
    assert s_clock.tier == TradabilityTier.TIER_5_UNTRADABLE
    assert s_clock.tradable is False
    assert any("Clock sync" in r for r in s_clock.rejection_reasons)

    # 4. Storage manifest invalid
    s_manifest = policy.evaluate(
        symbol="ALTUSDT",
        timestamp_ns=1700000000_000000000,
        spread_bps=5.0,
        depth_0_5pct_usd=50_000.0,
        volume_5m_usd=500_000.0,
        manifest_valid=False,
    )
    assert s_manifest.tier == TradabilityTier.TIER_5_UNTRADABLE
    assert s_manifest.tradable is False
    assert any("manifest" in r.lower() for r in s_manifest.rejection_reasons)
