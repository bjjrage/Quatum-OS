"""First-class catalog of every immutable Parquet part (table ``market_data_files``).

Read-only with respect to the lake: files are hashed/inspected, never modified. Registering a file
whose recorded SHA-256 differs from the bytes on disk marks it INTEGRITY_FAILED and keeps the
originally recorded hash -- evidence is never silently overwritten.
"""

from __future__ import annotations

import hashlib
import json
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .backend import PersistenceBackend

LOCAL_ONLY = "LOCAL_ONLY"
UPLOAD_PENDING = "UPLOAD_PENDING"
UPLOADING = "UPLOADING"
SYNCED = "SYNCED"
UPLOAD_FAILED = "UPLOAD_FAILED"
INTEGRITY_FAILED = "INTEGRITY_FAILED"
UPLOAD_STATUSES = (LOCAL_ONLY, UPLOAD_PENDING, UPLOADING, SYNCED, UPLOAD_FAILED, INTEGRITY_FAILED)

_TS_CANDIDATES = ("ts_exchange_ns", "ts_received_utc_ns", "timestamp_ns")
_IMMUTABLE_FIELDS = ("sha256", "row_count", "byte_size", "local_path", "storage_path")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _iso(ns_or_dt: Any) -> Optional[str]:
    try:
        if isinstance(ns_or_dt, int):
            return datetime.fromtimestamp(ns_or_dt / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(ns_or_dt, datetime):
            return ns_or_dt.astimezone(timezone.utc).isoformat() if ns_or_dt.tzinfo else ns_or_dt.isoformat() + "Z"
    except Exception:
        pass
    return None


def parquet_facts(path: Path) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """(row_count, min_ts, max_ts) from Parquet footer metadata only (no data scan)."""
    try:
        import pyarrow.parquet as pq

        meta = pq.ParquetFile(str(path)).metadata
        rows = meta.num_rows
        names = [meta.schema.column(i).name for i in range(meta.num_columns)]
        for cand in _TS_CANDIDATES:
            if cand in names:
                idx = names.index(cand)
                lo = hi = None
                for rg in range(meta.num_row_groups):
                    st = meta.row_group(rg).column(idx).statistics
                    if st is None or not st.has_min_max:
                        lo = hi = None
                        break
                    lo = st.min if lo is None else min(lo, st.min)
                    hi = st.max if hi is None else max(hi, st.max)
                if lo is not None:
                    return rows, _iso(lo), _iso(hi)
        return rows, None, None
    except Exception:
        return None, None, None


def parse_partition(raw_root: Path, path: Path) -> Optional[Dict[str, Any]]:
    try:
        rel = Path(path).resolve().relative_to(Path(raw_root).resolve())
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) != 7 or not parts[-1].startswith("part-") or not parts[-1].endswith(".parquet"):
        return None
    try:
        kv = {p.split("=", 1)[0]: p.split("=", 1)[1] for p in parts[1:6]}
        return {
            "venue": parts[0],
            "table_name": kv["table"],
            "partition_year": int(kv["year"]),
            "partition_month": int(kv["month"]),
            "partition_day": int(kv["day"]),
            "partition_hour": int(kv["hour"]),
            "storage_path": rel.as_posix(),
        }
    except Exception:
        return None


def read_current_run(runtime_manifest: Path = Path("data/runtime/current_run.json")) -> Tuple[Optional[str], Optional[str]]:
    """Read-only peek at the active recorder run (never writes it)."""
    try:
        d = json.loads(Path(runtime_manifest).read_text(encoding="utf-8"))
        return d.get("run_id"), d.get("config_fingerprint")
    except Exception:
        return None, None


