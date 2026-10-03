"""Execution plane canonical models: modes, order state machine, OrderIntent, instrument metadata.

Safety posture: infrastructure is live-READY but live trading is LOCKED (authorized live capital USD 0).
All timestamps are integer nanoseconds since epoch unless named otherwise.
"""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Provenance vocabulary (shared with the API layer)
PROVENANCE = ("REAL_RUNTIME", "LOCAL_PERSISTED", "CONFIG", "DERIVED", "PAPER_SIMULATION",
              "SANDBOX", "SHADOW", "MOCK", "UNAVAILABLE", "UNKNOWN")


class ExecutionMode(str, Enum):
    PAPER = "PAPER"
    SHADOW = "SHADOW"
    SANDBOX = "SANDBOX"
    LIVE_LOCKED = "LIVE_LOCKED"
    LIVE = "LIVE"


DEFAULT_EXECUTION_MODE = ExecutionMode.LIVE_LOCKED


def parse_mode(value: Optional[str]) -> ExecutionMode:
    """Unknown/garbled mode strings fall back to LIVE_LOCKED (UNKNOWN != ALLOWED)."""
    try:
        return ExecutionMode((value or "").strip().upper())
    except ValueError:
        return DEFAULT_EXECUTION_MODE


class OrderState(str, Enum):
    INTENT_CREATED = "INTENT_CREATED"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    ROUTING = "ROUTING"
    SUBMITTING = "SUBMITTING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"
    WOULD_SUBMIT = "WOULD_SUBMIT"  # SHADOW terminal: fully built, never transmitted


S = OrderState
TERMINAL_STATES: Set[OrderState] = {S.RISK_REJECTED, S.FILLED, S.CANCELED, S.REJECTED, S.EXPIRED, S.WOULD_SUBMIT}

VALID_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
    S.INTENT_CREATED: {S.RISK_APPROVED, S.RISK_REJECTED, S.REJECTED},
    S.RISK_APPROVED: {S.ROUTING, S.REJECTED, S.WOULD_SUBMIT},
    S.ROUTING: {S.SUBMITTING, S.REJECTED, S.WOULD_SUBMIT, S.ACKNOWLEDGED, S.FILLED},
    S.SUBMITTING: {S.ACKNOWLEDGED, S.PARTIALLY_FILLED, S.FILLED, S.REJECTED, S.UNKNOWN_OUTCOME,
                   S.RECONCILIATION_REQUIRED},
    S.ACKNOWLEDGED: {S.PARTIALLY_FILLED, S.FILLED, S.CANCEL_PENDING, S.CANCELED, S.EXPIRED,
                     S.REJECTED, S.RECONCILIATION_REQUIRED},
    S.PARTIALLY_FILLED: {S.PARTIALLY_FILLED, S.FILLED, S.CANCEL_PENDING, S.CANCELED, S.EXPIRED,
                         S.RECONCILIATION_REQUIRED},
    S.CANCEL_PENDING: {S.CANCELED, S.FILLED, S.PARTIALLY_FILLED, S.ACKNOWLEDGED, S.RECONCILIATION_REQUIRED,
                       S.UNKNOWN_OUTCOME},
    # Never treated as rejected/canceled: only reconciliation (venue truth) may resolve it.
    S.UNKNOWN_OUTCOME: {S.ACKNOWLEDGED, S.PARTIALLY_FILLED, S.FILLED, S.CANCELED, S.REJECTED, S.EXPIRED,
                        S.RECONCILIATION_REQUIRED, S.CANCEL_PENDING},
    S.RECONCILIATION_REQUIRED: {S.ACKNOWLEDGED, S.PARTIALLY_FILLED, S.FILLED, S.CANCELED, S.REJECTED,
                                S.EXPIRED, S.UNKNOWN_OUTCOME},
    S.RISK_REJECTED: set(), S.FILLED: set(), S.CANCELED: set(), S.REJECTED: set(), S.EXPIRED: set(),
    S.WOULD_SUBMIT: set(),
}


