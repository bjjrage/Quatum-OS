"""
Regime Snapshot and Market State Classification.

Auditable point-in-time snapshot of the macro, crypto-systemic, and microstructure
regime state captured on every candidate signal or periodic evaluation.
"""

from __future__ import annotations

import time
from typing import Optional, Any
from pydantic import BaseModel, Field


class RegimeSnapshot(BaseModel):
    """
    Authoritative 23-field Regime Snapshot specification from Trading / Quant OS v1.4.1 blueprint.
    
    Fields that are not yet collected by historical data or collectors must default to None
    with explicit documentation, rather than being silently omitted.
    """
    # 1. Primary time and identifier
    timestamp_ns: int = Field(..., description="Nanosecond timestamp of snapshot")
    regime_snapshot_id: str = Field(
        default_factory=lambda: f"regime_{time.time_ns()}",
        description="Unique deterministic or generated snapshot identifier"
    )

    # 2-4. Multi-horizon BTC directional state
    btc_state_1m: str = Field(default="FLAT", description="1-minute BTC state (FLAT, UP, DOWN, RUNNING_HARD_*)")
    btc_state_5m: str = Field(default="FLAT", description="5-minute BTC state")
    btc_state_15m: str = Field(default="FLAT", description="15-minute BTC state")

    # 5-6. BTC Realized Volatility
    btc_realized_vol_1h: float = Field(default=0.02, description="1-hour BTC realized volatility")
    btc_realized_vol_percentile: Optional[float] = Field(
        default=None,
        description="Historical percentile of BTC 1h realized volatility (None if historical window unavailable)"
    )

    # 7. Global market regime classification
    market_regime: str = Field(default="CHOP", description="RISK_ON, RISK_OFF, CHOP, DISLOCATION, etc.")

    # 8-10. Correlation and cross-sectional statistics
    mean_alt_btc_correlation: Optional[float] = Field(
        default=None,
        description="Rolling mean correlation between altcoin universe and BTC (None if uncomputed)"
    )
    cross_sectional_dispersion: Optional[float] = Field(
        default=None,
        description="Cross-sectional standard deviation of returns across altcoin universe"
    )
    funding_rate_zscore: Optional[float] = Field(
        default=None,
        description="Standardized z-score of perp funding rate across universe"
    )

    # 11-12. Derivative aggregate volume and liquidations
    aggregate_oi_delta_1h: Optional[float] = Field(
        default=None,
        description="1-hour change in aggregate open interest"
    )
    liquidation_volume_1h: Optional[float] = Field(
        default=None,
        description="1-hour total forced liquidation volume"
    )

    # 13-14. External sentiment / implied volatility signals
    deribit_dvol: Optional[float] = Field(
        default=None,
        description="Deribit DVOL index value (None if options collector dormant)"
    )
    polymarket_event_dispersion: Optional[float] = Field(
        default=None,
        description="Polymarket probability divergence or event uncertainty metric"
    )

    # 15-21. Microstructure and operational regimes
    relative_volume: Optional[float] = Field(
        default=None,
        description="Ratio of current 5m volume to 24h rolling median 5m volume"
    )
    spread_regime: Optional[str] = Field(
        default=None,
        description="NORMAL, TIGHT, WIDE, STRESSED"
    )
    depth_regime: Optional[str] = Field(
        default=None,
        description="NORMAL, THIN, DEEP, IMBALANCED"
    )
    news_intensity: Optional[float] = Field(
        default=None,
        description="Point-in-time quantified news/headline impact score (None if PIT news absent)"
    )
    latency_regime: Optional[str] = Field(
        default=None,
        description="NORMAL, ELEVATED, DEGRADED"
    )
    margin_pressure_regime: Optional[str] = Field(
        default=None,
        description="NORMAL, ELEVATED_LIQUIDATIONS, CASCADE"
    )

    # 22-23. Anomaly and break flags
    correlation_breakdown: bool = Field(
        default=False,
        description="True if systemic altcoin-BTC correlation has collapsed below threshold"
    )
    dislocation_detected: bool = Field(
        default=False,
        description="True if extreme basis, funding, or cross-venue price dislocation observed"
    )

    symbol: Optional[str] = None
    btc_state: Optional[Any] = None
    alt_residual_shock: Optional[float] = None
    alt_z_score: Optional[float] = None
    beta_down: Optional[float] = None
    beta_up: Optional[float] = None
    gamma_eth: Optional[float] = None
    reversal_detector_triggered: Optional[str] = None
    book_replenishment_ratio: float = 0.0
    pre_shock_vwap: Optional[float] = None
    pre_shock_origin: Optional[float] = None
    entry_price: Optional[float] = None
    realized_mfe: Optional[float] = None
    realized_mae: Optional[float] = None
    holding_time_s: Optional[float] = None
    exit_reason: Optional[str] = None
