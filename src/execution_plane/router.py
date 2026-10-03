"""ExecutionRouter: the ONLY path from an OrderIntent to a venue.

Strategy -> OrderIntent -> (staleness, kill switch, metadata, cluster) -> Deterministic Risk Engine ->
Capital authorization -> mode/venue/credential/reconciliation/clock/account gates -> Adapter -> Venue.

The router is stricter than the Risk Engine and can never relax it: the Risk Engine is evaluated inside
``submit`` itself (there is no code path that transmits without a RiskDecision), and real adapters
re-verify the live gates through the SubmitPermit.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.execution_plane.adapters.base import (AdapterError, AuthFailure, ExchangeAdapter, InvalidOrder,
                                               LiveLockedError, TransportNotConfigured, UnknownOutcomeError,
                                               VenueUnavailable, issue_permit)
from src.execution_plane.models import (ExecFill, ExecutionMode, FailureClass, InstrumentMeta, OrderIntent,
                                        OrderRecord, OrderState, TERMINAL_STATES, VALID_TRANSITIONS)
from src.execution_plane.security import CONFIGURED, CredentialProvider, scrub
from src.execution_plane.store import (ExecutionKillSwitch, ExecutionStore, ReconciliationEngine, iso_from_ns)
from src.execution_plane.telemetry import ClockMonitor, LatencyTrace, RateLimited, aggregate_latency
from src.risk.engine import ProposedOrder

S = OrderState
EPS = 1e-9
LIVE_MODES = (ExecutionMode.LIVE, ExecutionMode.LIVE_LOCKED)


class InvalidTransitionError(Exception):
    pass


class InstrumentRegistry:
    def __init__(self):
        self._m: Dict[Tuple[str, str], InstrumentMeta] = {}

    def register(self, meta: InstrumentMeta) -> None:
        self._m[(meta.venue, meta.symbol)] = meta

    def get(self, venue: str, symbol: str) -> Optional[InstrumentMeta]:
        return self._m.get((venue, symbol))


class ExecutionRouter:
    def __init__(self, store: ExecutionStore, risk_engine, adapters: Dict[str, ExchangeAdapter],
                 instruments: InstrumentRegistry, mode: ExecutionMode = ExecutionMode.LIVE_LOCKED,
                 capital_authorizer: Callable[[str], float] = lambda pocket_id: 0.0,
                 credentials: Optional[CredentialProvider] = None, paper_broker=None,
                 killswitch: Optional[ExecutionKillSwitch] = None, clock_monitor: Optional[ClockMonitor] = None,
                 audit=None, clock_ns: Callable[[], int] = time.time_ns, sleep: Callable[[float], None] = time.sleep,
                 max_rate_retries: int = 2, allow_test_adapters: bool = False,
                 future_skew_ms: float = 1000.0):
        self.store, self.risk, self.adapters, self.instruments = store, risk_engine, adapters, instruments
        self.mode = mode
        self.capital_authorizer = capital_authorizer
        self.credentials = credentials or CredentialProvider()
        self.paper_broker = paper_broker
        self.killswitch = killswitch or ExecutionKillSwitch(store.backend)
        self.clock_monitor = clock_monitor or ClockMonitor()
        self.audit = audit
        self._now, self._sleep = clock_ns, sleep
        self.max_rate_retries = max_rate_retries
        self.allow_test_adapters = allow_test_adapters
        self.future_skew_ms = future_skew_ms
        self.recon_status: Dict[str, str] = {v: "UNKNOWN" for v in adapters}
        self.recovery_pending: Dict[str, bool] = {}
        self.traces: Dict[str, LatencyTrace] = {}
        self.last_recovery: Dict[str, Any] = {}
        for v, a in adapters.items():
            if getattr(a, "is_test_only", False) and not allow_test_adapters:
                raise ValueError(f"test-only adapter {v!r} cannot be registered as a production venue")

    # ------------------------------------------------------------ plumbing
    def _secrets(self) -> List[str]:
        return self.credentials.known_values()

    def _audit(self, event_type: str, rec: Optional[OrderRecord], **extra) -> None:
        if self.audit is None:
            return
        payload: Dict[str, Any] = {"component": "execution_router", "mode": self.mode.value, **extra}
        eid = "n/a"
        if rec is not None:
            i = rec.intent
            eid = i.intent_id
            payload.update({"strategy_id": i.strategy_id, "capital_pocket_id": i.capital_pocket_id,
                            "venue": i.venue, "symbol": i.symbol, "intent_id": i.intent_id,
                            "client_order_id": i.client_order_id, "state": rec.state.value, "reason": rec.reason})
        try:
            self.audit.append(event_type, "execution_router", "order", eid, scrub(payload, self._secrets()))
        except Exception:
            pass  # audit trouble must not mask execution outcomes; surfaced via tests/monitoring

    def _to(self, rec: OrderRecord, new: OrderState, reason: str = "",
            fc: Optional[FailureClass] = None) -> None:
        old = rec.state
        if new is old and new is S.PARTIALLY_FILLED:
            pass
        elif new not in VALID_TRANSITIONS[old]:
            raise InvalidTransitionError(f"{old.value} -> {new.value}")
        rec.state, rec.reason, rec.updated_at_ns = new, reason or rec.reason, self._now()
        if fc is not None:
            rec.failure_class = fc
        self.store.add_transition(rec.intent.intent_id, old.value, new.value, reason, rec.updated_at_ns)
        self.store.save_order(rec)
        self._audit("ORDER_STATE_CHANGE", rec, from_state=old.value, to_state=new.value)

    def _reject(self, rec, reason, state=S.REJECTED, fc: Optional[FailureClass] = None) -> OrderRecord:
        self._to(rec, state, reason, fc or FailureClass.NON_RETRYABLE)
        self._finish_trace(rec)
        return rec

    def _trace(self, rec: OrderRecord) -> LatencyTrace:
        return self.traces.setdefault(rec.intent.intent_id, LatencyTrace(rec.intent.intent_id, rec.intent.venue))

    def _finish_trace(self, rec: OrderRecord) -> None:
        self.store.add_latency(self._trace(rec).to_dict())

    def get(self, intent_id: str) -> Optional[OrderRecord]:
        return self.store.get_order(intent_id)

    # ------------------------------------------------------------- gates
    def _kill_active(self, intent: OrderIntent) -> Optional[str]:
        if getattr(self.risk, "kill_switch_active", False):
            return "RISK_ENGINE_KILL_SWITCH"
        return self.killswitch.blocking(intent)

    def _authorized(self, intent: OrderIntent) -> float:
        try:
            return float(self.capital_authorizer(intent.capital_pocket_id) or 0.0)
        except Exception:
            return 0.0  # unknown != authorized

    def _clock_ok(self, adapter: ExchangeAdapter, strict: bool) -> Optional[str]:
        venue = adapter.venue
        if self.clock_monitor.status(venue) == "UNKNOWN":
            try:
                self.clock_monitor.measure(venue, adapter.get_server_time)
            except Exception:
                pass
        st = self.clock_monitor.status(venue)
        if st == "BLOCK":
            return "CLOCK_DRIFT_BLOCK"
        if st == "UNKNOWN":
            return "CLOCK_UNKNOWN"
        if st == "WARN" and strict:
            return "CLOCK_DRIFT_WARN"
        return None

    def _account_known(self, adapter: ExchangeAdapter) -> Optional[str]:
        try:
            snap = adapter.get_account()
        except Exception:
            return "ACCOUNT_UNKNOWN"
        try:
            self.store.add_account_snapshot(snap)
        except Exception:
            pass
        return None if snap.status == "KNOWN" else f"ACCOUNT_{snap.status}"

    def _auth_gates(self, rec: OrderRecord, adapter: ExchangeAdapter, meta, authorized: float) -> List[str]:
        """Gates for SANDBOX and LIVE. Returns list of failures (empty == pass)."""
        i, fails = rec.intent, []
        live = self.mode is ExecutionMode.LIVE
        if live:
            notional = (i.valuation_price or 0) * i.quantity * meta.contract_multiplier
            if authorized <= 0:
                fails.append("AUTHORIZED_LIVE_CAPITAL_ZERO")
            elif notional > authorized:
                fails.append("EXCEEDS_AUTHORIZED_CAPITAL")
        env_needed = "LIVE" if live else "SANDBOX"
        if adapter.environment != env_needed and not (adapter.environment == "MOCK" and self.allow_test_adapters):
            fails.append("SANDBOX_ISOLATION" if not live else "ADAPTER_ENVIRONMENT_MISMATCH")
        if adapter.environment != "MOCK" and not self.credentials.is_configured(i.venue, env_needed):
            fails.append("CREDENTIALS_NOT_CONFIGURED")
        caps = adapter.capabilities()
        if not caps.get("order_submit"):
            fails.append("VENUE_ORDER_SUBMIT_UNAVAILABLE")
        if self.recovery_pending.get(i.venue):
            fails.append("RECOVERY_PENDING")
        rs = self.recon_status.get(i.venue, "UNKNOWN")
        if live and rs != "HEALTHY":
            fails.append(f"RECONCILIATION_{rs}")
        if not live and rs == "MISMATCH":
            fails.append("RECONCILIATION_MISMATCH")
        if any(o.state is S.RECONCILIATION_REQUIRED and o.intent.venue == i.venue for o in self.store.list_orders()):
            fails.append("ORDERS_REQUIRE_RECONCILIATION")
        c = self._clock_ok(adapter, strict=live)
        if c:
            fails.append(c)
        a = self._account_known(adapter)
        if a:
            fails.append(a)
        return fails

    # ------------------------------------------------------------- submit
    def submit(self, intent: OrderIntent, signal_timestamp_ns: Optional[int] = None) -> OrderRecord:
        now = self._now()
        existing = self.store.find_by_key(intent.idempotency_key)
        if existing is not None:  # idempotent: never a second economic order
            self._audit("DUPLICATE_INTENT_IGNORED", existing)
            return existing
        rec = OrderRecord(intent=intent, mode=self.mode, updated_at_ns=now)
        tr = self._trace(rec)
        tr.mark("signal_timestamp_ns", signal_timestamp_ns or intent.decision_timestamp_ns)
        tr.mark("intent_created_at_ns", intent.created_at_ns)
        self.store.save_intent(intent, self.mode)
        self.store.add_transition(intent.intent_id, None, S.INTENT_CREATED.value, "intent created", now)
        self.store.save_order(rec)
        self._audit("INTENT_CREATED", rec)

        # 1. temporal provenance
        md_age = (now - intent.market_data_timestamp_ns) / 1e6
        dec_age = (now - intent.decision_timestamp_ns) / 1e6
        if md_age < -self.future_skew_ms or dec_age < -self.future_skew_ms:
            return self._reject(rec, "TIMESTAMP_IN_FUTURE")
        if md_age > intent.max_signal_age_ms or dec_age > intent.max_signal_age_ms:
            return self._reject(rec, f"STALE_SIGNAL: market_age_ms={md_age:.1f} decision_age_ms={dec_age:.1f}")

        # 2. execution kill switch
        ks = self._kill_active(intent)
        if ks:
            return self._reject(rec, f"KILL_SWITCH:{ks}")

        # 3. instrument metadata (PAPER excluded: PaperBroker has no venue precision rules)
        adapter = self.adapters.get(intent.venue)
        meta = self.instruments.get(intent.venue, intent.symbol)
        if self.mode is not ExecutionMode.PAPER:
            if adapter is None:
                return self._reject(rec, f"UNKNOWN_VENUE:{intent.venue}")
            if meta is None:
                return self._reject(rec, "EXECUTION_BLOCKED: instrument metadata missing")
            problems = meta.validate_order(intent.quantity, intent.valuation_price)
            if problems:
                return self._reject(rec, "EXECUTION_BLOCKED: " + "; ".join(problems), fc=FailureClass.INVALID_ORDER)

        # 4. event cluster must be known to Risk (UNKNOWN != SAFE)
        if intent.event_cluster_id and intent.event_cluster_id not in getattr(self.risk, "event_clusters", {}):
            return self._reject(rec, f"UNKNOWN_EVENT_CLUSTER:{intent.event_cluster_id}")

        # 5. deterministic Risk Engine (final authority; evaluated here, cannot be skipped)
        price = intent.valuation_price
        if price is None:
            return self._reject(rec, "MARKET order requires reference_price for risk valuation")
        po = ProposedOrder(order_id=intent.client_order_id, strategy_id=intent.strategy_id, symbol=intent.symbol,
                           side=intent.side, quantity=intent.quantity, price=price, venue=intent.venue,
                           timestamp_s=now / 1e9)
        decision = self.risk.evaluate_order(po, is_live=self.mode in LIVE_MODES, current_time_s=now / 1e9)
        tr.mark("risk_decided_at_ns", self._now())
        try:
            from src.persistence.domain import RiskStore
            RiskStore(self.store.backend).record_decision(decision, intent.strategy_id, intent.symbol,
                                                          decision_id=f"dec_{intent.intent_id}")
        except Exception:
            pass
        if not decision.approved:
            return self._reject(rec, f"RISK_VETO:{getattr(decision.violation_code, 'value', decision.violation_code)}",
                                state=S.RISK_REJECTED)
        self._to(rec, S.RISK_APPROVED, "risk approved")

        # 6. mode dispatch
        authorized = self._authorized(intent)
        if self.mode is ExecutionMode.LIVE_LOCKED:
            return self._reject(rec, "LIVE_LOCKED: real order transmission disabled")
        if self.mode is ExecutionMode.PAPER:
            return self._route_paper(rec)
        if self.mode is ExecutionMode.SHADOW:
            return self._route_shadow(rec, adapter, meta)
        fails = self._auth_gates(rec, adapter, meta, authorized)
        if fails:
            return self._reject(rec, "GATES_FAILED:" + ",".join(fails))
        return self._transmit(rec, adapter, meta, authorized)

    # --- paper / shadow
    def _route_paper(self, rec: OrderRecord) -> OrderRecord:
        if self.paper_broker is None:
            return self._reject(rec, "PAPER_NOT_WIRED")
        from src.paper.broker import PaperOrderSide, PaperOrderType
        i = rec.intent
        self._to(rec, S.ROUTING, "paper route")
        self._trace(rec).mark("router_dispatch_at_ns", self._now())
        po = self.paper_broker.submit_order(
            symbol=i.symbol, side=PaperOrderSide(i.side), order_type=PaperOrderType(i.order_type),
            quantity=i.quantity, limit_price=i.limit_price, venue=i.venue, current_time_ns=self._now())
        rec.venue_order_id = po.order_id
        self._to(rec, S.ACKNOWLEDGED, "paper broker accepted")
        if getattr(po, "filled_qty", 0) and po.filled_qty > 0:
            self.apply_fill(rec, ExecFill(
                fill_id=f"paper:{po.order_id}", intent_id=i.intent_id, client_order_id=i.client_order_id,
                venue="paper", venue_order_id=po.order_id, venue_trade_id=f"paper:{po.order_id}",
                price=po.filled_price or i.valuation_price, quantity=po.filled_qty, fee=po.fee_paid or 0.0,
                is_taker=po.is_taker, timestamp_ns=self._now()))
        self._finish_trace(rec)
        return rec

    def _route_shadow(self, rec: OrderRecord, adapter, meta) -> OrderRecord:
        self._to(rec, S.ROUTING, "shadow route")
        self._trace(rec).mark("router_dispatch_at_ns", self._now())
        request = adapter.serialize_order(rec.intent, meta)  # pure serialization; NO transmission
        self._to(rec, S.WOULD_SUBMIT, "SHADOW: would submit (not transmitted)")
        self.store.backend.put("execution_orders", rec.intent.intent_id, {
            **self.store.backend.get("execution_orders", rec.intent.intent_id),
            "shadow_request": scrub(request, self._secrets()), "data_source": "SHADOW"})
        self._finish_trace(rec)
        return rec

    # --- transmission (SANDBOX / LIVE)
    def _transmit(self, rec: OrderRecord, adapter, meta, authorized: float) -> OrderRecord:
        i = rec.intent
        self._to(rec, S.ROUTING, "dispatching")
        tr = self._trace(rec)
        tr.mark("router_dispatch_at_ns", self._now())
        first = True
        for _ in range(self.max_rate_retries + 1):
            rec.attempts += 1
            # attempt row is persisted BEFORE transmission: a crash leaves evidence => UNKNOWN_OUTCOME on restart
            self.store.add_attempt(i.intent_id, i.client_order_id, i.venue, rec.attempts, "STARTED", self._now())
            if first:
                self._to(rec, S.SUBMITTING, "submitting")
                first = False
            else:
                self.store.save_order(rec)
            permit = issue_permit("SUBMIT", i.venue, i.client_order_id, self.mode, authorized, True, self._now())
            tr.mark("submit_started_at_ns", self._now(), overwrite=True)
            try:
                ack = adapter.submit_order(permit, i, meta)
            except RateLimited as e:
                self.store.add_attempt(i.intent_id, i.client_order_id, i.venue, rec.attempts, "RATE_LIMITED",
                                       self._now(), ":result")
                self.store.add_rate_limit_event(i.venue, "SUBMIT_RATE_LIMITED", retry_after_s=e.retry_after_s)
                if rec.attempts > self.max_rate_retries:
                    return self._reject(rec, "RATE_LIMITED: retries exhausted", fc=FailureClass.RATE_LIMITED)
                self._sleep(min(e.retry_after_s or 0.0, 5.0))
                continue
            except UnknownOutcomeError as e:
                return self._unknown(rec, f"UNKNOWN_OUTCOME: {self._safe(e)}")
            except VenueUnavailable as e:
                if e.pre_send:
                    self.store.add_attempt(i.intent_id, i.client_order_id, i.venue, rec.attempts, "UNAVAILABLE_PRE_SEND",
                                           self._now(), ":result")
                    if rec.attempts > self.max_rate_retries:
                        return self._reject(rec, "VENUE_UNAVAILABLE (not transmitted)", fc=FailureClass.VENUE_UNAVAILABLE)
                    continue
                return self._unknown(rec, f"UNKNOWN_OUTCOME: {self._safe(e)}")
            except AuthFailure as e:
                return self._reject(rec, f"AUTH_FAILURE: {self._safe(e)}", fc=FailureClass.AUTH_FAILURE)
            except (InvalidOrder, LiveLockedError, TransportNotConfigured) as e:
                self.store.add_attempt(i.intent_id, i.client_order_id, i.venue, rec.attempts, "REJECTED", self._now(), ":result")
                return self._reject(rec, f"{type(e).__name__}: {self._safe(e)}", fc=e.failure_class)
            except PermissionError as e:
                return self._reject(rec, f"PERMIT_DENIED: {self._safe(e)}")
            except Exception as e:  # unexpected after possible send: fail closed
                return self._unknown(rec, f"UNKNOWN_OUTCOME: unexpected {type(e).__name__}")
            tr.mark("venue_ack_at_ns", self._now())
            self.store.add_attempt(i.intent_id, i.client_order_id, i.venue, rec.attempts, "ACK", self._now(), ":result")
            rec.venue_order_id = ack.get("venue_order_id")
            self._to(rec, S.ACKNOWLEDGED, "venue acknowledged")
            for f in ack.get("fills", []):
                self.apply_fill(rec, self._mk_fill(rec, f))
            self._finish_trace(rec)
            return rec
        return self._reject(rec, "SUBMIT_LOOP_EXHAUSTED", fc=FailureClass.RETRYABLE)

    def _safe(self, e: Exception) -> str:
        from src.execution_plane.security import redact_text
        return redact_text(str(e), self._secrets())

    def _unknown(self, rec: OrderRecord, reason: str) -> OrderRecord:
        i = rec.intent
        self.store.add_attempt(i.intent_id, i.client_order_id, i.venue, rec.attempts, "UNKNOWN_OUTCOME",
                               self._now(), ":result")
        self._to(rec, S.UNKNOWN_OUTCOME, reason, FailureClass.UNKNOWN_OUTCOME)
        self._finish_trace(rec)
        return rec

    # ------------------------------------------------------------- fills
    def _mk_fill(self, rec: OrderRecord, d: Dict[str, Any]) -> ExecFill:
        i = rec.intent
        return ExecFill(fill_id=f"{i.venue}:{d['venue_trade_id']}", intent_id=i.intent_id,
                        client_order_id=i.client_order_id, venue=i.venue,
                        venue_order_id=d.get("venue_order_id") or rec.venue_order_id,
                        venue_trade_id=str(d["venue_trade_id"]), price=float(d["price"]), quantity=float(d["qty"]),
                        fee=float(d.get("fee", 0.0)), fee_asset=d.get("fee_asset", "USDT"),
                        is_taker=d.get("is_taker"), timestamp_ns=int(d.get("timestamp_ns") or self._now()))

    def apply_fill(self, rec: OrderRecord, fill: ExecFill) -> bool:
        """Idempotent by venue_trade_id. Partial fills are first-class."""
        if any(f.venue_trade_id == fill.venue_trade_id for f in rec.fills):
            return False
        self.store.add_fill(fill)
        tr = self._trace(rec)
        tr.mark("first_fill_at_ns", fill.timestamp_ns)
        was = rec.state
        rec.fills.append(fill)
        total = rec.filled_qty
        if was in (S.CANCELED, S.REJECTED, S.EXPIRED, S.FILLED):
            self._to(rec, S.RECONCILIATION_REQUIRED, f"LATE_OR_EXTRA_FILL after {was.value}")
        elif total > rec.requested_qty + EPS:
            self._to(rec, S.RECONCILIATION_REQUIRED, "OVERFILL")
        elif total >= rec.requested_qty - EPS:
            self._to(rec, S.FILLED, "fully filled")
            tr.mark("terminal_fill_at_ns", fill.timestamp_ns)
        elif was is S.CANCEL_PENDING:
            self.store.save_order(rec)  # stay CANCEL_PENDING; cancel outcome decides final state
        else:
            self._to(rec, S.PARTIALLY_FILLED, f"partial fill {total}/{rec.requested_qty}")
        self.store.save_order(rec)
        self._audit("FILL", rec, fill_id=fill.fill_id, qty=fill.quantity, price=fill.price)
        if rec.terminal:
            self._finish_trace(rec)
        return True

    # ------------------------------------------------------------- cancel / replace
    def cancel(self, intent_id: str, reason: str = "requested") -> OrderRecord:
        rec = self.get(intent_id)
        if rec is None:
            raise KeyError(intent_id)
        if rec.state is S.CANCEL_PENDING or rec.terminal:
            return rec  # duplicate / already finished: idempotent
        if rec.state not in (S.ACKNOWLEDGED, S.PARTIALLY_FILLED):
            return rec  # nothing safe to cancel (unknown outcome must be resolved first)
        adapter = self.adapters[rec.intent.venue]
        rec.prior_state = rec.state
        self._to(rec, S.CANCEL_PENDING, f"cancel requested: {reason}")
        permit = issue_permit("CANCEL", rec.intent.venue, rec.intent.client_order_id, self.mode,
                              self._authorized(rec.intent), True, self._now())
        try:
            res = adapter.cancel_order(permit, rec.intent.client_order_id, rec.intent.symbol)
        except InvalidOrder as e:
            return self._after_cancel_reject(rec, adapter, e)
        except (UnknownOutcomeError, VenueUnavailable) as e:
            self._to(rec, S.UNKNOWN_OUTCOME, f"cancel outcome unknown: {self._safe(e)}", FailureClass.UNKNOWN_OUTCOME)
            return rec
        for f in res.get("fills", []):
            self.apply_fill(rec, self._mk_fill(rec, f))
        rec = self.get(intent_id)
        if rec.state is S.CANCEL_PENDING:
            self._to(rec, S.CANCELED, "venue confirmed cancel")
        self._finish_trace(rec)
        return rec

    def _after_cancel_reject(self, rec: OrderRecord, adapter, err: InvalidOrder) -> OrderRecord:
        """Cancel rejected: ask the venue what really happened before touching state."""
        i = rec.intent
        try:
            vo = adapter.get_order(i.client_order_id, i.symbol)
            vf = adapter.get_fills(i.symbol)
        except Exception:
            self._to(rec, S.RECONCILIATION_REQUIRED, f"cancel rejected and venue query failed ({err.code})")
            return rec
        for f in vf:
            if f.get("client_order_id") == i.client_order_id or (rec.venue_order_id and f.get("venue_order_id") == rec.venue_order_id):
                self.apply_fill(rec, self._mk_fill(rec, f))
        rec = self.get(i.intent_id)
        if rec.state is S.CANCEL_PENDING:
            if vo and vo["status"] == "FILLED":
                self._to(rec, S.RECONCILIATION_REQUIRED, "venue says FILLED but fills not fully received")
            elif vo and vo["status"] in ("NEW", "PARTIALLY_FILLED"):
                self._to(rec, rec.prior_state or S.ACKNOWLEDGED, f"cancel rejected ({err.code}); order still open")
            else:
                self._to(rec, S.RECONCILIATION_REQUIRED, f"cancel rejected ({err.code}); venue state {vo}")
        return rec

    def cancel_all_open(self, venue: Optional[str] = None, reason: str = "cancel_all") -> List[str]:
        done = []
        for o in self.store.open_orders():
            if o.state in (S.ACKNOWLEDGED, S.PARTIALLY_FILLED) and venue in (None, o.intent.venue):
                self.cancel(o.intent.intent_id, reason)
                done.append(o.intent.intent_id)
        return done

    def replace(self, intent_id: str, new_intent: OrderIntent) -> Tuple[OrderRecord, Optional[OrderRecord]]:
        """NON-atomic: cancel, require confirmed CANCELED, then a brand-new intent through the FULL pipeline."""
        old = self.cancel(intent_id, "replace")
        if old.state is not S.CANCELED:
            return old, None  # never place the replacement unless the original is provably dead
        return old, self.submit(new_intent)

    def activate_kill_switch(self, scope: str, actor: str, reason: str, target: str = "",
                             cancel_open_orders: bool = False) -> List[str]:
        """Blocks new risk. Cancels open orders only if explicitly requested. NEVER flattens positions."""
        self.killswitch.activate(scope, actor, reason, target)
        self._audit("KILL_SWITCH_ACTIVATED", None, scope=scope, target=target, actor=actor, reason=reason)
        if not cancel_open_orders:
            return []
        out = []
        for o in self.store.open_orders():
            i = o.intent
            hit = (scope == "GLOBAL" or (scope == "VENUE" and i.venue == target) or
                   (scope == "ACCOUNT" and i.capital_pocket_id == target) or
                   (scope == "STRATEGY" and i.strategy_id == target) or (scope == "SYMBOL" and i.symbol == target))
            if hit and o.state in (S.ACKNOWLEDGED, S.PARTIALLY_FILLED):
                self.cancel(i.intent_id, f"kill switch {scope}")
                out.append(i.intent_id)
        return out

    # ------------------------------------------------------------- unknown outcome
    def resolve_unknown(self, intent_id: str) -> str:
        """Query the venue by client_order_id. Only venue truth may resolve UNKNOWN_OUTCOME."""
        rec = self.get(intent_id)
        if rec is None or rec.state is not S.UNKNOWN_OUTCOME:
            return "NOT_UNKNOWN_OUTCOME"
        i, adapter = rec.intent, self.adapters[rec.intent.venue]
        try:
            vo = adapter.get_order(i.client_order_id, i.symbol)
        except Exception as e:
            self.store.add_recon_event(i.venue, "UNAVAILABLE", {"intent_id": intent_id, "error": self._safe(e)})
            return "VENUE_QUERY_FAILED"  # stays UNKNOWN_OUTCOME; retry stays blocked
        if vo is None:
            rec.venue_absent_confirmed = True
            self.store.save_order(rec)
            self.store.add_recon_event(i.venue, "RESOLVED", {"intent_id": intent_id, "venue": "NOT_FOUND"})
            self._audit("UNKNOWN_RESOLVED_NOT_FOUND", rec)
            return "VENUE_CONFIRMED_NOT_FOUND"
        rec.venue_order_id = vo.get("venue_order_id") or rec.venue_order_id
        st = vo["status"]
        target = {"NEW": S.ACKNOWLEDGED, "PARTIALLY_FILLED": S.ACKNOWLEDGED, "FILLED": S.ACKNOWLEDGED,
                  "CANCELED": S.CANCELED, "REJECTED": S.REJECTED, "EXPIRED": S.EXPIRED}.get(st)
        if target is None:
            self._to(rec, S.RECONCILIATION_REQUIRED, f"unmappable venue status {st}")
            return "RECONCILIATION_REQUIRED"
        if target is S.ACKNOWLEDGED:
            self._to(rec, S.ACKNOWLEDGED, "venue reports order exists")
            try:
                for f in adapter.get_fills(i.symbol):
                    if f.get("client_order_id") == i.client_order_id or f.get("venue_order_id") == rec.venue_order_id:
                        self.apply_fill(rec, self._mk_fill(rec, f))
            except Exception:
                rec = self.get(intent_id)
                if rec.state is not S.RECONCILIATION_REQUIRED and st == "FILLED" and rec.filled_qty < rec.requested_qty - EPS:
                    self._to(rec, S.RECONCILIATION_REQUIRED, "venue FILLED but fills unavailable")
        else:
            self._to(rec, target, f"venue reports {st}")
        self.store.add_recon_event(i.venue, "RESOLVED", {"intent_id": intent_id, "venue_status": st})
        return f"RESOLVED:{self.get(intent_id).state.value}"

    def retry_unknown(self, intent_id: str) -> OrderRecord:
        """Retry is safe ONLY after the venue has confirmed it never saw the order."""
        rec = self.get(intent_id)
        if rec is None or rec.state is not S.UNKNOWN_OUTCOME:
            raise PermissionError("retry only applies to UNKNOWN_OUTCOME orders")
        if not rec.venue_absent_confirmed:
            raise PermissionError("UNKNOWN_OUTCOME must be reconciled (venue confirmation) before any retry")
        i = rec.intent
        adapter, meta = self.adapters[i.venue], self.instruments.get(i.venue, i.symbol)
        authorized = self._authorized(i)
        fails = self._auth_gates(rec, adapter, meta, authorized) if self.mode in (ExecutionMode.SANDBOX, ExecutionMode.LIVE) else ["MODE_NOT_TRANSMITTING"]
        if fails:
            raise PermissionError("gates failed: " + ",".join(fails))
        # re-check freshness and risk: a stale retry must not go out
        now = self._now()
        if (now - i.market_data_timestamp_ns) / 1e6 > i.max_signal_age_ms:
            return self._reject_from_unknown(rec, "STALE_SIGNAL on retry")
        rec.venue_absent_confirmed = False
        return self._transmit(rec, adapter, meta, authorized)

    def _reject_from_unknown(self, rec, reason):
        self._to(rec, S.REJECTED, reason, FailureClass.NON_RETRYABLE)
        return rec

    # ------------------------------------------------------------- private events
    def on_private_event(self, venue: str, raw: Dict[str, Any]) -> int:
        adapter = self.adapters[venue]
        n = 0
        for ev in adapter.normalize_private_event(raw):
            n += 1
            self._handle_event(venue, ev)
        return n

    def _handle_event(self, venue: str, ev: Dict[str, Any]) -> None:
        cid = ev.get("client_order_id")
        rec = self.store.find_by_client_id(cid) if cid else None
        if ev.get("type") in ("FILL", "ORDER") and rec is None:
            self.recon_status[venue] = "MISMATCH"
            self.store.add_connection_event(venue, "UNKNOWN_ORDER_EVENT", client_order_id=cid)
            return
        if ev.get("type") == "FILL":
            self.apply_fill(rec, self._mk_fill(rec, ev))
        elif ev.get("type") == "ORDER":
            st = ev.get("status")
            if st == "NEW" and rec.state in (S.UNKNOWN_OUTCOME, S.SUBMITTING, S.RECONCILIATION_REQUIRED):
                rec.venue_order_id = ev.get("venue_order_id") or rec.venue_order_id  # late ACK
                self._to(rec, S.ACKNOWLEDGED, "late ACK via private stream")
                self._trace(rec).mark("venue_ack_at_ns", self._now())
            elif st == "CANCELED" and rec.state in (S.CANCEL_PENDING, S.ACKNOWLEDGED, S.PARTIALLY_FILLED, S.UNKNOWN_OUTCOME):
                self._to(rec, S.CANCELED, "venue cancel event")
            elif st == "REJECTED" and rec.state in (S.SUBMITTING, S.UNKNOWN_OUTCOME):
                self._to(rec, S.REJECTED, "venue reject event")
            # any other status never regresses an advanced state

    # ------------------------------------------------------------- reconcile / recover
    def _local_positions(self, venue: str) -> Dict[str, float]:
        pos: Dict[str, float] = {}
        for o in self.store.list_orders():
            if o.intent.venue != venue:
                continue
            sgn = 1.0 if o.intent.side == "BUY" else -1.0
            for f in o.fills:
                pos[o.intent.symbol] = pos.get(o.intent.symbol, 0.0) + sgn * f.quantity
        return pos

    def reconcile(self, venue: str) -> Dict[str, Any]:
        adapter = self.adapters[venue]
        for o in self.store.list_orders():
            if o.intent.venue == venue and o.state is S.UNKNOWN_OUTCOME:
                self.resolve_unknown(o.intent.intent_id)
        orders = [o for o in self.store.list_orders() if o.intent.venue == venue]
        fills = [f for o in orders for f in o.fills]
        res = ReconciliationEngine().reconcile(adapter, orders, fills, self._local_positions(venue))
        for d in res.diffs:
            if d["kind"] in ("STATE_DIVERGENCE", "FILL_QTY_MISMATCH") and d.get("client_order_id"):
                o = self.store.find_by_client_id(d["client_order_id"])
                if o and o.state not in (S.RECONCILIATION_REQUIRED,) and S.RECONCILIATION_REQUIRED in VALID_TRANSITIONS[o.state]:
                    self._to(o, S.RECONCILIATION_REQUIRED, f"reconciliation: {d['kind']}")
        stuck = [o for o in self.store.list_orders() if o.intent.venue == venue and o.state is S.UNKNOWN_OUTCOME]
        status = res.status
        if status == "HEALTHY" and (stuck or any(o.state is S.RECONCILIATION_REQUIRED for o in orders)):
            status = "MISMATCH"
        self.recon_status[venue] = status
        if status == "HEALTHY":
            self.recovery_pending[venue] = False
        evidence = res.evidence()
        evidence["status"] = status
        self.store.add_recon_event(venue, status, evidence)
        self._audit("RECONCILIATION", None, venue=venue, status=status, diffs=len(res.diffs))
        return evidence

    def recover(self) -> Dict[str, Any]:
        """Restart recovery: reload non-terminal orders; never infer completion; reconcile before new live orders."""
        summary: Dict[str, Any] = {"reloaded": 0, "to_unknown_outcome": 0, "pre_send_rejected": 0, "reconciled": {}}
        venues = set()
        for rec in self.store.open_orders():
            summary["reloaded"] += 1
            venues.add(rec.intent.venue)
            i = rec.intent
            if rec.state in (S.SUBMITTING, S.RECONCILIATION_REQUIRED) or (rec.state is S.CANCEL_PENDING):
                if rec.state is S.SUBMITTING:
                    self._to(rec, S.UNKNOWN_OUTCOME, "restart during submission", FailureClass.UNKNOWN_OUTCOME)
                    summary["to_unknown_outcome"] += 1
            elif rec.state in (S.INTENT_CREATED, S.RISK_APPROVED, S.ROUTING):
                started = [a for a in self.store.attempts(i.intent_id) if a["outcome"] == "STARTED"]
                if started:
                    self._to(rec, S.UNKNOWN_OUTCOME, "restart after submission attempt", FailureClass.UNKNOWN_OUTCOME) if S.UNKNOWN_OUTCOME in VALID_TRANSITIONS[rec.state] else None
                    summary["to_unknown_outcome"] += 1
                else:
                    self._to(rec, S.REJECTED, "RESTART_BEFORE_SUBMIT: provably never transmitted")
                    summary["pre_send_rejected"] += 1
        for v in venues:
            self.recovery_pending[v] = True
        for v, adapter in self.adapters.items():
            self.recon_status[v] = "UNKNOWN"
            ok_cfg = adapter.environment == "MOCK" or self.credentials.is_configured(v, adapter.environment)
            if ok_cfg and (v in venues):
                try:
                    summary["reconciled"][v] = self.reconcile(v)["status"]
                except Exception as e:
                    summary["reconciled"][v] = f"UNAVAILABLE:{type(e).__name__}"
            elif v in venues:
                summary["reconciled"][v] = "NOT_CONFIGURED"
        self.last_recovery = summary
        self._audit("RECOVERY", None, summary=summary)
        return summary

    # ------------------------------------------------------------- telemetry
    def latency_report(self) -> Dict[str, Any]:
        return aggregate_latency(self.store.latency_samples())
