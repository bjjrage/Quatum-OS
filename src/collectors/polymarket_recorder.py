"""Polymarket CLOB WebSocket and Discovery Recorder (2026 API compliant)."""
import asyncio
import json
import time
from typing import Dict, Any, List, Set, Optional
import aiohttp
import websockets

from config.settings import settings
from src.common.logger import setup_logger
from src.common.storage_sink import StorageSink
from src.common.types import Venue
from src.common.dns_patch import apply_dns_fallback

logger = setup_logger("polymarket_recorder")


class PolymarketRecorder:
    """Records Polymarket CLOB book, price_change, last_trade_price, and metadata."""

    def __init__(self, sink: StorageSink):
        apply_dns_fallback()
        self.sink = sink
        self.config = settings.polymarket
        self.active_asset_ids: Set[str] = set()
        self.market_metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[Any] = None
        self._subscribed_asset_ids: Set[str] = set()
        self._ws_task: Optional[asyncio.Task] = None
        self._discovery_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start discovery poller and WebSocket listener."""
        self._running = True
        self._session = aiohttp.ClientSession()
        logger.info("Starting Polymarket Discovery & WS listener...")

        # Run initial discovery to get active tokens
        await self._discover_markets()

        self._discovery_task = asyncio.create_task(self._discovery_loop())
        self._ws_task = asyncio.create_task(self._ws_listener_loop())

    async def stop(self) -> None:
        """Stop recorder cleanly."""
        self._running = False
        if self._discovery_task:
            self._discovery_task.cancel()
        if self._ws_task:
            self._ws_task.cancel()
        if self._session:
            await self._session.close()
        logger.info("Polymarket recorder stopped.")

    async def _discovery_loop(self) -> None:
        """Periodically polls Gamma API for new crypto binary markets."""
        while self._running:
            try:
                await asyncio.sleep(self.config.discovery_interval_sec)
                await self._discover_markets()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Polymarket discovery loop: {e}", exc_info=True)

    async def _discover_markets(self) -> None:
        """Fetch active crypto binary markets from Gamma REST API."""
        if not self._session:
            return

        try:
            # Query both markets and crypto tagged events
            urls = [
                "https://gamma-api.polymarket.com/events?limit=50&active=true&closed=false&tag_slug=crypto",
                f"{self.config.gamma_api_url}?limit=100&active=true&closed=false",
            ]
            all_markets = []
            for url in urls:
                try:
                    async with self._session.get(url, timeout=10.0) as resp:
                        if resp.status == 200:
                            payload = await resp.json()
                            if isinstance(payload, list):
                                for item in payload:
                                    if "markets" in item and isinstance(item["markets"], list):
                                        all_markets.extend(item["markets"])
                                    else:
                                        all_markets.append(item)
                except Exception as ex:
                    logger.debug(f"Failed to fetch {url}: {ex}")

            new_tokens: Set[str] = set()
            now_utc_ns = time.time_ns()

            for item in all_markets:
                question = item.get("question", "")
                market_id = item.get("id", "")
                condition_id = item.get("conditionId", "")
                resolution_source = item.get("resolutionSource", "UMA/Binance")
                end_date_iso = item.get("endDate", "")

                # Versioned fee schedule extraction
                fee_raw = json.dumps(item.get("feeSchedule") or item.get("fee") or {"fee_bps": 0})
                fee_version = item.get("feeModelVersion", "PM_FEE_v2026_DEFAULT")
                status = "needs_review" if not resolution_source or "uma" in resolution_source.lower() else "active"

                # Parse clobTokenIds (JSON string or list)
                clob_tokens = item.get("clobTokenIds")
                if isinstance(clob_tokens, str):
                    try:
                        clob_tokens = json.loads(clob_tokens)
                    except Exception:
                        clob_tokens = []
                elif not isinstance(clob_tokens, list):
                    clob_tokens = []

                for token_id in clob_tokens:
                    if token_id:
                        new_tokens.add(str(token_id))
                        self.market_metadata_cache[str(token_id)] = {
                            "market_id": market_id,
                            "condition_id": condition_id,
                            "question": question,
                            "resolution_source": resolution_source,
                            "end_date_iso": end_date_iso,
                        }

                # Record metadata history row
                meta_row = {
                    "ts_polled_utc_ns": now_utc_ns,
                    "market_id": str(market_id),
                    "condition_id": str(condition_id),
                    "question": question,
                    "resolution_source": resolution_source,
                    "end_date_iso": end_date_iso,
                    "fee_schedule_raw_json": fee_raw,
                    "fee_model_version": fee_version,
                    "status": status,
                }
                await self.sink.append(Venue.POLYMARKET.value, "polymarket_metadata_history", meta_row)

            diff = new_tokens - self.active_asset_ids
            if diff:
                logger.info(f"Discovered {len(diff)} new crypto tokens to record. Total: {len(new_tokens)}")
                self.active_asset_ids.update(new_tokens)

                # Dynamically subscribe active WS to newly discovered tokens
                if self._ws and not getattr(self._ws, "closed", False):
                    unsubscribed = list(diff - self._subscribed_asset_ids)
                    batch_size = 100
                    for i in range(0, len(unsubscribed), batch_size):
                        chunk = unsubscribed[i : i + batch_size]
                        payload = {
                            "assets_ids": chunk,
                            "type": "market",
                            "custom_feature_enabled": self.config.custom_feature_enabled,
                        }
                        await self._ws.send(json.dumps(payload))
                        self._subscribed_asset_ids.update(chunk)
                    logger.info(f"Dynamically subscribed {len(unsubscribed)} new tokens to active WS.")

        except Exception as e:
            logger.error(f"Error discovering Polymarket markets: {e}", exc_info=True)

    async def _ws_listener_loop(self) -> None:
        """Main WebSocket connection and event dispatch loop with backoff."""
        backoff = 1.0
        while self._running:
            try:
                logger.info(f"Connecting to Polymarket CLOB WS at {self.config.ws_url}...")
                async with websockets.connect(
                    self.config.ws_url,
                    ping_interval=None,  # We manage manual PING every 10s as specified
                    close_timeout=5.0,
                ) as ws:
                    self._ws = ws
                    self._subscribed_asset_ids.clear()
                    backoff = 1.0
                    logger.info("Connected to Polymarket CLOB WS.")

                    # Start dedicated manual heartbeat PING task
                    ping_task = asyncio.create_task(self._ping_loop(ws))
                    
                    try:
                        # Subscribe to active tokens
                        await self._subscribe(ws)

                        async for msg in ws:
                            if not self._running:
                                break
                            ts_recv_utc = time.time_ns()
                            ts_recv_mono = time.monotonic_ns()
                            await self._handle_message(msg, ts_recv_utc, ts_recv_mono)
                    finally:
                        ping_task.cancel()
                        try:
                            await ping_task
                        except asyncio.CancelledError:
                            pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Polymarket WS disconnected: {e}. Reconnecting in {backoff:.1f}s...")
                await asyncio.sleep(backoff)
                backoff = min(30.0, backoff * 1.5)

    async def _ping_loop(self, ws: Any) -> None:
        """Sends manual text PING every 10 seconds as required by Polymarket protocol."""
        while self._running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval_sec)
                await ws.send("PING")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Polymarket PING send failed: {e}")
                break

    async def _subscribe(self, ws: Any) -> None:
        """Send subscription payload for all discovered assets in batches of 100."""
        token_list = list(self.active_asset_ids)
        if not token_list:
            logger.warning("No tokens to subscribe to yet; using fallback asset list.")
            token_list = ["fallback_asset_monitoring"]

        batch_size = 100
        for i in range(0, len(token_list), batch_size):
            chunk = token_list[i : i + batch_size]
            payload = {
                "assets_ids": chunk,
                "type": "market",
                "custom_feature_enabled": self.config.custom_feature_enabled,
            }
            await ws.send(json.dumps(payload))
            self._subscribed_asset_ids.update(chunk)
        logger.info(f"Subscribed to {len(self._subscribed_asset_ids)} Polymarket assets with custom_feature_enabled=True.")

    async def _handle_message(self, raw_msg: str, ts_recv_utc: int, ts_recv_mono: int) -> None:
        """Parse incoming event without destructive reinterpretation."""
        if raw_msg == "PONG":
            return

        try:
            data = json.loads(raw_msg)
        except Exception:
            return

        # Polymarket sends lists of events or single objects
        events = data if isinstance(data, list) else [data]

        for event in events:
            event_type = event.get("event_type") or event.get("type", "unknown")
            asset_id = str(event.get("asset_id") or event.get("market") or "")

            ts_exchange = event.get("timestamp")
            if ts_exchange:
                try:
                    ts_exchange_ns = int(ts_exchange) * 1_000_000 if len(str(ts_exchange)) <= 13 else int(ts_exchange)
                except ValueError:
                    ts_exchange_ns = None
            else:
                ts_exchange_ns = None

            observed_age = (ts_recv_utc - ts_exchange_ns) if ts_exchange_ns else None

            # 1. Standard event: book
            if event_type == "book":
                bids = event.get("bids", [])
                asks = event.get("asks", [])
                bids_p = [float(b.get("price", 0)) for b in bids]
                bids_s = [float(b.get("size", 0)) for b in bids]
                asks_p = [float(a.get("price", 0)) for a in asks]
                asks_s = [float(a.get("size", 0)) for a in asks]

                # Record L2 depth
                depth_row = {
                    "ts_exchange_ns": ts_exchange_ns,
                    "ts_received_utc_ns": ts_recv_utc,
                    "ts_received_mono_ns": ts_recv_mono,
                    "venue": Venue.POLYMARKET.value,
                    "symbol": asset_id,
                    "bids_price": bids_p[:10],
                    "bids_size": bids_s[:10],
                    "asks_price": asks_p[:10],
                    "asks_size": asks_s[:10],
                    "depth_level": len(bids_p[:10]),
                }
                await self.sink.append(Venue.POLYMARKET.value, "orderbook_l2_depth", depth_row)

                # Record BBO if available
                if bids_p and asks_p:
                    best_bid = bids_p[0]
                    best_bid_sz = bids_s[0]
                    best_ask = asks_p[0]
                    best_ask_sz = asks_s[0]
                    bbo_row = {
                        "ts_exchange_ns": ts_exchange_ns,
                        "ts_received_utc_ns": ts_recv_utc,
                        "ts_received_mono_ns": ts_recv_mono,
                        "observed_event_age_ns": observed_age,
                        "venue": Venue.POLYMARKET.value,
                        "symbol": asset_id,
                        "bid_price": best_bid,
                        "bid_size": best_bid_sz,
                        "ask_price": best_ask,
                        "ask_size": best_ask_sz,
                        "spread": round(best_ask - best_bid, 6),
                    }
                    await self.sink.append(Venue.POLYMARKET.value, "bbo_ticks", bbo_row)

            # 2. Standard event: last_trade_price
            elif event_type == "last_trade_price":
                try:
                    price = float(event.get("price", 0.0))
                    size = float(event.get("size", 0.0))
                except (ValueError, TypeError):
                    continue

                if price <= 0.0:
                    logger.debug(f"Discarding zero/negative price trade tick for {asset_id}: price={price}")
                    continue

                side = str(event.get("side", "UNKNOWN")).upper()
                trade_id = str(event.get("trade_id") or f"{ts_recv_utc}_{asset_id}")

                trade_row = {
                    "ts_exchange_ns": ts_exchange_ns,
                    "ts_received_utc_ns": ts_recv_utc,
                    "ts_received_mono_ns": ts_recv_mono,
                    "observed_event_age_ns": observed_age,
                    "venue": Venue.POLYMARKET.value,
                    "symbol": asset_id,
                    "trade_id": trade_id,
                    "side": side,
                    "price": price,
                    "size": size,
                }
                await self.sink.append(Venue.POLYMARKET.value, "trade_ticks", trade_row)

            # 3. Custom events: best_bid_ask
            elif event_type == "best_bid_ask":
                best_bid = float(event.get("best_bid", 0.0))
                best_ask = float(event.get("best_ask", 0.0))
                bid_sz = float(event.get("bid_size", 0.0))
                ask_sz = float(event.get("ask_size", 0.0))
                bbo_row = {
                    "ts_exchange_ns": ts_exchange_ns,
                    "ts_received_utc_ns": ts_recv_utc,
                    "ts_received_mono_ns": ts_recv_mono,
                    "observed_event_age_ns": observed_age,
                    "venue": Venue.POLYMARKET.value,
                    "symbol": asset_id,
                    "bid_price": best_bid,
                    "bid_size": bid_sz,
                    "ask_price": best_ask,
                    "ask_size": ask_sz,
                    "spread": round(best_ask - best_bid, 6),
                }
                await self.sink.append(Venue.POLYMARKET.value, "bbo_ticks", bbo_row)
