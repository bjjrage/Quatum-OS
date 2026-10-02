"""Binance Futures Open Interest explicit REST Poller."""
import asyncio
import time
from typing import Dict, Optional
import aiohttp

from config.settings import settings
from src.common.logger import setup_logger
from src.common.storage_sink import StorageSink
from src.common.types import Venue

logger = setup_logger("binance_oi_poller")


class BinanceOpenInterestPoller:
    """Explicitly polls GET /fapi/v1/openInterest for INITIAL_CALIBRATION_SAMPLE_v0."""

    def __init__(self, sink: StorageSink):
        self.sink = sink
        self.config = settings.binance
        self.symbols = [s.upper() for s in self.config.initial_calibration_sample_v0]
        self.last_known_oi: Dict[str, float] = {}
        self._running = False
        self._session: Optional[aiohttp.ClientSession] = None
        self._poll_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start periodic polling loop."""
        self._running = True
        self._session = aiohttp.ClientSession()
        logger.info(f"Starting Binance Open Interest poller for {len(self.symbols)} contracts (interval {self.config.oi_poller_interval_sec}s)...")
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """Stop poller cleanly."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
        if self._session:
            await self._session.close()
        logger.info("Binance Open Interest poller stopped.")

    async def _poll_loop(self) -> None:
        """Periodic loop polling all symbols sequentially with rate-limit respect."""
        while self._running:
            start_mono = time.monotonic()
            await self._poll_all_symbols()
            elapsed = time.monotonic() - start_mono

            sleep_time = max(0.1, self.config.oi_poller_interval_sec - elapsed)
            try:
                await asyncio.sleep(sleep_time)
            except asyncio.CancelledError:
                break

    async def _poll_all_symbols(self) -> None:
        """Poll each symbol respecting weight limits (50 calls/min budget out of 2400)."""
        if not self._session:
            return

        for symbol in self.symbols:
            if not self._running:
                break
            await self._poll_single_symbol(symbol)
            # Tiny sleep of 20ms between requests to spread network traffic smoothly
            await asyncio.sleep(0.02)

    async def _poll_single_symbol(self, symbol: str) -> None:
        """Poll single symbol with retry and stale data policy."""
        url = f"{self.config.rest_base_url}/fapi/v1/openInterest?symbol={symbol}"
        attempts = 0
        success = False
        backoff = 0.5
        t_start_ms = time.perf_counter()

        while attempts <= self.config.max_retries and not success:
            attempts += 1
            try:
                t0 = time.perf_counter()
                async with self._session.get(url, timeout=self.config.request_timeout_sec) as resp:
                    latency_ms = (time.perf_counter() - t0) * 1000
                    ts_recv_utc = time.time_ns()
                    ts_recv_mono = time.monotonic_ns()

                    if resp.status == 200:
                        data = await resp.json()
                        oi_val = float(data.get("openInterest", 0.0))
                        ts_exchange_ms = data.get("time")
                        ts_exchange_ns = int(ts_exchange_ms) * 1_000_000 if ts_exchange_ms else None

                        self.last_known_oi[symbol] = oi_val

                        row = {
                            "ts_exchange_ns": ts_exchange_ns,
                            "ts_received_utc_ns": ts_recv_utc,
                            "ts_received_mono_ns": ts_recv_mono,
                            "symbol": symbol,
                            "open_interest": oi_val,
                            "is_stale": False,
                            "poll_latency_ms": round(latency_ms, 2),
                        }
                        await self.sink.append(Venue.BINANCE_PERP.value, "futures_open_interest", row)
                        success = True
                    elif resp.status == 429:
                        logger.warning(f"Binance rate limit 429 hit for {symbol}. Backing off {backoff*2}s.")
                        await asyncio.sleep(backoff * 2)
                    else:
                        logger.debug(f"Binance OI poll for {symbol} returned status {resp.status}")
                        await asyncio.sleep(backoff)
                        backoff *= 2
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.debug(f"Binance OI poll error for {symbol} (attempt {attempts}): {e}")
                await asyncio.sleep(backoff)
                backoff *= 2

        # Stale data policy: if all retries failed, record last known state with is_stale=True
        if not success:
            ts_recv_utc = time.time_ns()
            ts_recv_mono = time.monotonic_ns()
            last_val = self.last_known_oi.get(symbol, 0.0)
            stale_row = {
                "ts_exchange_ns": None,
                "ts_received_utc_ns": ts_recv_utc,
                "ts_received_mono_ns": ts_recv_mono,
                "symbol": symbol,
                "open_interest": last_val,
                "is_stale": True,
                "poll_latency_ms": (time.perf_counter() - t_start_ms) * 1000,
            }
            await self.sink.append(Venue.BINANCE_PERP.value, "futures_open_interest", stale_row)
            logger.warning(f"Recorded stale Open Interest for {symbol} due to polling failure.")
