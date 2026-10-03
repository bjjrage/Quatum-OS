"""Deribit Options & Underlying WebSocket recorder (DERIBIT RAW SCOPE v0)."""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Set, Optional
import aiohttp
import websockets

from config.settings import settings
from src.common.logger import setup_logger
from src.common.storage_sink import StorageSink
from src.common.types import Venue

logger = setup_logger("deribit_recorder")


def parse_deribit_expiry_timestamp(instrument_name: str) -> float:
    """Parse Deribit instrument name like BTC-27MAR26-65000-C into epoch timestamp for chronological sorting.
    
    Prevents alphabetical sorting bug where '1OCT26' sorted before '26DEC25'.
    """
    try:
        parts = instrument_name.split("-")
        if len(parts) >= 2:
            dt = datetime.strptime(parts[1], "%d%b%y")
            return dt.timestamp()
    except Exception:
        pass
    return float("inf")


class DeribitRecorder:
    """Records Deribit option tickers, orderbooks, trades, index prices and DVOL."""

    def __init__(self, sink: StorageSink):
        self.sink = sink
        self.config = settings.deribit
        self.active_instruments: Set[str] = set()
        self.underlying_prices: Dict[str, float] = {"BTC": 0.0, "ETH": 0.0}
        self.dvol_indices: Dict[str, float] = {"BTC": 0.0, "ETH": 0.0}
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[Any] = None
        self._subscribed_channels: Set[str] = set()
        self._ws_task: Optional[asyncio.Task] = None
        self._instrument_poller_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start instrument discovery and WebSocket connection."""
        self._running = True
        self._session = aiohttp.ClientSession()
        logger.info("Starting Deribit Options recorder...")

        await self._discover_instruments()
        self._instrument_poller_task = asyncio.create_task(self._instrument_poller_loop())
        self._ws_task = asyncio.create_task(self._ws_listener_loop())

    async def stop(self) -> None:
        """Stop recorder cleanly."""
        self._running = False
        if self._instrument_poller_task:
            self._instrument_poller_task.cancel()
        if self._ws_task:
            self._ws_task.cancel()
        if self._session:
            await self._session.close()
        logger.info("Deribit recorder stopped.")

    async def _instrument_poller_loop(self) -> None:
        """Periodically refreshes option instruments list (every 1 hour)."""
        while self._running:
            try:
                await asyncio.sleep(3600.0)
                await self._discover_instruments()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Deribit instrument poller: {e}", exc_info=True)

    def _sort_options_chronological_atm(self, instruments: Set[str], limit: int = 60) -> List[str]:
        """Sort instruments chronologically by expiry date, then by moneyness relative to underlying."""
        def sort_key(x: str):
            parts = x.split("-")
            cur = parts[0] if parts else "BTC"
            expiry_ts = parse_deribit_expiry_timestamp(x)
            try:
                strike = float(parts[2]) if len(parts) > 2 else 0.0
            except (ValueError, IndexError):
                strike = 0.0
            underlying = self.underlying_prices.get(cur, 65000.0 if cur == "BTC" else 3500.0)
            moneyness = abs(strike - underlying) if underlying > 0 else strike
            return (expiry_ts, moneyness)

        return sorted(list(instruments), key=sort_key)[:limit]

    async def _discover_instruments(self) -> None:
        """Query Deribit REST API for active options matching RAW SCOPE v0."""
        if not self._session:
            return

        try:
            now_ms = int(time.time() * 1000)
            max_expiry_ms = now_ms + (self.config.max_expiry_days * 86400 * 1000)
            selected: Set[str] = set()

            for currency in ["BTC", "ETH"]:
                url = f"{self.config.rest_url}/public/get_instruments?currency={currency}&kind=option&expired=false"
                async with self._session.get(url, timeout=10.0) as resp:
                    if resp.status != 200:
                        continue
                    payload = await resp.json()
                    instruments = payload.get("result", [])

                for inst in instruments:
                    expiry_ms = inst.get("expiration_timestamp", 0)
                    if expiry_ms > max_expiry_ms:
                        continue  # Exclude far-dated expiries > 60 days
                    
                    # Store instrument name
                    name = inst.get("instrument_name")
                    if name:
                        selected.add(name)

            new_instruments = selected - self.active_instruments
            self.active_instruments = selected
            logger.info(f"Deribit discovered {len(self.active_instruments)} options within 60-day expiry scope ({len(new_instruments)} new).")

            # Dynamic resubscription if WS is already connected and new instruments discovered
            if new_instruments and self._ws and not getattr(self._ws, "closed", False):
                await self._resubscribe_dynamic()
        except Exception as e:
            logger.error(f"Failed to discover Deribit instruments: {e}", exc_info=True)

    async def _resubscribe_dynamic(self) -> None:
        """Resubscribe WS to new instruments dynamically after periodic discovery."""
        if not self._ws or getattr(self._ws, "closed", False):
            return
        try:
            sample_options = self._sort_options_chronological_atm(self.active_instruments, limit=60)
            new_channels: List[str] = []
            for name in sample_options:
                t_ch = f"ticker.{name}.100ms"
                b_ch = f"book.{name}.10.100ms"
                if t_ch not in self._subscribed_channels:
                    new_channels.append(t_ch)
                if b_ch not in self._subscribed_channels:
                    new_channels.append(b_ch)

            if new_channels:
                sub_payload = {
                    "jsonrpc": "2.0",
                    "id": int(time.time()),
                    "method": "public/subscribe",
                    "params": {"channels": new_channels},
                }
                await self._ws.send(json.dumps(sub_payload))
                self._subscribed_channels.update(new_channels)
                logger.info(f"Dynamically subscribed to {len(new_channels)} new Deribit channels.")
        except Exception as e:
            logger.warning(f"Failed dynamic Deribit resubscription: {e}")

    async def _ws_listener_loop(self) -> None:
        """Main WebSocket loop for Deribit JSON-RPC 2.0 with auto-reconnect."""
        backoff = 1.0
        while self._running:
            try:
                logger.info(f"Connecting to Deribit WS at {self.config.ws_url}...")
                async with websockets.connect(
                    self.config.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5.0,
                ) as ws:
                    self._ws = ws
                    self._subscribed_channels.clear()
                    backoff = 1.0
                    logger.info("Connected to Deribit WS.")

                    # Enable Deribit heartbeat
                    heartbeat_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "public/set_heartbeat",
                        "params": {"interval": 15},
                    }
                    await ws.send(json.dumps(heartbeat_payload))

                    # Subscribe to index, DVOL and trade channels
                    channels = list(self.config.index_channels) + list(self.config.trade_channels)
                    
                    # Select options sorted chronologically by nearest expiry and ATM moneyness
                    sample_options = self._sort_options_chronological_atm(self.active_instruments, limit=60)

                    for name in sample_options:
                        channels.append(f"ticker.{name}.100ms")
                        channels.append(f"book.{name}.10.100ms")

                    sub_payload = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "public/subscribe",
                        "params": {"channels": channels},
                    }
                    await ws.send(json.dumps(sub_payload))
                    self._subscribed_channels.update(channels)
                    logger.info(f"Subscribed to {len(channels)} Deribit channels (indices, DVOL, trades, tickers).")

                    async for msg in ws:
                        if not self._running:
                            break
                        ts_recv_utc = time.time_ns()
                        ts_recv_mono = time.monotonic_ns()
                        await self._handle_message(msg, ws, ts_recv_utc, ts_recv_mono)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Deribit WS disconnected: {e}. Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)

    async def _handle_message(self, raw_msg: str, ws: Any, ts_recv_utc: int, ts_recv_mono: int) -> None:
        """Handle incoming Deribit JSON-RPC notification."""
        try:
            msg = json.loads(raw_msg)
        except Exception:
            return

        # Handle Heartbeat test request
        method = msg.get("method")
        if method == "heartbeat":
            params = msg.get("params", {})
            if params.get("type") == "test_request":
                resp = {"jsonrpc": "2.0", "id": 999, "method": "public/test"}
                await ws.send(json.dumps(resp))
            return

        if method != "subscription":
            return

        params = msg.get("params", {})
        channel = params.get("channel", "")
        data = params.get("data", {})

        # 1. Price Index updates: deribit_price_index.{btc|eth}_usd
        if channel.startswith("deribit_price_index."):
            currency = "BTC" if "btc" in channel else "ETH"
            price = float(data.get("price", 0.0))
            self.underlying_prices[currency] = price
            ts_exchange_ms = data.get("timestamp")
            ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None

            # Persist index metrics
            idx_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "instrument_name": f"{currency}_INDEX",
                "underlying_price": price,
                "mark_price": price,
                "mark_iv": 0.0,
                "bid_iv": 0.0,
                "ask_iv": 0.0,
                "delta": 0.0,
                "gamma": 0.0,
                "vega": 0.0,
                "theta": 0.0,
                "underlying_index_price": price,
                "dvol_index": self.dvol_indices.get(currency, 0.0),
            }
            await self.sink.append(Venue.DERIBIT.value, "deribit_metrics", idx_row)

        # 2. Volatility Index updates: deribit_volatility_index.{btc|eth}_usd (DVOL)
        elif channel.startswith("deribit_volatility_index."):
            currency = "BTC" if "btc" in channel else "ETH"
            vol = float(data.get("volatility", 0.0))
            self.dvol_indices[currency] = vol
            ts_exchange_ms = data.get("timestamp")
            ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None

            # Persist DVOL metrics
            dvol_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "instrument_name": f"{currency}_DVOL",
                "underlying_price": self.underlying_prices.get(currency, 0.0),
                "mark_price": vol,
                "mark_iv": vol,
                "bid_iv": 0.0,
                "ask_iv": 0.0,
                "delta": 0.0,
                "gamma": 0.0,
                "vega": 0.0,
                "theta": 0.0,
                "underlying_index_price": self.underlying_prices.get(currency, 0.0),
                "dvol_index": vol,
            }
            await self.sink.append(Venue.DERIBIT.value, "deribit_metrics", dvol_row)

        # 3. Ticker updates: ticker.{instrument_name}.100ms
        elif channel.startswith("ticker."):
            inst_name = data.get("instrument_name", "")
            ts_exchange_ms = data.get("timestamp")
            ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None
            observed_age = (ts_recv_utc - ts_exchange_ns) if ts_exchange_ns else None

            best_bid_p = float(data.get("best_bid_price", 0.0))
            best_bid_a = float(data.get("best_bid_amount", 0.0))
            best_ask_p = float(data.get("best_ask_price", 0.0))
            best_ask_a = float(data.get("best_ask_amount", 0.0))
            mark_p = float(data.get("mark_price", 0.0))
            mark_iv = float(data.get("mark_iv", 0.0))
            bid_iv = float(data.get("bid_iv", 0.0))
            ask_iv = float(data.get("ask_iv", 0.0))
            underlying_p = float(data.get("underlying_price", 0.0))
            currency = "BTC" if inst_name.startswith("BTC") else "ETH"

            greeks = data.get("greeks", {})
            delta = float(greeks.get("delta", 0.0)) if greeks else 0.0
            gamma = float(greeks.get("gamma", 0.0)) if greeks else 0.0
            vega = float(greeks.get("vega", 0.0)) if greeks else 0.0
            theta = float(greeks.get("theta", 0.0)) if greeks else 0.0

            # Record deribit metrics
            metrics_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "instrument_name": inst_name,
                "underlying_price": underlying_p,
                "mark_price": mark_p,
                "mark_iv": mark_iv,
                "bid_iv": bid_iv,
                "ask_iv": ask_iv,
                "delta": delta,
                "gamma": gamma,
                "vega": vega,
                "theta": theta,
                "underlying_index_price": self.underlying_prices.get(currency, 0.0),
                "dvol_index": self.dvol_indices.get(currency, 0.0),
            }
            await self.sink.append(Venue.DERIBIT.value, "deribit_metrics", metrics_row)

            # Record BBO tick
            if best_bid_p > 0 or best_ask_p > 0:
                bbo_row = {
                    "ts_exchange_ns": ts_exchange_ns,
                    "ts_received_utc_ns": ts_recv_utc,
                    "ts_received_mono_ns": ts_recv_mono,
                    "observed_event_age_ns": observed_age,
                    "venue": Venue.DERIBIT.value,
                    "symbol": inst_name,
                    "bid_price": best_bid_p,
                    "bid_size": best_bid_a,
                    "ask_price": best_ask_p,
                    "ask_size": best_ask_a,
                    "spread": round(best_ask_p - best_bid_p, 6),
                }
                await self.sink.append(Venue.DERIBIT.value, "bbo_ticks", bbo_row)

        # 4. Trades: trades.option.{btc|eth}.raw
        elif channel.startswith("trades."):
            trades = data if isinstance(data, list) else [data]
            for t in trades:
                inst_name = t.get("instrument_name", "")
                ts_exchange_ms = t.get("timestamp")
                ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None
                observed_age = (ts_recv_utc - ts_exchange_ns) if ts_exchange_ns else None

                trade_row = {
                    "ts_exchange_ns": ts_exchange_ns,
                    "ts_received_utc_ns": ts_recv_utc,
                    "ts_received_mono_ns": ts_recv_mono,
                    "observed_event_age_ns": observed_age,
                    "venue": Venue.DERIBIT.value,
                    "symbol": inst_name,
                    "trade_id": str(t.get("trade_id", "")),
                    "side": str(t.get("direction", "UNKNOWN")).upper(),
                    "price": float(t.get("price", 0.0)),
                    "size": float(t.get("amount", 0.0)),
                }
                await self.sink.append(Venue.DERIBIT.value, "trade_ticks", trade_row)

        # 5. Orderbook depth: book.{instrument_name}.10.100ms
        elif channel.startswith("book."):
            inst_name = data.get("instrument_name", "")
            ts_exchange_ms = data.get("timestamp")
            ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None

            bids = data.get("bids", [])
            asks = data.get("asks", [])
            bids_p = [float(b[0]) for b in bids]
            bids_s = [float(b[1]) for b in bids]
            asks_p = [float(a[0]) for a in asks]
            asks_s = [float(a[1]) for a in asks]

            depth_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "venue": Venue.DERIBIT.value,
                "symbol": inst_name,
                "bids_price": bids_p[:10],
                "bids_size": bids_s[:10],
                "asks_price": asks_p[:10],
                "asks_size": asks_s[:10],
                "depth_level": len(bids_p[:10]),
            }
            await self.sink.append(Venue.DERIBIT.value, "orderbook_l2_depth", depth_row)
