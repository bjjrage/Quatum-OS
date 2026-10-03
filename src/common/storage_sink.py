"""Thread-safe and async-compatible Parquet storage sink with immutable part-append model and durable write confirmation."""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

from .logger import setup_logger
from .manifest import ManifestCorruptError, PartitionManifest, compute_sha256
from .types import SCHEMAS

logger = setup_logger("storage_sink")


class ChunkWriteStatus(str, Enum):
    """Write lifecycle status of a chunk flushed to storage."""
    COMMITTED = "COMMITTED"
    QUARANTINED = "QUARANTINED"
    RETRY_REQUIRED = "RETRY_REQUIRED"


class StorageSinkState(str, Enum):
    """Health and failure state of the storage sink."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class StorageSink:
    """Buffers rows in-memory, confirms durable writes before removal, and quarantines write failures."""

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
        # Optional callback(path, sha256) invoked after a part is finalized; failures are ignored.
        self.on_part_finalized: Optional[Callable[[Path, str], None]] = None

        # Staging temp directory and quarantine dead-letter directory
        self.tmp_dir = self.base_path / ".tmp"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir = self.base_path / "quarantine"
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)

        # In-memory buffers: key is (venue, table_name) -> list of dicts
        self._buffers: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self._buffer_start_ts: Dict[Tuple[str, str], int] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None

        # Operational state machine
        self.sink_state: StorageSinkState = StorageSinkState.HEALTHY
        self.consecutive_double_failures: int = 0

        # Observable telemetry counters
        self.events_received: int = 0
        self.events_committed: int = 0
        self.events_failed: int = 0
        self.events_quarantined: int = 0
        self.write_failures: int = 0
        self.last_write_error: Optional[str] = None

    def get_metrics(self) -> Dict[str, Any]:
        """Return observable counters for health inspection and continuity reconciliation."""
        return {
            "sink_state": self.sink_state.value,
            "consecutive_double_failures": self.consecutive_double_failures,
            "events_received": self.events_received,
            "events_committed": self.events_committed,
            "events_failed": self.events_failed,
            "events_quarantined": self.events_quarantined,
            "write_failures": self.write_failures,
            "last_write_error": self.last_write_error,
            "buffered_events_count": sum(len(b) for b in self._buffers.values()),
        }

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
        uncommitted = sum(len(b) for b in self._buffers.values())
        if uncommitted > 0:
            self.sink_state = StorageSinkState.FAILED
            logger.critical(
                f"StorageSink stopped with {uncommitted} UNCOMMITTED rows retained in memory due to write failures!"
            )
        logger.info("StorageSink stopped and flushed.")

    async def append(self, venue: str, table_name: str, row: Dict[str, Any]) -> None:
        """Append a single row to buffer, flushing if row threshold is met."""
        key = (venue, table_name)
        async with self._lock:
            self.events_received += 1
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
            self.events_received += len(rows)
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
        rows_to_write = list(rows)

        # Run disk IO in worker thread to prevent blocking asyncio event loop
        loop = asyncio.get_running_loop()
        status: ChunkWriteStatus = await loop.run_in_executor(
            None, self._write_chunk_sync, venue, table_name, rows_to_write, ts_start_ns
        )

        if status == ChunkWriteStatus.COMMITTED:
            self._buffers[key] = self._buffers[key][len(rows_to_write):]
            self._buffer_start_ts[key] = time.time_ns()
            self.consecutive_double_failures = 0
            if self.sink_state == StorageSinkState.FAILED:
                self.sink_state = StorageSinkState.HEALTHY

        elif status == ChunkWriteStatus.QUARANTINED:
            self._buffers[key] = self._buffers[key][len(rows_to_write):]
            self._buffer_start_ts[key] = time.time_ns()
            self.sink_state = StorageSinkState.DEGRADED

        elif status == ChunkWriteStatus.RETRY_REQUIRED:
            # DOUBLE FAILURE: Parquet failed AND quarantine failed!
            # Keep rows in buffer without truncation; do NOT advance buffer_start_ts.
            self.sink_state = StorageSinkState.FAILED
            self.consecutive_double_failures += 1
            logger.critical(
                f"DOUBLE FAILURE on {venue}/{table_name}: Parquet write and dead-letter quarantine both failed! "
                f"Retaining {len(rows_to_write)} rows in memory for retry. Sink state=FAILED."
            )

    def _write_chunk_sync(self, venue: str, table_name: str, rows: List[Dict[str, Any]], ts_start_ns: int) -> ChunkWriteStatus:
        """Synchronous write of rows to an immutable Parquet part file.
        
        Returns:
            ChunkWriteStatus.COMMITTED on successful parquet write,
            ChunkWriteStatus.QUARANTINED on parquet write failure with successful dead-letter quarantine,
            ChunkWriteStatus.RETRY_REQUIRED on double failure (parquet and quarantine both failed).
        """
        if not rows:
            return ChunkWriteStatus.COMMITTED

        schema = SCHEMAS.get(table_name)
        if not schema:
            err_msg = f"No PyArrow schema defined for table {table_name}. Skipping chunk."
            logger.error(err_msg)
            self.write_failures += 1
            self.events_failed += len(rows)
            self.last_write_error = err_msg
            q_ok = self._quarantine_failed_chunk(venue, table_name, rows, ts_start_ns, ValueError(err_msg))
            return ChunkWriteStatus.QUARANTINED if q_ok else ChunkWriteStatus.RETRY_REQUIRED

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

            self.events_committed += len(rows)
            logger.info(
                f"Wrote immutable part: {venue}/{table_name} -> {filename} ({len(rows)} rows, {byte_size} bytes)"
            )
            hook = getattr(self, "on_part_finalized", None)
            if hook is not None:
                try:
                    hook(dest_file, sha256_hash)
                except Exception as hook_err:  # local capture must never depend on the control plane
                    logger.warning(f"on_part_finalized hook failed (ignored): {hook_err}")
            return ChunkWriteStatus.COMMITTED
        except Exception as e:
            self.write_failures += 1
            self.events_failed += len(rows)
            self.last_write_error = f"{type(e).__name__}: {str(e)}"
            logger.error(f"Failed to write parquet part for {venue}/{table_name}: {e}", exc_info=True)
            if tmp_file.exists():
                try:
                    tmp_file.unlink()
                except Exception:
                    pass
            # Quarantine dead-letter: ensure data is never silently dropped
            q_ok = self._quarantine_failed_chunk(venue, table_name, rows, ts_start_ns, e)
            return ChunkWriteStatus.QUARANTINED if q_ok else ChunkWriteStatus.RETRY_REQUIRED

    def _quarantine_failed_chunk(
        self,
        venue: str,
        table_name: str,
        rows: List[Dict[str, Any]],
        ts_start_ns: int,
        error: Exception,
    ) -> bool:
        """Quarantine dead-letter dump for uncommitted rows. Returns True on successful write, False otherwise."""
        tmp_q = None
        try:
            target_dir = self.quarantine_dir / venue / f"table={table_name}"
            target_dir.mkdir(parents=True, exist_ok=True)
            part_uuid = uuid.uuid4().hex[:8]
            q_file = target_dir / f"quarantine-{ts_start_ns}-{part_uuid}.json"
            
            payload = {
                "venue": venue,
                "table_name": table_name,
                "ts_start_ns": ts_start_ns,
                "quarantined_at_utc": datetime.now(timezone.utc).isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "row_count": len(rows),
                "rows": rows,
            }
            tmp_q = target_dir / f".tmp_q_{part_uuid}.tmp"
            with open(tmp_q, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_q, q_file)
            self.events_quarantined += len(rows)
            logger.warning(f"Quarantined {len(rows)} failed rows to dead-letter {q_file}")
            return True
        except Exception as q_err:
            logger.critical(f"FATAL: Failed to write quarantine dead-letter for {venue}/{table_name}: {q_err}", exc_info=True)
            if tmp_q and tmp_q.exists():
                try:
                    tmp_q.unlink()
                except Exception:
                    pass
            return False
