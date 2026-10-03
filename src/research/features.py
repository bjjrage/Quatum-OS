"""Generic feature engineering engine and bar aggregation primitives."""
import math
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class OHLCVBar(BaseModel):
    """Normalized OHLCV Bar."""
    symbol: str
    venue: str
    ts_start_ns: int
    ts_end_ns: int
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    tick_count: int = 0
    vwap: float = 0.0


class BarAggregator:
    """Aggregates irregular ticks into regular time bars."""

    def __init__(self, bar_duration_ms: int = 1000):
        self.bar_duration_ns = bar_duration_ms * 1_000_000
        self._current_bar: Optional[Dict[str, Any]] = None

    def process_tick(
        self,
        symbol: str,
        venue: str,
        ts_utc_ns: int,
        price: float,
        size: float = 1.0,
    ) -> Optional[OHLCVBar]:
        """Ingest tick and return completed OHLCVBar when a time bucket completes."""
        bar_idx = ts_utc_ns // self.bar_duration_ns
        bar_start_ns = bar_idx * self.bar_duration_ns
        bar_end_ns = bar_start_ns + self.bar_duration_ns

        completed_bar = None

        if self._current_bar is not None and self._current_bar["bar_start_ns"] != bar_start_ns:
            # Emit completed bar
            b = self._current_bar
            vwap = (b["volume_weighted_sum"] / b["volume"]) if b["volume"] > 0 else b["close"]
            completed_bar = OHLCVBar(
                symbol=b["symbol"],
                venue=b["venue"],
                ts_start_ns=b["bar_start_ns"],
                ts_end_ns=b["bar_start_ns"] + self.bar_duration_ns,
                open=b["open"],
                high=b["high"],
                low=b["low"],
                close=b["close"],
                volume=round(b["volume"], 4),
                tick_count=b["tick_count"],
                vwap=round(vwap, 4),
            )
            self._current_bar = None

        if self._current_bar is None:
            self._current_bar = {
                "symbol": symbol,
                "venue": venue,
                "bar_start_ns": bar_start_ns,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size,
                "volume_weighted_sum": price * size,
                "tick_count": 1,
            }
        else:
            self._current_bar["high"] = max(self._current_bar["high"], price)
            self._current_bar["low"] = min(self._current_bar["low"], price)
            self._current_bar["close"] = price
            self._current_bar["volume"] += size
            self._current_bar["volume_weighted_sum"] += price * size
            self._current_bar["tick_count"] += 1

        return completed_bar


class FeatureEngine:
    """Computes quantitative features over price series and order books."""

    @staticmethod
    def calc_log_returns(prices: List[float], horizon: int = 1) -> List[float]:
        """Compute rolling log returns ln(P_t / P_{t-horizon})."""
        if len(prices) <= horizon:
            return []
        returns = []
        for i in range(horizon, len(prices)):
            p0 = prices[i - horizon]
            p1 = prices[i]
            if p0 > 0 and p1 > 0:
                returns.append(math.log(p1 / p0))
            else:
                returns.append(0.0)
        return returns

    @staticmethod
    def calc_realized_volatility(returns: List[float], annualize_factor: float = 1.0) -> float:
        """Compute sample realized volatility from returns."""
        n = len(returns)
        if n < 2:
            return 0.0
        mean_ret = sum(returns) / n
        var = sum((r - mean_ret) ** 2 for r in returns) / (n - 1)
        return math.sqrt(var * annualize_factor)

    @staticmethod
    def calc_orderbook_imbalance(bid_size: float, ask_size: float) -> float:
        """Calculate normalized orderbook imbalance: (V_b - V_a) / (V_b + V_a) in [-1.0, 1.0]."""
        total = bid_size + ask_size
        if total <= 0.0:
            return 0.0
        return round((bid_size - ask_size) / total, 4)

    @staticmethod
    def calc_spread_bps(bid: float, ask: float) -> float:
        """Calculate bid-ask spread in basis points relative to mid."""
        mid = (bid + ask) / 2.0
        if mid <= 0.0:
            return 0.0
        return round(((ask - bid) / mid) * 10000.0, 2)

    @staticmethod
    def calc_z_score(value: float, mean: float, std: float) -> float:
        """Normalized z-score shock metric."""
        if std <= 1e-12:
            return 0.0
        return (value - mean) / std
