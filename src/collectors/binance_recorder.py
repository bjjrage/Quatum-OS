"""Binance USD(S)-M Futures WebSocket recorder adhering to separated 2026 API streams."""
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
import websockets

from config.settings import settings
from src.common.logger import setup_logger
from src.common.storage_sink import StorageSink
from src.common.types import Venue

logger = setup_logger("binance_recorder")


class BinanceRecorder:
    """Records Binance USD(S)-M Futures public & market streams with dual WS connections."""

    def __init__(self, sink: StorageSink):
        self.sink = sink
        self.config = settings.binance
        self.symbols = [s.lower() for s in self.config.initial_calibration_sample_v0]
        self._running = False
        self._public_ws_task: Optional[asyncio.Task] = None
        self._market_ws_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start both Public and Market WebSocket streams concurrently."""
        self._running = True
        logger.info(f"Starting Binance Recorder for {len(self.symbols)} contracts (sample v0)...")
        self._public_ws_task = asyncio.create_task(self._public_stream_loop())
        self._market_ws_task = asyncio.create_task(self._market_stream_loop())

    async def stop(self) -> None:
        """Stop recorder cleanly."""
        self._running = False
        if self._public_ws_task:
            self._public_ws_task.cancel()
        if self._market_ws_task:
            self._market_ws_task.cancel()
        logger.info("Binance recorder stopped.")

    async def _public_stream_loop(self) -> None:
        """Connects to wss://fstream.binance.com/public/stream for bookTicker and depth5."""
        backoff = 1.0
        while self._running:
            try:
                logger.info(f"Connecting to Binance PUBLIC stream: {self.config.public_ws_url}...")
                async with websockets.connect(
                    self.config.public_ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5.0,
                ) as ws:
                    backoff = 1.0
                    logger.info("Connected to Binance PUBLIC stream.")

                    # Build public subscription params
                    params = []
                    for s in self.symbols:
                        params.append(f"{s}@bookTicker")
                        params.append(f"{s}@depth5@100ms")

                    sub_payload = {"method": "SUBSCRIBE", "params": params, "id": 101}
                    await ws.send(json.dumps(sub_payload))
                    logger.info(f"Subscribed to {len(params)} public streams (bookTicker, depth5).")

                    async for msg in ws:
                        if not self._running:
                            break
                        ts_recv_utc = time.time_ns()
                        ts_recv_mono = time.monotonic_ns()
                        await self._handle_public_message(msg, ts_recv_utc, ts_recv_mono)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Binance PUBLIC WS disconnected: {e}. Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)

    async def _market_stream_loop(self) -> None:
        """Connects to wss://fstream.binance.com/market/stream for aggTrade, markPrice, and !forceOrder@arr."""
        backoff = 1.0
        while self._running:
            try:
                logger.info(f"Connecting to Binance MARKET stream: {self.config.market_ws_url}...")
                async with websockets.connect(
                    self.config.market_ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=5.0,
                ) as ws:
                    backoff = 1.0
                    logger.info("Connected to Binance MARKET stream.")

                    # Build market subscription params
                    params = ["!forceOrder@arr"]
                    for s in self.symbols:
                        params.append(f"{s}@aggTrade")
                        params.append(f"{s}@markPrice@1s")

                    sub_payload = {"method": "SUBSCRIBE", "params": params, "id": 202}
                    await ws.send(json.dumps(sub_payload))
                    logger.info(f"Subscribed to {len(params)} market streams (aggTrade, markPrice, !forceOrder@arr).")

                    async for msg in ws:
                        if not self._running:
                            break
                        ts_recv_utc = time.time_ns()
                        ts_recv_mono = time.monotonic_ns()
                        await self._handle_market_message(msg, ts_recv_utc, ts_recv_mono)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Binance MARKET WS disconnected: {e}. Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)

    async def _handle_public_message(self, raw_msg: str, ts_recv_utc: int, ts_recv_mono: int) -> None:
        """Handle bookTicker and depth5 messages from public stream."""
        try:
            msg = json.loads(raw_msg)
        except Exception:
            return

        stream = msg.get("stream", "")
        data = msg.get("data", msg)

        # Filter UM/CM merge: accept st=1 (USD(S)-M) when field is present
        st = data.get("st")
        if st is not None and int(st) != self.config.symbol_type_filter:
            return

        ts_exchange_ms = data.get("E") or data.get("T")
        ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None
        observed_age = (ts_recv_utc - ts_exchange_ns) if ts_exchange_ns else None

        # 1. bookTicker
        if "@bookTicker" in stream or data.get("e") == "bookTicker":
            symbol = data.get("s", "").upper()
            bid_p = float(data.get("b", 0.0))
            bid_s = float(data.get("B", 0.0))
            ask_p = float(data.get("a", 0.0))
            ask_s = float(data.get("A", 0.0))
            bbo_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "observed_event_age_ns": observed_age,
                "venue": Venue.BINANCE_PERP.value,
                "symbol": symbol,
                "bid_price": bid_p,
                "bid_size": bid_s,
                "ask_price": ask_p,
                "ask_size": ask_s,
                "spread": round(ask_p - bid_p, 6),
            }
            await self.sink.append(Venue.BINANCE_PERP.value, "bbo_ticks", bbo_row)

        # 2. depth5
        elif "@depth5" in stream:
            symbol = stream.split("@")[0].upper()
            bids = data.get("b", [])
            asks = data.get("a", [])
            bids_p = [float(b[0]) for b in bids]
            bids_s = [float(b[1]) for b in bids]
            asks_p = [float(a[0]) for a in asks]
            asks_s = [float(a[1]) for a in asks]

            depth_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "venue": Venue.BINANCE_PERP.value,
                "symbol": symbol,
                "bids_price": bids_p[:5],
                "bids_size": bids_s[:5],
                "asks_price": asks_p[:5],
                "asks_size": asks_s[:5],
                "depth_level": len(bids_p[:5]),
            }
            await self.sink.append(Venue.BINANCE_PERP.value, "orderbook_l2_depth", depth_row)

    async def _handle_market_message(self, raw_msg: str, ts_recv_utc: int, ts_recv_mono: int) -> None:
        """Handle aggTrade, markPrice, and !forceOrder@arr messages from market stream."""
        try:
            msg = json.loads(raw_msg)
        except Exception:
            return

        stream = msg.get("stream", "")
        data = msg.get("data", msg)

        # Filter UM/CM merge: accept st=1 (USD(S)-M) when field is present
        st = data.get("st")
        if st is not None and int(st) != self.config.symbol_type_filter:
            return

        ts_exchange_ms = data.get("E") or data.get("T")
        ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None
        observed_age = (ts_recv_utc - ts_exchange_ns) if ts_exchange_ns else None

        # 1. aggTrade (individual trade replacement)
        if "@aggTrade" in stream or data.get("e") == "aggTrade":
            symbol = data.get("s", "").upper()
            trade_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "observed_event_age_ns": observed_age,
                "venue": Venue.BINANCE_PERP.value,
                "symbol": symbol,
                "trade_id": str(data.get("a", "")),
                "side": "SELL" if data.get("m") else "BUY",  # m = Was the buyer the market maker?
                "price": float(data.get("p", 0.0)),
                "size": float(data.get("q", 0.0)),
            }
            await self.sink.append(Venue.BINANCE_PERP.value, "trade_ticks", trade_row)

        # 2. markPrice@1s
        elif "@markPrice" in stream or data.get("e") == "markPriceUpdate":
            symbol = data.get("s", "").upper()
            mark_p = float(data.get("p", 0.0))
            index_p = float(data.get("i", 0.0))
            funding_r = float(data.get("r", 0.0))

            futures_metrics = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "symbol": symbol,
                "mark_price": mark_p,
                "index_price": index_p,
                "funding_rate": funding_r,
            }
            await self.sink.append(Venue.BINANCE_PERP.value, "futures_market_metrics", futures_metrics)

        # 3. !forceOrder@arr (Liquidation proxy stream)
        elif "!forceOrder" in stream or data.get("e") == "forceOrder":
            order_info = data.get("o", data)
            symbol = order_info.get("s", "").upper()
            ps = order_info.get("ps")  # Pair symbol
            st_val = order_info.get("st")  # Symbol type

            # Filter for USD(S)-M if st is present
            if st_val is not None and int(st_val) != self.config.symbol_type_filter:
                return

            liq_row = {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "symbol": symbol,
                "pair_symbol": str(ps) if ps else symbol,
                "symbol_type": int(st_val) if st_val is not None else 1,
                "side": str(order_info.get("S", "")).upper(),
                "price": float(order_info.get("p", 0.0)),
                "orig_qty": float(order_info.get("q", 0.0)),
                "executed_qty": float(order_info.get("z", 0.0)),
                "is_partial_proxy": True,
            }
            await self.sink.append(Venue.BINANCE_PERP.value, "forced_liquidations", liq_row)