def _manifest_info(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """(sha256 of manifest.json, sha256 recorded for this part in the manifest)."""
    mf = Path(path).parent / "manifest.json"
    try:
        raw = mf.read_bytes()
        entries = {p["part_filename"]: p for p in json.loads(raw)["parts"]}
        entry = entries.get(Path(path).name)
        return hashlib.sha256(raw).hexdigest(), (entry or {}).get("sha256")
    except Exception:
        return None, None


class MarketDataCatalog:
    TABLE = "market_data_files"

    def __init__(self, backend: PersistenceBackend, raw_root: Path = Path("data/raw"), clock: Callable[[], float] = time.time):
        self.backend = backend
        self.raw_root = Path(raw_root)
        self._clock = clock

    @staticmethod
    def file_id_for(storage_path: str) -> str:
        return "mdf_" + hashlib.sha256(storage_path.encode("utf-8")).hexdigest()[:24]

    def _now_iso(self) -> str:
        return datetime.fromtimestamp(self._clock(), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def get(self, file_id: str) -> Optional[Dict[str, Any]]:
        return self.backend.get(self.TABLE, file_id)

    def list(self, **filters: Any) -> List[Dict[str, Any]]:
        return self.backend.list(self.TABLE, **filters)

    def _save(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        self.backend.put(self.TABLE, rec["file_id"], rec)
        return rec

    def register_file(
        self, path: Path, run_id: Optional[str], config_fingerprint: Optional[str],
        queue_upload: bool = True, known_sha256: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        path = Path(path)
        part = parse_partition(self.raw_root, path)
        if part is None or not path.exists():
            return None
        file_id = self.file_id_for(part["storage_path"])
        sha = known_sha256 or sha256_file(path)
        size = path.stat().st_size
        existing = self.get(file_id)
        if existing is not None:
            if existing["sha256"] != sha or existing["byte_size"] != size:
                return self._mark_integrity(existing, f"on-disk bytes differ from catalog (observed sha256={sha}, size={size})", observed_sha256=sha)
            return existing
        rows, tmin, tmax = parquet_facts(path)
        mf_sha, mf_entry_sha = _manifest_info(path)
        rec: Dict[str, Any] = {
            "file_id": file_id,
            "run_id": run_id,
            **{k: part[k] for k in ("venue", "table_name", "partition_year", "partition_month", "partition_day", "partition_hour")},
            "symbol": None,
            "local_path": str(path),
            "storage_path": part["storage_path"],
            "row_count": rows,
            "byte_size": size,
            "min_event_timestamp": tmin,
            "max_event_timestamp": tmax,
            "sha256": sha,
            "manifest_sha256": mf_sha,
            "manifest_part_sha256": mf_entry_sha,
            "upload_status": UPLOAD_PENDING if queue_upload else LOCAL_ONLY,
            "created_at": self._now_iso(),
            "uploaded_at": None,
            "retry_count": 0,
            "last_error": None,
            "next_attempt_at": 0.0,
            "config_fingerprint": config_fingerprint,
        }
        if mf_entry_sha is not None and mf_entry_sha != sha:
            rec["upload_status"] = INTEGRITY_FAILED
            rec["last_error"] = f"manifest part sha256 {mf_entry_sha} != computed {sha}"
        return self._save(rec)

    def _mark_integrity(self, rec: Dict[str, Any], error: str, **extra: Any) -> Dict[str, Any]:
        new = {**rec, "upload_status": INTEGRITY_FAILED, "last_error": error, **extra}
        return self._save(new)

    def update(self, file_id: str, **fields: Any) -> Dict[str, Any]:
        rec = self.get(file_id)
        if rec is None:
            raise KeyError(file_id)
        bad = [f for f in fields if f in _IMMUTABLE_FIELDS and fields[f] != rec.get(f)]
        if bad:
            raise ValueError(f"Refusing to alter immutable catalog fields: {bad}")
        if "upload_status" in fields and fields["upload_status"] not in UPLOAD_STATUSES:
            raise ValueError(f"invalid upload_status {fields['upload_status']}")
        return self._save({**rec, **fields})

    def verify_local(self, file_id: str) -> bool:
        rec = self.get(file_id)
        if rec is None:
            raise KeyError(file_id)
        p = Path(rec["local_path"])
        if not p.exists():
            self._mark_integrity(rec, "local file missing")
            return False
        sha, size = sha256_file(p), p.stat().st_size
        if sha != rec["sha256"] or size != rec["byte_size"]:
            self._mark_integrity(rec, f"local bytes differ from catalog (observed sha256={sha}, size={size})", observed_sha256=sha)
            return False
        return True

    def scan(self, run_id: Optional[str], config_fingerprint: Optional[str], limit: Optional[int] = None) -> int:
        """Register finalized, not-yet-cataloged parts (skips .tmp staging). Returns newly registered count."""
        n = 0
        for p in sorted(self.raw_root.rglob("part-*.parquet")):
            if ".tmp" in p.parts:
                continue
            part = parse_partition(self.raw_root, p)
            if part is None or self.get(self.file_id_for(part["storage_path"])) is not None:
                continue
            if self.register_file(p, run_id, config_fingerprint) is not None:
                n += 1
                if limit and n >= limit:
                    break
        return n

    def stats(self) -> Dict[str, int]:
        out = {s: 0 for s in UPLOAD_STATUSES}
        for r in self.list():
            out[r["upload_status"]] = out.get(r["upload_status"], 0) + 1
        return out


class CatalogIngestor:
    """Non-blocking sink hook: ``enqueue`` never blocks/raises into the recorder; a worker registers files."""

    def __init__(self, catalog: MarketDataCatalog, run_id: Optional[str], config_fingerprint: Optional[str]):
        self.catalog = catalog
        self.run_id = run_id
        self.config_fingerprint = config_fingerprint
        self._q: "queue.SimpleQueue[Optional[Tuple[Path, Optional[str]]]]" = queue.SimpleQueue()
        self._thread = threading.Thread(target=self._run, name="catalog-ingestor", daemon=True)
        self._thread.start()

    def enqueue(self, path: Path, sha256: Optional[str] = None) -> None:
        try:
            self._q.put_nowait((Path(path), sha256))
        except Exception:
            pass

    def _run(self) -> None:
        while True:
            item = self._q.get()
            if item is None:
                return
            try:
                self.catalog.register_file(item[0], self.run_id, self.config_fingerprint, known_sha256=item[1])
            except Exception:
                pass  # recorder must never be affected; startup scan() will catch up

    def stop(self) -> None:
        self._q.put(None)
        self._thread.join(timeout=5)
