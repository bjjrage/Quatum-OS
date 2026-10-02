"""Thread-safe and async-compatible Parquet storage sink with immutable part-append model."""
import asyncio
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
import pyarrow as pa
import pyarrow.parquet as pq

from .manifest import compute_sha256, PartitionManifest
from .logger import setup_logger
from .types import SCHEMAS

logger = setup_logger("storage_sink")


class StorageSink:
    """Buffers rows in-memory and flushes immutable part-{ts}-{uuid}.parquet chunks."""

    def __init__(
        self,
        base_path: Path,
        flush_interval_sec: float = 60.0,
        flush_row_threshold: int = 5000,
        compression: str = "zstd",
        compression_level: int = 7,
        manifest_enabled: bool = True,
    ):
        self.base_path = Path(base_path)
        self.flush_interval_sec = flush_interval_sec
        self.flush_row_threshold = flush_row_threshold
        self.compression = compression
        self.compression_level = compression_level
        self.manifest_enabled = manifest_enabled

        # Staging temp directory
        self.tmp_dir = self.base_path / ".tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

        # In-memory buffers: key is (venue, table_name) -> list of dicts
        self._buffers: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
        self._buffer_start_ts: Dict[tuple[str, str], int] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start periodic flushing background loop."""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush_loop())
        logger.info("StorageSink started.")

    async def stop(self) -> None:
        """Stop sink and flush all remaining buffers to disk."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self.flush_all()
        logger.info("StorageSink stopped and flushed.")

    async def append(self, venue: str, table_name: str, row: Dict[str, Any]) -> None:
        """Append a single row to buffer, flushing if row threshold is met."""
        key = (venue, table_name)
        async with self._lock:
            if key not in self._buffers:
                self._buffers[key] = []
                self._buffer_start_ts[key] = time.time_ns()
            self._buffers[key].append(row)
            
            if len(self._buffers[key]) >= self.flush_row_threshold:
                await self._flush_buffer_unlocked(venue, table_name)

    async def append_batch(self, venue: str, table_name: str, rows: List[Dict[str, Any]]) -> None:
        """Append multiple rows to buffer."""
        if not rows:
            return
        key = (venue, table_name)
        async with self._lock:
            if key not in self._buffers:
                self._buffers[key] = []
                self._buffer_start_ts[key] = time.time_ns()
            self._buffers[key].extend(rows)
            
            if len(self._buffers[key]) >= self.flush_row_threshold:
                await self._flush_buffer_unlocked(venue, table_name)

    async def flush_all(self) -> None:
        """Flush all active buffers across all venues and tables."""
        async with self._lock:
            keys = list(self._buffers.keys())
            for venue, table_name in keys:
                await self._flush_buffer_unlocked(venue, table_name)

    async def _periodic_flush_loop(self) -> None:
        """Background loop flushing buffers older than flush_interval_sec."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval_sec)
                await self.flush_all()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in StorageSink periodic flush loop: {e}", exc_info=True)

    async def _flush_buffer_unlocked(self, venue: str, table_name: str) -> None:
        """Flush buffer to disk without acquiring lock (caller must hold lock)."""
        key = (venue, table_name)
        rows = self._buffers.get(key, [])
        if not rows:
            return

        ts_start_ns = self._buffer_start_ts.get(key, time.time_ns())
        self._buffers[key] = []
        self._buffer_start_ts[key] = time.time_ns()

        # Run disk IO in worker thread to prevent blocking asyncio event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_chunk_sync, venue, table_name, rows, ts_start_ns)

    def _write_chunk_sync(self, venue: str, table_name: str, rows: List[Dict[str, Any]], ts_start_ns: int) -> None:
        """Synchronous write of rows to an immutable Parquet part file."""
        if not rows:
            return

        schema = SCHEMAS.get(table_name)
        if not schema:
            logger.error(f"No PyArrow schema defined for table {table_name}. Skipping chunk.")
            return

        # Partition path calculation based on UTC timestamp
        now_utc = datetime.now(timezone.utc)
        part_uuid = uuid.uuid4().hex[:8]
        filename = f"part-{ts_start_ns}-{part_uuid}.parquet"
        
        partition_dir = (
            self.base_path
            / venue
            / f"table={table_name}"
            / f"year={now_utc.year:04d}"
            / f"month={now_utc.month:02d}"
            / f"day={now_utc.day:02d}"
            / f"hour={now_utc.hour:02d}"
        )
        partition_dir.mkdir(parents=True, exist_ok=True)

        tmp_file = self.tmp_dir / f"{filename}.tmp"
        dest_file = partition_dir / filename

        try:
            # Build PyArrow Table
            table = pa.Table.from_pylist(rows, schema=schema)
            
            # Write to temporary file with ZSTD compression
            pq.write_table(
                table,
                tmp_file,
                compression=self.compression,
                compression_level=self.compression_level,
            )

            # Checksum
            sha256_hash = compute_sha256(tmp_file)
            byte_size = tmp_file.stat().st_size

            # Atomic move to final destination
            os.replace(tmp_file, dest_file)

            # Update partition manifest
            if self.manifest_enabled:
                manifest = PartitionManifest(partition_dir)
                manifest.record_part(
                    part_filename=filename,
                    row_count=len(rows),
                    byte_size=byte_size,
                    sha256_hash=sha256_hash,
                )

            logger.info(
                f"Wrote immutable part: {venue}/{table_name} -> {filename} ({len(rows)} rows, {byte_size} bytes)"
            )
        except Exception as e:
            logger.error(f"Failed to write parquet part for {venue}/{table_name}: {e}", exc_info=True)
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass
