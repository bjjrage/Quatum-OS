"""Asynchronous Parquet replication to object storage. The recorder never calls this.

Flow per cataloged part: UPLOAD_PENDING -> UPLOADING -> verify local sha/size -> upload ->
verify remote metadata (size, hash when available, optional download hash) -> SYNCED.
Any mismatch -> INTEGRITY_FAILED (never overwritten). Transport errors -> UPLOAD_FAILED with bounded
exponential backoff. Local Parquet files are NEVER deleted.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional

from .backend import NotConfiguredError
from .catalog import (
    INTEGRITY_FAILED,
    SYNCED,
    UPLOAD_FAILED,
    UPLOAD_PENDING,
    UPLOADING,
    MarketDataCatalog,
    sha256_file,
)
from .supabase_backend import ObjectStorageTransport
from .sync import OutboxSyncer, backoff_delay


@dataclass
class ReplicationReport:
    synced: int = 0
    failed: int = 0
    integrity_failed: int = 0
    skipped_not_due: int = 0
    not_configured: bool = False
    errors: List[str] = field(default_factory=list)


class ParquetReplicator:
    def __init__(
        self,
        catalog: MarketDataCatalog,
        storage: Optional[ObjectStorageTransport],
        bucket: Optional[str],
        max_attempts: int = 8,
        base_delay: float = 2.0,
        max_delay: float = 600.0,
        verify_mode: str = "size",  # "size" | "download_hash"
        clock: Callable[[], float] = time.time,
    ):
        if verify_mode not in ("size", "download_hash"):
            raise ValueError("verify_mode must be 'size' or 'download_hash'")
        self.catalog = catalog
        self.storage = storage
        self.bucket = bucket
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.verify_mode = verify_mode
        self._clock = clock

    def recover_stuck(self) -> int:
        """Files left in UPLOADING by a crashed process go back to UPLOAD_PENDING."""
        n = 0
        for rec in self.catalog.list(upload_status=UPLOADING):
            self.catalog.update(rec["file_id"], upload_status=UPLOAD_PENDING)
            n += 1
        return n

    def requeue_failed(self) -> int:
        n = 0
        for rec in self.catalog.list(upload_status=UPLOAD_FAILED):
            self.catalog.update(rec["file_id"], upload_status=UPLOAD_PENDING, retry_count=0, next_attempt_at=0.0)
            n += 1
        return n

    def _now_iso(self) -> str:
        return datetime.fromtimestamp(self._clock(), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def replicate_once(self, limit: int = 50) -> ReplicationReport:
        rep = ReplicationReport()
        if self.storage is None or not self.bucket:
            rep.not_configured = True  # nothing is claimed; files stay UPLOAD_PENDING
            return rep
        candidates = self.catalog.list(upload_status=UPLOAD_PENDING) + [
            r for r in self.catalog.list(upload_status=UPLOAD_FAILED) if r.get("retry_count", 0) < self.max_attempts
        ]
        for rec in candidates[:limit]:
            if rec.get("next_attempt_at", 0) > self._clock():
                rep.skipped_not_due += 1
                continue
            self._replicate_one(rec["file_id"], rep)
            if rep.not_configured:
                break
        return rep

    def _replicate_one(self, file_id: str, rep: ReplicationReport) -> None:
        cat = self.catalog
        rec = cat.update(file_id, upload_status=UPLOADING)
        local = Path(rec["local_path"])
        try:
            if not local.exists() or sha256_file(local) != rec["sha256"] or local.stat().st_size != rec["byte_size"]:
                cat.verify_local(file_id)  # marks INTEGRITY_FAILED with details
                rep.integrity_failed += 1
                return
            self.storage.upload(self.bucket, rec["storage_path"], local, rec["sha256"])
            info = self.storage.head(self.bucket, rec["storage_path"])
            if info is None:
                raise RuntimeError("remote object missing after upload")
            problem = None
            if info.size != rec["byte_size"]:
                problem = f"remote size {info.size} != local {rec['byte_size']}"
            elif info.sha256 is not None and info.sha256 != rec["sha256"]:
                problem = f"remote sha256 {info.sha256} != local {rec['sha256']}"
            elif self.verify_mode == "download_hash":
                remote_sha = self.storage.download_sha256(self.bucket, rec["storage_path"])
                if remote_sha != rec["sha256"]:
                    problem = f"downloaded sha256 {remote_sha} != local {rec['sha256']}"
            if problem:
                cat.update(file_id, upload_status=INTEGRITY_FAILED, last_error=problem)
                rep.integrity_failed += 1
                return
            cat.update(file_id, upload_status=SYNCED, uploaded_at=self._now_iso(), last_error=None)
            rep.synced += 1
        except NotConfiguredError:
            cat.update(file_id, upload_status=UPLOAD_PENDING)
            rep.not_configured = True
        except Exception as e:  # noqa: BLE001 - upload failures are retryable, never fatal
            retries = rec.get("retry_count", 0) + 1
            cat.update(
                file_id, upload_status=UPLOAD_FAILED, retry_count=retries, last_error=str(e)[:500],
                next_attempt_at=self._clock() + backoff_delay(retries - 1, self.base_delay, self.max_delay),
            )
            rep.failed += 1
            rep.errors.append(str(e))


class ControlPlaneSyncService:
    """Background thread: catalog scan + parquet replication + outbox replay. Failure-isolated."""

    def __init__(self, tick: Callable[[], None], interval: float = 30.0):
        self._tick = tick
        self._interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="control-plane-sync", daemon=True)
        self.last_error: Optional[str] = None

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
                self.last_error = None
            except Exception as e:  # noqa: BLE001
                self.last_error = str(e)
            self._stop.wait(self._interval)

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)
