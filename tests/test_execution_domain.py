"""Unit tests for Execution Domain Contracts and Lifecycle State Transitions."""

import pytest
from src.execution import (
    OrderState,
    OrderIntent,
    Fill,
    ExecutionReceipt,
    VALID_ORDER_STATE_TRANSITIONS,
    compute_idempotency_key,
    OrderLifecycleTracker,
    InvalidOrderTransitionError,
)


def test_idempotency_key_deterministic_computation():
    """Verify that idempotency key computation is purely deterministic and reproducible."""
    key1 = compute_idempotency_key(
        strategy_id="STR-001",
        order_intent_id="intent_1001",
        round_trip_index=0,
        timestamp_bucket=170000000,
    )
    key2 = compute_idempotency_key(
        strategy_id="STR-001",
        order_intent_id="intent_1001",
        round_trip_index=0,
        timestamp_bucket=170000000,
    )
    assert key1 == key2
    assert len(key1) == 64

    # Different round trip produces different key
    key3 = compute_idempotency_key(
        strategy_id="STR-001",
        order_intent_id="intent_1001",
        round_trip_index=1,
        timestamp_bucket=170000000,
    )
    assert key3 != key1


def test_order_lifecycle_tracker_valid_and_invalid_transitions():
    """Verify state transition rules on order lifecycle."""
    tracker = OrderLifecycleTracker()
    intent = OrderIntent(
        order_intent_id="intent_2001",
        strategy_id="STR-002",
        symbol="SOLUSDT",
        venue="binance_perp",
        side="BUY",
        order_type="LIMIT",
        quantity=10.0,
        limit_price=150.0,
    )
    tracker.track_order(intent)
    assert tracker.get_state("intent_2001") == OrderState.SUBMITTED

    # Valid progression: SUBMITTED -> ROUTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED
    tracker.transition_to("intent_2001", OrderState.ROUTED)
    assert tracker.get_state("intent_2001") == OrderState.ROUTED

    tracker.transition_to("intent_2001", OrderState.ACKNOWLEDGED)
    assert tracker.get_state("intent_2001") == OrderState.ACKNOWLEDGED

    tracker.transition_to("intent_2001", OrderState.PARTIALLY_FILLED)
    assert tracker.get_state("intent_2001") == OrderState.PARTIALLY_FILLED

    tracker.transition_to("intent_2001", OrderState.FILLED)
    assert tracker.get_state("intent_2001") == OrderState.FILLED

    # FILLED is terminal: transition back to SUBMITTED or ACKNOWLEDGED is strictly forbidden
    with pytest.raises(InvalidOrderTransitionError, match="cannot transition from FILLED to SUBMITTED"):
        tracker.transition_to("intent_2001", OrderState.SUBMITTED)

    with pytest.raises(InvalidOrderTransitionError, match="cannot transition from FILLED to ACKNOWLEDGED"):
        tracker.transition_to("intent_2001", OrderState.ACKNOWLEDGED)


def test_execution_receipt_audit_contract_and_dry_run_invariant():
    """Verify ExecutionReceipt captures latencies, fees, slippage, and dry_run=True invariant."""
    fill1 = Fill(
        fill_id="fill_1",
        order_intent_id="intent_3001",
        symbol="BTCUSDT",
        venue="binance_perp",
        side="BUY",
        fill_price=60000.0,
        fill_quantity=0.5,
        fee_amount=1.5,
        fee_asset="USDT",
        is_taker=True,
    )
    fill2 = Fill(
        fill_id="fill_2",
        order_intent_id="intent_3001",
        symbol="BTCUSDT",
        venue="binance_perp",
        side="BUY",
        fill_price=60002.0,
        fill_quantity=0.5,
        fee_amount=1.5,
        fee_asset="USDT",
        is_taker=True,
    )

    receipt = ExecutionReceipt(
        receipt_id="rec_3001",
        order_intent_id="intent_3001",
        venue="binance_perp",
        exchange_order_id="binance_order_998877",
        status=OrderState.FILLED,
        fills=[fill1, fill2],
        latency_sent_to_ack_ms=35.0,
        latency_ack_to_fill_ms=120.0,
        total_fee_usd=3.0,
        realized_slippage_bps=0.33,
        dry_run=True,
    )

    assert receipt.dry_run is True  # Live execution locked
    assert receipt.total_filled_quantity == 1.0
    assert receipt.weighted_average_price == 60001.0
    assert receipt.latency_sent_to_ack_ms == 35.0
    assert receipt.latency_ack_to_fill_ms == 120.0