class FailureClass(str, Enum):
    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_FAILURE = "AUTH_FAILURE"
    INVALID_ORDER = "INVALID_ORDER"
    VENUE_UNAVAILABLE = "VENUE_UNAVAILABLE"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"


# Only these are safe to retry blindly; UNKNOWN_OUTCOME / RECONCILIATION_REQUIRED never are.
SAFE_TO_RETRY = {FailureClass.RETRYABLE, FailureClass.RATE_LIMITED}


class SideEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class OrderIntent(BaseModel):
    """Canonical intent. No order enters execution without a valid OrderIntent."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    intent_id: str
    strategy_id: str
    strategy_version: str
    capital_pocket_id: str
    venue: str
    symbol: str
    side: str
    order_type: str  # LIMIT | MARKET
    quantity: float
    limit_price: Optional[float] = None
    reference_price: Optional[float] = None  # required for MARKET (risk valuation only)
    time_in_force: str = "GTC"
    reduce_only: bool = False
    post_only: bool = False
    market_data_timestamp_ns: int
    decision_timestamp_ns: int
    max_signal_age_ms: float
    event_cluster_id: Optional[str] = None
    client_order_id: str = ""
    idempotency_key: str = ""
    created_at_ns: int
    config_fingerprint: str = "UNKNOWN"
    provenance: Dict[str, str] = Field(default_factory=dict)

    @field_validator("side")
    @classmethod
    def _side(cls, v: str) -> str:
        if v not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        return v

    @field_validator("order_type")
    @classmethod
    def _otype(cls, v: str) -> str:
        if v not in ("LIMIT", "MARKET"):
            raise ValueError("order_type must be LIMIT or MARKET")
        return v

    @field_validator("time_in_force")
    @classmethod
    def _tif(cls, v: str) -> str:
        if v not in ("GTC", "IOC", "FOK", "GTX"):
            raise ValueError("unsupported time_in_force")
        return v

    @model_validator(mode="before")
    @classmethod
    def _derive_ids(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if not d.get("idempotency_key"):
            d["idempotency_key"] = _digest({
                k: d.get(k) for k in ("strategy_id", "strategy_version", "capital_pocket_id", "venue", "symbol",
                                      "side", "order_type", "quantity", "limit_price", "decision_timestamp_ns")})
        if not d.get("client_order_id"):
            d["client_order_id"] = "qos" + d["idempotency_key"][:29]  # <=32 chars, venue-safe charset
        return d

    @model_validator(mode="after")
    def _checks(self) -> "OrderIntent":
        if not (self.quantity > 0):
            raise ValueError("quantity must be > 0")
        if self.order_type == "LIMIT" and not (self.limit_price and self.limit_price > 0):
            raise ValueError("LIMIT requires positive limit_price")
        if not (self.max_signal_age_ms > 0):
            raise ValueError("max_signal_age_ms must be > 0")
        if self.post_only and self.order_type != "LIMIT":
            raise ValueError("post_only requires LIMIT")
        if not self.strategy_id or not self.capital_pocket_id or not self.venue or not self.symbol:
            raise ValueError("strategy_id, capital_pocket_id, venue, symbol are required")
        return self

    @property
    def valuation_price(self) -> Optional[float]:
        return self.limit_price if self.order_type == "LIMIT" else self.reference_price


def _dec(x: Any) -> Decimal:
    try:
        return Decimal(str(x))
    except (InvalidOperation, ValueError) as e:
        raise ValueError(f"not a number: {x!r}") from e


class InstrumentMeta(BaseModel):
    """Normalized instrument metadata. Never guess precision; never silently round."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    venue: str
    venue_symbol: str
    tick_size: float
    step_size: float
    min_qty: float
    min_notional: float
    contract_multiplier: float = 1.0
    margin_type: str = "LINEAR"  # LINEAR | INVERSE
    base_asset: str
    quote_asset: str
    margin_asset: str

    def validate_order(self, quantity: float, price: Optional[float]) -> List[str]:
        """Return list of problems (empty == valid). Exact Decimal arithmetic, no rounding."""
        problems: List[str] = []
        try:
            q, step, mq = _dec(quantity), _dec(self.step_size), _dec(self.min_qty)
            if step <= 0 or _dec(self.tick_size) <= 0:
                return ["INVALID_METADATA: non-positive tick/step"]
            if q < mq:
                problems.append(f"QTY_BELOW_MIN: {quantity} < {self.min_qty}")
            if (q / step) != (q / step).to_integral_value():
                problems.append(f"QTY_PRECISION: {quantity} not a multiple of step {self.step_size}")
            if price is not None:
                p, tick = _dec(price), _dec(self.tick_size)
                if p <= 0:
                    problems.append("PRICE_NON_POSITIVE")
                elif (p / tick) != (p / tick).to_integral_value():
                    problems.append(f"PRICE_PRECISION: {price} not a multiple of tick {self.tick_size}")
                notional = q * p * _dec(self.contract_multiplier)
                if notional < _dec(self.min_notional):
                    problems.append(f"NOTIONAL_BELOW_MIN: {notional} < {self.min_notional}")
        except ValueError as e:
            problems.append(f"INVALID_NUMBER: {e}")
        return problems


