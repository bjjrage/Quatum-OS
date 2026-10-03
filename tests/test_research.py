"""Unit tests for Research Infrastructure (PIT loader, features, bar aggregation, events)."""
import math
from pathlib import Path
import pytest
import pyarrow.parquet as pq

from src.research.pit_loader import PointInTimeDataLoader, SyntheticMarketGenerator
from src.research.features import FeatureEngine, BarAggregator
from src.research.events import EventDetector, ShockDirection
from src.common.storage_sink import StorageSink


def test_synthetic_market_generator_determinism() -> None:
    """Synthetic generator produces identical series with same seed and valid ticks."""
    gen1 = SyntheticMarketGenerator(seed=123)
    gen2 = SyntheticMarketGenerator(seed=123)

    ticks1 = gen1.generate_bbo_series(num_ticks=20)
    ticks2 = gen2.generate_bbo_series(num_ticks=20)

    assert len(ticks1) == 20
    assert ticks1[0]["bid_price"] == ticks2[0]["bid_price"]
    assert ticks1[-1]["ask_price"] == ticks2[-1]["ask_price"]

    # Verify polymarket generator bounds
    poly_ticks = gen1.generate_polymarket_ticks(num_ticks=30)
    assert len(poly_ticks) == 30
    for pt in poly_ticks:
        assert 0.0 < pt["bid_price"] <= 1.0
        assert 0.0 < pt["ask_price"] <= 1.0
        assert pt["bid_price"] <= pt["ask_price"]


@pytest.mark.asyncio
async def test_point_in_time_data_loader_strict_as_of(tmp_path: Path) -> None:
    """PIT loader strictly eliminates future lookahead bias based on as_of timestamp."""
    sink = StorageSink(base_path=tmp_path, flush_interval_sec=300.0, flush_row_threshold=1000)
    await sink.start()

    t0 = 1_700_000_000_000_000_000
    rows = [
        {
            "ts_exchange_ns": t0 + i * 1_000_000,
            "ts_received_utc_ns": t0 + i * 1_000_000,
            "ts_received_mono_ns": 1_000_000,
            "observed_event_age_ns": 0,
            "venue": "binance_perp",
            "symbol": "BTCUSDT",
            "bid_price": 60000.0 + i,
            "bid_size": 1.0,
            "ask_price": 60001.0 + i,
            "ask_size": 1.0,
            "spread": 1.0,
        }
        for i in range(10)
    ]
    await sink.append_batch("binance_perp", "bbo_ticks", rows)
    await sink.stop()

    loader = PointInTimeDataLoader(base_data_path=tmp_path)

    # Query as of t0 + 4ms: should return exactly 5 rows (i = 0, 1, 2, 3, 4)
    as_of = t0 + 4 * 1_000_000
    table = loader.load_table_as_of("binance_perp", "bbo_ticks", as_of_utc_ns=as_of)
    assert table.num_rows == 5

    # Rows strictly have ts_received <= as_of
    ts_col = table["ts_received_utc_ns"].to_pylist()
    assert max(ts_col) <= as_of


def test_bar_aggregator_ohlcv() -> None:
    """Bar aggregator converts irregular ticks into structured OHLCV bars."""
    agg = BarAggregator(bar_duration_ms=1000)
    t0 = 1_000_000_000_000_000  # Start of a 1s bucket

    # Ticks within 1st second
    b1 = agg.process_tick("BTCUSDT", "binance_perp", t0 + 100_000_000, price=100.0, size=2.0)
    b2 = agg.process_tick("BTCUSDT", "binance_perp", t0 + 200_000_000, price=105.0, size=1.0)
    b3 = agg.process_tick("BTCUSDT", "binance_perp", t0 + 900_000_000, price=98.0, size=1.0)
    assert b1 is None and b2 is None and b3 is None  # Bucket still open

    # First tick in 2nd second triggers emission of 1st bar
    bar = agg.process_tick("BTCUSDT", "binance_perp", t0 + 1_000_000_000, price=102.0, size=1.0)
    assert bar is not None
    assert bar.open == 100.0
    assert bar.high == 105.0
    assert bar.low == 98.0
    assert bar.close == 98.0
    assert bar.volume == 4.0
    assert bar.tick_count == 3


def test_feature_engine_calculations() -> None:
    """FeatureEngine calculates mathematical returns, volatility, and imbalance accurately."""
    prices = [100.0, 105.0, 102.0, 108.0]
    returns = FeatureEngine.calc_log_returns(prices, horizon=1)
    assert len(returns) == 3
    assert math.isclose(returns[0], math.log(105.0 / 100.0), rel_tol=1e-6)

    vol = FeatureEngine.calc_realized_volatility(returns)
    assert vol > 0.0

    imbalance = FeatureEngine.calc_orderbook_imbalance(bid_size=30.0, ask_size=10.0)
    assert imbalance == 0.5  # (30 - 10) / (30 + 10) = 20 / 40 = 0.5

    spread_bps = FeatureEngine.calc_spread_bps(bid=99.0, ask=101.0)
    assert spread_bps == 200.0  # (2 / 100) * 10000 = 200 bps


def test_event_detector_impulse_detection() -> None:
    """EventDetector flags genuine price shocks and classifies direction."""
    detector = EventDetector(vol_lookback_bars=10, impulse_threshold_z=2.0, min_return_bps=10.0)

    # 10 quiet bars (price ~100.0), then an abrupt jump to 110.0 (+10%)
    prices = [100.0 + (i % 2) * 0.1 for i in range(12)]
    prices.append(110.0)  # Shock bar
    timestamps = [1_000_000_000_000_000 + i * 1_000_000_000 for i in range(len(prices))]

    events = detector.detect_impulses(prices, timestamps, symbol="BTCUSDT")
    assert len(events) >= 1
    shock = events[0]
    assert shock.direction == ShockDirection.EXPANSION_UP
    assert shock.impulse_return > 0.05
    assert shock.z_score >= 2.0
