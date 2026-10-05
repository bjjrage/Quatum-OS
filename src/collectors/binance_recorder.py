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
        self._fallback_task: Optional[asyncio.Task] = None
        self._public_up = False                 # True mientras la conexión de precios (bookTicker) está viva
        self._public_down_since: Optional[float] = time.time()
        self.fallback_rows = 0                  # filas escritas por el respaldo REST (diagnóstico)

    async def start(self) -> None:
        """Start both Public and Market WebSocket streams concurrently."""
        self._running = True
        logger.info(f"Starting Binance Recorder for {len(self.symbols)} contracts (sample v0)...")
        self._public_ws_task = asyncio.create_task(self._public_stream_loop())
        self._market_ws_task = asyncio.create_task(self._market_stream_loop())
        self._fallback_task = asyncio.create_task(self._rest_fallback_loop())

    async def stop(self) -> None:
        """Stop recorder cleanly."""
        self._running = False
        if self._public_ws_task:
            self._public_ws_task.cancel()
        if self._market_ws_task:
            self._market_ws_task.cancel()
        if self._fallback_task:
            self._fallback_task.cancel()
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
                    ping_timeout=60,          # aguanta cortes breves de red sin tirar la conexión
                    open_timeout=20,
                    close_timeout=5.0,
                    max_queue=4096,
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
                    if self._public_down_since is not None:
                        logger.info(f"Binance PUBLIC back after {time.time() - self._public_down_since:.0f}s "
                                    f"(respaldo REST escribió {self.fallback_rows} filas en total).")
                    self._public_up, self._public_down_since = True, None

                    async for msg in ws:
                        if not self._running:
                            break
                        ts_recv_utc = time.time_ns()
                        ts_recv_mono = time.monotonic_ns()
                        await self._handle_public_message(msg, ts_recv_utc, ts_recv_mono)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._public_up or self._public_down_since is None:
                    self._public_down_since = time.time()
                self._public_up = False
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
                    ping_timeout=60,          # aguanta cortes breves de red sin tirar la conexión
                    open_timeout=20,
                    close_timeout=5.0,
                    max_queue=4096,
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

    async def _rest_fallback_loop(self, interval_s: float = 1.0, grace_s: float = 3.0) -> None:
        """Mientras la conexión de precios está caída, pide la mejor compra/venta de todos los contratos por REST
        (1 pedido/s, peso 5) y la guarda igual que el WebSocket. Así un corte no deja agujeros en bbo_ticks."""
        import aiohttp
        url = self.config.rest_base_url.rstrip("/") + "/fapi/v1/ticker/bookTicker"
        wanted = {s.upper() for s in self.symbols}
        active = False
        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    await asyncio.sleep(interval_s)
                    down_for = (time.time() - self._public_down_since) if self._public_down_since else 0.0
                    if self._public_up or down_for < grace_s:
                        if active:
                            logger.info("Binance REST fallback OFF (WebSocket de precios recuperado).")
                            active = False
                        continue
                    if not active:
                        logger.warning("Binance REST fallback ON: WebSocket de precios caído, se piden precios por REST.")
                        active = True
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=5.0)) as resp:
                        if resp.status != 200:
                            continue
                        data = await resp.json()
                    ts_recv_utc, ts_recv_mono = time.time_ns(), time.monotonic_ns()
                    rows = self.rest_book_rows(data, wanted, ts_recv_utc, ts_recv_mono)
                    for row in rows:
                        await self.sink.append(Venue.BINANCE_PERP.value, "bbo_ticks", row)
                    self.fallback_rows += len(rows)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.debug(f"Binance REST fallback request failed: {e}")

    @staticmethod
    def rest_book_rows(data: Any, wanted: set, ts_recv_utc: int, ts_recv_mono: int) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for d in data if isinstance(data, list) else []:
            sym = str(d.get("symbol", "")).upper()
            if sym not in wanted:
                continue
            try:
                bid_p, ask_p = float(d.get("bidPrice", 0.0)), float(d.get("askPrice", 0.0))
                bid_s, ask_s = float(d.get("bidQty", 0.0)), float(d.get("askQty", 0.0))
            except (TypeError, ValueError):
                continue
            if bid_p <= 0 or ask_p <= 0 or bid_p > ask_p:
                continue
            t_ms = d.get("time")
            ts_exchange_ns = int(t_ms) * 1_000_000 if t_ms else None
            rows.append({
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "observed_event_age_ns": (ts_recv_utc - ts_exchange_ns) if ts_exchange_ns else None,
                "venue": Venue.BINANCE_PERP.value,
                "symbol": sym,
                "bid_price": bid_p,
                "bid_size": bid_s,
                "ask_price": ask_p,
                "ask_size": ask_s,
                "spread": round(ask_p - bid_p, 6),
            })
        return rows

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
