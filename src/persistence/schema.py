"""Control-plane schema: single source of truth for tables, indexed columns and immutability.

The committed SQL migration in ``migrations/`` is rendered from this module and a test
asserts they never drift. Every remote row is ``{pk, <indexed columns>, payload jsonb}``;
the full evidentiary record always lives in ``payload``.

Soft references only (no FOREIGN KEY constraints) are used on purpose: rows arrive
asynchronously through the outbox and a child may legitimately be synced before its
parent. Referential consistency is checked by reconciliation, not by the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

MIGRATION_0001_NAME = "0001_control_plane.sql"
MIGRATION_0002_NAME = "0002_data_hash.sql"


@dataclass(frozen=True)
class TableSpec:
    name: str
    pk: str
    columns: Tuple[Tuple[str, str], ...]  # (column, postgres type) -- indexed columns
    immutable: bool
    purpose: str

    @property
    def column_names(self) -> List[str]:
        return [c for c, _ in self.columns]


def _cols(spec: str) -> Tuple[Tuple[str, str], ...]:
    out = []
    for token in spec.split():
        name, _, typ = token.partition(":")
        out.append((name, typ or "text"))
    return tuple(out)


def _t(name: str, pk: str, cols: str, immutable: bool, purpose: str) -> TableSpec:
    return TableSpec(name, pk, _cols(cols), immutable, purpose)


_SPECS: List[TableSpec] = [
    _t("system_instances", "instance_id", "git_sha mode started_at:timestamptz", False, "API/recorder process instances"),
    _t("strategy_registry", "strategy_id", "family origin stage economic_edge_validated:boolean", False, "Strategy inventory and lifecycle stage"),
    _t("strategy_versions", "version_key", "strategy_id strategy_version config_fingerprint", True, "Immutable strategy version snapshots"),
    _t("strategy_rule_evidence", "rule_key", "strategy_id rule_id status", False, "Rule provenance (INTUITION_UNVALIDATED ...)"),
    _t("counterparty_theses", "thesis_key", "strategy_id strategy_version evidence_status", False, "Counterparty thesis per strategy version"),
    _t("experiments", "experiment_id", "strategy_id strategy_version dataset_fingerprint config_fingerprint gate_result created_at:timestamptz", True, "Every experiment incl. failures (trial accounting)"),
    _t("experiment_metrics", "metric_key", "experiment_id", True, "Metrics per experiment"),
    _t("experiment_artifacts", "artifact_id", "experiment_id storage_path sha256", True, "Artifacts produced by experiments"),
    _t("holdout_datasets", "dataset_id", "strategy_id dataset_fingerprint", True, "Sealed holdout dataset registrations"),
    _t("holdout_access_audit", "audit_id", "strategy_id strategy_version audit_hash opened_at:timestamptz", True, "Replica of holdout access audit"),
    _t("strategy_gate_results", "gate_result_id", "strategy_id strategy_version gate_type status dataset_fingerprint config_fingerprint", True, "Auditable gate evaluations"),
    _t("paper_accounts", "paper_account_id", "status data_source", False, "Paper accounts"),
    _t("paper_orders", "order_id", "paper_account_id strategy_id symbol status idempotency_key", False, "Paper orders (status transitions idempotent)"),
    _t("paper_fills", "fill_id", "order_id paper_account_id symbol", True, "Paper fills"),
    _t("paper_positions", "position_key", "paper_account_id symbol", False, "Paper positions / snapshots"),
    _t("risk_decisions", "decision_id", "strategy_id symbol approved:boolean violation_code timestamp_utc:timestamptz", True, "Deterministic risk decisions (approve/veto)"),
    _t("risk_events", "event_id", "event_type strategy_id timestamp_utc:timestamptz", True, "Risk events"),
    _t("kill_switch_events", "event_id", "action scope actor timestamp_utc:timestamptz", True, "Kill switch activate/reset"),
    _t("capital_pockets", "capital_pocket_id", "pocket_type state_kind authorized_live_capital_usd:numeric", False, "Capital pocket definitions/state"),
    _t("prop_rule_profiles", "profile_key", "provider_id profile_version verification_status evidence_fingerprint", False, "Prop firm rule profiles"),
    _t("prop_profile_evidence", "evidence_id", "provider_id profile_version evidence_fingerprint", True, "Evidence backing prop profiles"),
    _t("prop_exam_attempts", "attempt_id", "strategy_id strategy_version provider_id profile_version passed:boolean", True, "Prop exam attempts"),
    _t("prop_exam_simulations", "simulation_id", "strategy_id provider_id profile_version status", True, "Prop exam Monte Carlo results"),
    _t("multi_account_evidence", "evidence_id", "provider_name account_id", True, "Written multi-account evidence"),
    _t("event_clusters", "cluster_id", "description", False, "EventCluster definitions"),
    _t("audit_events", "audit_id", "event_type entity_type entity_id timestamp_utc:timestamptz chain_hash", True, "Append-oriented audit trail (hash chained)"),
    _t(
        "market_data_files",
        "file_id",
        "run_id venue table_name symbol partition_year:integer partition_month:integer partition_day:integer "
        "partition_hour:integer local_path storage_path row_count:bigint byte_size:bigint "
        "min_event_timestamp:timestamptz max_event_timestamp:timestamptz sha256 manifest_sha256 upload_status "
        "created_at:timestamptz uploaded_at:timestamptz retry_count:integer last_error config_fingerprint",
        False,
        "Catalog of every immutable Parquet part",
    ),
    _t("research_datasets", "dataset_id", "dataset_fingerprint config_fingerprint storage_path", True, "Research dataset registrations"),
    _t("research_artifacts", "artifact_id", "artifact_type sha256 storage_path", True, "Backtest/model/report artifacts"),
    _t("configuration_snapshots", "snapshot_id", "config_kind config_fingerprint created_at:timestamptz", True, "Versioned configuration snapshots"),
    # ---- Execution plane (v1): all evidentiary, soft refs ----
    _t("execution_intents", "intent_id", "strategy_id venue symbol idempotency_key client_order_id execution_mode created_at:timestamptz", True, "Canonical OrderIntents (immutable evidence)"),
    _t("execution_orders", "intent_id", "client_order_id venue_order_id venue symbol state idempotency_key", False, "Current order lifecycle state (mutable projection)"),
    _t("execution_attempts", "attempt_id", "intent_id client_order_id venue attempt_no outcome started_at:timestamptz", True, "Every submission attempt (written BEFORE transmission)"),
    _t("order_state_transitions", "transition_id", "intent_id from_state to_state at:timestamptz", True, "Order state machine transitions"),
    _t("execution_fills", "fill_id", "intent_id venue venue_trade_id", True, "Normalized fills incl. partials and fees"),
    _t("reconciliation_events", "event_id", "venue status at:timestamptz", True, "Reconciliation evidence"),
    _t("connection_events", "event_id", "venue event_type at:timestamptz", True, "Connection/private-stream/clock events"),
    _t("rate_limit_events", "event_id", "venue event_type at:timestamptz", True, "Rate-limit telemetry"),
    _t("latency_samples", "sample_id", "intent_id venue", True, "Execution latency traces"),
    _t("account_snapshots", "snapshot_id", "venue account_id status at:timestamptz", True, "Normalized account snapshots")
]

TABLE_SPECS: Dict[str, TableSpec] = {s.name: s for s in _SPECS}


def get_spec(table: str) -> TableSpec:
    try:
        return TABLE_SPECS[table]
    except KeyError:
        raise KeyError(f"Unknown control-plane table '{table}'") from None


def remote_row(table: str, key: str, data: dict) -> dict:
    """Project a record into the remote row shape (pk + indexed columns + payload)."""
    spec = get_spec(table)
    row = {spec.pk: key}
    for col in spec.column_names:
        val = data.get(col)
        if isinstance(val, (dict, list)):
            val = None
        row[col] = val
    row["payload"] = data
    return row


def render_migration_sql() -> str:
    lines: List[str] = [
        "-- Trading / Quant OS control plane, migration 0001 (GENERATED by src/persistence/schema.py).",
        "-- Do not edit by hand: tests/test_persistence_schema.py asserts this file equals the rendered output.",
        "-- Soft references only (no FKs): rows arrive asynchronously through the outbox.",
        "",
        "create or replace function public.forbid_mutation() returns trigger",
        "language plpgsql as $$",
        "begin",
        "  raise exception 'table % is append-only: % not allowed', TG_TABLE_NAME, TG_OP;",
        "end;",
        "$$;",
        "",
    ]
    for spec in _SPECS:
        lines.append(f"-- {spec.purpose}")
        lines.append(f"create table if not exists public.{spec.name} (")
        lines.append(f"  {spec.pk} text primary key,")
        for col, typ in spec.columns:
            lines.append(f"  {col} {typ},")
        lines.append("  payload jsonb not null,")
        lines.append("  synced_at timestamptz not null default now()")
        lines.append(");")
        for col, _ in spec.columns:
            lines.append(f"create index if not exists idx_{spec.name}_{col} on public.{spec.name} ({col});")
        lines.append(f"alter table public.{spec.name} enable row level security;")
        lines.append(f"revoke all on public.{spec.name} from anon, authenticated;")
        if spec.immutable:
            lines.append(f"drop trigger if exists trg_{spec.name}_append_only on public.{spec.name};")
            lines.append(
                f"create trigger trg_{spec.name}_append_only before update or delete on public.{spec.name} "
                "for each row execute function public.forbid_mutation();"
            )
        lines.append("")
    return "\n".join(lines)


def render_migration_0002_sql() -> str:
    lines: List[str] = [
        "-- Trading / Quant OS control plane, migration 0002 (GENERATED by src/persistence/schema.py).",
        "-- Safe schema migration: adds data_hash column to all mutable control-plane tables.",
        "-- PostgREST conditional PATCH uses data_hash for atomic CAS updates without RPC.",
        "",
    ]
    mutable_specs = [s for s in _SPECS if not s.immutable]
    for s in mutable_specs:
        lines.append(f"alter table if exists public.{s.name} add column if not exists data_hash text;")
    lines.append("")
    return "\n".join(lines)

