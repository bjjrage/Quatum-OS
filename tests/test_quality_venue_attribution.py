"""Regression: rows/symbols must be attributed to the venue that owns the files, tables without a `venue`
column (deribit_metrics, futures_open_interest, metadata history) must be counted, never silently dropped."""
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.quality.metrics import QualityMetricsCollector as Engine
from config.settings import settings


def _write(base: Path, venue: str, table: str, rows: dict):
    d = base / venue / f"table={table}" / "year=2026" / "month=10" / "day=03" / "hour=01"
    d.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(rows), d / "part-1.parquet")


def test_symbols_and_tables_are_attributed_per_venue(tmp_path):
    ts = [1_791_000_000_000_000_000, 1_791_000_001_000_000_000]
    _write(tmp_path, "polymarket", "bbo_ticks", {"ts_received_utc_ns": ts, "venue": ["polymarket"] * 2, "symbol": ["0xabc", "0xdef"]})
    _write(tmp_path, "binance_perp", "bbo_ticks", {"ts_received_utc_ns": ts, "venue": ["binance_perp"] * 2, "symbol": ["BTCUSDT", "ETHUSDT"]})
    _write(tmp_path, "binance_perp", "futures_open_interest", {"ts_received_utc_ns": ts, "symbol": ["BTCUSDT"] * 2, "open_interest": [1.0, 2.0]})
    _write(tmp_path, "deribit", "deribit_metrics", {"ts_received_utc_ns": ts, "instrument_name": ["BTC-9OCT26-100000-C"] * 2})
    _write(tmp_path, "polymarket", "polymarket_metadata_history", {"ts_polled_utc_ns": ts, "question": ["q"] * 2})
    eng = Engine(base_data_path=tmp_path)
    _, feeds = eng.collect_duckdb_metrics()
    assert feeds["binance_perp"].unique_symbols == ["BTCUSDT", "ETHUSDT"]
    assert feeds["polymarket"].unique_symbols == ["0xabc", "0xdef"], "polymarket tokens must not leak to other venues"
    assert "0xabc" not in feeds["binance_perp"].unique_symbols and "0xabc" not in feeds["deribit"].unique_symbols
    assert "futures_open_interest" in feeds["binance_perp"].tables
    assert feeds["deribit"].tables.get("deribit_metrics") == 2
    assert feeds["polymarket"].tables.get("polymarket_metadata_history") == 2
