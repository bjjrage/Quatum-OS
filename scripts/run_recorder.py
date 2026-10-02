"""Main entrypoint for running the Batch 0 Market Data Recorder service."""
import asyncio
import signal
import sys
from src.collectors.manager import CollectorManager
from src.common.logger import setup_logger

logger = setup_logger("main_service")


async def main() -> None:
    manager = CollectorManager()
    loop = asyncio.get_running_loop()

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal. Shutting down gracefully...")
        stop_event.set()

    # Register OS signals for graceful shutdown
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows may not implement add_signal_handler for all signals
            pass

    try:
        await manager.start()
        logger.info("Batch 0 Market Data Foundation is now live and recording.")
        
        while not stop_event.is_set():
            await asyncio.sleep(1.0)

    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupt received, stopping...")
    finally:
        await manager.stop()
        logger.info("Service shut down cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
