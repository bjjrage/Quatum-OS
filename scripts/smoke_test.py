"""Smoke test script for Batch 0: verifies live connections, parquet generation and DuckDB reads."""
import argparse
import asyncio
import shutil
import sys
from pathlib import Path
import duckdb

from src.collectors.manager import CollectorManager
from src.common.logger import setup_logger

logger = setup_logger("smoke_test")


async def run_smoke_test(duration_sec: int) -> bool:
    test_dir = Path("data/smoke_test")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"--- STARTING BATCH 0 SMOKE TEST (Duration: {duration_sec}s) ---")
    logger.info(f"Target directory: {test_dir.absolute()}")

    manager = CollectorManager(base_data_path=str(test_dir))

    try:
        await manager.start()
        logger.info(f"Collecting live market data for {duration_sec} seconds...")
        for remaining in range(duration_sec, 0, -5):
            logger.info(f"Recording in progress... {remaining}s remaining")
            await asyncio.sleep(min(5, remaining))

    finally:
        logger.info("Stopping manager and flushing all buffers...")
        await manager.stop()

    # Verification phase via DuckDB
    logger.info("--- VERIFYING PARQUET OUTPUT VIA DUCKDB ---")
    parquet_files = list(test_dir.glob("**/*.parquet"))
    logger.info(f"Found {len(parquet_files)} parquet part files.")

    if not parquet_files:
        logger.error("SMOKE TEST FAILED: Zero parquet files were written.")
        return False

    con = duckdb.connect()
    success = True
    total_records = 0

    print("\n" + "=" * 80)
    print(f"{'VENUE':<15} | {'TABLE':<25} | {'PARQUET FILES':<15} | {'ROW COUNT':<10}")
    print("-" * 80)

    # Group by venue and table
    venues = [d.name for d in test_dir.iterdir() if d.is_dir() and d.name != ".tmp"]
    for venue in venues:
        venue_dir = test_dir / venue
        table_dirs = [td.name.replace("table=", "") for td in venue_dir.iterdir() if td.is_dir()]
        for table in table_dirs:
            glob_path = str(venue_dir / f"table={table}/**/*.parquet").replace("\\", "/")
            try:
                res = con.execute(f"SELECT COUNT(*) FROM read_parquet('{glob_path}')").fetchone()
                row_count = res[0] if res else 0
                parts_count = len(list((venue_dir / f"table={table}").glob("**/*.parquet")))
                total_records += row_count
                status = "OK" if row_count > 0 else "EMPTY"
                print(f"{venue:<15} | {table:<25} | {parts_count:<15} | {row_count:<10} [{status}]")
                if row_count == 0:
                    success = False
            except Exception as e:
                print(f"{venue:<15} | {table:<25} | ERROR: {e}")
                success = False

    print("=" * 80)
    print(f"TOTAL ROWS RECORDED ACROSS ALL VENUES: {total_records}")
    print("=" * 80 + "\n")

    # Verify manifest files
    manifests = list(test_dir.glob("**/manifest.json"))
    logger.info(f"Found {len(manifests)} manifest.json files. Checking integrity...")
    if not manifests:
        logger.warning("No manifest.json files found.")

    if success and total_records > 0:
        logger.info("--- BATCH 0 SMOKE TEST PASSED SUCCESSFULLY ---")
        return True
    else:
        logger.error("--- BATCH 0 SMOKE TEST FAILED ---")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Batch 0 Market Data Recorder smoke test.")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds (default: 30)")
    args = parser.parse_args()

    success = asyncio.run(run_smoke_test(args.duration))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
