"""Persistence abstraction: domain -> PersistenceBackend -> Local (SQLite) / Supabase adapters.

Local write NEVER depends on cloud availability. Every local change on a table is also queued
in a local outbox, replayed to the remote by ``OutboxSyncer``.

Invariants:
  * immutable (evidentiary) tables: same payload = idempotent no-op; different payload for an
    existing key raises ``ImmutableConflictError`` -- evidence is never silently overwritten.
  * unknown table -> KeyError (no ad-hoc tables).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .schema import get_spec


class PersistenceError(RuntimeError):
    pass


class ImmutableConflictError(PersistenceError):
    """Attempt to change an existing record of an append-only table."""


class NotConfiguredError(PersistenceError):
    """Remote backend has no credentials/configuration."""


class BackendUnavailableError(PersistenceError):
    """Transient failure talking to a backend (retryable)."""


INSERTED = "INSERTED"
UNCHANGED = "UNCHANGED"
UPDATED = "UPDATED"


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def payload_hash(data: Any) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


class PersistenceBackend(ABC):
    name: str = "ABSTRACT"

    @abstractmethod
    def put(self, table: str, key: str, data: Dict[str, Any], expected_hash: Optional[str] = None) -> str: ...

    @abstractmethod
    def get(self, table: str, key: str) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def list(self, table: str, limit: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def status(self) -> Dict[str, Any]: ...


def _now_ts() -> float:
    return time.time()


class LocalPersistenceBackend(PersistenceBackend):
    """SQLite-backed local control plane (stdlib only, WAL, thread-safe)."""

    name = "LOCAL"

    def __init__(self, db_path: Union[str, Path] = "data/control_plane/control_plane.db", clock: Callable[[], float] = _now_ts):
        # Test/ops isolation: the DEFAULT location may be redirected via env so automated tests
        # never write kill-switch/governance state into the real control plane. Explicit paths win.
        if str(db_path) == "data/control_plane/control_plane.db":
            db_path = os.environ.get("QUANT_OS_CONTROL_PLANE_DB") or db_path
        self.db_path = str(db_path)
        self._clock = clock
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        if self.db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS records (
                    table_name TEXT NOT NULL,
                    key TEXT NOT NULL,
                    data TEXT NOT NULL,
                    data_hash TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (table_name, key)
                );
                CREATE INDEX IF NOT EXISTS idx_records_table_seq ON records(table_name, seq);
                CREATE TABLE IF NOT EXISTS outbox (
                    outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    key TEXT NOT NULL,
                    data_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    next_attempt_at REAL NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    synced_at REAL,
                    UNIQUE (table_name, key, data_hash)
                );
                CREATE INDEX IF NOT EXISTS idx_outbox_status ON outbox(status, next_attempt_at);
                """
            )

    # ---- records -------------------------------------------------------
    def put(self, table: str, key: str, data: Dict[str, Any], expected_hash: Optional[str] = None) -> str:
        spec = get_spec(table)
        if not key:
            raise ValueError("key must be non-empty")
        h = payload_hash(data)
        now = self._clock()
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row = self._conn.execute(
                    "SELECT data_hash FROM records WHERE table_name=? AND key=?", (table, key)
                ).fetchone()
                if row is not None:
                    if row["data_hash"] == h:
                        self._conn.execute("COMMIT")
                        return UNCHANGED
                    if spec.immutable:
                        self._conn.execute("ROLLBACK")
                        raise ImmutableConflictError(
                            f"{table}[{key}] is append-only; refusing to overwrite existing evidence."
                        )
                    if expected_hash is not None and row["data_hash"] != expected_hash:
                        self._conn.execute("ROLLBACK")
                        raise PersistenceError(
                            f"Lost update detected on {table}[{key}]: expected hash {expected_hash} but found {row['data_hash']}."
                        )
                    self._conn.execute(
                        "UPDATE records SET data=?, data_hash=?, updated_at=? WHERE table_name=? AND key=?",
                        (canonical_json(data), h, now, table, key),
                    )
                    result = UPDATED
                else:
                    if expected_hash is not None:
                        self._conn.execute("ROLLBACK")
                        raise PersistenceError(
                            f"Lost update detected on {table}[{key}]: expected hash {expected_hash} but record does not exist."
                        )
                    seq = self._conn.execute("SELECT COALESCE(MAX(seq),0)+1 FROM records WHERE table_name=?", (table,)).fetchone()[0]
                    self._conn.execute(
                        "INSERT INTO records(table_name,key,data,data_hash,seq,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                        (table, key, canonical_json(data), h, seq, now, now),
                    )
                    result = INSERTED
                self._conn.execute(
                    "INSERT INTO outbox(table_name,key,data_hash,status,created_at) VALUES (?,?,?,'PENDING',?) "
                    "ON CONFLICT(table_name,key,data_hash) DO UPDATE SET status='PENDING', attempts=0, next_attempt_at=0 "
                    "WHERE outbox.status='SYNCED'",
                    (table, key, h, now),
                )
                self._conn.execute("COMMIT")
                return result
            except (ImmutableConflictError, PersistenceError):
                raise
            except Exception:
                try:
                    self._conn.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise

    def get(self, table: str, key: str) -> Optional[Dict[str, Any]]:
        get_spec(table)
        with self._lock:
            row = self._conn.execute("SELECT data FROM records WHERE table_name=? AND key=?", (table, key)).fetchone()
        return json.loads(row["data"]) if row else None

    def list(self, table: str, limit: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        get_spec(table)
        with self._lock:
            rows = self._conn.execute("SELECT data FROM records WHERE table_name=? ORDER BY seq", (table,)).fetchall()
        out = [json.loads(r["data"]) for r in rows]
        for k, v in filters.items():
            out = [r for r in out if r.get(k) == v]
        if limit is not None:
            out = out[:limit]
        return out

    def count(self, table: str) -> int:
        get_spec(table)
        with self._lock:
            return self._conn.execute("SELECT COUNT(*) FROM records WHERE table_name=?", (table,)).fetchone()[0]

    def status(self) -> Dict[str, Any]:
        return {
            "status": "OK",
            "source": "LOCAL",
            "data_source": "LOCAL_PERSISTED",
            "db_path": self.db_path,
            "outbox": self.outbox_stats(),
        }

    # ---- outbox --------------------------------------------------------
    def outbox_stats(self) -> Dict[str, int]:
        with self._lock:
            rows = self._conn.execute("SELECT status, COUNT(*) c FROM outbox GROUP BY status").fetchall()
        stats = {"PENDING": 0, "SYNCED": 0, "FAILED": 0}
        for r in rows:
            stats[r["status"]] = r["c"]
        return stats

    def outbox_due(self, limit: int = 100) -> List[Dict[str, Any]]:
        now = self._clock()
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM outbox WHERE status='PENDING' AND next_attempt_at<=? ORDER BY outbox_id LIMIT ?",
                (now, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def outbox_mark_synced(self, outbox_id: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE outbox SET status='SYNCED', synced_at=?, last_error=NULL WHERE outbox_id=?",
                (self._clock(), outbox_id),
            )

    def outbox_mark_retry(self, outbox_id: int, error: str, next_attempt_at: float, failed: bool) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE outbox SET attempts=attempts+1, last_error=?, next_attempt_at=?, status=? WHERE outbox_id=?",
                (error[:500], next_attempt_at, "FAILED" if failed else "PENDING", outbox_id),
            )

    def outbox_requeue_failed(self) -> int:
        with self._lock:
            cur = self._conn.execute("UPDATE outbox SET status='PENDING', attempts=0, next_attempt_at=0 WHERE status='FAILED'")
            return cur.rowcount

    def outbox_entry_payload(self, table: str, key: str) -> Optional[Dict[str, Any]]:
        return self.get(table, key)

    def close(self) -> None:
        with self._lock:
            self._conn.close()
