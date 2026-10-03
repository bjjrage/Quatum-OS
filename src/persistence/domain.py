"""Domain persistence adapters built on a PersistenceBackend.

Invariants: UNKNOWN != SAFE, CORRUPTED != EMPTY, MISSING != PASS, UNVERIFIED != ALLOWED.
Local files / engines remain authoritative; the backend is a durable replica + control plane.
"""
from __future__ import annotations

import dataclasses
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.persistence.backend import PersistenceBackend, payload_hash, canonical_json

# ----------------------------------------------------------------- capital
OWN_CAPITAL_BASELINE_USD = 2000.0
AUTHORIZED_LIVE_CAPITAL_USD = 0.0
POCKET_STATE_KINDS = ("REAL", "PAPER", "HYPOTHETICAL", "PROP_EVALUATION", "NOT_CONFIGURED")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapitalError(ValueError):
    pass


class CapitalPocketStore:
    """Capital pockets. Live authorization is hard-locked at $0 until evidence earns it."""

    def __init__(self, backend: PersistenceBackend):
        self.backend = backend

    def upsert(self, pocket_id: str, pocket_type: str, state_kind: str, amount_usd: Optional[float],
               authorized_live_capital_usd: float = AUTHORIZED_LIVE_CAPITAL_USD, notes: str = "") -> str:
        if state_kind not in POCKET_STATE_KINDS:
            raise CapitalError(f"Unknown state_kind {state_kind!r}")
        if authorized_live_capital_usd != AUTHORIZED_LIVE_CAPITAL_USD:
            raise CapitalError("Live capital authorization is locked at $0")
        if state_kind == "REAL" and (amount_usd is None):
            raise CapitalError("REAL pocket requires explicit amount")
        return self.backend.put("capital_pockets", pocket_id, {
            "capital_pocket_id": pocket_id, "pocket_type": pocket_type, "state_kind": state_kind,
            "amount_usd": amount_usd, "authorized_live_capital_usd": authorized_live_capital_usd,
            "notes": notes, "updated_at": _now_iso(),
        })

    def seed_baseline(self) -> None:
        """Own capital baseline USD 2,000 -- an unconfirmed model baseline, never REAL."""
        if self.backend.get("capital_pockets", "OWN_MAIN") is None:
            self.upsert("OWN_MAIN", "OWN", "HYPOTHETICAL", OWN_CAPITAL_BASELINE_USD,
                        notes="Model baseline; may rise toward 20k only if evidence earns it")

    def get(self, pocket_id: str) -> Optional[Dict[str, Any]]:
        return self.backend.get("capital_pockets", pocket_id)

    def list(self) -> List[Dict[str, Any]]:
        return self.backend.list("capital_pockets")


# -------------------------------------------------------------------- prop
FICTIONAL_PROVIDERS = frozenset({"alphafunding", "betatrader", "gammaprop"})
PROP_STATUSES = ("UNKNOWN", "PENDING", "VERIFIED", "REJECTED", "STALE")
_REQUIRED_VERIFIED = ("provider_id", "profile_version", "verified_at", "verified_by", "rules")


class PropProfileError(ValueError):
    pass


