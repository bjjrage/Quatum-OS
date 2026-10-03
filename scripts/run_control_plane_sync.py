"""Separate-process control-plane sync (never imported by the recorder).

scan raw Parquet -> catalog -> replicate to object storage -> sync outbox to Postgres.
Read-only on local Parquet; never deletes local files. Without Supabase config it reports
NOT_CONFIGURED and still catalogs locally.

Usage: uv run python scripts/run_control_plane_sync.py [--once] [--interval 30]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from src.persistence.backend import LocalPersistenceBackend
from src.persistence.catalog import MarketDataCatalog, read_current_run
from src.persistence.config import SupabaseConfig
from src.persistence.replication import ParquetReplicator
from src.persistence.supabase_backend import (
    SupabasePersistenceBackend, SupabaseStorageTransport, UrllibRestTransport,
)
from src.persistence.sync import OutboxSyncer


def run_once(local: LocalPersistenceBackend, cfg: SupabaseConfig, raw_root: Path) -> dict:
    run_id, cfp = read_current_run()
    catalog = MarketDataCatalog(local, raw_root=raw_root)
    scanned = catalog.scan(run_id, cfp)
    storage = bucket = None
    remote = SupabasePersistenceBackend(cfg)
    if cfg.is_configured:
        storage = SupabaseStorageTransport(UrllibRestTransport(cfg))
        bucket = cfg.bucket_market_data
    rep = ParquetReplicator(catalog, storage, bucket)
    rep.recover_stuck()
    rep_report = rep.replicate_once()
    sync_report = OutboxSyncer(local, remote).sync_once()
    return {"scanned": scanned, "remote": cfg.status(), "replication": str(rep_report),
            "outbox": local.outbox_stats(), "sync": str(sync_report), "catalog": catalog.stats()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=float, default=30.0)
    ap.add_argument("--db", default="data/control_plane/control_plane.db")
    ap.add_argument("--raw-root", default="data/raw")
    a = ap.parse_args()
    local = LocalPersistenceBackend(a.db)
    cfg = SupabaseConfig.from_env()
    while True:
        try:
            print(json.dumps(run_once(local, cfg, Path(a.raw_root)), default=str))
        except Exception as e:  # keep looping; never affect recorder
            print(f"sync cycle error: {type(e).__name__}: {e}", file=sys.stderr)
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
