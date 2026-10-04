"""Global configuration settings for Trading OS Batch 0 Data Recorder."""
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

class PolymarketConfig(BaseModel):
    ws_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    gamma_api_url: str = "https://gamma-api.polymarket.com/markets"
    clob_api_url: str = "https://clob.polymarket.com"
    standard_events: List[str] = Field(
        default_factory=lambda: ["book", "price_change", "last_trade_price", "tick_size_change"]
    )
    custom_feature_enabled: bool = True
    custom_events: List[str] = Field(
        default_factory=lambda: ["best_bid_ask", "new_market", "market_resolved"]
    )
    heartbeat_interval_sec: float = 10.0
    discovery_interval_sec: float = 900.0  # 15 minutes
    book_snapshot_interval_sec: float = 60.0  # REST /books polling: WS only sends `book` once per subscription
    crypto_keywords: List[str] = Field(
        default_factory=lambda: ["Bitcoin", "BTC", "Ethereum", "ETH", "Solana", "SOL"]
    )

class DeribitConfig(BaseModel):
    ws_url: str = "wss://www.deribit.com/ws/api/v2"
    rest_url: str = "https://www.deribit.com/api/v2"
    heartbeat_interval_sec: float = 15.0
    max_expiry_days: int = 60
    moneyness_min: float = 0.75
    moneyness_max: float = 1.25
    index_channels: List[str] = Field(
        default_factory=lambda: [
            "deribit_price_index.btc_usd",
            "deribit_price_index.eth_usd",
            "deribit_volatility_index.btc_usd",
            "deribit_volatility_index.eth_usd",
        ]
    )
    trade_channels: List[str] = Field(
        default_factory=lambda: [
            "trades.option.btc.100ms",
            "trades.option.eth.100ms",
        ]
    )

class BinanceFuturesConfig(BaseModel):
    # Current 2026 separated WebSocket endpoints
    public_ws_url: str = "wss://fstream.binance.com/public/stream"
    market_ws_url: str = "wss://fstream.binance.com/market/stream"
    rest_base_url: str = "https://fapi.binance.com"
    
    # 25-contract sample by liquidity tiers
    initial_calibration_sample_v0: List[str] = Field(
        default_factory=lambda: [
            # Tier 1: Majors
            "BTCUSDT", "ETHUSDT", "SOLUSDT",
            # Tier 2: Large Caps
            "BNBUSDT", "DOGEUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
            # Tier 3: Mid Caps
            "SUIUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "TIAUSDT", "INJUSDT", "RENDERUSDT", "FETUSDT",
            # Tier 4: High-Vol Alts
            "WIFUSDT", "1000PEPEUSDT", "SEIUSDT", "BLURUSDT", "JTOUSDT", "ORDIUSDT", "MEMEUSDT",
        ]
    )
    oi_poller_interval_sec: float = 30.0
    symbol_type_filter: int = 1  # st=1 (USDⓈ-M)
    request_timeout_sec: float = 3.0
    max_retries: int = 2

class StorageConfig(BaseModel):
    base_data_path: Path = Path("data/raw")
    flush_interval_sec: float = 60.0
    flush_row_threshold: int = 5000
    compression: str = "zstd"
    compression_level: int = 7
    manifest_enabled: bool = True

class Settings(BaseModel):
    project_name: str = "trading-os"
    environment: str = "production"
    log_level: str = "INFO"
    polymarket: PolymarketConfig = Field(default_factory=PolymarketConfig)
    deribit: DeribitConfig = Field(default_factory=DeribitConfig)
    binance: BinanceFuturesConfig = Field(default_factory=BinanceFuturesConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

settings = Settings()