class PropProfileStore:
    def __init__(self, backend: PersistenceBackend, allow_fixture_providers: bool = False):
        self.backend = backend
        self.allow_fixture_providers = allow_fixture_providers

    @staticmethod
    def evidence_fingerprint(evidence_refs: List[str], rules: Dict[str, Any]) -> str:
        return payload_hash({"evidence_refs": sorted(evidence_refs), "rules": rules})

    def put_profile(self, provider_id: str, profile_version: str, verification_status: str = "UNKNOWN",
                    rules: Optional[Dict[str, Any]] = None, evidence_refs: Optional[List[str]] = None,
                    verified_at: Optional[str] = None, verified_by: Optional[str] = None,
                    is_fixture: bool = False) -> str:
        if verification_status not in PROP_STATUSES:
            raise PropProfileError(f"Unknown verification_status {verification_status!r}")
        rules = rules or {}
        refs = list(evidence_refs or [])
        fictional = provider_id.strip().lower() in FICTIONAL_PROVIDERS
        if fictional and not (is_fixture and self.allow_fixture_providers):
            if verification_status == "VERIFIED":
                raise PropProfileError(f"Fictional provider {provider_id!r} cannot be VERIFIED")
        if is_fixture and not self.allow_fixture_providers:
            raise PropProfileError("Fixture profiles are only allowed in tests")
        if verification_status == "VERIFIED":
            probe = {"provider_id": provider_id, "profile_version": profile_version,
                     "verified_at": verified_at, "verified_by": verified_by, "rules": rules}
            missing = [k for k in _REQUIRED_VERIFIED if not probe.get(k)]
            if not refs:
                missing.append("evidence_refs")
            if missing:
                raise PropProfileError(f"VERIFIED requires evidence; missing: {missing}")
            if fictional:
                # fixture path only reachable in tests
                pass
        fp = self.evidence_fingerprint(refs, rules)
        key = f"{provider_id}:{profile_version}"
        data = {"profile_key": key, "provider_id": provider_id, "profile_version": profile_version,
                "verification_status": verification_status, "rules": rules, "evidence_refs": refs,
                "verified_at": verified_at, "verified_by": verified_by, "evidence_fingerprint": fp,
                "is_fixture": is_fixture, "data_source": "FIXTURE" if is_fixture else "LOCAL_PERSISTED"}
        if verification_status == "VERIFIED":
            self.backend.put("prop_profile_evidence", f"{key}:{fp[:16]}", {
                "evidence_id": f"{key}:{fp[:16]}", "provider_id": provider_id,
                "profile_version": profile_version, "evidence_fingerprint": fp, "evidence_refs": refs})
        return self.backend.put("prop_rule_profiles", key, data)

    def get(self, provider_id: str, profile_version: str) -> Optional[Dict[str, Any]]:
        return self.backend.get("prop_rule_profiles", f"{provider_id}:{profile_version}")

    def list(self) -> List[Dict[str, Any]]:
        return self.backend.list("prop_rule_profiles")


# ------------------------------------------------------------------- audit
GENESIS_HASH = "0" * 64


class AuditChainError(RuntimeError):
    pass


