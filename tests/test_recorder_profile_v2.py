"""Unit tests for Recorder Profile v2 and Bybit linear adapter."""

import pytest
from src.collectors.recorder_profile_v2 import (
    RecorderProfileV2Config,
    LiquidationStreamTag,
    IngestionResolution,
    get_profile_v2_tag_for_stream,
)
from src.collectors.bybit_adapter import (
    BybitLinearPerpetualAdapter,
    BybitLiquidationEvent,
)


def test_profile_v2_isolation_and_streams():
    """Verify that Profile v2 is strictly isolated from Batch 0 data directory."""
    cfg = RecorderProfileV2Config(
        raw_storage_dir="data/raw_v2",
        runtime_state_dir="data/runtime_v2",
    )
    # Isolation check passes when paths are distinct
    assert cfg.validate_isolation(batch_0_raw_dir="data/raw") is True

    # Isolation check fails loudly if pointing to Batch 0 directory
    with pytest.raises(ValueError, match="Isolation violation"):
        cfg_bad = RecorderProfileV2Config(raw_storage_dir="data/raw")
        cfg_bad.validate_isolation(batch_0_raw_dir="data/raw")

    # High frequency resolution verified
    assert cfg.binance_depth_stream == IngestionResolution.DEPTH_100MS.value


def test_liquidation_proxy_tagging_invariants():
    """Verify that liquidation streams are tagged as PARTIAL_LIQUIDATION_INDICATOR."""
    tag_info = get_profile_v2_tag_for_stream("!forceOrder@arr")
    assert tag_info.tag == LiquidationStreamTag.PARTIAL_LIQUIDATION_INDICATOR.value
    assert tag_info.is_partial_proxy is True
    assert "partial" in tag_info.notes.lower()


def test_bybit_adapter_orderbook_and_liquidation_parsing():
    """Verify Bybit linear WebSocket payload parsing and comparative documentation."""
    # 1. Orderbook snapshot
    raw_depth = {
        "topic": "orderbook.50.BTCUSDT",
        "ts": 1700000000123,
        "data": {
            "s": "BTCUSDT",
            "b": [["60000.0", "1.5"], ["59990.0", "2.0"]],
            "a": [["60010.0", "0.8"], ["60020.0", "3.0"]],
        },
    }
    snap = BybitLinearPerpetualAdapter.parse_orderbook_snapshot(raw_depth)
    assert snap is not None
    assert snap.symbol == "BTCUSDT"
    assert snap.venue == "bybit"
    assert snap.bids_price[0] == 60000.0
    assert snap.bids_size[0] == 1.5
    assert snap.asks_price[0] == 60010.0
    assert snap.asks_size[0] == 0.8

    # 2. Liquidation event
    raw_liq = {
        "topic": "allLiquidation.BTCUSDT",
        "data": {
            "symbol": "BTCUSDT",
            "side": "Buy",
            "price": "60100.5",
            "size": "0.25",
            "updatedTime": 1700000000123,
        },
    }
    liq = BybitLinearPerpetualAdapter.parse_liquidation_event(raw_liq)
    assert liq is not None
    assert liq.symbol == "BTCUSDT"
    assert liq.side == "Buy"
    assert liq.price == 60100.5
    assert liq.tag == LiquidationStreamTag.PARTIAL_LIQUIDATION_INDICATOR.value
    assert liq.is_partial_proxy is True

    # 3. Comparative evaluation report
    eval_doc = BybitLinearPerpetualAdapter.get_comparative_evaluation()
    assert "binance_usdt_futures" in eval_doc
    assert "bybit_linear_perpetuals" in eval_doc
    assert "PARTIAL_LIQUIDATION_INDICATOR" in eval_doc["binance_usdt_futures"]["liquidation_stream_limitation"]
