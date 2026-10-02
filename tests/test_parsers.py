"""Tests for market data event message parsers across all 3 venues."""
import pytest
import time
from pathlib import Path

from src.common.storage_sink import StorageSink
from src.collectors.polymarket_recorder import PolymarketRecorder
from src.collectors.deribit_recorder import DeribitRecorder
from src.collectors.binance_recorder import BinanceRecorder


@pytest.mark.asyncio
async def test_polymarket_message_parser(tmp_path: Path) -> None:
    sink = StorageSink(base_path=tmp_path, flush_interval_sec=100.0)
    recorder = PolymarketRecorder(sink)

    now_utc = time.time_ns()
    now_mono = time.monotonic_ns()

    # 1. Test last_trade_price
    trade_json = '{"event_type": "last_trade_price", "asset_id": "poly_btc_1", "price": 0.55, "size": 100.0, "side": "BUY", "timestamp": 1727885400000}'
    await recorder._handle_message(trade_json, now_utc, now_mono)

    # 2. Test best_bid_ask (custom feature)
    bbo_json = '{"event_type": "best_bid_ask", "asset_id": "poly_btc_1", "best_bid": 0.54, "best_ask": 0.56, "bid_size": 200.0, "ask_size": 150.0, "timestamp": 1727885400000}'
    await recorder._handle_message(bbo_json, now_utc, now_mono)

    # Check buffered rows
    assert len(sink._buffers[("polymarket", "trade_ticks")]) == 1
    assert len(sink._buffers[("polymarket", "bbo_ticks")]) == 1
    trade_row = sink._buffers[("polymarket", "trade_ticks")][0]
    assert trade_row["price"] == 0.55
    assert trade_row["symbol"] == "poly_btc_1"


@pytest.mark.asyncio
async def test_binance_message_parser(tmp_path: Path) -> None:
    sink = StorageSink(base_path=tmp_path, flush_interval_sec=100.0)
    recorder = BinanceRecorder(sink)

    now_utc = time.time_ns()
    now_mono = time.monotonic_ns()

    # 1. Test public stream: bookTicker
    bbo_json = '{"stream": "btcusdt@bookTicker", "data": {"e": "bookTicker", "s": "BTCUSDT", "b": "65000.1", "B": "2.5", "a": "65000.2", "A": "3.1", "E": 1727885400123}}'
    await recorder._handle_public_message(bbo_json, now_utc, now_mono)

    # 2. Test market stream: aggTrade
    trade_json = '{"stream": "btcusdt@aggTrade", "data": {"e": "aggTrade", "s": "BTCUSDT", "a": 987654321, "p": "65000.15", "q": "0.15", "m": false, "T": 1727885400234}}'
    await recorder._handle_market_message(trade_json, now_utc, now_mono)

    # 3. Test market stream: !forceOrder@arr with st=1 (USD(S)-M)
    liq_json = '{"stream": "!forceOrder@arr", "data": {"e": "forceOrder", "o": {"s": "BTCUSDT", "ps": "BTCUSDT", "st": 1, "S": "SELL", "p": "64950.0", "q": "0.8", "z": "0.8"}, "E": 1727885400345}}'
    await recorder._handle_market_message(liq_json, now_utc, now_mono)

    # 4. Test market stream: !forceOrder@arr with st=2 (Coin-M) -> Should be filtered out!
    liq_coin_m = '{"stream": "!forceOrder@arr", "data": {"e": "forceOrder", "o": {"s": "BTCUSD_PERP", "ps": "BTCUSD", "st": 2, "S": "SELL", "p": "64950.0", "q": "10", "z": "10"}, "E": 1727885400345}}'
    await recorder._handle_market_message(liq_coin_m, now_utc, now_mono)

    assert len(sink._buffers[("binance_perp", "bbo_ticks")]) == 1
    assert len(sink._buffers[("binance_perp", "trade_ticks")]) == 1
    assert len(sink._buffers[("binance_perp", "forced_liquidations")]) == 1  # Only 1 (st=1)

    liq_row = sink._buffers[("binance_perp", "forced_liquidations")][0]
    assert liq_row["is_partial_proxy"] is True
    assert liq_row["symbol_type"] == 1