class AuditLog:
    """Append-oriented hash-chained audit log.

    The chain detects accidental/naive tampering of persisted rows. It is NOT a claim of
    cryptographic immutability: anyone holding write access can rebuild the whole chain.
    """

    def __init__(self, backend: PersistenceBackend, git_sha: str = "UNKNOWN", config_fingerprint: str = "UNKNOWN"):
        self.backend = backend
        self.git_sha = git_sha
        self.config_fingerprint = config_fingerprint

    def _ordered(self) -> List[Dict[str, Any]]:
        rows = self.backend.list("audit_events")
        return sorted(rows, key=lambda r: r["seq"])

    def append(self, event_type: str, actor: str, entity_type: str, entity_id: str,
               payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rows = self._ordered()
        prev = rows[-1]["chain_hash"] if rows else GENESIS_HASH
        seq = (rows[-1]["seq"] + 1) if rows else 1
        body = {"audit_id": f"aud_{seq:012d}_{uuid.uuid4().hex[:8]}", "seq": seq, "event_type": event_type,
                "actor": actor, "timestamp_utc": _now_iso(), "entity_type": entity_type,
                "entity_id": entity_id, "payload": payload or {}, "git_sha": self.git_sha,
                "config_fingerprint": self.config_fingerprint, "prev_hash": prev}
        body["chain_hash"] = payload_hash(body)
        self.backend.put("audit_events", body["audit_id"], body)
        return body

    def verify_chain(self) -> Dict[str, Any]:
        prev = GENESIS_HASH
        expected_seq = 1
        for r in self._ordered():
            core = {k: v for k, v in r.items() if k != "chain_hash"}
            if r["seq"] != expected_seq or r["prev_hash"] != prev or payload_hash(core) != r["chain_hash"]:
                return {"status": "BROKEN", "broken_at_seq": r["seq"]}
            prev = r["chain_hash"]
            expected_seq += 1
        return {"status": "OK", "length": expected_seq - 1, "head": prev}

    def list(self) -> List[Dict[str, Any]]:
        return self._ordered()


# --------------------------------------------------------- config snapshots
CONFIG_KINDS = ("CODE_DEFAULTS", "RUNTIME", "RESEARCH", "RISK", "PROP_PROFILE", "CAPITAL_AUTHORIZATION")


class ConfigSnapshotStore:
    def __init__(self, backend: PersistenceBackend):
        self.backend = backend

    def snapshot(self, config_kind: str, config: Dict[str, Any], version: str = "1") -> Dict[str, Any]:
        if config_kind not in CONFIG_KINDS:
            raise ValueError(f"Unknown config_kind {config_kind!r}")
        fp = payload_hash(config)
        sid = f"{config_kind}:{version}:{fp[:16]}"
        data = {"snapshot_id": sid, "config_kind": config_kind, "version": version,
                "config_fingerprint": fp, "config": config, "created_at": _now_iso()}
        existing = self.backend.get("configuration_snapshots", sid)
        if existing is not None:
            return existing
        self.backend.put("configuration_snapshots", sid, data)
        return data

    def list(self, config_kind: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self.backend.list("configuration_snapshots")
        return [r for r in rows if config_kind is None or r["config_kind"] == config_kind]


# -------------------------------------------------------------- experiments
def _to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj):
        return json.loads(canonical_json(dataclasses.asdict(obj)))
    if isinstance(obj, dict):
        return json.loads(canonical_json(obj))
    raise TypeError(f"Cannot serialize {type(obj).__name__}")


def make_persisted_experiment_registry(storage_dir, backend: PersistenceBackend):
    """Return an ExperimentRegistry subclass instance mirroring every experiment (incl. failures)."""
    from src.research.experiments import ExperimentRegistry

    class PersistedExperimentRegistry(ExperimentRegistry):
        def __init__(self, sdir, be: PersistenceBackend):
            self._backend = be
            super().__init__(sdir)

        def record_experiment(self, record) -> int:
            n = super().record_experiment(record)
            d = _to_dict(record)
            if not isinstance(d.get("gate_result"), str):
                d["gate_result"] = canonical_json(d.get("gate_result"))
            self._backend.put("experiments", record.experiment_id, d)
            return n

        def get_trial_count(self, strategy_id: str) -> int:
            # Fail-closed: never undercount; take the larger of local authority and replica.
            local = super().get_trial_count(strategy_id)
            replica = len(self._backend.list("experiments", strategy_id=strategy_id))
            return max(local, replica)

        def backfill(self) -> int:
            """Mirror local authoritative records into the backend (idempotent)."""
            n = 0
            for rec in getattr(self, "_experiments", {}).values() if isinstance(getattr(self, "_experiments", None), dict) else []:
                self._backend.put("experiments", rec.experiment_id, _to_dict(rec))
                n += 1
            return n

    return PersistedExperimentRegistry(storage_dir, backend)


# ----------------------------------------------------------------- holdouts
class HoldoutReplicaError(RuntimeError):
    pass


def replicate_holdout_audits(audit_path, backend: PersistenceBackend) -> int:
    """Replicate the local holdout audit file. Corrupt/unreadable file -> raise (never empty)."""
    p = Path(audit_path)
    if not p.exists():
        return 0
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # CORRUPTED != EMPTY
        raise HoldoutReplicaError(f"Holdout audit file corrupted: {e}") from e
    if not isinstance(data, list):
        raise HoldoutReplicaError("Holdout audit file must be a JSON list")
    n = 0
    for rec in data:
        row = dict(rec)
        row["audit_hash"] = payload_hash(rec)
        row["opened_at"] = row.get("timestamp_utc")
        row["strategy_id"] = row.get("strategy_id")
        row["strategy_version"] = row.get("strategy_version")
        backend.put("holdout_access_audit", row["audit_id"], row)
        n += 1
    return n


# ------------------------------------------------------------- paper / risk
class PaperStore:
    """Idempotent paper lifecycle persistence. Only real engine outputs are recorded."""

    def __init__(self, backend: PersistenceBackend):
        self.backend = backend

    def record_account(self, account_id: str, cash_usd: float, data_source: str = "LOCAL_PERSISTED") -> str:
        return self.backend.put("paper_accounts", account_id, {
            "paper_account_id": account_id, "status": "ACTIVE", "data_source": data_source,
            "cash_usd": cash_usd, "updated_at": _now_iso()})

    def record_order(self, order: Dict[str, Any], idempotency_key: str) -> str:
        if not idempotency_key:
            raise ValueError("idempotency_key required")
        key = order.get("order_id") or f"ord_{payload_hash(idempotency_key)[:16]}"
        existing = self.find_order_by_key(idempotency_key)
        if existing is not None:
            key = existing["order_id"]
            order = {**existing, **order, "order_id": key}
        data = {**order, "order_id": key, "idempotency_key": idempotency_key}
        return self.backend.put("paper_orders", key, data)

    def find_order_by_key(self, idempotency_key: str) -> Optional[Dict[str, Any]]:
        rows = self.backend.list("paper_orders", idempotency_key=idempotency_key)
        return rows[0] if rows else None

    def record_fill(self, fill: Dict[str, Any]) -> str:
        return self.backend.put("paper_fills", fill["fill_id"], fill)

    def record_position(self, position_id: str, position: Dict[str, Any]) -> str:
        return self.backend.put("paper_positions", position_id, {"position_id": position_id, **position})

    def orders(self) -> List[Dict[str, Any]]:
        return self.backend.list("paper_orders")

    def fills(self) -> List[Dict[str, Any]]:
        return self.backend.list("paper_fills")


class RiskStore:
    """Persists risk decisions & kill-switch events. Replica only: never consulted to override Risk Engine."""

    def __init__(self, backend: PersistenceBackend):
        self.backend = backend

    def record_decision(self, decision: Any, strategy_id: str = "", symbol: str = "",
                        decision_id: Optional[str] = None) -> str:
        d = _to_dict(decision)
        d.setdefault("strategy_id", strategy_id)
        d.setdefault("symbol", symbol)
        d["approved"] = bool(d.get("approved", d.get("is_approved", False)))
        vc = d.get("violation_code")
        d["violation_code"] = None if vc is None else str(vc)
        d.setdefault("timestamp_utc", _now_iso())
        did = decision_id or d.get("decision_id") or f"dec_{uuid.uuid4().hex[:16]}"
        d["decision_id"] = did
        return self.backend.put("risk_decisions", did, d)

    def record_kill_switch(self, action: str, actor: str, reason: str, scope: str = "GLOBAL") -> str:
        if action not in ("ACTIVATE", "RESET"):
            raise ValueError("action must be ACTIVATE or RESET")
        if not actor or not reason:
            raise ValueError("actor and reason required")
        eid = f"ks_{time.time_ns()}_{uuid.uuid4().hex[:6]}"
        return self.backend.put("kill_switch_events", eid, {
            "event_id": eid, "action": action, "scope": scope, "actor": actor, "reason": reason,
            "timestamp_utc": _now_iso()})

    def kill_switch_state(self) -> str:
        """Last recorded state; UNKNOWN if no events (UNKNOWN != SAFE)."""
        rows = sorted(self.backend.list("kill_switch_events"), key=lambda r: r["event_id"])
        if not rows:
            return "UNKNOWN"
        return "ACTIVE" if rows[-1]["action"] == "ACTIVATE" else "RESET"

    def decisions(self) -> List[Dict[str, Any]]:
        return self.backend.list("risk_decisions")
