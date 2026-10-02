"""Tests for StorageSink: atomic part-based append, checksums, and DuckDB readability."""
import asyncio
import json
import pytest
import time
from pathlib import Path
import duckdb

from src.common.storage_sink import StorageSink


@pytest.mark.asyncio
async def test_storage_sink_append_and_flush(tmp_path: Path) -> None:
    sink = StorageSink(
        base_path=tmp_path,
        flush_interval_sec=300.0,
        flush_row_threshold=1000,
        compression="zstd",
        manifest_enabled=True,
    )
    await sink.start()

    now_utc = time.time_ns()
    now_mono = time.monotonic_ns()

    rows = [
        {
            "ts_exchange_ns": now_utc - 5_000_000,
            "ts_received_utc_ns": now_utc,
            "ts_received_mono_ns": now_mono,
            "observed_event_age_ns": 5_000_000,
            "venue": "binance_perp",
            "symbol": "BTCUSDT",
            "bid_price": 65100.0 + i,
            "bid_size": 1.0,
            "ask_price": 65101.0 + i,
            "ask_size": 1.2,
            "spread": 1.0,
        }
        for i in range(10)
    ]

    await sink.append_batch("binance_perp", "bbo_ticks", rows)
    await sink.stop()

    # Verify parquet file exists in partition directory
    parquet_files = list(tmp_path.glob("**/*.parquet"))
    assert len(parquet_files) == 1
    part_file = parquet_files[0]
    assert part_file.name.startswith("part-")
    assert part_file.name.endswith(".parquet")

    # Verify manifest.json exists
    manifest_files = list(tmp_path.glob("**/manifest.json"))
    assert len(manifest_files) == 1
    with open(manifest_files[0], "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    assert manifest_data["total_rows"] == 10
    assert len(manifest_data["parts"]) == 1
    assert "sha256" in manifest_data["parts"][0]

    # Verify file is readable by DuckDB
    con = duckdb.connect()
    res = con.execute(f"SELECT COUNT(*), AVG(bid_price) FROM read_parquet('{part_file.as_posix()}')").fetchone()
    assert res is not None
    assert res[0] == 10
    assert res[1] > 65100.0
