"""Rate limits, clock drift and latency telemetry."""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class RateLimited(Exception):
    def __init__(self, retry_after_s: float, message: str = "rate limited"):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class VenueRateLimiter:
    """Per-venue request-weight window + retry-after cooldown. Never retries on its own."""

    def __init__(self, venue: str, weight_limit: float = 1200.0, window_s: float = 60.0,
                 clock: Callable[[], float] = time.monotonic, on_event: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.venue, self.weight_limit, self.window_s = venue, weight_limit, window_s
        self._clock, self._on_event = clock, on_event
        self._window_start = clock()
        self.used = 0.0
        self.cooldown_until = 0.0
        self.remaining_quota: Optional[float] = None
        self.order_count_limit: Optional[int] = None

    def _emit(self, event_type: str, **kw):
        if self._on_event:
            self._on_event({"venue": self.venue, "event_type": event_type, **kw})

    def acquire(self, weight: float = 1.0) -> None:
        now = self._clock()
        if now < self.cooldown_until:
            self._emit("COOLDOWN_BLOCK", retry_after_s=self.cooldown_until - now)
            raise RateLimited(self.cooldown_until - now, "venue cooldown active")
        if now - self._window_start >= self.window_s:
            self._window_start, self.used = now, 0.0
        if self.used + weight > self.weight_limit:
            wait = self.window_s - (now - self._window_start)
            self._emit("WEIGHT_EXHAUSTED", retry_after_s=wait)
            raise RateLimited(max(wait, 0.0), "request weight exhausted")
        self.used += weight

    def penalize(self, retry_after_s: float) -> None:
        self.cooldown_until = self._clock() + max(0.0, retry_after_s)
        self._emit("VENUE_429", retry_after_s=retry_after_s)

    def update_remaining(self, remaining: Optional[float]) -> None:
        self.remaining_quota = remaining

    def snapshot(self) -> Dict[str, Any]:
        now = self._clock()
        return {"venue": self.venue, "weight_limit": self.weight_limit, "used": self.used,
                "remaining_quota": self.remaining_quota,
                "cooldown_remaining_s": max(0.0, self.cooldown_until - now)}


@dataclass
class ClockSample:
    venue: str
    local_send_ns: int
    venue_time_ms: int
    local_recv_ns: int

    @property
    def rtt_ms(self) -> float:
        return (self.local_recv_ns - self.local_send_ns) / 1e6

    @property
    def offset_ms(self) -> float:
        """venue_time - local midpoint (positive => local clock behind venue)."""
        mid_ns = (self.local_send_ns + self.local_recv_ns) / 2
        return self.venue_time_ms - mid_ns / 1e6


class ClockMonitor:
    """Measures exchange clock drift. Missing measurement is UNKNOWN, never OK."""

    def __init__(self, warn_ms: float = 250.0, block_ms: float = 1000.0,
                 clock_ns: Callable[[], int] = time.time_ns):
        self.warn_ms, self.block_ms, self._clock_ns = warn_ms, block_ms, clock_ns
        self.samples: Dict[str, ClockSample] = {}

    def measure(self, venue: str, get_server_time_ms: Callable[[], int]) -> ClockSample:
        send = self._clock_ns()
        vt = get_server_time_ms()
        recv = self._clock_ns()
        s = ClockSample(venue, send, int(vt), recv)
        self.samples[venue] = s
        return s

    def status(self, venue: str) -> str:
        s = self.samples.get(venue)
        if s is None:
            return "UNKNOWN"
        d = abs(s.offset_ms)
        return "BLOCK" if d > self.block_ms else ("WARN" if d > self.warn_ms else "OK")

    def snapshot(self, venue: str) -> Dict[str, Any]:
        s = self.samples.get(venue)
        if s is None:
            return {"venue": venue, "status": "UNKNOWN", "offset_ms": None, "rtt_ms": None}
        return {"venue": venue, "status": self.status(venue), "offset_ms": s.offset_ms, "rtt_ms": s.rtt_ms,
                "warn_ms": self.warn_ms, "block_ms": self.block_ms}


_TS = ("signal_timestamp_ns", "intent_created_at_ns", "risk_decided_at_ns", "router_dispatch_at_ns",
       "submit_started_at_ns", "venue_ack_at_ns", "first_fill_at_ns", "terminal_fill_at_ns")
_DUR = {
    "signal_to_intent_ms": ("signal_timestamp_ns", "intent_created_at_ns"),
    "intent_to_risk_ms": ("intent_created_at_ns", "risk_decided_at_ns"),
    "risk_to_submit_ms": ("risk_decided_at_ns", "submit_started_at_ns"),
    "submit_to_ack_ms": ("submit_started_at_ns", "venue_ack_at_ns"),
    "ack_to_first_fill_ms": ("venue_ack_at_ns", "first_fill_at_ns"),
    "submit_to_first_fill_ms": ("submit_started_at_ns", "first_fill_at_ns"),
}


@dataclass
class LatencyTrace:
    intent_id: str
    venue: str
    ts: Dict[str, Optional[int]] = field(default_factory=lambda: {k: None for k in _TS})

    def mark(self, key: str, ns: int, overwrite: bool = False) -> None:
        if key not in self.ts:
            raise KeyError(key)
        if self.ts[key] is None or overwrite:
            self.ts[key] = ns

    def durations(self) -> Dict[str, Optional[float]]:
        out: Dict[str, Optional[float]] = {}
        for name, (a, b) in _DUR.items():
            ta, tb = self.ts.get(a), self.ts.get(b)
            out[name] = None if (ta is None or tb is None) else (tb - ta) / 1e6  # never fabricate
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {"intent_id": self.intent_id, "venue": self.venue, "timestamps_ns": dict(self.ts),
                "durations_ms": self.durations()}


def percentile(values: List[float], q: float) -> Optional[float]:
    """Nearest-rank percentile; None for no data."""
    if not values:
        return None
    if 0 < q <= 1.0:
        q = q * 100.0
    s = sorted(values)
    k = max(1, math.ceil(q / 100.0 * len(s)))
    return s[k - 1]


def aggregate_latency(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    for name in _DUR:
        vals = [s["durations_ms"][name] for s in samples
                if s.get("durations_ms", {}).get(name) is not None]
        metrics[name] = {"n": len(vals), "p50": percentile(vals, 50), "p95": percentile(vals, 95),
                         "p99": percentile(vals, 99)}
    return {"samples_count": len(samples), "metrics": metrics}
