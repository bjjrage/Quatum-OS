"""Normalized types and schemas for Batch 0 market data recorder.

TIMESTAMP DEFINITIONS:
- ts_exchange_ns: Epoch timestamp in UTC nanoseconds as reported by the exchange.
- ts_received_utc_ns: Application receive timestamp captured immediately when the application
                      receives/processes the WebSocket message (UTC epoch nanoseconds).
- ts_received_mono_ns: Monotonic timestamp local (nanoseconds), reserved exclusively
                       for internal durations/intervals.
- observed_event_age_ns: Latency estimate / observed age (ts_received_utc_ns - ts_exchange_ns).
                         Not exact socket/kernel network latency.
- clock_offset_ns: Estimated local NTP clock offset in nanoseconds (nullable).
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import pyarrow as pa


class Venue(str, Enum):
    POLYMARKET = "polymarket"
    DERIBIT = "deribit"
    BINANCE_PERP = "binance_perp"
    PUMPFUN = "pumpfun"


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class RawEnvelope(BaseModel):
    envelope_id: str
    venue: str
    stream_channel: str
    received_utc_ns: int
    raw_payload: str


class BboTick(BaseModel):
    ts_exchange_ns: Optional[int] = None
    ts_received_utc_ns: int
    ts_received_mono_ns: int
    observed_event_age_ns: Optional[int] = None
    venue: str
    symbol: str
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    spread: float
    capture_source: str = "unknown"


class TradeTick(BaseModel):
    ts_exchange_ns: Optional[int] = None
    ts_received_utc_ns: int
    ts_received_mono_ns: int
    observed_event_age_ns: Optional[int] = None
    venue: str
    symbol: str
    trade_id: str
    side: str
    price: float
    size: float


class OrderbookL2Depth(BaseModel):
    ts_exchange_ns: Optional[int] = None
    ts_received_utc_ns: int
    ts_received_mono_ns: int
    venue: str
    symbol: str
    bids_price: List[float]
    bids_size: List[float]
    asks_price: List[float]
    asks_size: List[float]
    depth_level: int


class DeribitMetrics(BaseModel):
    ts_exchange_ns: Optional[int] = None
    ts_received_utc_ns: int
    ts_received_mono_ns: int
    instrument_name: str
    underlying_price: float
    mark_price: float
    mark_iv: float
    bid_iv: float
    ask_iv: float
    delta: float
    gamma: float
    vega: float
    theta: float
    underlying_index_price: float
    dvol_index: float


class FuturesOpenInterest(BaseModel):
    ts_exchange_ns: Optional[int] = None
    ts_received_utc_ns: int
    ts_received_mono_ns: int
    symbol: str
    open_interest: float
    is_stale: bool = False
    poll_latency_ms: float = 0.0


class ForcedLiquidation(BaseModel):
    ts_exchange_ns: Optional[int] = None
    ts_received_utc_ns: int
    ts_received_mono_ns: int
    symbol: str
    pair_symbol: Optional[str] = None  # ps
    symbol_type: Optional[int] = None   # st (1 for USDⓈ-M)
    side: str
    price: float
    orig_qty: float
    executed_qty: float
    is_partial_proxy: bool = True       # Documented partial proxy stream


class PolymarketMetadataHistory(BaseModel):
    ts_polled_utc_ns: int
    market_id: str
    condition_id: str
    question: str
    resolution_source: str
    end_date_iso: str
    fee_schedule_raw_json: str
    fee_model_version: str
    status: str


# PyArrow Table Schemas for parquet sinks
SCHEMAS: Dict[str, pa.Schema] = {
    # --- pump.fun (Solana), decodificado de los eventos del programa ---
    "pumpfun_trades": pa.schema([
        ("ts_received_utc_ns", pa.int64()),
        ("slot", pa.int64()),
        ("signature", pa.string()),
        ("mint", pa.string()),
        ("user", pa.string()),
        ("is_buy", pa.bool_()),
        ("sol_amount", pa.int64()),            # lamports (1 SOL = 1e9)
        ("token_amount", pa.int64()),          # unidades mínimas (6 decimales)
        ("ts_chain_s", pa.int64()),
        ("virtual_sol_reserves", pa.int64()),
        ("virtual_token_reserves", pa.int64()),
        ("real_sol_reserves", pa.int64()),
        ("real_token_reserves", pa.int64()),
        ("creator", pa.string()),
        ("fee", pa.int64()),
        ("creator_fee", pa.int64()),
    ]),
    "pumpfun_creates": pa.schema([
        ("ts_received_utc_ns", pa.int64()),
        ("slot", pa.int64()),
        ("signature", pa.string()),
        ("mint", pa.string()),
        ("name", pa.string()),
        ("symbol", pa.string()),
        ("uri", pa.string()),
        ("bonding_curve", pa.string()),
        ("user", pa.string()),
        ("creator", pa.string()),
        ("ts_chain_s", pa.int64()),
    ]),
    "depth_snapshots": pa.schema([
        ("ts_utc_ns", pa.int64()),
        ("symbol", pa.string()),
        ("mid", pa.float64()),
        ("spread_bps", pa.float64()),
        ("bid_usd_05", pa.float64()),
        ("ask_usd_05", pa.float64()),
        ("imbalance_05", pa.float64()),
        ("bid_usd_1", pa.float64()),
        ("ask_usd_1", pa.float64()),
        ("imbalance_1", pa.float64()),
        ("open_interest", pa.float64()),
    ]),
    "x_mentions": pa.schema([
        ("ts_query_utc_ns", pa.int64()),
        ("mint", pa.string()),
        ("symbol", pa.string()),
        ("name", pa.string()),
        ("token_age_s", pa.int64()),
        ("unique_buyers_5m", pa.int64()),
        ("net_buy_sol_5m", pa.float64()),
        ("posts_found", pa.int64()),
        ("earliest_post_utc", pa.string()),
        ("accounts_json", pa.string()),
        ("max_followers", pa.int64()),
        ("total_followers", pa.int64()),
        ("has_large_account", pa.bool_()),
        ("coordinated_shilling", pa.bool_()),
        ("summary", pa.string()),
        ("cost_usd", pa.float64()),
        ("model", pa.string()),
        ("x_status", pa.string()),
        ("consumer", pa.string()),
        ("query_version", pa.string()),
        ("query_hash", pa.string()),
        ("request_id", pa.string()),
    ]),
    "token_boosts": pa.schema([                     # dexscreener: promoción paga
        ("ts_polled_utc_ns", pa.int64()),
        ("chain_id", pa.string()),
        ("token_address", pa.string()),
        ("amount", pa.float64()),
        ("total_amount", pa.float64()),
        ("url", pa.string()),
        ("description", pa.string()),
        ("links_json", pa.string()),
    ]),
    "token_profiles": pa.schema([                   # dexscreener: perfil pago
        ("ts_polled_utc_ns", pa.int64()),
        ("chain_id", pa.string()),
        ("token_address", pa.string()),
        ("url", pa.string()),
        ("description", pa.string()),
        ("links_json", pa.string()),
    ]),
    "token_prices": pa.schema([                     # dexscreener: precio de tokens promocionados (todas las chains)
        ("ts_polled_utc_ns", pa.int64()),
        ("chain_id", pa.string()),
        ("token_address", pa.string()),
        ("pair_address", pa.string()),
        ("dex_id", pa.string()),
        ("price_usd", pa.float64()),
        ("price_native", pa.float64()),
        ("liquidity_usd", pa.float64()),
        ("fdv", pa.float64()),
        ("market_cap", pa.float64()),
        ("volume_m5", pa.float64()),
        ("volume_h1", pa.float64()),
        ("buys_m5", pa.int64()),
        ("sells_m5", pa.int64()),
        ("pair_created_ms", pa.int64()),
    ]),
    "calls": pa.schema([                            # telegram: contratos publicados en canales de calls
        ("ts_message_utc_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("channel", pa.string()),
        ("channel_id", pa.int64()),
        ("message_id", pa.int64()),
        ("chain", pa.string()),
        ("token_address", pa.string()),
        ("views", pa.int64()),
        ("is_forward", pa.bool_()),
        ("text", pa.string()),
    ]),
    "pumpfun_completes": pa.schema([
        ("ts_received_utc_ns", pa.int64()),
        ("slot", pa.int64()),
        ("signature", pa.string()),
        ("mint", pa.string()),
        ("user", pa.string()),
        ("bonding_curve", pa.string()),
        ("ts_chain_s", pa.int64()),
    ]),
    "bbo_ticks": pa.schema([
        ("ts_exchange_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("ts_received_mono_ns", pa.int64()),
        ("observed_event_age_ns", pa.int64()),
        ("venue", pa.string()),
        ("symbol", pa.string()),
        ("bid_price", pa.float64()),
        ("bid_size", pa.float64()),
        ("ask_price", pa.float64()),
        ("ask_size", pa.float64()),
        ("spread", pa.float64()),
        ("capture_source", pa.string()),
    ]),
    "trade_ticks": pa.schema([
        ("ts_exchange_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("ts_received_mono_ns", pa.int64()),
        ("observed_event_age_ns", pa.int64()),
        ("venue", pa.string()),
        ("symbol", pa.string()),
        ("trade_id", pa.string()),
        ("side", pa.string()),
        ("price", pa.float64()),
        ("size", pa.float64()),
    ]),
    "orderbook_l2_depth": pa.schema([
        ("ts_exchange_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("ts_received_mono_ns", pa.int64()),
        ("venue", pa.string()),
        ("symbol", pa.string()),
        ("bids_price", pa.list_(pa.float64())),
        ("bids_size", pa.list_(pa.float64())),
        ("asks_price", pa.list_(pa.float64())),
        ("asks_size", pa.list_(pa.float64())),
        ("depth_level", pa.int32()),
    ]),
    "deribit_metrics": pa.schema([
        ("ts_exchange_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("ts_received_mono_ns", pa.int64()),
        ("instrument_name", pa.string()),
        ("underlying_price", pa.float64()),
        ("mark_price", pa.float64()),
        ("mark_iv", pa.float64()),
        ("bid_iv", pa.float64()),
        ("ask_iv", pa.float64()),
        ("delta", pa.float64()),
        ("gamma", pa.float64()),
        ("vega", pa.float64()),
        ("theta", pa.float64()),
        ("underlying_index_price", pa.float64()),
        ("dvol_index", pa.float64()),
    ]),
    "futures_open_interest": pa.schema([
        ("ts_exchange_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("ts_received_mono_ns", pa.int64()),
        ("symbol", pa.string()),
        ("open_interest", pa.float64()),
        ("is_stale", pa.bool_()),
        ("poll_latency_ms", pa.float64()),
    ]),
    "futures_market_metrics": pa.schema([
        ("ts_exchange_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("ts_received_mono_ns", pa.int64()),
        ("symbol", pa.string()),
        ("mark_price", pa.float64()),
        ("index_price", pa.float64()),
        ("funding_rate", pa.float64()),
    ]),
    "forced_liquidations": pa.schema([
        ("ts_exchange_ns", pa.int64()),
        ("ts_received_utc_ns", pa.int64()),
        ("ts_received_mono_ns", pa.int64()),
        ("symbol", pa.string()),
        ("pair_symbol", pa.string()),
        ("symbol_type", pa.int32()),
        ("side", pa.string()),
        ("price", pa.float64()),
        ("orig_qty", pa.float64()),
        ("executed_qty", pa.float64()),
        ("is_partial_proxy", pa.bool_()),
    ]),
    "polymarket_metadata_history": pa.schema([
        ("ts_polled_utc_ns", pa.int64()),
        ("market_id", pa.string()),
        ("condition_id", pa.string()),
        ("question", pa.string()),
        ("resolution_source", pa.string()),
        ("end_date_iso", pa.string()),
        ("fee_schedule_raw_json", pa.string()),
        ("fee_model_version", pa.string()),
        ("status", pa.string()),
        ("clob_token_ids_json", pa.string()),   # [YES_token, NO_token]: required to join books/trades to a question
        ("outcomes_json", pa.string()),
        ("description", pa.string()),            # resolution rules text (source, time, tie-breaks)
    ]),
}
