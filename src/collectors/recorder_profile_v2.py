"""
Recorder Profile v2 — High-Resolution Market Data Ingestion.

Architectural Invariants:
1. PARALLEL OPERATION: Profile v2 operates strictly in parallel to the Batch 0 recorder.
   Under NO circumstances may Profile v2 share storage sinks, state manifests, or run IDs
   with Batch 0 (PID running on data/raw/).
2. HIGH FREQUENCY: Binance depth upgraded to depth20@100ms for micro-reversal detection.
3. LIQUIDATION PROXY TAGGING: Liquidation stream (!forceOrder@arr) is explicitly tagged as
   `PARTIAL_LIQUIDATION_INDICATOR`. Binance truncates and throttles this stream; it is NEVER
   treated as the complete liquidation universe.
4. DATA PATH SEPARATION: All raw output routes strictly to data/raw_v2/.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class LiquidationStreamTag(str, Enum):
    PARTIAL_LIQUIDATION_INDICATOR = "PARTIAL_LIQUIDATION_INDICATOR"


class IngestionResolution(str, Enum):
    DEPTH_100MS = "depth20@100ms"
    DEPTH_250MS = "depth20@250ms"
    DEPTH_500MS = "depth20@500ms"


class RecorderProfileV2Config(BaseModel):
    """Configuration contract for Recorder Profile v2."""
    profile_name: str = "profile_v2_high_res"
    raw_storage_dir: str = "data/raw_v2"
    runtime_state_dir: str = "data/runtime_v2"
    binance_depth_stream: str = IngestionResolution.DEPTH_100MS.value
    binance_liquidation_stream: str = "!forceOrder@arr"
    liquidation_tag: str = LiquidationStreamTag.PARTIAL_LIQUIDATION_INDICATOR.value
    target_symbols: List[str] = Field(
        default_factory=lambda: ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]
    )
    is_isolated_from_batch_0: bool = True
    metadata_notes: str = (
        "Binance !forceOrder@arr is explicitly a PARTIAL_LIQUIDATION_INDICATOR proxy. "
        "Exhaustive liquidation volume cannot be inferred solely from public WebSocket feeds."
    )

    def validate_isolation(self, batch_0_raw_dir: str = "data/raw") -> bool:
        """Verify that profile v2 path is strictly disjoint from Batch 0 storage."""
        norm_v2 = os.path.normpath(self.raw_storage_dir)
        norm_b0 = os.path.normpath(batch_0_raw_dir)
        if norm_v2 == norm_b0 or norm_v2.startswith(norm_b0 + os.sep):
            raise ValueError(
                f"Isolation violation: Profile v2 raw dir '{self.raw_storage_dir}' "
                f"collides with Batch 0 raw dir '{batch_0_raw_dir}'."
            )
        return True


class ProfileV2EventTag(BaseModel):
    """Event-level metadata tag applied to Profile v2 ingested streams."""
    stream_name: str
    tag: str
    is_partial_proxy: bool
    notes: str


def get_profile_v2_tag_for_stream(stream_name: str) -> ProfileV2EventTag:
    """Return explicit semantic metadata tag for a given stream."""
    if "!forceorder" in stream_name.lower():
        return ProfileV2EventTag(
            stream_name=stream_name,
            tag=LiquidationStreamTag.PARTIAL_LIQUIDATION_INDICATOR.value,
            is_partial_proxy=True,
            notes="Binance limits push frequency; partial sample of liquidation cascades.",
        )
    return ProfileV2EventTag(
        stream_name=stream_name,
        tag="FULL_MARKET_FEED",
        is_partial_proxy=False,
        notes="Standard BBO/Depth market feed.",
    )
