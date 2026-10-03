"""
Order Lifecycle Tracking and Reconciliation.

Enforces state transition rules, preventing impossible transitions (e.g. FILLED -> SUBMITTED).
"""

from __future__ import annotations

from typing import Dict, Optional
from src.execution.models import (
    OrderState,
    OrderIntent,
    Fill,
    ExecutionReceipt,
    VALID_ORDER_STATE_TRANSITIONS,
)


class InvalidOrderTransitionError(Exception):
    """Raised when an illegal order lifecycle transition is attempted."""
    pass


class OrderLifecycleTracker:
    """
    Manages deterministic state transitions for order intents in memory.
    """

    def __init__(self) -> None:
        self._states: Dict[str, OrderState] = {}
        self._intents: Dict[str, OrderIntent] = {}

    def track_order(self, intent: OrderIntent) -> None:
        if intent.order_intent_id in self._intents:
            raise ValueError(f"Order intent '{intent.order_intent_id}' is already tracked.")
        self._intents[intent.order_intent_id] = intent
        self._states[intent.order_intent_id] = OrderState.SUBMITTED

    def get_state(self, order_intent_id: str) -> Optional[OrderState]:
        return self._states.get(order_intent_id)

    def transition_to(self, order_intent_id: str, next_state: OrderState) -> OrderState:
        """
        Transition an order to the next lifecycle state.
        
        Raises:
            KeyError: if order_intent_id is not tracked.
            InvalidOrderTransitionError: if the requested transition is illegal.
        """
        if order_intent_id not in self._states:
            raise KeyError(f"Order intent '{order_intent_id}' is not being tracked.")

        current = self._states[order_intent_id]
        if current == next_state:
            return current

        allowed = VALID_ORDER_STATE_TRANSITIONS.get(current, set())
        if next_state not in allowed:
            raise InvalidOrderTransitionError(
                f"Illegal order state transition for '{order_intent_id}': "
                f"cannot transition from {current.value} to {next_state.value}."
            )

        self._states[order_intent_id] = next_state
        return next_state
