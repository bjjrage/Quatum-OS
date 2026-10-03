# Persistence & Control Plane (v1.5)

## Storage architecture (frozen)

| Layer | Technology | Role |
|---|---|---|
| Raw market data | Local Parquet + ZSTD (`data/raw/`) | Authoritative, append-only, never auto-deleted |
| Analytics | DuckDB over Parquet | Research queries |
| Control plane | Supabase Postgres (`migrations/0001_control_plane.sql`) | Experiments, holdout audits, paper, risk, capital, prop, audit, config, file catalog |
| Object copies | Supabase Storage | Replica of finalized Parquet parts |
| Local control-plane DB | SQLite WAL (`data/control_plane/control_plane.db`) | Durable local ledger + **outbox** |

No raw ticks in Postgres. **Local writes never depend on the cloud**: every domain write lands in the
local SQLite ledger first and is enqueued in an outbox; `scripts/run_control_plane_sync.py` (a separate
process) drains it. Recorder never waits on cloud; replication is read-only on finalized `part-*.parquet`.

Invariants: UNKNOWN != SAFE, CORRUPTED != EMPTY, MISSING != PASS, UNVERIFIED != ALLOWED.

## Configuration

Env vars (see `.env.example`; placeholders only): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`
(server-side only), `SUPABASE_ANON_KEY`, `SUPABASE_STORAGE_BUCKET_MARKET_DATA`,
`SUPABASE_STORAGE_BUCKET_RESEARCH`. Without them, remote status is reported
`{"status":"NOT_CONFIGURED","source":"SUPABASE",...}`; outbox rows stay `PENDING` (attempts not burned).

## Migrations

Ordered, versioned SQL in `migrations/`. `0001_control_plane.sql` is **generated** from
`src/persistence/schema.py::render_migration_sql()`; a test fails on drift. Apply with the Supabase SQL
editor / CLI using the service role. Each table: primary key, typed indexed columns, full `payload jsonb`,
`synced_at`. Evidentiary tables are append-only (`forbid_mutation()` trigger).
Foreign keys are intentionally **soft references** because the outbox syncs asynchronously and out of order.

## Tables (33) and purpose

See `TABLE_SPECS` in `src/persistence/schema.py` (purpose string per table): strategy registry/versions/rule
evidence, counterparty theses, experiments (+metrics/artifacts), holdout datasets & access audit, gate results,
paper accounts/orders/fills/positions, risk decisions/events, kill-switch events, capital pockets, prop rule
profiles/evidence/exam attempts/simulations, multi-account evidence, event clusters, audit events,
market_data_files (Parquet catalog), research datasets/artifacts, configuration snapshots.

## RLS / access assumptions

RLS enabled on every table; **no** policies for `anon`/`authenticated`; `revoke all` from them. All access is
via the service-role key from backend processes only; never ship it to `apps/web`. Honest limit: a
service-role/superuser can disable triggers, so immutability is enforced in application code and by trigger, but
is **not** cryptographically guaranteed. The audit hash chain detects naive tampering only.

## Authority rules

- `ExperimentRegistry` (local JSON) stays authoritative; `PersistedExperimentRegistry` mirrors every experiment,
  including failures, and trial count = `max(local, replica)` (never undercounts, survives restart).
- Holdout: local fail-closed audit governs; replica copies it; a corrupt file raises (never replicates as empty).
- Risk: DB records decisions/kill-switch events; it never overrides the deterministic Risk Engine.
  No kill-switch events => `UNKNOWN`, not safe.
- Capital: own baseline USD 2,000 (`HYPOTHETICAL`), authorized live capital USD 0 (locked). Pocket kinds:
  REAL / PAPER / HYPOTHETICAL / PROP_EVALUATION / NOT_CONFIGURED.
- Prop: `VERIFIED` requires provider_id, profile_version, verified_at, verified_by, rules, and evidence refs;
  fictional providers (AlphaFunding/BetaTrader/GammaProp) cannot be VERIFIED outside explicit test fixtures.
  API demo seeds are labelled `data_source: MOCK`.

## Parquet catalog / replication

`MarketDataCatalog` registers finalized parts (footer-only row count/ts range, sha256, manifest cross-check).
Status: LOCAL_ONLY / UPLOAD_PENDING / UPLOADING / SYNCED / UPLOAD_FAILED / INTEGRITY_FAILED. Sha mismatch =>
INTEGRITY_FAILED. `ParquetReplicator` verifies local sha, uploads (no overwrite), verifies remote size
(optionally by download hash) and never deletes local files. `StorageSink.on_part_finalized` is an optional,
failure-isolated hook.

## Retention & backup

Local Parquet: never auto-deleted. Postgres: no automatic purge of evidentiary tables. Back up with Supabase
PITR/daily backups plus periodic `pg_dump` of the control-plane tables; local SQLite via file copy while WAL
checkpointed. Run: `uv run python scripts/run_control_plane_sync.py --once`.
