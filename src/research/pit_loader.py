"""Point-in-Time Data Loader and Synthetic Market Generator.

Strict Point-in-Time (PIT) invariant:
Queries only return data that was recorded and available at or before decision time T_decision:
    ts_received_utc_ns <= T_decision
This mathematically prevents future lookahead bias in research and backtesting.
"""
from dataclasses import dataclass
from pathlib import Path
import random
import time
from typing import Dict, Any, List, Optional, Generator
import duckdb
import pyarrow as pa

from config.settings import settings


@dataclass
class MarketEvent:
    """Standardized event envelope for event-driven simulation and replay."""
    event_type: str
    venue: str
    symbol: str
    ts_received_utc_ns: int
    data: Dict[str, Any]


class PointInTimeDataLoader:
    """Loads historical lakehouse data strictly respecting point-in-time constraints."""

    def __init__(self, base_data_path: Optional[Path] = None):
        self.base_data_path = Path(base_data_path or settings.storage.base_data_path)

    def load_table_as_of(
        self,
        venue: str,
        table_name: str,
        as_of_utc_ns: int,
        start_utc_ns: Optional[int] = None,
        symbol: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pa.Table:
        """Query rows from Parquet partitions strictly received on or before as_of_utc_ns."""
        pattern = self.base_data_path / venue / f"table={table_name}" / "**/*.parquet"
        files = list(self.base_data_path.glob(f"{venue}/table={table_name}/**/*.parquet"))
        
        if not files:
            # Return empty table matching known schema or empty pyarrow table
            from src.common.types import SCHEMAS
            schema = SCHEMAS.get(table_name, pa.schema([("ts_received_utc_ns", pa.int64())]))
            return pa.Table.from_batches([], schema=schema)

        file_paths = [f.as_posix() for f in files]
        con = duckdb.connect()

        where_clauses = [f"ts_received_utc_ns <= {as_of_utc_ns}"]
        if start_utc_ns is not None:
            where_clauses.append(f"ts_received_utc_ns >= {start_utc_ns}")
        if symbol is not None:
            where_clauses.append(f"symbol = '{symbol}'")

        where_sql = " AND ".join(where_clauses)
        limit_sql = f" LIMIT {limit}" if limit else ""

        query = f"""
            SELECT * 
            FROM read_parquet({file_paths})
            WHERE {where_sql}
            ORDER BY ts_received_utc_ns ASC
            {limit_sql}
        """

        reader = con.execute(query).arrow()
        arrow_table = reader.read_all() if hasattr(reader, "read_all") else reader
        con.close()
        return arrow_table

    def stream_events_as_of(
        self,
        venues: List[str],
        start_utc_ns: int,
        end_utc_ns: int,
        batch_size: int = 5000,
    ) -> Generator[MarketEvent, None, None]:
        """Stream chronological market events across multiple venues in strict arrival order."""
        all_files = []
        for v in venues:
            all_files.extend(list(self.base_data_path.glob(f"{v}/**/*.parquet")))

        if not all_files:
            return

        file_paths = [f.as_posix() for f in all_files]
        con = duckdb.connect()

        query = f"""
            SELECT 
                venue,
                symbol,
                ts_received_utc_ns,
                bid_price,
                ask_price,
                spread
            FROM read_parquet({file_paths})
            WHERE ts_received_utc_ns >= {start_utc_ns} 
              AND ts_received_utc_ns <= {end_utc_ns}
            ORDER BY ts_received_utc_ns ASC
        """

        cursor = con.execute(query)
        while True:
            chunk = cursor.fetch_arrow_chunk()
            if chunk is None or chunk.num_rows == 0:
                break
            
            pydict = chunk.to_pydict()
            for i in range(chunk.num_rows):
                yield MarketEvent(
                    event_type="bbo_tick",
                    venue=pydict["venue"][i],
                    symbol=pydict["symbol"][i],
                    ts_received_utc_ns=pydict["ts_received_utc_ns"][i],
                    data={
                        "bid_price": pydict["bid_price"][i],
                        "ask_price": pydict["ask_price"][i],
                        "spread": pydict["spread"][i],
                    },
                )
        con.close()


class SyntheticMarketGenerator:
    """Generates synthetic, deterministic multi-venue market data for offline research."""

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_bbo_series(
        self,
        symbol: str = "BTCUSDT",
        initial_price: float = 65000.0,
        num_ticks: int = 100,
        volatility_bps: float = 5.0,
        dt_ns: int = 100_000_000,  # 100ms
        start_ts_ns: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Generate synthetic BBO ticks with geometric random walk and realistic spreads."""
        ts = start_ts_ns or 1_700_000_000_000_000_000
        price = initial_price
        ticks = []

        for _ in range(num_ticks):
            # Price jump
            ret = self.rng.gauss(0.0, volatility_bps * 1e-4)
            price = round(price * (1.0 + ret), 2)
            spread = round(max(0.1, price * 0.0001), 2)
            bid = round(price - spread / 2.0, 2)
            ask = round(price + spread / 2.0, 2)

            tick = {
                "ts_exchange_ns": ts - 20_000_000,  # 20ms network latency
                "ts_received_utc_ns": ts,
                "ts_received_mono_ns": ts,
                "observed_event_age_ns": 20_000_000,
                "venue": "binance_perp",
                "symbol": symbol,
                "bid_price": bid,
                "bid_size": round(self.rng.uniform(0.5, 5.0), 4),
                "ask_price": ask,
                "ask_size": round(self.rng.uniform(0.5, 5.0), 4),
                "spread": spread,
            }
            ticks.append(tick)
            ts += dt_ns

        return ticks

    def generate_polymarket_ticks(
        self,
        token_id: str = "BTC-ABOVE-65K-20261015",
        initial_prob: float = 0.52,
        num_ticks: int = 100,
        dt_ns: int = 500_000_000,
        start_ts_ns: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Generate binary prediction market contract ticks ($0.00 - $1.00)."""
        ts = start_ts_ns or 1_700_000_000_000_000_000
        prob = initial_prob
        ticks = []

        for _ in range(num_ticks):
            prob = max(0.01, min(0.99, prob + self.rng.gauss(0.0, 0.005)))
            spread = 0.01
            bid = round(max(0.01, prob - spread / 2.0), 3)
            ask = round(min(0.99, prob + spread / 2.0), 3)

            tick = {
                "ts_exchange_ns": ts - 30_000_000,
                "ts_received_utc_ns": ts,
                "ts_received_mono_ns": ts,
                "observed_event_age_ns": 30_000_000,
                "venue": "polymarket",
                "symbol": token_id,
                "bid_price": bid,
                "bid_size": round(self.rng.uniform(100.0, 5000.0), 1),
                "ask_price": ask,
                "ask_size": round(self.rng.uniform(100.0, 5000.0), 1),
                "spread": round(ask - bid, 3),
            }
            ticks.append(tick)
            ts += dt_ns

        return ticks
