"""Controlled backfill utility for Supabase control-plane data_hash column.

Invariants:
- Uses the EXACT SAME canonical Python payload_hash(payload) from src.persistence.backend.
- Never invents a separate PostgreSQL JSON serialization hash.
- Scans all authoritative mutable tables from src.persistence.schema.TABLE_SPECS.
- Idempotent: can be executed safely multiple times.
- Fails closed: if an existing data_hash mismatches the computed hash, STOPS immediately.
- Never mutates the underlying payload.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from src.persistence.backend import PersistenceError, payload_hash
from src.persistence.config import SupabaseConfig
from src.persistence.schema import TABLE_SPECS, TableSpec
from src.persistence.supabase_backend import SupabasePersistenceBackend


def get_mutable_specs() -> List[TableSpec]:
    """Retrieve authoritative list of mutable control-plane tables."""
    return [s for s in TABLE_SPECS.values() if not s.immutable]


def backfill_data_hashes(
    backend: SupabasePersistenceBackend,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Inspect and backfill data_hash on all mutable control-plane tables.
    
    Returns a structured summary report.
    """
    transport = backend._require()
    mutable_specs = get_mutable_specs()

    tables_scanned = 0
    rows_examined = 0
    hashes_backfilled = 0
    already_valid = 0
    table_reports: Dict[str, Any] = {}

    for spec in mutable_specs:
        table = spec.name
        tables_scanned += 1

        # Fetch PK, payload, and data_hash
        status, body = transport.request(
            "GET",
            f"/rest/v1/{table}",
            params={"select": f"{spec.pk},payload,data_hash", "order": f"{spec.pk}.asc"},
        )
        backend._check(status, body)

        rows = body if isinstance(body, list) else []
        t_examined = len(rows)
        t_backfilled = 0
        t_valid = 0

        for r in rows:
            rows_examined += 1
            pk_val = r.get(spec.pk)
            payload = r.get("payload")
            current_hash = r.get("data_hash")

            if payload is None:
                continue

            computed_hash = payload_hash(payload)

            if current_hash is None:
                if not dry_run:
                    # Target only this exact row where data_hash is null
                    patch_params = {spec.pk: f"eq.{pk_val}", "data_hash": "is.null"}
                    p_status, p_body = transport.request(
                        "PATCH",
                        f"/rest/v1/{table}",
                        params=patch_params,
                        json_body={"data_hash": computed_hash},
                        headers={"Prefer": "return=representation"},
                    )
                    backend._check(p_status, p_body)
                    if isinstance(p_body, list) and len(p_body) != 1:
                        raise PersistenceError(
                            f"BACKFILL_RACE: Expected 1 row updated for {table}[{pk_val}], got {len(p_body)}"
                        )
                t_backfilled += 1
                hashes_backfilled += 1
            elif current_hash != computed_hash:
                raise PersistenceError(
                    f"INTEGRITY_FAILURE: {table}[{pk_val}] data_hash {current_hash!r} "
                    f"differs from computed canonical hash {computed_hash!r}. Aborting backfill."
                )
            else:
                t_valid += 1
                already_valid += 1

        # Post-backfill verification: check for any remaining NULL data_hash
        if not dry_run:
            v_status, v_body = transport.request(
                "GET",
                f"/rest/v1/{table}",
                params={"select": spec.pk, "data_hash": "is.null"},
            )
            backend._check(v_status, v_body)
            null_count = len(v_body) if isinstance(v_body, list) else 0
        else:
            null_count = t_backfilled

        table_reports[table] = {
            "rows_examined": t_examined,
            "backfilled": t_backfilled,
            "already_valid": t_valid,
            "null_hashes_remaining": null_count,
        }

    total_null_remaining = sum(t["null_hashes_remaining"] for t in table_reports.values())
    status_str = "DRY_RUN" if dry_run else ("COMPLETE" if total_null_remaining == 0 else "BLOCKED")

    return {
        "status": status_str,
        "dry_run": dry_run,
        "tables_scanned": tables_scanned,
        "rows_examined": rows_examined,
        "hashes_backfilled": hashes_backfilled,
        "already_valid": already_valid,
        "null_hashes_remaining": total_null_remaining,
        "table_reports": table_reports,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Supabase data_hash column canonically.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect without modifying data_hash.")
    args = parser.parse_args()

    cfg = SupabaseConfig.from_env()
    if not cfg.is_configured:
        print(f"Error: Supabase is not configured. Missing: {cfg.missing()}", file=sys.stderr)
        return 1

    backend = SupabasePersistenceBackend(cfg)
    try:
        report = backfill_data_hashes(backend, dry_run=args.dry_run)
        print(json.dumps(report, indent=2))
        return 0 if report["status"] in ("COMPLETE", "DRY_RUN") else 2
    except Exception as e:
        print(f"Backfill aborted due to error: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