class ExecFill(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fill_id: str
    intent_id: str
    client_order_id: str
    venue: str
    venue_order_id: Optional[str] = None
    venue_trade_id: str
    price: float
    quantity: float
    fee: float = 0.0
    fee_asset: str = "USDT"
    is_taker: Optional[bool] = None
    timestamp_ns: int


class OrderRecord(BaseModel):
    """Mutable projection of one order's lifecycle (source of truth is the persisted transitions)."""
    intent: OrderIntent
    state: OrderState = OrderState.INTENT_CREATED
    mode: ExecutionMode = DEFAULT_EXECUTION_MODE
    venue_order_id: Optional[str] = None
    reason: str = ""
    failure_class: Optional[FailureClass] = None
    fills: List[ExecFill] = Field(default_factory=list)
    attempts: int = 0
    cancel_requested: bool = False
    prior_state: Optional[OrderState] = None  # state before CANCEL_PENDING
    updated_at_ns: int = 0

    @property
    def requested_qty(self) -> float:
        return self.intent.quantity

    @property
    def filled_qty(self) -> float:
        return float(sum(_dec(f.quantity) for f in self.fills))

    @property
    def remaining_qty(self) -> float:
        return max(0.0, float(_dec(self.intent.quantity) - sum((_dec(f.quantity) for f in self.fills), Decimal(0))))

    @property
    def avg_fill_price(self) -> Optional[float]:
        if not self.fills:
            return None
        notional = sum(_dec(f.price) * _dec(f.quantity) for f in self.fills)
        return float(notional / sum(_dec(f.quantity) for f in self.fills))

    @property
    def total_fees(self) -> float:
        return float(sum(_dec(f.fee) for f in self.fills))

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def summary(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent.intent_id, "client_order_id": self.intent.client_order_id,
            "venue_order_id": self.venue_order_id, "strategy_id": self.intent.strategy_id,
            "venue": self.intent.venue, "symbol": self.intent.symbol, "side": self.intent.side,
            "state": self.state.value, "mode": self.mode.value, "reason": self.reason,
            "failure_class": self.failure_class.value if self.failure_class else None,
            "requested_qty": self.requested_qty, "filled_qty": self.filled_qty,
            "remaining_qty": self.remaining_qty, "avg_fill_price": self.avg_fill_price,
            "fees": self.total_fees, "fill_count": len(self.fills),
            "idempotency_key": self.intent.idempotency_key, "attempts": self.attempts,
        }


class AccountSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    venue: str
    account_id: Optional[str] = None
    equity: Optional[float] = None
    available_balance: Optional[float] = None
    margin_used: Optional[float] = None
    positions: List[Dict[str, Any]] = Field(default_factory=list)
    open_orders: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp_ns: Optional[int] = None
    data_source: str = "UNAVAILABLE"
    status: str = "NOT_CONFIGURED"  # NOT_CONFIGURED | KNOWN | UNKNOWN | ERROR


def not_configured_account(venue: str) -> AccountSnapshot:
    """Never fabricate zero balances."""
    return AccountSnapshot(venue=venue)
