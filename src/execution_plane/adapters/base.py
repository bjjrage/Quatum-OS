"""Common ExchangeAdapter contract, permit mechanism and error taxonomy.

Strategies must never talk to an adapter. Every mutating adapter call (submit / cancel / cancel_all)
requires a ``SubmitPermit`` that only the ExecutionRouter can mint, and real (LIVE-environment)
adapters additionally re-verify the live gates themselves (defense in depth, independent of the router).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from src.execution_plane.authority import (
    ExecutionAuthorization,
    ExecutionAuthorizationVerifier,
    SubmitPermit,
)
from src.execution_plane.models import (AccountSnapshot, ExecutionMode, FailureClass, InstrumentMeta,
                                        OrderIntent)


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
        from src.execution_plane.store import ReconciliationEngine
        return ReconciliationEngine().reconcile(self, local_orders, local_fills, local_positions)
