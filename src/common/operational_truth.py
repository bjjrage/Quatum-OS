"""Operational truth semantic vocabulary and fail-closed state contracts.

Invariants:
- UNKNOWN != SAFE
- MISSING != ZERO
- UNVERIFIED != PASS
- NO DATA != HEALTHY
- PROCESS_ALIVE != FEEDS_HEALTHY
- ZERO_MEASUREMENT != NEVER_MEASURED
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional


class OperationalStatus(str, Enum):
    """Authoritative operational lifecycle and health states."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_STARTED = "NOT_STARTED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    STALE = "STALE"
    RECONCILED = "RECONCILED"
    MISMATCH = "MISMATCH"
    NOT_RUN = "NOT_RUN"
    NOT_CONFIGURED = "NOT_CONFIGURED"


def safe_metric(value: Optional[float], default: Optional[float] = None) -> Optional[float]:
    """Preserve None for unmeasured metrics rather than fabricating 0.0."""
    if value is None:
        return default
    return float(value)


def is_fresh(timestamp_s: Optional[float], now_s: float, max_age_s: float = 1800.0) -> bool:
    """Return True if timestamp is strictly within max_age_s from now."""
    if timestamp_s is None or timestamp_s <= 0:
        return False
    age = now_s - timestamp_s
    return 0.0 <= age <= max_age_s
