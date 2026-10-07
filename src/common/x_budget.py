"""Shared, persistent X spend guard and request provenance ledger."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DAILY_BUDGET_USD = 1.0
DEFAULT_CALL_RESERVATION_USD = 0.25
QUERY_VERSION = "x_search_v1"


def daily_budget(root: Path = ROOT) -> float:
    from src.common.secret_loader import read_env_file
    raw = os.environ.get("X_DAILY_BUDGET_USD") or read_env_file(Path(root) / ".env").get("X_DAILY_BUDGET_USD")
    try:
        value = float(raw) if raw is not None else DEFAULT_DAILY_BUDGET_USD
        return value if math.isfinite(value) and value >= 0 else DEFAULT_DAILY_BUDGET_USD
    except (TypeError, ValueError):
        return DEFAULT_DAILY_BUDGET_USD


class XBudgetLedger:
    def __init__(self, root: Path = ROOT, limit_usd: Optional[float] = None):
        self.root = Path(root)
        self.path = self.root / "data" / "runtime" / "x_budget.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit_usd = daily_budget(self.root) if limit_usd is None else max(0.0, float(limit_usd))
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS x_calls (
                call_id TEXT PRIMARY KEY, day TEXT NOT NULL, ts_utc_ns INTEGER NOT NULL,
                consumer TEXT NOT NULL, model TEXT NOT NULL, query_version TEXT NOT NULL,
                query_hash TEXT NOT NULL, status TEXT NOT NULL,
                estimated_cost REAL NOT NULL, actual_cost REAL,
                posts_count INTEGER, narrative_link INTEGER, request_id TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS ix_x_calls_day ON x_calls(day)")

    def seed_legacy(self, day: str, consumer: str, amount: float) -> None:
        """Import a previously persisted per-consumer spend once during migration."""
        amount = max(0.0, float(amount))
        if amount <= 0:
            return
        with self._connect() as db:
            db.execute("""INSERT OR IGNORE INTO x_calls
                (call_id,day,ts_utc_ns,consumer,model,query_version,query_hash,status,estimated_cost,actual_cost)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (f"legacy:{consumer}:{day}", day, 0, consumer, "legacy", "legacy_import", "", "IMPORTED", 0.0, amount))

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=20.0, isolation_level=None)
        db.execute("PRAGMA busy_timeout=20000")
        return db

    @staticmethod
    def _day(now_ns: Optional[int] = None) -> str:
        return datetime.fromtimestamp((now_ns or time.time_ns()) / 1e9, tz=timezone.utc).date().isoformat()

    def reserve(self, consumer: str, query: str, model: str, estimated_cost: float = DEFAULT_CALL_RESERVATION_USD,
                now_ns: Optional[int] = None) -> Optional[str]:
        estimate = max(0.0, float(estimated_cost))
        if self.limit_usd <= 0 or estimate <= 0:
            return None
        day = self._day(now_ns)
        call_id = uuid.uuid4().hex
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            spent = db.execute("""SELECT COALESCE(SUM(CASE WHEN status='IN_FLIGHT'
                              THEN estimated_cost ELSE COALESCE(actual_cost, estimated_cost) END),0)
                              FROM x_calls WHERE day=?""", (day,)).fetchone()[0]
            if float(spent) + estimate > self.limit_usd + 1e-12:
                db.execute("ROLLBACK")
                return None
            db.execute("""INSERT INTO x_calls
                (call_id,day,ts_utc_ns,consumer,model,query_version,query_hash,status,estimated_cost)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (call_id, day, now_ns or time.time_ns(), consumer, model, QUERY_VERSION,
                 query_hash, "IN_FLIGHT", estimate))
            db.execute("COMMIT")
        return call_id

    def finish(self, call_id: str, status: str, actual_cost: Optional[float], posts_count: Optional[int] = None,
               narrative_link: Optional[bool] = None, request_id: Optional[str] = None) -> None:
        with self._connect() as db:
            if actual_cost is not None and (not math.isfinite(float(actual_cost)) or float(actual_cost) < 0):
                actual_cost = None
            db.execute("""UPDATE x_calls SET status=?, actual_cost=?, posts_count=?, narrative_link=?, request_id=?
                         WHERE call_id=?""",
                       (status, actual_cost, posts_count,
                        None if narrative_link is None else int(narrative_link),
                        request_id, call_id))

    def snapshot(self, day: Optional[str] = None) -> Dict[str, Any]:
        day = day or self._day()
        with self._connect() as db:
            rows = db.execute("""SELECT consumer,status,estimated_cost,actual_cost FROM x_calls WHERE day=?""",
                              (day,)).fetchall()
        spent = sum(float(actual if actual is not None else estimated) for _, _, estimated, actual in rows)
        reserved = sum(float(estimated) for _, status, estimated, _ in rows if status == "IN_FLIGHT")
        return {"day": day, "limit_usd": self.limit_usd, "spent_usd": spent,
                "reserved_usd": reserved, "remaining_usd": max(0.0, self.limit_usd - spent),
                "calls": len(rows), "by_consumer": {
                    c: sum(1 for cc, _, _, _ in rows if cc == c) for c in sorted({r[0] for r in rows})}}
