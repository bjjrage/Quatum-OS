"""Event detection engine for microstructure shocks, price impulses, and liquidity dislocations."""
from dataclasses import dataclass
from enum import Enum
import math
from typing import List, Optional, Dict, Any

from .features import FeatureEngine


class ShockDirection(str, Enum):
    EXPANSION_UP = "EXPANSION_UP"
    EXPANSION_DOWN = "EXPANSION_DOWN"


@dataclass
class PriceImpulseEvent:
    """Represents a validated statistical price impulse event (STR-002 input)."""
    event_id: str
    symbol: str
    venue: str
    ts_start_ns: int
    ts_peak_ns: int
    start_price: float
    peak_price: float
    impulse_return: float
    prior_volatility: float
    z_score: float
    direction: ShockDirection
    has_forced_liquidations: bool = False
    forced_liquidation_volume: float = 0.0


class EventDetector:
    """Detects statistical price impulses and microstructure liquidity shocks."""

    def __init__(
        self,
        vol_lookback_bars: int = 30,
        impulse_threshold_z: float = 2.5,
        min_return_bps: float = 10.0,
    ):
        self.vol_lookback = vol_lookback_bars
        self.impulse_z = impulse_threshold_z
        self.min_return_bps = min_return_bps

    def detect_impulses(
        self,
        prices: List[float],
        timestamps_ns: List[int],
        symbol: str = "BTCUSDT",
        venue: str = "binance_perp",
        forced_liquidation_vols: Optional[List[float]] = None,
    ) -> List[PriceImpulseEvent]:
        """Scan historical price series and extract all verified price impulse events."""
        if len(prices) < self.vol_lookback + 2:
            return []

        returns = FeatureEngine.calc_log_returns(prices, horizon=1)
        events: List[PriceImpulseEvent] = []

        # Rolling window evaluation
        for i in range(self.vol_lookback, len(returns)):
            window = returns[i - self.vol_lookback : i]
            sigma = FeatureEngine.calc_realized_volatility(window)
            if sigma <= 1e-6:
                continue

            current_ret = returns[i]
            z = current_ret / sigma

            ret_bps = abs(current_ret) * 10000.0

            if abs(z) >= self.impulse_z and ret_bps >= self.min_return_bps:
                direction = ShockDirection.EXPANSION_UP if z > 0 else ShockDirection.EXPANSION_DOWN
                p_start = prices[i]
                p_peak = prices[i + 1]
                t_start = timestamps_ns[i]
                t_peak = timestamps_ns[i + 1]

                liq_vol = forced_liquidation_vols[i + 1] if forced_liquidation_vols else 0.0

                event = PriceImpulseEvent(
                    event_id=f"impulse_{symbol}_{t_peak}_{len(events)+1}",
                    symbol=symbol,
                    venue=venue,
                    ts_start_ns=t_start,
                    ts_peak_ns=t_peak,
                    start_price=p_start,
                    peak_price=p_peak,
                    impulse_return=round(current_ret, 6),
                    prior_volatility=round(sigma, 6),
                    z_score=round(z, 2),
                    direction=direction,
                    has_forced_liquidations=(liq_vol > 0.0),
                    forced_liquidation_volume=liq_vol,
                )
                events.append(event)

        return events
