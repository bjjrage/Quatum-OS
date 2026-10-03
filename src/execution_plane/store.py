"""ExecutionStore (on the EXISTING persistence layer), kill switch, reconciliation engine, private stream."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from src.execution_plane.models import (ExecFill, ExecutionMode, OrderIntent, OrderRecord, OrderState,
                                        TERMINAL_STATES)
from src.persistence.backend import PersistenceBackend


def iso_from_ns(ns: Optional[int]) -> str:
    ns = ns if ns is not None else time.time_ns()
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).isoformat()


class ExecutionStore:
    """All execution evidence goes through the existing PersistenceBackend (SQLite ledger + outbox)."""

    def __init__(self, backend: PersistenceBackend):
        self.backend = backend

    # ---- intents / orders ----
    def save_intent(self, intent: OrderIntent, mode: ExecutionMode) -> None:
        d = intent.model_dump(mode="json")
        d.update({"execution_mode": mode.value, "created_at": iso_from_ns(intent.created_at_ns)})
        self.backend.put("execution_intents", intent.intent_id, d)

    def save_order(self, rec: OrderRecord) -> None:
        d = rec.model_dump(mode="json")
        d.update({"intent_id": rec.intent.intent_id, "client_order_id": rec.intent.client_order_id,
                  "venue_order_id": rec.venue_order_id, "venue": rec.intent.venue, "symbol": rec.intent.symbol,
                  "state": rec.state.value, "idempotency_key": rec.intent.idempotency_key,
                  "summary": rec.summary()})
        self.backend.put("execution_orders", rec.intent.intent_id, d)

    def _rec(self, d: Optional[Dict[str, Any]]) -> Optional[OrderRecord]:
        if d is None:
            return None
        return OrderRecord.model_validate({k: d[k] for k in OrderRecord.model_fields if k in d})

    def get_order(self, intent_id: str) -> Optional[OrderRecord]:
        return self._rec(self.backend.get("execution_orders", intent_id))

    def list_orders(self) -> List[OrderRecord]:
        rows = sorted(self.backend.list("execution_orders"), key=lambda r: r["intent_id"])
        return [self._rec(r) for r in rows]

    def find_by_key(self, key: str) -> Optional[OrderRecord]:
        for r in self.backend.list("execution_orders", idempotency_key=key):
            return self._rec(r)
        return None

    def find_by_client_id(self, cid: str) -> Optional[OrderRecord]:
        for r in self.backend.list("execution_orders", client_order_id=cid):
            return self._rec(r)
        return None

    def open_orders(self) -> List[OrderRecord]:
        return [o for o in self.list_orders() if o.state not in TERMINAL_STATES]

    # ---- append-only evidence ----
    def add_transition(self, intent_id: str, frm: Optional[str], to: str, reason: str, at_ns: int, extra=None) -> None:
        tid = f"{intent_id}:{at_ns}:{uuid.uuid4().hex[:6]}"
        self.backend.put("order_state_transitions", tid, {
            "transition_id": tid, "intent_id": intent_id, "from_state": frm, "to_state": to, "reason": reason,
            "at": iso_from_ns(at_ns), "at_ns": at_ns, **(extra or {})})

    def transitions(self, intent_id: str) -> List[Dict[str, Any]]:
        rows = self.backend.list("order_state_transitions", intent_id=intent_id)
        return sorted(rows, key=lambda r: (r["at_ns"], r["transition_id"]))

    def add_attempt(self, intent_id: str, client_order_id: str, venue: str, n: int, outcome: str,
                    at_ns: int, suffix: str = "", detail: str = "") -> None:
        aid = f"{intent_id}:{n}{suffix}"
        self.backend.put("execution_attempts", aid, {
            "attempt_id": aid, "intent_id": intent_id, "client_order_id": client_order_id, "venue": venue,
            "attempt_no": n, "outcome": outcome, "started_at": iso_from_ns(at_ns), "detail": detail})

    def attempts(self, intent_id: str) -> List[Dict[str, Any]]:
        return sorted(self.backend.list("execution_attempts", intent_id=intent_id), key=lambda r: r["attempt_id"])

    def add_fill(self, fill: ExecFill) -> None:
        self.backend.put("execution_fills", fill.fill_id, fill.model_dump(mode="json"))

    def fills(self) -> List[Dict[str, Any]]:
        return sorted(self.backend.list("execution_fills"), key=lambda r: (r["timestamp_ns"], r["fill_id"]))

    def _event(self, table: str, pk: str, venue: str, event_type: str, payload: Dict[str, Any]) -> str:
        eid = f"{venue}:{time.time_ns()}:{uuid.uuid4().hex[:6]}"
        at = iso_from_ns(None)
        self.backend.put(table, eid, {pk: eid, "venue": venue, "event_type": event_type, "at": at, **payload})
        return eid

    def add_connection_event(self, venue: str, event_type: str, **payload) -> str:
        return self._event("connection_events", "event_id", venue, event_type, payload)

    def add_rate_limit_event(self, venue: str, event_type: str, **payload) -> str:
        return self._event("rate_limit_events", "event_id", venue, event_type, payload)

    def add_recon_event(self, venue: str, status: str, evidence: Dict[str, Any]) -> str:
        eid = f"{venue}:{time.time_ns()}:{uuid.uuid4().hex[:6]}"
        self.backend.put("reconciliation_events", eid, {"event_id": eid, "venue": venue, "status": status,
                                                         "at": iso_from_ns(None), "evidence": evidence})
        return eid

    def recon_events(self, venue: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = self.backend.list("reconciliation_events")
        return sorted([r for r in rows if venue in (None, r["venue"])], key=lambda r: r["event_id"])

    def add_latency(self, trace: Dict[str, Any]) -> None:
        n = sum(1 for v in trace["timestamps_ns"].values() if v is not None)
        sid = f"{trace['intent_id']}:{n}"
        self.backend.put("latency_samples", sid, {"sample_id": sid, **trace})

    def latency_samples(self) -> List[Dict[str, Any]]:
        best: Dict[str, Dict[str, Any]] = {}
        for r in self.backend.list("latency_samples"):
            n = sum(1 for v in r["timestamps_ns"].values() if v is not None)
            cur = best.get(r["intent_id"])
            if cur is None or n > sum(1 for v in cur["timestamps_ns"].values() if v is not None):
                best[r["intent_id"]] = r
        return [best[k] for k in sorted(best)]

    def add_account_snapshot(self, snap) -> str:
        sid = f"{snap.venue}:{snap.timestamp_ns or time.time_ns()}"
        d = snap.model_dump(mode="json")
        d.update({"snapshot_id": sid, "at": iso_from_ns(snap.timestamp_ns)})
        self.backend.put("account_snapshots", sid, d)
        return sid

    def latest_account_snapshot(self, venue: str) -> Optional[Dict[str, Any]]:
        rows = [r for r in self.backend.list("account_snapshots") if r["venue"] == venue]
        return sorted(rows, key=lambda r: r["snapshot_id"])[-1] if rows else None


# ------------------------------------------------------------------ kill switch
SCOPES = ("GLOBAL", "VENUE", "ACCOUNT", "STRATEGY", "SYMBOL")


class ExecutionKillSwitch:
    """Scoped kill switch, replayed from persisted events (survives restart). Never flattens positions."""

    def __init__(self, backend: PersistenceBackend):
        self.backend = backend
        self._active: Dict[tuple, bool] = {}
        self._replay()

    def _replay(self) -> None:
        rows = sorted(self.backend.list("kill_switch_events"), key=lambda r: r["event_id"])
        for r in rows:
            if r.get("target_kind") != "EXEC":
                continue
            self._active[(r["scope"], r.get("target") or "")] = r["action"] == "ACTIVATE"

    def _record(self, action: str, scope: str, target: str, actor: str, reason: str) -> None:
        if scope not in SCOPES:
            raise ValueError(f"unknown kill-switch scope {scope!r}")
        if scope != "GLOBAL" and not target:
            raise ValueError("non-global scope requires a target")
        if not actor or not reason:
            raise ValueError("actor and reason required")
        eid = f"ks_{time.time_ns()}_{uuid.uuid4().hex[:6]}"
        self.backend.put("kill_switch_events", eid, {
            "event_id": eid, "action": action, "scope": scope, "target": target, "target_kind": "EXEC",
            "actor": actor, "reason": reason, "timestamp_utc": iso_from_ns(None)})
        self._active[(scope, target if scope != "GLOBAL" else "")] = action == "ACTIVATE"

    def activate(self, scope: str, actor: str, reason: str, target: str = "") -> None:
        self._record("ACTIVATE", scope, target, actor, reason)

    def reset(self, scope: str, actor: str, reason: str, target: str = "") -> None:
        self._record("RESET", scope, target, actor, reason)

    def blocking(self, intent: OrderIntent) -> Optional[str]:
        checks = [("GLOBAL", ""), ("VENUE", intent.venue), ("ACCOUNT", intent.capital_pocket_id),
                  ("STRATEGY", intent.strategy_id), ("SYMBOL", intent.symbol)]
        for scope, target in checks:
            if self._active.get((scope, target)):
                return f"{scope}:{target}" if target else scope
        return None

    def active_scopes(self) -> List[str]:
        return sorted(f"{s}:{t}" if t else s for (s, t), v in self._active.items() if v)


# ------------------------------------------------------------- reconciliation
@dataclass
class ReconResult:
    venue: str
    status: str  # HEALTHY | MISMATCH | UNAVAILABLE
    diffs: List[Dict[str, Any]] = field(default_factory=list)
    resolutions: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""

    def evidence(self) -> Dict[str, Any]:
        return {"venue": self.venue, "status": self.status, "diffs": self.diffs,
                "resolutions": self.resolutions, "reason": self.reason}


class ReconciliationEngine:
    """Deterministic comparison of local vs venue state. Never rewrites state; only reports."""

    def __init__(self, qty_tolerance: float = 1e-9):
        self.tol = qty_tolerance

    def reconcile(self, adapter, local_orders: List[OrderRecord], local_fills: List[ExecFill],
                  local_positions: Dict[str, float]) -> ReconResult:
        venue = adapter.venue
        try:
            venue_open = adapter.get_open_orders()
            venue_positions = adapter.get_positions()
            symbols = sorted({o.intent.symbol for o in local_orders})
            venue_fills: Optional[List[Dict[str, Any]]] = []
            if symbols:
                for s in symbols:
                    venue_fills.extend(adapter.get_fills(s))
            else:
                venue_fills = None  # nothing local to compare against
            lookups = {}
            for o in local_orders:
                if o.state in (OrderState.ACKNOWLEDGED, OrderState.PARTIALLY_FILLED, OrderState.CANCEL_PENDING,
                               OrderState.UNKNOWN_OUTCOME, OrderState.RECONCILIATION_REQUIRED):
                    lookups[o.intent.client_order_id] = adapter.get_order(o.intent.client_order_id, o.intent.symbol)
        except Exception as e:  # query failed: UNKNOWN, never HEALTHY
            return ReconResult(venue, "UNAVAILABLE", reason=f"{type(e).__name__}: {e}")

        diffs: List[Dict[str, Any]] = []
        resolutions: List[Dict[str, Any]] = []
        local_by_cid = {o.intent.client_order_id: o for o in local_orders}
        local_by_vid = {o.venue_order_id: o for o in local_orders if o.venue_order_id}

        for vo in venue_open:
            if vo["client_order_id"] not in local_by_cid and vo.get("venue_order_id") not in local_by_vid:
                diffs.append({"kind": "ORPHAN_VENUE_ORDER", "client_order_id": vo["client_order_id"],
                              "venue_order_id": vo.get("venue_order_id")})

        venue_open_ids = {vo["client_order_id"] for vo in venue_open}
        for cid, vo in sorted(lookups.items()):
            o = local_by_cid[cid]
            if o.state is OrderState.UNKNOWN_OUTCOME:
                resolutions.append({"client_order_id": cid, "venue_state": vo})
                continue
            if cid in venue_open_ids:
                continue
            if vo is None or vo["status"] in ("FILLED", "CANCELED", "REJECTED", "EXPIRED"):
                if o.state is OrderState.CANCEL_PENDING and vo is not None and vo["status"] == "CANCELED":
                    continue
                diffs.append({"kind": "STATE_DIVERGENCE", "client_order_id": cid, "local_state": o.state.value,
                              "venue_status": None if vo is None else vo["status"]})

        if venue_fills is not None:
            local_ids = {f.venue_trade_id for f in local_fills}
            venue_ids = {f["venue_trade_id"] for f in venue_fills}
            for f in sorted(venue_fills, key=lambda r: r["venue_trade_id"]):
                ours = (f.get("client_order_id") in local_by_cid) or (f.get("venue_order_id") in local_by_vid)
                if ours and f["venue_trade_id"] not in local_ids:
                    diffs.append({"kind": "FILL_MISSING_LOCALLY", "venue_trade_id": f["venue_trade_id"],
                                  "qty": f["qty"]})
            for f in sorted(local_fills, key=lambda r: r.venue_trade_id):
                if f.venue_trade_id not in venue_ids:
                    diffs.append({"kind": "FILL_MISSING_ON_VENUE", "venue_trade_id": f.venue_trade_id})
            for o in sorted(local_orders, key=lambda r: r.intent.client_order_id):
                vqty = sum(f["qty"] for f in venue_fills
                           if f.get("client_order_id") == o.intent.client_order_id
                           or (o.venue_order_id and f.get("venue_order_id") == o.venue_order_id))
                if abs(vqty - o.filled_qty) > self.tol and o.state is not OrderState.UNKNOWN_OUTCOME:
                    diffs.append({"kind": "FILL_QTY_MISMATCH", "client_order_id": o.intent.client_order_id,
                                  "local": o.filled_qty, "venue": vqty})

        vpos = {p["symbol"]: p["quantity"] for p in venue_positions}
        for sym in sorted(set(vpos) | set(local_positions)):
            if abs(vpos.get(sym, 0.0) - local_positions.get(sym, 0.0)) > self.tol:
                diffs.append({"kind": "POSITION_MISMATCH", "symbol": sym, "local": local_positions.get(sym, 0.0),
                              "venue": vpos.get(sym, 0.0)})
        return ReconResult(venue, "MISMATCH" if diffs else "HEALTHY", diffs, resolutions)
