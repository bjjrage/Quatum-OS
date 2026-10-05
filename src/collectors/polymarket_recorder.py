"""Polymarket CLOB WebSocket and Discovery Recorder (2026 API compliant)."""
import asyncio
import json
import re
import time
from typing import Dict, Any, List, Set, Optional, Tuple
import aiohttp
import websockets

from config.settings import settings
from src.common.logger import setup_logger
from src.common.storage_sink import StorageSink
from src.common.types import Venue
from src.common.dns_patch import apply_dns_fallback

logger = setup_logger("polymarket_recorder")


def _f(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if v == v and v not in (float("inf"), float("-inf")) else default


def normalize_book_levels(bids: List[Dict[str, Any]], asks: List[Dict[str, Any]]) -> Tuple[
        List[float], List[float], List[float], List[float]]:
    """Return (bids_p, bids_s, asks_p, asks_s) sorted best-first.

    Polymarket CLOB does NOT guarantee best-first ordering (bids commonly arrive ascending), so
    index 0 must never be trusted. Bids are sorted price DESC, asks price ASC; zero-size and
    non-positive-price levels are dropped.
    """
    b = sorted(((_f(x.get("price")), _f(x.get("size"))) for x in (bids or [])), key=lambda t: -t[0])
    a = sorted(((_f(x.get("price")), _f(x.get("size"))) for x in (asks or [])), key=lambda t: t[0])
    b = [t for t in b if t[0] > 0.0 and t[1] > 0.0]
    a = [t for t in a if t[0] > 0.0 and t[1] > 0.0]
    return [t[0] for t in b], [t[1] for t in b], [t[0] for t in a], [t[1] for t in a]


_TICKER_RE = re.compile(r"\b(BTC|ETH|SOL)\b")
_WORD_RE = re.compile(r"\b(bitcoin|ethereum|solana)\b", re.IGNORECASE)


def is_crypto_market_question(question: str) -> bool:
    """True when the market question is about BTC / ETH / SOL (the markets STR-001 can price off Deribit)."""
    if not question:
        return False
    return bool(_TICKER_RE.search(question) or _WORD_RE.search(question))


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
        self._snapshot_task: Optional[asyncio.Task] = None
        self._fast_task: Optional[asyncio.Task] = None
        self._fast_tokens: Dict[str, float] = {}      # token -> fin del mercado (epoch s) de los mercados cortos
        self._fast_seen_slugs: Set[str] = set()

    async def start(self) -> None:
        """Start discovery poller and WebSocket listener."""
        self._running = True
        self._session = aiohttp.ClientSession()
        logger.info("Starting Polymarket Discovery & WS listener...")

        # Run initial discovery to get active tokens
        await self._discover_markets()

        self._discovery_task = asyncio.create_task(self._discovery_loop())
        self._ws_task = asyncio.create_task(self._ws_listener_loop())
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())
        self._fast_task = asyncio.create_task(self._fast_updown_loop())

    async def stop(self) -> None:
        """Stop recorder cleanly."""
        self._running = False
        if self._discovery_task:
            self._discovery_task.cancel()
        if self._ws_task:
            self._ws_task.cancel()
        if getattr(self, "_snapshot_task", None):
            self._snapshot_task.cancel()
        if getattr(self, "_fast_task", None):
            self._fast_task.cancel()
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
            urls = []
            for page in range(5):  # up to 500 crypto-tagged events
                urls.append(
                    "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false"
                    f"&tag_slug=crypto&offset={page * 100}"
                )
            all_markets = []
            for url in urls:
                try:
                    async with self._session.get(url, timeout=10.0) as resp:
                        if resp.status != 200:
                            break
                        payload = await resp.json()
                        if not isinstance(payload, list) or not payload:
                            break
                        for item in payload:
                            if "markets" in item and isinstance(item["markets"], list):
                                all_markets.extend(item["markets"])
                            else:
                                all_markets.append(item)
                except Exception as ex:
                    logger.debug(f"Failed to fetch {url}: {ex}")
                    break

            new_tokens: Set[str] = set()
            now_utc_ns = time.time_ns()

            for item in all_markets:
                await self._ingest_item(item, now_utc_ns, new_tokens)

            now_s = time.time()
            self._fast_tokens = {t: e for t, e in self._fast_tokens.items() if e > now_s - 900}
            new_tokens |= set(self._fast_tokens)          # los mercados cortos los mantiene el buscador rápido

            if new_tokens:
                removed = self.active_asset_ids - new_tokens
                if removed:
                    logger.info(f"Dropping {len(removed)} closed/non-crypto tokens from the active set.")
                self.active_asset_ids = set(new_tokens)  # never grows unboundedly with dead markets
            diff = new_tokens - self._subscribed_asset_ids
            if diff:
                logger.info(f"Discovered {len(diff)} new crypto tokens to record. Total: {len(new_tokens)}")

                # Dynamically subscribe active WS to newly discovered tokens
                if self._ws and not getattr(self._ws, "closed", False):
                    unsubscribed = list(diff - self._subscribed_asset_ids)
                    batch_size = 100
                    for i in range(0, len(unsubscribed), batch_size):
                        chunk = unsubscribed[i : i + batch_size]
                        payload = {"assets_ids": chunk, "operation": "subscribe"}
                        await self._ws.send(json.dumps(payload))
                        self._subscribed_asset_ids.update(chunk)
                    logger.info(f"Dynamically subscribed {len(unsubscribed)} new tokens to active WS.")

        except Exception as e:
            logger.error(f"Error discovering Polymarket markets: {e}", exc_info=True)


    async def _ingest_item(self, item: Dict[str, Any], now_utc_ns: int, new_tokens: Set[str]) -> None:
        """Procesa un mercado de Gamma: guarda su metadata y agrega sus tokens a `new_tokens`."""
        question = item.get("question", "")
        if item.get("closed") is True or item.get("active") is False:
            return
        if not is_crypto_market_question(question):
            return  # sports / politics / etc. are not recorded: they cannot be priced from Deribit
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
            "clob_token_ids_json": json.dumps([str(t) for t in clob_tokens]),
            "outcomes_json": json.dumps(item.get("outcomes")) if item.get("outcomes") is not None else "",
            "description": str(item.get("description", ""))[:4000],
        }
        await self.sink.append(Venue.POLYMARKET.value, "polymarket_metadata_history", meta_row)

    async def _fast_updown_loop(self) -> None:
        """Cada 60 s busca por nombre los mercados cortos "sube o baja" (5 y 15 min) de BTC/ETH/SOL: viven tan poco
        que el listado general (cada 15 min, top 500) casi nunca los alcanza. Formato: {cripto}-updown-{5m|15m}-{inicio}."""
        while self._running:
            try:
                await self._fast_updown_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Fast up/down discovery failed: {e}")
            try:
                await asyncio.sleep(60.0)
            except asyncio.CancelledError:
                break

    async def _fast_updown_once(self, now_s: Optional[float] = None) -> int:
        if not self._session:
            return 0
        now_s = now_s if now_s is not None else time.time()
        base_url = "https://gamma-api.polymarket.com/markets"
        new_tokens: Set[str] = set()
        now_utc_ns = time.time_ns()
        for coin in ("btc", "eth", "sol"):
            for label, step in (("5m", 300), ("15m", 900)):
                t0 = int(now_s // step) * step
                for k in (0, 1, 2):
                    slug = f"{coin}-updown-{label}-{t0 + k * step}"
                    if slug in self._fast_seen_slugs:
                        continue
                    try:
                        async with self._session.get(base_url, params={"slug": slug}, timeout=10.0) as resp:
                            if resp.status != 200:
                                continue
                            payload = await resp.json()
                    except Exception:
                        continue
                    items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
                    found: Set[str] = set()
                    for item in items:
                        if not isinstance(item, dict) or not item.get("clobTokenIds"):
                            continue
                        await self._ingest_item(item, now_utc_ns, found)
                    if found:
                        self._fast_seen_slugs.add(slug)
                        end_s = float(t0 + (k + 1) * step)
                        for tok in found:
                            self._fast_tokens[tok] = end_s
                        new_tokens |= found
        if len(self._fast_seen_slugs) > 5000:
            self._fast_seen_slugs = set(sorted(self._fast_seen_slugs)[-2000:])
        if new_tokens:
            self.active_asset_ids |= new_tokens
            await self._subscribe_new(new_tokens)
        return len(new_tokens)

    async def _subscribe_new(self, tokens: Set[str]) -> None:
        diff = set(tokens) - self._subscribed_asset_ids
        if not diff or not self._ws or getattr(self._ws, "closed", False):
            return
        chunk_list = sorted(diff)
        for i in range(0, len(chunk_list), 100):
            chunk = chunk_list[i: i + 100]
            await self._ws.send(json.dumps({"assets_ids": chunk, "operation": "subscribe"}))
            self._subscribed_asset_ids.update(chunk)
        logger.info(f"Subscribed {len(diff)} short up/down tokens to active WS.")

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

    async def _record_book(self, event: Dict[str, Any], asset_id: str, ts_exchange_ns: Optional[int],
                           ts_recv_utc: int, ts_recv_mono: int, observed_age: Optional[int]) -> None:
        bids_p, bids_s, asks_p, asks_s = normalize_book_levels(event.get("bids", []), event.get("asks", []))
        await self.sink.append(Venue.POLYMARKET.value, "orderbook_l2_depth", {
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
        })
        if bids_p and asks_p and bids_p[0] <= asks_p[0]:
            await self.sink.append(Venue.POLYMARKET.value, "bbo_ticks", {
                "ts_exchange_ns": ts_exchange_ns,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "observed_event_age_ns": observed_age,
                "venue": Venue.POLYMARKET.value,
                "symbol": asset_id,
                "bid_price": bids_p[0],
                "bid_size": bids_s[0],
                "ask_price": asks_p[0],
                "ask_size": asks_s[0],
                "spread": round(asks_p[0] - bids_p[0], 6),
            })

    async def _snapshot_loop(self) -> None:
        """The WS only sends `book` once per subscription. Poll full books over REST so L2 depth exists
        at a steady cadence (needed for sizing and fill simulation)."""
        interval = float(getattr(self.config, "book_snapshot_interval_sec", 60.0))
        while self._running:
            try:
                await asyncio.sleep(interval)
                tokens = sorted(self.active_asset_ids)
                if not tokens or not self._session:
                    continue
                for i in range(0, len(tokens), 50):
                    chunk = tokens[i:i + 50]
                    try:
                        async with self._session.post(
                            f"{self.config.clob_api_url}/books",
                            json=[{"token_id": t} for t in chunk],
                            timeout=10.0,
                        ) as resp:
                            if resp.status != 200:
                                continue
                            books = await resp.json()
                    except Exception as ex:
                        logger.debug(f"Book snapshot batch failed: {ex}")
                        continue
                    ts_utc, ts_mono = time.time_ns(), time.monotonic_ns()
                    for bk in books if isinstance(books, list) else []:
                        ts_raw = bk.get("timestamp")
                        try:
                            ts_ex = int(ts_raw) * 1_000_000 if ts_raw and len(str(ts_raw)) <= 13 else (int(ts_raw) if ts_raw else None)
                        except ValueError:
                            ts_ex = None
                        age = (ts_utc - ts_ex) if ts_ex else None
                        await self._record_book(bk, str(bk.get("asset_id") or ""), ts_ex, ts_utc, ts_mono, age)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Polymarket snapshot loop: {e}", exc_info=True)

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

            # 1. Standard event: book (full snapshot)
            if event_type == "book":
                await self._record_book(event, asset_id, ts_exchange_ns, ts_recv_utc, ts_recv_mono, observed_age)

            # 1b. Incremental level updates: carry best_bid / best_ask after the change
            elif event_type == "price_change":
                for ch in event.get("price_changes") or []:
                    ch_asset = str(ch.get("asset_id") or asset_id)
                    bb = _f(ch.get("best_bid"))
                    ba = _f(ch.get("best_ask"))
                    if bb <= 0.0 or ba <= 0.0 or bb > ba:
                        continue  # incomplete / crossed update: never invent a quote
                    px, sz, sd = _f(ch.get("price")), _f(ch.get("size")), str(ch.get("side", "")).upper()
                    bid_sz = sz if (sd == "BUY" and abs(px - bb) < 1e-12) else None
                    ask_sz = sz if (sd == "SELL" and abs(px - ba) < 1e-12) else None
                    await self.sink.append(Venue.POLYMARKET.value, "bbo_ticks", {
                        "ts_exchange_ns": ts_exchange_ns,
                        "ts_received_utc_ns": ts_recv_utc,
                        "ts_received_mono_ns": ts_recv_mono,
                        "observed_event_age_ns": observed_age,
                        "venue": Venue.POLYMARKET.value,
                        "symbol": ch_asset,
                        "bid_price": bb,
                        "bid_size": bid_sz,
                        "ask_price": ba,
                        "ask_size": ask_sz,
                        "spread": round(ba - bb, 6),
                    })

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
                best_bid = _f(event.get("best_bid"))
                best_ask = _f(event.get("best_ask"))
                bid_sz = _f(event.get("bid_size"))
                ask_sz = _f(event.get("ask_size"))
                if best_bid <= 0.0 or best_ask <= 0.0 or best_bid > best_ask:
                    continue  # incomplete or crossed quote: skip instead of recording zeros
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
