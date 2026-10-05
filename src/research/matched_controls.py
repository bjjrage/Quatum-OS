"""Causal matching utilities for research controls; never used by live strategies.

V1 remains the existing unmatched random-symbol control. V2 is a standalone,
pre-result matching design using only liquidity, prior 3-day return and
realized volatility available at the declared decision timestamp. Tolerances
are methodological defaults, not optimized parameters or evidence of alpha.
"""
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Mapping

UNMATCHED_CONTROL_V1 = "UNMATCHED_CONTROL_V1"
MATCHED_CONTROL_V2 = "MATCHED_CONTROL_V2"
DEFAULT_MAX_LIQUIDITY_RATIO = 2.0
DEFAULT_MAX_ABS_RET3_DIFF = 0.05
DEFAULT_MAX_VOLATILITY_RATIO = 2.0


def _finite_positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _ratio(a: float, b: float) -> float:
    return max(a / b, b / a)


def match_control_v2(
    target_features: Mapping[str, Mapping[str, Any]],
    candidate_features: Mapping[str, Mapping[str, Any]],
    decision_ts_ms: int,
    seed: int = 1,
    max_liquidity_ratio: float = DEFAULT_MAX_LIQUIDITY_RATIO,
    max_abs_ret3_diff: float = DEFAULT_MAX_ABS_RET3_DIFF,
    max_volatility_ratio: float = DEFAULT_MAX_VOLATILITY_RATIO,
) -> Dict[str, Dict[str, Any]]:
    """Match each target to one distinct, eligible non-target symbol or NO_MATCH.

    Feature dictionaries must contain ``qv30``, ``ret3``, ``vol30`` and
    ``as_of_ms``. A future-dated or incomplete snapshot is rejected. Matching
    is greedy in sorted target-symbol order and deterministic for a given seed.
    """
    if max_liquidity_ratio < 1 or max_volatility_ratio < 1 or max_abs_ret3_diff < 0:
        raise ValueError("matching tolerances must be non-negative and ratios at least 1")
    targets = set(target_features)
    eligible = []
    for symbol, row in candidate_features.items():
        if symbol in targets:
            continue
        try:
            as_of = int(row["as_of_ms"])
        except (KeyError, TypeError, ValueError):
            continue
        if as_of > int(decision_ts_ms):
            continue
        qv, ret3, vol = _finite_positive(row.get("qv30")), _finite(row.get("ret3")), _finite_positive(row.get("vol30"))
        if qv is not None and ret3 is not None and vol is not None:
            eligible.append((symbol, {"qv30": qv, "ret3": ret3, "vol30": vol, "as_of_ms": as_of}))
    eligible.sort(key=lambda pair: pair[0])
    used: set[str] = set()
    result: Dict[str, Dict[str, Any]] = {}
    for target in sorted(target_features):
        row = target_features[target]
        try:
            target_as_of = int(row["as_of_ms"])
        except (KeyError, TypeError, ValueError):
            target_as_of = int(decision_ts_ms) + 1
        tqv = _finite_positive(row.get("qv30"))
        tret = _finite(row.get("ret3"))
        tvol = _finite_positive(row.get("vol30"))
        if target_as_of > int(decision_ts_ms) or None in (tqv, tret, tvol):
            result[target] = {"status": "NO_MATCH", "control_symbol": None, "match_version": MATCHED_CONTROL_V2}
            continue
        matches = []
        for symbol, feature in eligible:
            if symbol in used:
                continue
            qvr = _ratio(tqv, feature["qv30"])
            vr = _ratio(tvol, feature["vol30"])
            rd = abs(tret - feature["ret3"])
            if qvr > max_liquidity_ratio or vr > max_volatility_ratio or rd > max_abs_ret3_diff:
                continue
            distance = abs(math.log(qvr)) + rd / max(max_abs_ret3_diff, 1e-12) + abs(math.log(vr))
            tie = hashlib.sha256(f"{seed}:{target}:{symbol}".encode()).hexdigest()
            matches.append((distance, tie, symbol, feature, qvr, rd, vr))
        if not matches:
            result[target] = {"status": "NO_MATCH", "control_symbol": None, "match_version": MATCHED_CONTROL_V2}
            continue
        distance, _, symbol, feature, qvr, rd, vr = min(matches)
        used.add(symbol)
        result[target] = {
            "status": "MATCHED",
            "control_symbol": symbol,
            "match_version": MATCHED_CONTROL_V2,
            "distance": distance,
            "target_as_of_ms": target_as_of,
            "control_as_of_ms": feature["as_of_ms"],
            "liquidity_ratio": qvr,
            "abs_ret3_difference": rd,
            "volatility_ratio": vr,
        }
    return result
