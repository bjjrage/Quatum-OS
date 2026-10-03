import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

# Ensure root repository directory is on sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

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

    fingerprint = compute_config_fingerprint()
    manifest = None

    if manifest_path.exists():
        try:
            existing = RuntimeManifest.load(manifest_path)
            if existing.config_fingerprint == fingerprint:
                existing.pid = os.getpid()
                existing.git_sha = git_sha
                existing.status = AcceptanceState.RUNNING
                existing.update_heartbeat()
                manifest = existing
                logger.info(f"Resuming continuous acceptance run: {manifest.run_id} (Elapsed: {manifest.elapsed_seconds():.1f}s)")
        except Exception as e:
            logger.warning(f"Could not resume manifest: {e}. Starting fresh.")

    if manifest is None:
        manifest = RuntimeManifest.create_new(
            pid=os.getpid(),
            git_sha=git_sha,
            config_fingerprint=fingerprint,
        )
        logger.info(f"Initialized new runtime manifest: {manifest.run_id} (PID: {os.getpid()}, SHA: {git_sha[:8]})")

    manifest.save(manifest_path)

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
