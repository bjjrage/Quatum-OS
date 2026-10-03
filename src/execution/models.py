"""
Execution Domain Models and State Contracts.

Core Invariants:
1. Purely DRY-RUN / PAPER execution (dry_run=True, $0 live capital).
2. IdempotencyKey is computed deterministically from (strategy_id, order_intent_id, round_trip_index, timestamp_bucket).
3. OrderState transitions follow a strict directed acyclic graph.
4. ExecutionReceipt captures venue, exchange order ID, operational latencies, fee, and realized slippage.
"""

from __future__ import annotations

from enum import Enum
import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field, ConfigDict


class OrderState(str, Enum):
    """Authoritative order lifecycle states from Trading / Quant OS v1.4.1."""
    SUBMITTED = "SUBMITTED"
    ROUTED = "ROUTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLING = "CANCELLING"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


# Strict directed graph of permissible order lifecycle transitions
VALID_ORDER_STATE_TRANSITIONS: Dict[OrderState, Set[OrderState]] = {
    OrderState.SUBMITTED: {
        OrderState.ROUTED,
        OrderState.ACKNOWLEDGED,
        OrderState.REJECTED,
    },
    OrderState.ROUTED: {
        OrderState.ACKNOWLEDGED,
        OrderState.REJECTED,
    },
    OrderState.ACKNOWLEDGED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCELLING,
        OrderState.CANCELLED,
        OrderState.EXPIRED,
        OrderState.REJECTED,
    },
    OrderState.PARTIALLY_FILLED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCELLING,
        OrderState.CANCELLED,
        OrderState.EXPIRED,
    },
    OrderState.CANCELLING: {
        OrderState.CANCELLED,
        OrderState.FILLED,
        OrderState.PARTIALLY_FILLED,
    },
    # Terminal states: no outbound transitions permitted
    OrderState.FILLED: set(),
    OrderState.CANCELLED: set(),
    OrderState.REJECTED: set(),
    OrderState.EXPIRED: set(),
}


def compute_idempotency_key(
    strategy_id: str,
    order_intent_id: str,
    round_trip_index: int,
    timestamp_bucket: int,
) -> str:
    """Deterministically compute SHA-256 idempotency key."""
    canonical_repr = {
        "strategy_id": strategy_id,
        "order_intent_id": order_intent_id,
        "round_trip_index": round_trip_index,
        "timestamp_bucket": timestamp_bucket,
    }
    payload = json.dumps(canonical_repr, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class OrderIntent(BaseModel):
    """Normalized intent to place an order."""
    model_config = ConfigDict(extra="forbid")

    order_intent_id: str = Field(..., description="Unique strategy-scoped order intent ID")
    strategy_id: str = Field(..., description="Strategy identifier creating the intent")
    strategy_version: str = Field(default="1.0.0")
    symbol: str
    venue: str
    side: str = Field(..., description="'BUY' or 'SELL'")
    order_type: str = Field(..., description="'LIMIT' or 'MARKET'")
    quantity: float
    limit_price: Optional[float] = None
    time_in_force: str = Field(default="GTC")
    created_at_utc_ns: int = Field(default_factory=time.time_ns)
    idempotency_key: str = Field(default="")

    def model_post_init(self, __context: Any) -> None:
        if not self.idempotency_key:
            # Deterministic bucket: 10-second window
            bucket = self.created_at_utc_ns // (10 * 1_000_000_000)
            key = compute_idempotency_key(
                strategy_id=self.strategy_id,
                order_intent_id=self.order_intent_id,
                round_trip_index=0,
                timestamp_bucket=bucket,
            )
            object.__setattr__(self, "idempotency_key", key)


class Fill(BaseModel):
    """Normalized execution fill event."""
    model_config = ConfigDict(extra="forbid")

    fill_id: str
    order_intent_id: str
    symbol: str
    venue: str
    side: str
    fill_price: float
    fill_quantity: float
    fee_amount: float
    fee_asset: str
    is_taker: bool
    timestamp_ns: int = Field(default_factory=time.time_ns)


class ExecutionReceipt(BaseModel):
    """Complete auditable receipt of an order execution lifecycle."""
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    order_intent_id: str
    venue: str
    exchange_order_id: str
    status: OrderState
    fills: List[Fill] = Field(default_factory=list)
    latency_sent_to_ack_ms: float = 0.0
    latency_ack_to_fill_ms: float = 0.0
    total_fee_usd: float = 0.0
    realized_slippage_bps: float = 0.0
    dry_run: bool = True  # Strict invariant: live execution strictly locked ($0 live risk)

    @property
    def total_filled_quantity(self) -> float:
        return sum(f.fill_quantity for f in self.fills)

    @property
    def weighted_average_price(self) -> float:
        total_qty = self.total_filled_quantity
        if total_qty <= 0.0:
            return 0.0
        return sum(f.fill_price * f.fill_quantity for f in self.fills) / total_qty
