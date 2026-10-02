import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

from src.collectors.manager import CollectorManager
from src.common.logger import setup_logger
from src.quality.acceptance import RuntimeManifest
from src.quality.fingerprint import compute_config_fingerprint

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

    manifest_path = Path("data/runtime/current_run.json")
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        git_sha = "UNKNOWN"

    manifest = RuntimeManifest.create_new(
        pid=os.getpid(),
        git_sha=git_sha,
        config_fingerprint=compute_config_fingerprint(),
    )
    manifest.save(manifest_path)
    logger.info(f"Initialized runtime manifest: {manifest.run_id} (PID: {os.getpid()}, SHA: {git_sha[:8]})")

    try:
        await manager.start()
        logger.info("Batch 0 Market Data Foundation is now live and recording.")
        
        heartbeat_counter = 0
        while not stop_event.is_set():
            await asyncio.sleep(1.0)
            heartbeat_counter += 1
            if heartbeat_counter >= 30:
                manifest.update_heartbeat()
                manifest.save(manifest_path)
                heartbeat_counter = 0

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
