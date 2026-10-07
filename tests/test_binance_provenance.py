import asyncio
import math
from array import array

import pyarrow as pa
import pyarrow.parquet as pq

from src.collectors.binance_recorder import BinanceRecorder
from src.research.recorder_studies import binance_seconds, bbo_source_counts, mid_at_or_before


class _Sink:
    def __init__(self):
        self.rows = []

    async def append(self, venue, table, row):
        self.rows.append((venue, table, row))


def test_binance_ws_and_rest_provenance(tmp_path):
    sink = _Sink()
    rec = BinanceRecorder(sink)
    raw = '{"stream":"btcusdt@bookTicker","data":{"e":"bookTicker","s":"BTCUSDT","E":1000,"b":"99","B":"2","a":"101","A":"3"}}'
    asyncio.run(rec._handle_public_message(raw, 1_000_000_001, 5))
    assert sink.rows[0][2]["capture_source"] == "websocket"

    rows = rec.rest_book_rows([{"symbol": "BTCUSDT", "bidPrice": "99", "bidQty": "2",
                                "askPrice": "101", "askQty": "3", "time": 1000}],
                              {"BTCUSDT"}, 1_000_000_001, 5)
    assert rows[0]["capture_source"] == "rest_fallback"


def test_legacy_parquet_is_unknown_and_rest_excluded_by_default(tmp_path):
    out = tmp_path / "binance_perp" / "table=bbo_ticks" / "old.parquet"
    out.parent.mkdir(parents=True)
    # This old file deliberately has no capture_source column.
    pq.write_table(pa.table({"ts_exchange_ns": [10_000_000_000], "ts_received_utc_ns": [12_000_000_000],
                             "symbol": ["BTCUSDT"], "bid_price": [99.0], "ask_price": [101.0]}), out)
    newer = out.parent / "new.parquet"
    pq.write_table(pa.table({"ts_exchange_ns": [10_500_000_000, 10_700_000_000],
                             "ts_received_utc_ns": [12_500_000_000, 12_700_000_000],
                             "symbol": ["BTCUSDT", "BTCUSDT"], "bid_price": [199.0, 299.0],
                             "ask_price": [201.0, 301.0], "capture_source": ["websocket", "rest_fallback"]}), newer)

    counts = bbo_source_counts(tmp_path)
    assert counts == {"rows_websocket": 1, "rows_rest_fallback": 1, "rows_unknown": 1,
                      "fallback_pct": 100 / 3}
    s0, quotes, _ = binance_seconds(tmp_path)
    assert (quotes["BTCUSDT"][0][0] + quotes["BTCUSDT"][1][0]) / 2 == 200.0
    _, all_quotes, _ = binance_seconds(tmp_path, include_rest_fallback=True)
    assert (all_quotes["BTCUSDT"][0][0] + all_quotes["BTCUSDT"][1][0]) / 2 == 300.0


def test_causal_mid_never_uses_future_or_stale_quotes():
    b, a = array("d", [math.nan, math.nan, 99.0, math.nan]), array("d", [math.nan, math.nan, 101.0, math.nan])
    assert math.isnan(mid_at_or_before(b, a, 0, 30))  # future-only quote
    assert mid_at_or_before(b, a, 3, 1) == 100.0
    assert math.isnan(mid_at_or_before(b, a, 3, 0))
