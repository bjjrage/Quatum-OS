"""
Bybit Linear Perpetual Data Ingestion Adapter & Comparative Microstructure Evaluation.

Provides:
1. Normalized message parsing from Bybit Linear (USDT perpetual) WebSocket streams.
2. Mapping into standard internal OS tick/orderbook schema.
3. Liquidation stream tagging (PARTIAL_LIQUIDATION_INDICATOR).
4. Comparative analysis: Binance vs Bybit liquidation / reversal data quality.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from src.common.types import OrderbookL2Depth
from src.collectors.recorder_profile_v2 import LiquidationStreamTag


class BybitLiquidationEvent(BaseModel):
    """Normalized Bybit linear liquidation event."""
    symbol: str
    side: str  # "Buy" or "Sell"
    price: float
    size: float
    timestamp_ms: int
    exchange: str = "bybit"
    tag: str = LiquidationStreamTag.PARTIAL_LIQUIDATION_INDICATOR.value
    is_partial_proxy: bool = True
    notes: str = "Bybit linear liquidation push; tagged as partial liquidation indicator."


class BybitLinearPerpetualAdapter:
    """Adapter for Bybit v5 Linear Perpetual WebSocket streams."""

    @staticmethod
    def parse_orderbook_snapshot(raw_msg: Dict[str, Any], ts_received_ns: int = 0) -> Optional[OrderbookL2Depth]:
        """Parse Bybit orderbook snapshot (e.g. topic 'orderbook.50.BTCUSDT')."""
        topic = raw_msg.get("topic", "")
        if not topic.startswith("orderbook"):
            return None

        data = raw_msg.get("data", {})
        symbol = data.get("s", "")
        ts = raw_msg.get("ts", 0)

        raw_bids = data.get("b", [])
        raw_asks = data.get("a", [])

        bids_price = [float(b[0]) for b in raw_bids]
        bids_size = [float(b[1]) for b in raw_bids]
        asks_price = [float(a[0]) for a in raw_asks]
        asks_size = [float(a[1]) for a in raw_asks]

        return OrderbookL2Depth(
            ts_exchange_ns=ts * 1_000_000,
            ts_received_utc_ns=ts_received_ns or (ts * 1_000_000),
            ts_received_mono_ns=ts_received_ns or (ts * 1_000_000),
            venue="bybit",
            symbol=symbol,
            bids_price=bids_price,
            bids_size=bids_size,
            asks_price=asks_price,
            asks_size=asks_size,
            depth_level=len(bids_price),
        )

    @staticmethod
    def parse_liquidation_event(raw_msg: Dict[str, Any]) -> Optional[BybitLiquidationEvent]:
        """Parse Bybit allLiquidation stream message."""
        topic = raw_msg.get("topic", "")
        if "liquidation" not in topic.lower():
            return None

        data = raw_msg.get("data", {})
        if not data:
            return None

        return BybitLiquidationEvent(
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            price=float(data.get("price", 0.0)),
            size=float(data.get("size", 0.0)),
            timestamp_ms=int(data.get("updatedTime", 0)),
        )

    @staticmethod
    def get_comparative_evaluation() -> Dict[str, Any]:
        """Return comparative architecture evaluation of Binance vs Bybit for Liquidity Shock Reversals."""
        return {
            "binance_usdt_futures": {
                "market_share": "Dominant global volume and deepest top-of-book liquidity for altcoins.",
                "websocket_depth_resolution": "depth20@100ms provides superior micro-reversal bar formation.",
                "liquidation_stream_limitation": (
                    "!forceOrder@arr stream is heavily throttled by Binance (max 1 push/sec per symbol). "
                    "Must be strictly tagged as PARTIAL_LIQUIDATION_INDICATOR."
                ),
                "data_quality_score": "High top-of-book depth fidelity; partial liquidation proxy.",
            },
            "bybit_linear_perpetuals": {
                "market_share": "Second largest perpetual derivatives venue; high retail leverage participation.",
                "websocket_depth_resolution": "orderbook.50 at 20ms or 50ms intervals.",
                "liquidation_stream_limitation": (
                    "allLiquidation topic broadcasts individual liquidation fills, but is subject to WebSocket "
                    "dropouts during extreme volatility cascades. Still a partial proxy."
                ),
                "data_quality_score": "High liquidation granularity; useful cross-venue confirmation.",
            },
            "architectural_recommendation": (
                "Primary signal trigger should execute on Binance depth20@100ms orderbook replenishment, "
                "with Bybit liquidation bursts serving as cross-market confirmation proxy."
            ),
        }
