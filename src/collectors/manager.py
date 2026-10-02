"""CollectorManager: orchestrates all market data collectors and telemetry."""
import asyncio
import time
from typing import Optional, Dict, Any
import psutil

from config.settings import settings
from src.common.logger import setup_logger
from src.common.storage_sink import StorageSink
from .polymarket_recorder import PolymarketRecorder
from .deribit_recorder import DeribitRecorder
from .binance_recorder import BinanceRecorder
from .binance_oi_poller import BinanceOpenInterestPoller

logger = setup_logger("collector_manager")


class CollectorManager:
    """Master manager controlling all collectors and system telemetry."""

    def __init__(self, base_data_path: Optional[str] = None):
        data_path = base_data_path or str(settings.storage.base_data_path)
        self.sink = StorageSink(
            base_path=data_path,
            flush_interval_sec=settings.storage.flush_interval_sec,
            flush_row_threshold=settings.storage.flush_row_threshold,
            compression=settings.storage.compression,
            compression_level=settings.storage.compression_level,
            manifest_enabled=settings.storage.manifest_enabled,
        )
        self.polymarket = PolymarketRecorder(self.sink)
        self.deribit = DeribitRecorder(self.sink)
        self.binance = BinanceRecorder(self.sink)
        self.binance_oi = BinanceOpenInterestPoller(self.sink)
        
        self._running = False
        self._telemetry_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start storage sink, collectors, and telemetry."""
        logger.info("Initializing Batch 0 Production Market Data Foundation...")
        self._running = True

        # 1. Start persistence sink first
        await self.sink.start()

        # 2. Start collectors concurrently
        await self.polymarket.start()
        await self.deribit.start()
        await self.binance.start()
        await self.binance_oi.start()

        # 3. Start telemetry reporting loop
        self._telemetry_task = asyncio.create_task(self._telemetry_loop())
        logger.info("All Batch 0 recorders and pollers running successfully.")

    async def stop(self) -> None:
        """Stop all collectors and flush sinks gracefully."""
        logger.info("Stopping all collectors...")
        self._running = False

        if self._telemetry_task:
            self._telemetry_task.cancel()

        # Stop collectors concurrently
        await asyncio.gather(
            self.polymarket.stop(),
            self.deribit.stop(),
            self.binance.stop(),
            self.binance_oi.stop(),
            return_exceptions=True,
        )

        # Stop and flush sink
        await self.sink.stop()
        logger.info("Batch 0 shutdown complete.")

    async def _telemetry_loop(self) -> None:
        """Emits structured system and queue telemetry every 60 seconds."""
        process = psutil.Process()
        while self._running:
            try:
                await asyncio.sleep(60.0)
                mem_info = process.memory_info()
                cpu_pct = process.cpu_percent(interval=None)
                disk_usage = psutil.disk_usage(str(self.sink.base_path))

                telemetry: Dict[str, Any] = {
                    "event": "telemetry_report",
                    "rss_ram_mb": round(mem_info.rss / (1024 * 1024), 2),
                    "cpu_percent": round(cpu_pct, 2),
                    "disk_free_gb": round(disk_usage.free / (1024 * 1024 * 1024), 2),
                    "active_polymarket_tokens": len(self.polymarket.active_asset_ids),
                    "active_deribit_instruments": len(self.deribit.active_instruments),
                    "active_binance_symbols": len(self.binance.symbols),
                }

                logger.info(f"System Telemetry: RAM={telemetry['rss_ram_mb']}MB, CPU={telemetry['cpu_percent']}%, DiskFree={telemetry['disk_free_gb']}GB")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}", exc_info=True)
