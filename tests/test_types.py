"""Tests for types and schema definitions."""
import time
from src.common.types import (
    BboTick,
    TradeTick,
    OrderbookL2Depth,
    DeribitMetrics,
    FuturesOpenInterest,
    ForcedLiquidation,
    PolymarketMetadataHistory,
    SCHEMAS,
)


def test_bbo_tick_model() -> None:
    now_utc = time.time_ns()
    now_mono = time.monotonic_ns()
    tick = BboTick(
        ts_exchange_ns=now_utc - 10_000_000,
        ts_received_utc_ns=now_utc,
        ts_received_mono_ns=now_mono,
        observed_event_age_ns=10_000_000,
        venue="binance_perp",
        symbol="BTCUSDT",
        bid_price=65000.0,
        bid_size=1.5,
        ask_price=65001.0,
        ask_size=2.0,
        spread=1.0,
    )
    assert tick.symbol == "BTCUSDT"
    assert tick.spread == 1.0
    assert tick.observed_event_age_ns == 10_000_000


def test_forced_liquidation_partial_proxy() -> None:
    now_utc = time.time_ns()
    now_mono = time.monotonic_ns()
    liq = ForcedLiquidation(
        ts_exchange_ns=now_utc,
        ts_received_utc_ns=now_utc,
        ts_received_mono_ns=now_mono,
        symbol="BTCUSDT",
        pair_symbol="BTCUSDT",
        symbol_type=1,
        side="SELL",
        price=64000.0,
        orig_qty=0.5,
        executed_qty=0.5,
    )
    assert liq.is_partial_proxy is True
    assert liq.symbol_type == 1


def test_arrow_schemas_completeness() -> None:
    expected_tables = {
        "bbo_ticks",
        "trade_ticks",
        "orderbook_l2_depth",
        "deribit_metrics",
        "futures_open_interest",
        "futures_market_metrics",
        "forced_liquidations",
        "polymarket_metadata_history",
        "pumpfun_trades",
        "pumpfun_creates",
        "pumpfun_completes",
        "x_mentions",
        "depth_snapshots",
    }
    assert set(SCHEMAS.keys()) == expected_tables
    for table_name, schema in SCHEMAS.items():
        if table_name == "polymarket_metadata_history":
            assert "ts_polled_utc_ns" in schema.names
        elif table_name == "depth_snapshots":
            assert "ts_utc_ns" in schema.names and "imbalance_05" in schema.names
        elif table_name == "x_mentions":
            assert "ts_query_utc_ns" in schema.names and "mint" in schema.names
        elif table_name.startswith("pumpfun_"):
            assert "ts_received_utc_ns" in schema.names and "slot" in schema.names
        else:
            assert "ts_received_utc_ns" in schema.names
            assert "ts_received_mono_ns" in schema.names
