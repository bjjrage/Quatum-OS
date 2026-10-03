"""Clock offset estimation and latency correction without mutating raw timestamps.

DISTINCTION OF TIMESTAMPS:
1. ts_exchange_ns: Immutable raw exchange timestamp reported by exchange matching engine.
2. ts_received_utc_ns: Immutable application receive timestamp recorded on local OS clock.
3. raw_observed_age_ns = ts_received_utc_ns - ts_exchange_ns:
   Direct difference. If local host clock has NTP skew relative to exchange GPS/atomic clocks,
   raw_observed_age will be shifted by the host clock offset theta_local.
4. clock_offset_ns: Estimated offset of local host clock relative to exchange atomic time.
   theta_local = t_local - t_exchange. (If theta < 0, local clock is lagging behind exchange).
5. estimated_network_latency_ns = raw_observed_age_ns - clock_offset_ns:
   True physical network transit latency estimate, free of host clock skew.
"""
from typing import List, Optional, Tuple
import math
from pydantic import BaseModel, Field


class ClockOffsetAnalysis(BaseModel):
    """Analysis of host clock skew vs exchange timestamps."""
    clock_offset_ms: float = 0.0
    is_skew_detected: bool = False
    raw_negative_count: int = 0
    total_events_analyzed: int = 0
    corrected_p50_ms: float = 0.0
    corrected_p95_ms: float = 0.0
    corrected_p99_ms: float = 0.0
    corrected_max_ms: float = 0.0
    true_causal_violations: int = 0  # Events with negative latency even after offset correction


def infer_clock_offset_from_distribution(
    raw_ages_ms: List[float],
    assumed_min_transit_latency_ms: float = 15.0,
) -> float:
    """Infer host clock offset from raw observed event ages.
    
    In a high-throughput WebSocket stream, the minimum observed raw age corresponds
    to minimum packet transit time (speed of light in fiber + gateway processing).
    Therefore:
        min(raw_ages) = min_transit_latency + clock_offset
        clock_offset = min(raw_ages) - min_transit_latency
    """
    if not raw_ages_ms:
        return 0.0

    # Use 1st percentile to avoid single outlier corruptions
    sorted_ages = sorted(raw_ages_ms)
    idx_p01 = max(0, int(len(sorted_ages) * 0.01))
    p01_age = sorted_ages[idx_p01]

    # If 1st percentile is negative or significantly different from realistic transit times
    if p01_age < 0.0:
        return round(p01_age - assumed_min_transit_latency_ms, 2)
    return 0.0


def analyze_timestamp_latencies(
    raw_ages_ms: List[float],
    explicit_offset_ms: Optional[float] = None,
    assumed_min_transit_latency_ms: float = 15.0,
) -> ClockOffsetAnalysis:
    """Perform rigorous latency analysis separating host clock skew from network transit.
    
    Does NOT mutate raw timestamps. Computes corrected latency metrics:
        corrected_latency = raw_age - clock_offset
    """
    if not raw_ages_ms:
        return ClockOffsetAnalysis()

    total = len(raw_ages_ms)
    raw_neg = sum(1 for a in raw_ages_ms if a < 0.0)

    # Determine offset
    if explicit_offset_ms is not None:
        offset_ms = explicit_offset_ms
    elif raw_neg > 0:
        offset_ms = infer_clock_offset_from_distribution(
            raw_ages_ms, assumed_min_transit_latency_ms=assumed_min_transit_latency_ms
        )
    else:
        offset_ms = 0.0

    skew_detected = abs(offset_ms) > 100.0  # Skew > 100ms is significant host drift

    # Compute corrected latencies
    corrected = [a - offset_ms for a in raw_ages_ms]
    corrected.sort()

    def quantile(q: float) -> float:
        idx = min(len(corrected) - 1, max(0, int(len(corrected) * q)))
        return round(corrected[idx], 2)

    # True causal violations are events that remain negative by more than 50ms buffer
    # (accounting for jitter in offset estimation)
    true_violations = sum(1 for c in corrected if c < -50.0)

    return ClockOffsetAnalysis(
        clock_offset_ms=round(offset_ms, 2),
        is_skew_detected=skew_detected,
        raw_negative_count=raw_neg,
        total_events_analyzed=total,
        corrected_p50_ms=quantile(0.50),
        corrected_p95_ms=quantile(0.95),
        corrected_p99_ms=quantile(0.99),
        corrected_max_ms=round(corrected[-1], 2),
        true_causal_violations=true_violations,
    )
