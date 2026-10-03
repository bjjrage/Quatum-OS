"""Tests for telemetry, rate limiting, clock drift, latency aggregation, and private streams."""
import pytest
from src.execution_plane.adapters.fake import FakeExchangeAdapter, FakeStreamConnector
from src.execution_plane.security import CredentialProvider
from src.execution_plane.stream import PrivateStreamManager, backoff_delay
from src.execution_plane.telemetry import (
    ClockMonitor,
    ClockSample,
    LatencyTrace,
    RateLimited,
    VenueRateLimiter,
    aggregate_latency,
    percentile,
)


def test_rate_limiter_budget_and_cooldown():
    now = [100.0]
    events = []
    limiter = VenueRateLimiter(
        venue="binance_perp",
        weight_limit=10.0,
        window_s=60.0,
        clock=lambda: now[0],
        on_event=events.append,
    )

    # 1. Acquire up to limit
    limiter.acquire(4.0)
    assert limiter.used == 4.0
    limiter.acquire(6.0)
    assert limiter.used == 10.0

    # 2. Exceeding limit raises RateLimited
    with pytest.raises(RateLimited) as exc:
        limiter.acquire(1.0)
    assert exc.value.retry_after_s > 0

    # 3. Time advances beyond window -> resets window
    now[0] += 61.0
    limiter.acquire(5.0)
    assert limiter.used == 5.0

    # 4. Explicit penalty enforces cooldown
    limiter.penalize(10.0)
    with pytest.raises(RateLimited):
        limiter.acquire(1.0)
    now[0] += 10.5
    limiter.acquire(1.0)  # works now


def test_clock_monitor_drift_thresholds():
    now_ns = [1_700_000_000_000_000_000]
    cm = ClockMonitor(warn_ms=250.0, block_ms=1000.0, clock_ns=lambda: now_ns[0])

    # Unmeasured venue is UNKNOWN (never OK)
    assert cm.status("binance_perp") == "UNKNOWN"
    snap = cm.snapshot("binance_perp")
    assert snap["status"] == "UNKNOWN"

    # Perfect sync (offset 0ms) -> OK
    s = cm.measure("binance_perp", lambda: now_ns[0] // 1_000_000)
    assert cm.status("binance_perp") == "OK"

    # 300ms drift -> WARN
    cm.measure("binance_perp", lambda: (now_ns[0] // 1_000_000) + 300)
    assert cm.status("binance_perp") == "WARN"

    # 1500ms drift -> BLOCK
    cm.measure("binance_perp", lambda: (now_ns[0] // 1_000_000) + 1500)
    assert cm.status("binance_perp") == "BLOCK"
    assert cm.snapshot("binance_perp")["status"] == "BLOCK"


def test_latency_trace_durations_and_percentiles():
    t = LatencyTrace("intent_1", "binance_perp")
    base = 1_000_000_000_000
    t.mark("signal_timestamp_ns", base)
    t.mark("intent_created_at_ns", base + 5_000_000)  # +5ms
    t.mark("risk_decided_at_ns", base + 8_000_000)    # +3ms
    t.mark("submit_started_at_ns", base + 10_000_000) # +2ms
    t.mark("venue_ack_at_ns", base + 50_000_000)      # +40ms
    t.mark("first_fill_at_ns", base + 70_000_000)     # +20ms

    d = t.to_dict()
    assert d["durations_ms"]["signal_to_intent_ms"] == 5.0
    assert d["durations_ms"]["intent_to_risk_ms"] == 3.0
    assert d["durations_ms"]["submit_to_ack_ms"] == 40.0
    assert d["durations_ms"]["ack_to_first_fill_ms"] == 20.0

    # Percentiles (nearest rank)
    vals = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    assert percentile(vals, 0.50) == 50.0
    assert percentile(vals, 0.90) == 90.0

    agg = aggregate_latency([d, d])
    assert agg["samples_count"] == 2
    assert agg["metrics"]["submit_to_ack_ms"]["p50"] == 40.0


def test_private_stream_backoff_and_lifecycle():
    assert backoff_delay(1) == 1.0
    assert backoff_delay(2) == 2.0
    assert backoff_delay(3) == 4.0
    assert backoff_delay(10, cap=30.0) == 30.0

    adapter = FakeExchangeAdapter()
    received = []
    connector = FakeStreamConnector(fail_first=0, events=[{"type": "ORDER", "status": "NEW"}])

    mgr = PrivateStreamManager(
        adapter=adapter,
        handler=received.append,
        connector=connector,
    )

    # 1. Connect
    assert mgr.connect() is True
    assert mgr.health()["state"] == "CONNECTED"

    # 2. Pump events
    count = mgr.pump()
    assert count == 1
    assert len(received) == 1

    # 3. Disconnect and reconnect
    assert mgr.on_disconnect() is True
    assert mgr.health()["reconnect_count"] == 1
    assert mgr.health()["state"] == "CONNECTED"

    # 4. Connector failing first causes backoff
    failing_connector = FakeStreamConnector(fail_first=2)
    failing_mgr = PrivateStreamManager(
        adapter=adapter,
        handler=received.append,
        connector=failing_connector,
        sleep=lambda s: None,
    )
    # Reconnects after retry
    assert failing_mgr.connect() is True
    assert failing_mgr.health()["consecutive_failures"] == 0
    assert len(failing_mgr.delays) == 2

    # 5. Explicit disconnect
    mgr.disconnect()
    assert mgr.health()["state"] == "DISCONNECTED"
