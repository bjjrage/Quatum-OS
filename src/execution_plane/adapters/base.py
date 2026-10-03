"""Common ExchangeAdapter contract, permit mechanism and error taxonomy.

Strategies must never talk to an adapter. Every mutating adapter call (submit / cancel / cancel_all)
requires a ``SubmitPermit`` that only the ExecutionRouter can mint, and real (LIVE-environment)
adapters additionally re-verify the live gates themselves (defense in depth, independent of the router).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from src.execution_plane.models import (AccountSnapshot, ExecutionMode, FailureClass, InstrumentMeta,
                                        OrderIntent)

_ISSUER = object()  # private: only router.py imports this


class AdapterError(Exception):
    failure_class: FailureClass = FailureClass.NON_RETRYABLE

    def __init__(self, message: str, failure_class: Optional[FailureClass] = None,
                 retry_after_s: Optional[float] = None, code: Optional[str] = None):
        super().__init__(message)
        if failure_class is not None:
            self.failure_class = failure_class
        self.retry_after_s = retry_after_s
        self.code = code


class UnknownOutcomeError(AdapterError):
    """Request may have reached the venue (timeout / ambiguous 5xx after send). NEVER retry blindly."""
    failure_class = FailureClass.UNKNOWN_OUTCOME


class VenueUnavailable(AdapterError):
    failure_class = FailureClass.VENUE_UNAVAILABLE

    def __init__(self, message: str, pre_send: bool = False, **kw):
        super().__init__(message, **kw)
        self.pre_send = pre_send  # True: provably never transmitted -> safe to retry


class AuthFailure(AdapterError):
    failure_class = FailureClass.AUTH_FAILURE


class InvalidOrder(AdapterError):
    failure_class = FailureClass.INVALID_ORDER


class LiveLockedError(AdapterError):
    failure_class = FailureClass.NON_RETRYABLE


class TransportNotConfigured(AdapterError):
    failure_class = FailureClass.VENUE_UNAVAILABLE


import hashlib
import hmac
import secrets
import time
import uuid

@dataclass(frozen=True)
class ExecutionAuthorization:
    """Structurally and cryptographically verifiable authorization for mutating actions.
    
    Minted exclusively after an approved RiskDecision through ExecutionRouter or ExecutionAuthorizer.
    Bound to intent_id, client_order_id, venue, symbol, mode, kind, risk_decision_id,
    risk_decision_fingerprint, expires_at_ns, and single-use nonce.
    """
    kind: str  # SUBMIT | CANCEL | CANCEL_ALL
    venue: str
    client_order_id: Optional[str]
    mode: ExecutionMode
    authorized_live_capital_usd: float
    risk_approved: bool
    issued_ns: int
    intent_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    risk_decision_id: Optional[str] = None
    risk_decision_fingerprint: Optional[str] = None
    expires_at_ns: int = 0
    nonce: str = ""
    signature: str = ""
    _issuer: Any = None

    def __post_init__(self):
        if self._issuer is not _ISSUER:
            raise PermissionError("ExecutionAuthorization can only be issued by ExecutionAuthorizer / ExecutionRouter")


SubmitPermit = ExecutionAuthorization


class ExecutionAuthorizer:
    """Authority for minting and verifying tamper-evident, non-reusable execution permits."""

    _default_instance: Optional["ExecutionAuthorizer"] = None

    def __init__(self, secret_key: Optional[bytes] = None, default_validity_window_ns: int = 10_000_000_000):
        self._secret_key: bytes = secret_key or secrets.token_bytes(32)
        self.default_validity_window_ns: int = default_validity_window_ns  # 10s default
        self._consumed_nonces: set[str] = set()

    @classmethod
    def get_default(cls) -> "ExecutionAuthorizer":
        if cls._default_instance is None:
            cls._default_instance = cls()
        return cls._default_instance

    @classmethod
    def reset_default(cls) -> None:
        cls._default_instance = None

    def _compute_signature(
        self,
        kind: str,
        venue: str,
        client_order_id: Optional[str],
        mode: ExecutionMode,
        authorized_live_capital_usd: float,
        risk_approved: bool,
        issued_ns: int,
        intent_id: Optional[str],
        symbol: Optional[str],
        side: Optional[str],
        risk_decision_id: Optional[str],
        risk_decision_fingerprint: Optional[str],
        expires_at_ns: int,
        nonce: str,
    ) -> str:
        payload = (
            f"{kind}:{venue}:{client_order_id or ''}:{mode.value}:{authorized_live_capital_usd:.4f}:"
            f"{risk_approved}:{issued_ns}:{intent_id or ''}:{symbol or ''}:{side or ''}:"
            f"{risk_decision_id or ''}:{risk_decision_fingerprint or ''}:{expires_at_ns}:{nonce}"
        )
        return hmac.new(self._secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def mint(
        self,
        kind: str,
        venue: str,
        mode: ExecutionMode,
        client_order_id: Optional[str] = None,
        intent_id: Optional[str] = None,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        risk_decision: Optional[Any] = None,
        authorized_live_capital_usd: float = 0.0,
        current_time_ns: Optional[int] = None,
        validity_window_ns: Optional[int] = None,
    ) -> ExecutionAuthorization:
        """Mint a cryptographic, tamper-evident authorization token bound to an approved RiskDecision."""
        if risk_decision is None:
            raise PermissionError("ExecutionAuthorizer: Cannot mint authorization without a RiskDecision.")

        if not getattr(risk_decision, "approved", False):
            violation = getattr(risk_decision, "violation_code", "UNKNOWN_VIOLATION")
            raise PermissionError(f"ExecutionAuthorizer: RiskDecision rejected ({violation}). Minting prohibited.")

        now_ns = current_time_ns if current_time_ns is not None else time.time_ns()
        window_ns = validity_window_ns if validity_window_ns is not None else self.default_validity_window_ns
        expires_at_ns = (now_ns + window_ns) if window_ns > 0 else 0
        nonce = uuid.uuid4().hex

        # Compute risk decision fingerprint
        vcode = getattr(risk_decision.violation_code, "value", str(getattr(risk_decision, "violation_code", "")))
        reason = getattr(risk_decision, "reason", "")
        metrics = getattr(risk_decision, "metrics", {})
        metrics_repr = ",".join(f"{k}={v}" for k, v in sorted(metrics.items())) if isinstance(metrics, dict) else str(metrics)
        fp_raw = f"{risk_decision.approved}:{vcode}:{reason}:{metrics_repr}"
        risk_fp = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()
        risk_dec_id = getattr(risk_decision, "decision_id", None) or f"dec_{intent_id or nonce[:8]}"

        sig = self._compute_signature(
            kind=kind,
            venue=venue,
            client_order_id=client_order_id,
            mode=mode,
            authorized_live_capital_usd=authorized_live_capital_usd,
            risk_approved=True,
            issued_ns=now_ns,
            intent_id=intent_id,
            symbol=symbol,
            side=side,
            risk_decision_id=risk_dec_id,
            risk_decision_fingerprint=risk_fp,
            expires_at_ns=expires_at_ns,
            nonce=nonce,
        )

        return ExecutionAuthorization(
            kind=kind,
            venue=venue,
            client_order_id=client_order_id,
            mode=mode,
            authorized_live_capital_usd=authorized_live_capital_usd,
            risk_approved=True,
            issued_ns=now_ns,
            intent_id=intent_id,
            symbol=symbol,
            side=side,
            risk_decision_id=risk_dec_id,
            risk_decision_fingerprint=risk_fp,
            expires_at_ns=expires_at_ns,
            nonce=nonce,
            signature=sig,
            _issuer=_ISSUER,
        )

    def verify(
        self,
        auth: Any,
        expected_venue: str,
        expected_kind: str = "SUBMIT",
        expected_symbol: Optional[str] = None,
        expected_client_order_id: Optional[str] = None,
        expected_mode: Optional[ExecutionMode] = None,
        current_time_ns: Optional[int] = None,
    ) -> None:
        """Verify authorization validity, cryptographic signature, scope binding, expiration, and replay."""
        # 1. Type verification: absolutely no duck typing
        if not isinstance(auth, ExecutionAuthorization):
            raise PermissionError("Authorization rejected: invalid object type (duck typing strictly prohibited).")

        # 2. Risk approval check
        if not auth.risk_approved:
            raise PermissionError("Authorization rejected: risk_approved is False.")

        # 3. Cryptographic signature check
        expected_sig = self._compute_signature(
            kind=auth.kind,
            venue=auth.venue,
            client_order_id=auth.client_order_id,
            mode=auth.mode,
            authorized_live_capital_usd=auth.authorized_live_capital_usd,
            risk_approved=auth.risk_approved,
            issued_ns=auth.issued_ns,
            intent_id=auth.intent_id,
            symbol=auth.symbol,
            side=auth.side,
            risk_decision_id=auth.risk_decision_id,
            risk_decision_fingerprint=auth.risk_decision_fingerprint,
            expires_at_ns=auth.expires_at_ns,
            nonce=auth.nonce,
        )
        if not hmac.compare_digest(auth.signature, expected_sig):
            raise PermissionError("Authorization rejected: invalid cryptographic signature (tampered or forged permit).")

        # 4. Scope bindings
        if auth.kind != expected_kind:
            raise PermissionError(f"Authorization scope mismatch: expected kind {expected_kind}, got {auth.kind}.")
        venue_matches = (auth.venue == expected_venue) or (
            expected_venue in ("SIM", "paper") and auth.venue in ("SIM", "paper")
        )
        if not venue_matches:
            raise PermissionError(f"Authorization venue mismatch: expected venue {expected_venue}, got {auth.venue}.")
        if expected_symbol is not None and auth.symbol is not None:
            sym_matches = (auth.symbol == expected_symbol) or (
                auth.symbol.replace("-", "") == expected_symbol.replace("-", "")
            )
            if not sym_matches:
                raise PermissionError(f"Authorization symbol mismatch: expected symbol {expected_symbol}, got {auth.symbol}.")
        if expected_client_order_id is not None and auth.client_order_id not in (None, expected_client_order_id):
            raise PermissionError(f"Authorization client_order_id mismatch: expected {expected_client_order_id}, got {auth.client_order_id}.")
        if expected_mode is not None and auth.mode != expected_mode:
            raise PermissionError(f"Authorization mode mismatch: expected {expected_mode}, got {auth.mode}.")

        # 5. Expiration check
        now_ns = current_time_ns if current_time_ns is not None else time.time_ns()
        if auth.expires_at_ns > 0 and now_ns > auth.expires_at_ns:
            raise PermissionError(f"Authorization expired: current_time_ns={now_ns} > expires_at_ns={auth.expires_at_ns}.")

        # 6. Replay protection
        if auth.nonce in self._consumed_nonces:
            raise PermissionError(f"Authorization rejected: permit token already consumed (replay detected, nonce={auth.nonce}).")
        self._consumed_nonces.add(auth.nonce)


def mint_test_authorization(
    kind: str = "SUBMIT",
    venue: str = "binance_perp",
    client_order_id: Optional[str] = "test-order-1",
    symbol: Optional[str] = "BTCUSDT",
    mode: ExecutionMode = ExecutionMode.SANDBOX,
    authorized_live_capital_usd: float = 0.0,
    risk_approved: bool = True,
    current_time_ns: Optional[int] = None,
    validity_window_ns: int = 3_600_000_000_000,
) -> ExecutionAuthorization:
    """Test helper for unit tests to mint a valid authorization with mock RiskDecision."""
    from src.risk.engine import RiskDecision
    authorizer = ExecutionAuthorizer.get_default()
    decision = RiskDecision(approved=risk_approved, reason="Test harness authorization")
    return authorizer.mint(
        kind=kind,
        venue=venue,
        mode=mode,
        client_order_id=client_order_id,
        symbol=symbol,
        risk_decision=decision,
        authorized_live_capital_usd=authorized_live_capital_usd,
        current_time_ns=current_time_ns,
        validity_window_ns=validity_window_ns,
    )


def issue_permit(
    kind: str,
    venue: str,
    client_order_id: Optional[str],
    mode: ExecutionMode,
    authorized_live_capital_usd: float,
    risk_approved: bool,
    issued_ns: int,
    symbol: Optional[str] = None,
) -> ExecutionAuthorization:
    """Backward-compatible wrapper for tests. Production must use router / authorizer."""
    return mint_test_authorization(
        kind=kind,
        venue=venue,
        client_order_id=client_order_id,
        symbol=symbol,
        mode=mode,
        authorized_live_capital_usd=authorized_live_capital_usd,
        risk_approved=risk_approved,
        current_time_ns=issued_ns,
        validity_window_ns=0,
    )


class ExchangeAdapter(ABC):
    venue: str = "abstract"
    environment: str = "LIVE"  # LIVE | SANDBOX | MOCK
    is_test_only: bool = False

    # ---- safety ----
    def _check_permit(self, permit: Any, kind: str, client_order_id: Optional[str] = None) -> None:
        if not isinstance(permit, ExecutionAuthorization):
            raise PermissionError("mutating call requires a router-issued SubmitPermit/ExecutionAuthorization")
        if permit.kind != kind or permit.venue != self.venue:
            raise PermissionError("permit does not match request")
        if client_order_id is not None and permit.client_order_id not in (None, client_order_id):
            raise PermissionError("permit client_order_id mismatch")
        if self.environment == "LIVE":
            if not (permit.mode is ExecutionMode.LIVE and permit.authorized_live_capital_usd > 0
                    and permit.risk_approved):
                raise LiveLockedError("real transmission rejected: LIVE mode + authorized capital + risk approval required")
        elif self.environment == "SANDBOX":
            if permit.mode is not ExecutionMode.SANDBOX:
                raise LiveLockedError("sandbox adapter requires SANDBOX execution mode")
        # MOCK (test-only fake): any mode the router allows

    # ---- lifecycle / info ----
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def health(self) -> Dict[str, Any]: ...

    @abstractmethod
    def capabilities(self) -> Dict[str, Any]: ...

    @abstractmethod
    def get_server_time(self) -> int:
        """Venue time in epoch milliseconds."""

    # ---- account reads ----
    @abstractmethod
    def get_account(self) -> AccountSnapshot: ...

    @abstractmethod
    def get_balances(self) -> Dict[str, Any]: ...

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """[{symbol, quantity(signed), entry_price}]"""

    @abstractmethod
    def get_open_orders(self) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def get_order(self, client_order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Dict if found; None ONLY if the venue definitively reports not-found; raises if query failed."""

    @abstractmethod
    def get_fills(self, symbol: Optional[str] = None, since_ns: Optional[int] = None) -> List[Dict[str, Any]]: ...

    # ---- mutations (permit-gated) ----
    @abstractmethod
    def serialize_order(self, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]:
        """Pure: exact venue request, no network (used by SHADOW)."""

    @abstractmethod
    def submit_order(self, permit: SubmitPermit, intent: OrderIntent, meta: InstrumentMeta) -> Dict[str, Any]: ...

    @abstractmethod
    def cancel_order(self, permit: SubmitPermit, client_order_id: str, symbol: str) -> Dict[str, Any]: ...

    @abstractmethod
    def cancel_all(self, permit: SubmitPermit, symbol: Optional[str] = None) -> Dict[str, Any]: ...

    def replace_order(self, permit: SubmitPermit, client_order_id: str, symbol: str,
                      new_quantity: Optional[float], new_price: Optional[float]) -> Dict[str, Any]:
        """Atomic replace is NOT assumed. The router performs cancel-confirm + new intent instead."""
        raise AdapterError("atomic replace not guaranteed on this venue; use router cancel+new",
                           FailureClass.NON_RETRYABLE)

    # ---- private stream ----
    def subscribe_private_stream(self, handler: Callable[[Dict[str, Any]], None], connector: Any = None):
        from src.execution_plane.stream import PrivateStreamManager
        return PrivateStreamManager(self, handler, connector)

    def normalize_private_event(self, raw: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def reconcile(self, local_orders, local_fills, local_positions):
        from src.execution_plane.reconcile import ReconciliationEngine
        return ReconciliationEngine().reconcile(self, local_orders, local_fills, local_positions)
