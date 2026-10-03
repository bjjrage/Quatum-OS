"""
Portfolio Selection Gates (v1.4.2 Hardened & Fail-Closed).

Implements four mandatory evidence gates before a strategy can be allocated capital or promoted:
- Gate A: Latency Sensitivity Gate (replays backtest with delays: 0s, +1s, +5s, +30s; edge half-life; LATENCY_RACE detection; operational stack budget)
- Gate B: Temporal Stability & Alpha Decay Gate (early vs late half, rolling 30-day Sharpe positive >= 75%, DECAYING flag, regime stability)
- Gate C: Multiple Selection Correction Gate (Bailey & López de Prado DSR, Benjamini-Hochberg FDR across trial_count from ExperimentRegistry)
- Gate D: Correlation & Capacity Gate (Normal < 0.60, Stress < 0.70, EventCluster overlap check, 1% 5m volume capacity check)

Governance Rules:
1. All thresholds are explicitly configurable provisional research priors, not validated economic truths.
2. Every evaluation produces a fully auditable StrategyGateResult with metrics, thresholds, fingerprints, and reasons.
3. Insufficient data yields GateStatus.PENDING, never silent PASS.
4. status=PASS cannot be instantiated if metrics fail thresholds, criteria evaluations contain False or are empty, or falsification evidence is present.
5. All gate artifacts and results are immutable (frozen=True, extra="forbid").
"""

from __future__ import annotations

from enum import Enum
import math
import time
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field, ConfigDict, model_validator

from src.quant.black76 import norm_cdf
from src.research.experiments import MultipleTestingContext, RegistryIntegrityStatus


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


CANONICAL_GATE_TYPES = {
    "A": "LATENCY_SENSITIVITY",
    "B": "TEMPORAL_STABILITY",
    "C": "MULTIPLE_SELECTION",
    "D": "CORRELATION_CAPACITY",
}

FORBIDDEN_PASS_FINGERPRINTS = {
    "ds_prov_unspecified",
    "cfg_prov_unspecified",
    "PROVENANCE_UNSPECIFIED",
    "PROVENANCE_MISSING",
    "",
}


def benjamini_hochberg(p_values: List[float], alpha: float = 0.05) -> Tuple[List[float], List[bool]]:
    """
    Benjamini-Hochberg False Discovery Rate (FDR) procedure.
    Enforces monotonic step-up adjusted p-values (q-values) and bounds to [0.0, 1.0].

    Returns:
        adjusted_p_values: Monotonically adjusted q-values in original input order.
        significant: Boolean pass mask for adjusted_p_value <= alpha in original input order.
    """
    m = len(p_values)
    if m == 0:
        return [], []
    for p in p_values:
        if p is None or not isinstance(p, (int, float)) or isinstance(p, bool):
            raise ValueError(f"p-value must be numeric, got {type(p).__name__}")
        if math.isnan(p) or math.isinf(p) or not (0.0 <= float(p) <= 1.0):
            raise ValueError(f"p-value must be finite float in [0.0, 1.0], got {p}")

    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    q_values = [0.0] * m

    cum_min = 1.0
    for rank in range(m, 0, -1):
        orig_idx, p_val = indexed[rank - 1]
        val = (float(p_val) * m) / float(rank)
        cum_min = min(cum_min, val)
        q_values[orig_idx] = max(0.0, min(1.0, cum_min))

    passes = [q <= alpha for q in q_values]
    return q_values, passes


class StrategyGateEvidenceSnapshot(BaseModel):
    """Immutable snapshot of evidence supporting a gate evaluation."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    gate_type: str
    dataset_fingerprint: str
    config_fingerprint: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    thresholds: Dict[str, float] = Field(default_factory=dict)
    criteria_evaluations: Dict[str, bool] = Field(default_factory=dict)
    reasons: List[str] = Field(default_factory=list)
    falsification_evidence: Optional[str] = None
    captured_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class StrategyGateResult(BaseModel):
    """Complete auditable evaluation contract for all portfolio selection gates (v1.4.2 Fail-Closed)."""
    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy_id: str = "DEFAULT"
    strategy_version: str = "1.0.0"
    gate_type: str = "UNKNOWN_GATE"
    gate_name: Optional[str] = None
    status: GateStatus
    score: float = 0.0
    threshold: float = 0.0
    metrics: Dict[str, float] = Field(default_factory=dict)
    thresholds: Dict[str, float] = Field(default_factory=dict)
    criteria_evaluations: Dict[str, bool] = Field(default_factory=dict)
    threshold_is_provisional: bool = True
    dataset_fingerprint: str = ""
    config_fingerprint: str = ""
    experiment_ids: List[str] = Field(default_factory=list)
    evaluated_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    reasons: List[str] = Field(default_factory=list)
    falsification_evidence: Optional[str] = None
    diagnostics: Dict[str, Any] = Field(default_factory=dict)

    @property
    def parameter_fingerprint(self) -> str:
        return self.config_fingerprint

    @model_validator(mode="before")
    @classmethod
    def _validate_gate_contract(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        gate_type = data.get("gate_type") or data.get("gate_name") or "UNKNOWN_GATE"
        gate_name = data.get("gate_name") or gate_type
        data["gate_type"] = gate_type
        data["gate_name"] = gate_name

        status = data.get("status")
        if isinstance(status, str):
            status = GateStatus(status)

        ds_fp = str(data.get("dataset_fingerprint", ""))
        cfg_fp = str(data.get("config_fingerprint", ""))
        if not ds_fp.strip() or not cfg_fp.strip():
            raise ValueError(
                f"Provenance violation: dataset_fingerprint ('{ds_fp}') and config_fingerprint ('{cfg_fp}') "
                "must be non-empty strings."
            )

        criteria = data.get("criteria_evaluations") or {}
        reasons = list(data.get("reasons") or [])
        falsification = data.get("falsification_evidence")

        if status == GateStatus.PASS:
            if ds_fp in FORBIDDEN_PASS_FINGERPRINTS or cfg_fp in FORBIDDEN_PASS_FINGERPRINTS:
                raise ValueError(
                    f"Provenance violation: placeholder fingerprints ('{ds_fp}', '{cfg_fp}') cannot be used for status=PASS."
                )

            score = data.get("score")
            threshold = data.get("threshold")
            if score is not None and (math.isnan(score) or math.isinf(score)):
                raise ValueError(f"Invalid score: {score} is nonfinite.")
            if threshold is not None and (math.isnan(threshold) or math.isinf(threshold)):
                raise ValueError(f"Invalid threshold: {threshold} is nonfinite.")

            metrics = data.get("metrics") or {}
            for k, v in metrics.items():
                if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
                    raise ValueError(f"Invalid metric '{k}': {v} is nonfinite.")

            thresholds = data.get("thresholds") or {}
            for k, v in thresholds.items():
                if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
                    raise ValueError(f"Invalid threshold '{k}': {v} is nonfinite.")

            if falsification:
                raise ValueError(
                    f"Invalid StrategyGateResult: cannot declare status=PASS with falsification_evidence: {falsification}"
                )
            if reasons:
                raise ValueError(
                    f"Invalid StrategyGateResult: cannot declare status=PASS with non-empty reasons: {reasons}"
                )
            if not criteria:
                raise ValueError(
                    "Invalid StrategyGateResult: status=PASS requires non-empty criteria_evaluations mapping."
                )
            if any(val is False for val in criteria.values()):
                failed_crit = [k for k, v in criteria.items() if v is False]
                raise ValueError(
                    f"Invalid StrategyGateResult: status=PASS cannot contain False criteria evaluations: {failed_crit}"
                )

        elif status == GateStatus.FAIL:
            if not reasons and falsification:
                reasons = [falsification]
                data["reasons"] = reasons
            elif not reasons:
                reasons = [f"Failed gate {gate_type} threshold evaluation."]
                data["reasons"] = reasons
            if not falsification and reasons:
                data["falsification_evidence"] = "; ".join(reasons)

        elif status == GateStatus.PENDING:
            if falsification:
                raise ValueError(
                    f"Invalid StrategyGateResult: cannot declare status=PENDING with falsification_evidence: {falsification}"
                )
            if not reasons:
                raise ValueError(
                    "Invalid StrategyGateResult: status=PENDING requires non-empty reasons explaining pending evidence."
                )

        return data

    @classmethod
    def create_pass(
        cls,
        strategy_id: str,
        gate_type: str,
        dataset_fingerprint: str,
        config_fingerprint: str,
        criteria_evaluations: Dict[str, bool],
        score: float = 1.0,
        threshold: float = 0.5,
        strategy_version: str = "1.0.0",
        metrics: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        experiment_ids: Optional[List[str]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        reasons: Optional[List[str]] = None,
    ) -> StrategyGateResult:
        return cls(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            status=GateStatus.PASS,
            score=score,
            threshold=threshold,
            metrics=metrics or {},
            thresholds=thresholds or {},
            criteria_evaluations=criteria_evaluations,
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            experiment_ids=experiment_ids or [],
            reasons=[],
            falsification_evidence=None,
            diagnostics=diagnostics or {},
        )

    @classmethod
    def create_fail(
        cls,
        strategy_id: str,
        gate_type: str,
        dataset_fingerprint: str,
        config_fingerprint: str,
        score: float = 0.0,
        threshold: float = 0.5,
        strategy_version: str = "1.0.0",
        metrics: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        criteria_evaluations: Optional[Dict[str, bool]] = None,
        reasons: Optional[List[str]] = None,
        falsification_evidence: Optional[str] = None,
        experiment_ids: Optional[List[str]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> StrategyGateResult:
        r = list(reasons or [])
        f = falsification_evidence or ("; ".join(r) if r else f"Failed gate {gate_type}")
        if not r:
            r = [f]
        crit = criteria_evaluations if criteria_evaluations is not None else {"gate_passed": False}
        return cls(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            status=GateStatus.FAIL,
            score=score,
            threshold=threshold,
            metrics=metrics or {},
            thresholds=thresholds or {},
            criteria_evaluations=crit,
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            experiment_ids=experiment_ids or [],
            reasons=r,
            falsification_evidence=f,
            diagnostics=diagnostics or {},
        )

    @classmethod
    def create_pending(
        cls,
        strategy_id: str,
        gate_type: str,
        dataset_fingerprint: str,
        config_fingerprint: str,
        score: float = 0.0,
        threshold: float = 0.5,
        strategy_version: str = "1.0.0",
        metrics: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        criteria_evaluations: Optional[Dict[str, bool]] = None,
        reasons: Optional[List[str]] = None,
        experiment_ids: Optional[List[str]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> StrategyGateResult:
        r = list(reasons or ["Evaluation pending additional empirical evidence."])
        crit = criteria_evaluations if criteria_evaluations is not None else {"evidence_sufficient": False}
        return cls(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            status=GateStatus.PENDING,
            score=score,
            threshold=threshold,
            metrics=metrics or {},
            thresholds=thresholds or {},
            criteria_evaluations=crit,
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            experiment_ids=experiment_ids or [],
            reasons=r,
            falsification_evidence=None,
            diagnostics=diagnostics or {},
        )


# ============================================================================
# Gate A: Latency Sensitivity Gate
# ============================================================================

class LatencySensitivityGate:
    """Evaluates strategy vulnerability to order submission and execution delays."""

    def __init__(
        self,
        max_sharpe_drop_pct_at_5s: float = 0.50,
        min_edge_half_life_s: float = 5.0,
        observed_p50_latency_ms: float = 50.0,
        observed_p95_latency_ms: float = 250.0,
        observed_p99_latency_ms: float = 1000.0,
        latency_safety_margin_multiplier: float = 2.0,
    ):
        self.max_sharpe_drop_pct_at_5s = max_sharpe_drop_pct_at_5s
        self.min_edge_half_life_s = min_edge_half_life_s
        self.observed_p50_latency_ms = observed_p50_latency_ms
        self.observed_p95_latency_ms = observed_p95_latency_ms
        self.observed_p99_latency_ms = observed_p99_latency_ms
        self.latency_safety_margin_multiplier = latency_safety_margin_multiplier

    def evaluate(
        self,
        sharpes_by_delay: Dict[float, float],
        strategy_id: str = "STR-CANDIDATE",
        strategy_version: str = "1.0.0",
        dataset_fingerprint: str = "",
        config_fingerprint: str = "",
        experiment_ids: Optional[List[str]] = None,
        observed_p99_latency_ms: Optional[float] = None,
    ) -> StrategyGateResult:
        gate_name = "Gate A: Latency Sensitivity"
        gate_type = "LATENCY_SENSITIVITY"
        ds_fp = dataset_fingerprint or "PROVENANCE_MISSING"
        cfg_fp = config_fingerprint or "PROVENANCE_MISSING"

        p99_ms = observed_p99_latency_ms or self.observed_p99_latency_ms
        operational_latency_budget_s = (p99_ms / 1000.0) * self.latency_safety_margin_multiplier
        effective_min_half_life_s = max(self.min_edge_half_life_s, operational_latency_budget_s)

        s0 = sharpes_by_delay.get(0.0)
        s5 = sharpes_by_delay.get(5.0)

        if s0 is None or math.isnan(s0) or math.isinf(s0) or s0 <= 0.0:
            evidence = "Strategy has no positive baseline Sharpe at 0s delay."
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.max_sharpe_drop_pct_at_5s,
                metrics={"baseline_sharpe_0s": float(s0) if s0 is not None and not math.isnan(s0) else 0.0},
                thresholds={"max_sharpe_drop_pct_at_5s": self.max_sharpe_drop_pct_at_5s},
                reasons=["Non-positive, non-finite, or missing 0s baseline Sharpe."],
                falsification_evidence=evidence,
                experiment_ids=experiment_ids or [],
                diagnostics={"sharpes_by_delay": sharpes_by_delay},
            )

        decay_curve: Dict[str, float] = {}
        sorted_delays = sorted(sharpes_by_delay.keys())
        for d in sorted_delays:
            val = sharpes_by_delay[d]
            decay_curve[f"{d}s"] = (val / s0) if not math.isnan(val) else 0.0

        if s5 is not None and not math.isnan(s5):
            drop_5s = max(0.0, 1.0 - (s5 / s0))
        else:
            drop_5s = 1.0

        half_life_s = float("inf")
        for d in sorted_delays:
            if d > 0.0 and sharpes_by_delay[d] <= 0.50 * s0:
                half_life_s = d
                break

        is_latency_race = (half_life_s < effective_min_half_life_s) or (drop_5s > self.max_sharpe_drop_pct_at_5s)
        classification = "LATENCY_RACE" if is_latency_race else "ROBUST_EXECUTION"

        diagnostics = {
            "decay_curve": decay_curve,
            "sharpe_drop_pct_at_5s": drop_5s,
            "edge_half_life_s": half_life_s if math.isfinite(half_life_s) else 999.0,
            "is_latency_race": is_latency_race,
            "classification": classification,
            "observed_p99_latency_ms": p99_ms,
            "operational_latency_budget_s": operational_latency_budget_s,
            "effective_min_half_life_s": effective_min_half_life_s,
        }
        metrics = {
            "baseline_sharpe_0s": s0,
            "sharpe_5s": s5 if s5 is not None else 0.0,
            "sharpe_drop_pct_at_5s": drop_5s,
            "edge_half_life_s": min(half_life_s, 999.0),
            "operational_budget_s": operational_latency_budget_s,
        }
        thresholds = {
            "max_sharpe_drop_pct_at_5s": self.max_sharpe_drop_pct_at_5s,
            "min_edge_half_life_s": effective_min_half_life_s,
        }
        criteria = {
            "drop_at_5s_acceptable": drop_5s <= self.max_sharpe_drop_pct_at_5s,
            "edge_half_life_sufficient": half_life_s >= effective_min_half_life_s,
            "not_latency_race": not is_latency_race,
        }

        if is_latency_race:
            reasons = [
                f"Strategy edge degrades too quickly with latency (drop at 5s: {drop_5s:.1%} > {self.max_sharpe_drop_pct_at_5s:.1%}, "
                f"half-life: {half_life_s:.1f}s < required {effective_min_half_life_s:.1f}s). Classified as LATENCY_RACE."
            ]
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=1.0 - drop_5s,
                threshold=1.0 - self.max_sharpe_drop_pct_at_5s,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                experiment_ids=experiment_ids or [],
                reasons=reasons,
                falsification_evidence=reasons[0],
                diagnostics=diagnostics,
            )

        if not dataset_fingerprint or not config_fingerprint or ds_fp in FORBIDDEN_PASS_FINGERPRINTS:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=1.0 - drop_5s,
                threshold=1.0 - self.max_sharpe_drop_pct_at_5s,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                experiment_ids=experiment_ids or [],
                reasons=["Provenance unverified: dataset_fingerprint and config_fingerprint must be specified."],
                diagnostics=diagnostics,
            )

        return StrategyGateResult.create_pass(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            dataset_fingerprint=ds_fp,
            config_fingerprint=cfg_fp,
            criteria_evaluations=criteria,
            score=1.0 - drop_5s,
            threshold=1.0 - self.max_sharpe_drop_pct_at_5s,
            metrics=metrics,
            thresholds=thresholds,
            experiment_ids=experiment_ids or [],
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate B: Temporal Stability & Alpha Decay Gate
# ============================================================================

class TemporalStabilityGate:
    """Evaluates stability of returns across sub-periods and detects alpha decay."""

    def __init__(
        self,
        min_decay_ratio: float = 0.50,
        min_positive_rolling_pct: float = 0.75,
        rolling_window_periods: int = 30,
        max_drawdown_increase_ratio: float = 2.0,
    ):
        self.min_decay_ratio = min_decay_ratio
        self.min_positive_rolling_pct = min_positive_rolling_pct
        self.rolling_window_periods = rolling_window_periods
        self.max_drawdown_increase_ratio = max_drawdown_increase_ratio

    def _compute_sharpe(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        for r in returns:
            if math.isnan(r) or math.isinf(r):
                return 0.0
        mean_r = sum(returns) / len(returns)
        var_r = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std_r = math.sqrt(var_r)
        if std_r <= 1e-12:
            return 0.0
        return (mean_r / std_r) * math.sqrt(365.25 * 24 * 12)

    def evaluate(
        self,
        returns: List[float],
        vol_regimes: Optional[List[str]] = None,
        strategy_id: str = "STR-CANDIDATE",
        strategy_version: str = "1.0.0",
        dataset_fingerprint: str = "",
        config_fingerprint: str = "",
        experiment_ids: Optional[List[str]] = None,
    ) -> StrategyGateResult:
        gate_name = "Gate B: Temporal Stability & Alpha Decay"
        gate_type = "TEMPORAL_STABILITY"
        ds_fp = dataset_fingerprint or "PROVENANCE_MISSING"
        cfg_fp = config_fingerprint or "PROVENANCE_MISSING"
        n = len(returns)

        if n < self.rolling_window_periods * 2:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.min_decay_ratio,
                metrics={"sample_size": float(n)},
                thresholds={"min_decay_ratio": self.min_decay_ratio, "required_min_samples": float(self.rolling_window_periods * 2)},
                experiment_ids=experiment_ids or [],
                reasons=["Insufficient observation history for temporal stability split."],
                diagnostics={"sample_size": n, "required_min": self.rolling_window_periods * 2},
            )

        mid = n // 2
        early_returns = returns[:mid]
        late_returns = returns[mid:]

        sr_early = self._compute_sharpe(early_returns)
        sr_late = self._compute_sharpe(late_returns)

        decay_ratio = (sr_late / sr_early) if sr_early > 0.0 else (1.0 if sr_late >= sr_early else 0.0)

        rolling_sharpes: List[float] = []
        w = self.rolling_window_periods
        for i in range(n - w + 1):
            sub = returns[i : i + w]
            rolling_sharpes.append(self._compute_sharpe(sub))

        pos_count = sum(1 for s in rolling_sharpes if s > 0.0)
        pct_positive = pos_count / len(rolling_sharpes) if rolling_sharpes else 0.0

        is_decaying = decay_ratio < self.min_decay_ratio
        is_unstable = pct_positive < self.min_positive_rolling_pct

        diagnostics = {
            "sharpe_early": sr_early,
            "sharpe_late": sr_late,
            "decay_ratio": decay_ratio,
            "rolling_positive_pct": pct_positive,
            "is_decaying": is_decaying,
            "is_unstable": is_unstable,
            "total_observations": n,
        }
        metrics = {
            "early_sharpe": sr_early,
            "late_sharpe": sr_late,
            "decay_ratio": decay_ratio,
            "rolling_positive_pct": pct_positive,
        }
        thresholds = {
            "min_decay_ratio": self.min_decay_ratio,
            "min_positive_rolling_pct": self.min_positive_rolling_pct,
        }
        criteria = {
            "decay_ratio_acceptable": not is_decaying,
            "rolling_stability_acceptable": not is_unstable,
        }

        failures: List[str] = []
        if is_decaying:
            failures.append(
                f"Alpha decay detected: late-period Sharpe ({sr_late:.2f}) vs early ({sr_early:.2f}) "
                f"yields decay ratio {decay_ratio:.2f} < threshold {self.min_decay_ratio:.2f}."
            )
        if is_unstable:
            failures.append(
                f"Temporal instability detected: rolling {w}-period positive Sharpe percentage "
                f"({pct_positive:.1%}) < required {self.min_positive_rolling_pct:.1%}."
            )

        if failures:
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=decay_ratio,
                threshold=self.min_decay_ratio,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                experiment_ids=experiment_ids or [],
                reasons=failures,
                falsification_evidence=" ".join(failures),
                diagnostics=diagnostics,
            )

        if not dataset_fingerprint or not config_fingerprint or ds_fp in FORBIDDEN_PASS_FINGERPRINTS:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=decay_ratio,
                threshold=self.min_decay_ratio,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                experiment_ids=experiment_ids or [],
                reasons=["Provenance unverified: dataset_fingerprint and config_fingerprint must be specified."],
                diagnostics=diagnostics,
            )

        return StrategyGateResult.create_pass(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            dataset_fingerprint=ds_fp,
            config_fingerprint=cfg_fp,
            criteria_evaluations=criteria,
            score=decay_ratio,
            threshold=self.min_decay_ratio,
            metrics=metrics,
            thresholds=thresholds,
            experiment_ids=experiment_ids or [],
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate C: Multiple Selection Correction Gate
# ============================================================================

def _inv_norm_cdf(p: float) -> float:
    """Acklam's approximation for inverse standard normal CDF (probit)."""
    if p <= 0.0:
        return -8.0
    if p >= 1.0:
        return 8.0

    a = [
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    ]
    b = [
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    ]
    c = [
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    ]
    d = [
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)

    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5])
            * q
            / (
                ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r
                + 1.0
            )
        )

    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(
        ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
    ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


def expected_max_sharpe(n_trials: int, var_sharpe: float = 1.0, euler_mascheroni: float = 0.5772156649) -> float:
    """Bailey & López de Prado (2014) equation (8) expected maximum Sharpe ratio."""
    if n_trials <= 1:
        return 0.0
    p1 = 1.0 - (1.0 / float(n_trials))
    p2 = 1.0 - (1.0 / (float(n_trials) * math.e))
    z1 = _inv_norm_cdf(p1)
    z2 = _inv_norm_cdf(p2)
    sr_0 = math.sqrt(var_sharpe) * (
        (1.0 - euler_mascheroni) * z1 + euler_mascheroni * z2
    )
    return max(0.0, sr_0)


def deflated_sharpe_ratio(
    estimated_sharpe: float,
    n_trials: int,
    sample_length: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    euler_mascheroni: float = 0.5772156649,
) -> float:
    """Bailey & López de Prado (2014) Deflated Sharpe Ratio."""
    if sample_length < 2:
        return 0.0
    if math.isnan(estimated_sharpe) or math.isinf(estimated_sharpe):
        return 0.0
    sr = estimated_sharpe
    e_max = expected_max_sharpe(n_trials=n_trials, euler_mascheroni=euler_mascheroni)
    var_sr = (1.0 - skewness * sr + ((kurtosis - 1.0) / 4.0) * (sr ** 2)) / float(sample_length - 1)
    if var_sr <= 0.0 or math.isnan(var_sr) or math.isinf(var_sr):
        var_sr = 1.0 / float(sample_length - 1)
    sigma_sr = math.sqrt(var_sr)
    dsr_stat = (sr - e_max) / sigma_sr
    dsr_prob = norm_cdf(dsr_stat)
    return max(0.0, min(1.0, dsr_prob))


class MultipleSelectionGate:
    """Applies Bailey & López de Prado Deflated Sharpe Ratio and Benjamini-Hochberg FDR."""

    def __init__(
        self,
        min_dsr: float = 0.95,
        max_adjusted_pvalue: float = 0.05,
        euler_mascheroni: float = 0.5772156649,
    ):
        self.min_dsr = min_dsr
        self.max_adjusted_pvalue = max_adjusted_pvalue
        self.euler_mascheroni = euler_mascheroni

    def expected_max_sharpe(self, n_trials: int, var_sharpe: float = 1.0) -> float:
        return expected_max_sharpe(n_trials, var_sharpe, self.euler_mascheroni)

    def deflated_sharpe_ratio(
        self,
        estimated_sharpe: float,
        n_trials: int,
        sample_length: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
    ) -> float:
        return deflated_sharpe_ratio(
            estimated_sharpe=estimated_sharpe,
            n_trials=n_trials,
            sample_length=sample_length,
            skewness=skewness,
            kurtosis=kurtosis,
            euler_mascheroni=self.euler_mascheroni,
        )

    def evaluate(
        self,
        sharpe_ratio: float,
        trial_count: int,
        sample_length: int = 100,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        strategy_id: str = "STR-CANDIDATE",
        strategy_version: str = "1.0.0",
        dataset_fingerprint: str = "",
        config_fingerprint: str = "",
        experiment_ids: Optional[List[str]] = None,
        multiple_testing_context: Optional[MultipleTestingContext] = None,
        raw_p_value: Optional[float] = None,
        all_raw_p_values: Optional[List[float]] = None,
    ) -> StrategyGateResult:
        gate_name = "Gate C: Multiple Selection Correction"
        gate_type = "MULTIPLE_SELECTION"
        ds_fp = dataset_fingerprint or "PROVENANCE_MISSING"
        cfg_fp = config_fingerprint or "PROVENANCE_MISSING"

        # Check nonfinite distribution moments
        if any(math.isnan(x) or math.isinf(x) for x in (sharpe_ratio, skewness, kurtosis)):
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.min_dsr,
                reasons=["Non-finite input detected (Sharpe, skewness, or kurtosis). Fail-closed."],
                falsification_evidence="Non-finite distribution moments detected.",
            )

        # Minimum provisional floor sample length
        if sample_length < 30:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.min_dsr,
                reasons=[f"Insufficient sample length ({sample_length} < 30 provisional floor)."],
            )

        # Context extraction
        if multiple_testing_context is not None:
            if multiple_testing_context.registry_integrity_status != RegistryIntegrityStatus.HEALTHY:
                return StrategyGateResult.create_pending(
                    strategy_id=strategy_id,
                    strategy_version=strategy_version,
                    gate_type=gate_type,
                    dataset_fingerprint=ds_fp,
                    config_fingerprint=cfg_fp,
                    score=0.0,
                    threshold=self.min_dsr,
                    reasons=[f"Registry integrity status is {multiple_testing_context.registry_integrity_status.value}: GOVERNANCE_BLOCKED."],
                )
            effective_trials = max(trial_count, multiple_testing_context.trial_count, 1)
            candidate_p = raw_p_value if raw_p_value is not None else multiple_testing_context.candidate_raw_p_value
            p_vals = list(multiple_testing_context.raw_p_values)
            if candidate_p is not None and (not p_vals or p_vals[-1] != candidate_p):
                p_vals.append(candidate_p)
            exp_ids = experiment_ids or multiple_testing_context.experiment_ids
        else:
            effective_trials = max(trial_count, 1)
            candidate_p = raw_p_value
            if all_raw_p_values is not None:
                p_vals = list(all_raw_p_values)
            elif candidate_p is not None:
                p_vals = [candidate_p]
            else:
                p_vals = []
            exp_ids = experiment_ids or []

        # DSR evaluation
        dsr = self.deflated_sharpe_ratio(
            estimated_sharpe=sharpe_ratio,
            n_trials=effective_trials,
            sample_length=sample_length,
            skewness=skewness,
            kurtosis=kurtosis,
        )
        e_max = self.expected_max_sharpe(n_trials=effective_trials)
        dsr_pass = (dsr >= self.min_dsr)

        # FDR evaluation
        fdr_computed = False
        q_val = 1.0
        fdr_pass = False
        fdr_reason = None

        if candidate_p is None or len(p_vals) < effective_trials:
            fdr_reason = f"Incomplete raw p-values across {effective_trials} trials ({len(p_vals)} available). FDR cannot be certified."
        else:
            try:
                q_vals, passes = benjamini_hochberg(p_vals, alpha=self.max_adjusted_pvalue)
                # Candidate is the last entry in p_vals
                q_val = q_vals[-1]
                fdr_pass = (q_val <= self.max_adjusted_pvalue)
                fdr_computed = True
            except Exception as e:
                fdr_reason = f"Failed to compute Benjamini-Hochberg FDR: {e}"

        diagnostics = {
            "estimated_sharpe": sharpe_ratio,
            "trial_count": effective_trials,
            "sample_length": sample_length,
            "expected_max_null_sharpe": e_max,
            "deflated_sharpe_ratio": dsr,
            "dsr_pass": dsr_pass,
            "raw_p_value": candidate_p,
            "bh_adjusted_p_value": q_val if fdr_computed else None,
            "fdr_pass": fdr_pass,
            "fdr_computed": fdr_computed,
        }
        metrics = {
            "dsr": dsr,
            "expected_max_null_sharpe": e_max,
            "bh_adjusted_p_value": q_val if fdr_computed else 1.0,
        }
        thresholds = {
            "min_dsr": self.min_dsr,
            "max_adjusted_pvalue": self.max_adjusted_pvalue,
        }
        criteria = {
            "dsr_significant": dsr_pass,
            "fdr_significant": fdr_pass,
        }

        # If FDR cannot be certified, fail-closed to PENDING
        if not fdr_computed:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=dsr,
                threshold=self.min_dsr,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                experiment_ids=exp_ids,
                reasons=[fdr_reason or "FDR pending raw p-values."],
                diagnostics=diagnostics,
            )

        if dsr_pass and fdr_pass:
            if not dataset_fingerprint or not config_fingerprint or ds_fp in FORBIDDEN_PASS_FINGERPRINTS:
                return StrategyGateResult.create_pending(
                    strategy_id=strategy_id,
                    strategy_version=strategy_version,
                    gate_type=gate_type,
                    dataset_fingerprint=ds_fp,
                    config_fingerprint=cfg_fp,
                    score=dsr,
                    threshold=self.min_dsr,
                    metrics=metrics,
                    thresholds=thresholds,
                    criteria_evaluations=criteria,
                    experiment_ids=exp_ids,
                    reasons=["Provenance unverified: dataset_fingerprint and config_fingerprint must be specified."],
                    diagnostics=diagnostics,
                )

            return StrategyGateResult.create_pass(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                criteria_evaluations=criteria,
                score=dsr,
                threshold=self.min_dsr,
                metrics=metrics,
                thresholds=thresholds,
                experiment_ids=exp_ids,
                diagnostics=diagnostics,
            )

        failures = []
        if not dsr_pass:
            failures.append(
                f"Deflated Sharpe Ratio ({dsr:.3f} < {self.min_dsr:.3f}) fails multiple testing correction "
                f"after {effective_trials} historical trials (expected null max: {e_max:.2f})."
            )
        if not fdr_pass:
            failures.append(
                f"Benjamini-Hochberg FDR adjusted p-value ({q_val:.4f} > {self.max_adjusted_pvalue:.4f}) breaches significance threshold."
            )

        return StrategyGateResult.create_fail(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            dataset_fingerprint=ds_fp,
            config_fingerprint=cfg_fp,
            score=dsr,
            threshold=self.min_dsr,
            metrics=metrics,
            thresholds=thresholds,
            criteria_evaluations=criteria,
            experiment_ids=exp_ids,
            reasons=failures,
            falsification_evidence="; ".join(failures),
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate D: Correlation & Capacity Gate
# ============================================================================

class CorrelationCapacityGate:
    """Evaluates strategy correlation to existing portfolio and market capacity constraints."""

    def __init__(
        self,
        max_normal_correlation: float = 0.60,
        max_stress_correlation: float = 0.70,
        max_capacity_volume_pct: float = 0.01,
    ):
        self.max_normal_corr = max_normal_correlation
        self.max_stress_corr = max_stress_correlation
        self.max_capacity_pct = max_capacity_volume_pct

    def _pearson_correlation(self, x: List[float], y: List[float]) -> Optional[float]:
        n = len(x)
        if n != len(y) or n < 10:
            return None
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        var_x = sum((xi - mean_x) ** 2 for xi in x)
        var_y = sum((yi - mean_y) ** 2 for yi in y)
        if var_x <= 1e-14 or var_y <= 1e-14 or math.isnan(var_x) or math.isnan(var_y):
            return None
        cov_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom = math.sqrt(var_x * var_y)
        if denom <= 1e-14 or math.isnan(denom):
            return None
        r = cov_xy / denom
        return max(-1.0, min(1.0, r))

    def evaluate(
        self,
        candidate_returns: List[float],
        active_returns_by_strategy: Dict[str, List[float]],
        avg_5m_volume_usd: float,
        proposed_allocation_usd: float,
        regimes: Optional[List[str]] = None,
        candidate_event_clusters: Optional[List[str]] = None,
        active_event_clusters: Optional[Dict[str, List[str]]] = None,
        strategy_id: str = "STR-CANDIDATE",
        strategy_version: str = "1.0.0",
        dataset_fingerprint: str = "",
        config_fingerprint: str = "",
        experiment_ids: Optional[List[str]] = None,
    ) -> StrategyGateResult:
        gate_name = "Gate D: Correlation & Capacity"
        gate_type = "CORRELATION_CAPACITY"
        ds_fp = dataset_fingerprint or "PROVENANCE_MISSING"
        cfg_fp = config_fingerprint or "PROVENANCE_MISSING"

        # Validate explicit positive finite allocation and volume
        if (
            not isinstance(proposed_allocation_usd, (int, float))
            or not isinstance(avg_5m_volume_usd, (int, float))
            or math.isnan(proposed_allocation_usd)
            or math.isinf(proposed_allocation_usd)
            or math.isnan(avg_5m_volume_usd)
            or math.isinf(avg_5m_volume_usd)
            or proposed_allocation_usd <= 0
            or avg_5m_volume_usd <= 0
        ):
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.max_normal_corr,
                reasons=["avg_5m_volume_usd and proposed_allocation_usd must be explicit positive finite numbers."],
                falsification_evidence="Non-positive or non-finite volume or allocation.",
            )

        n = len(candidate_returns)
        if n < 30:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.max_normal_corr,
                reasons=[f"Insufficient sample length: {n} candidate return observations (< 30)."],
            )

        if regimes is not None and len(regimes) != n:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.max_normal_corr,
                reasons=[f"Regimes length mismatch with candidate return observations ({len(regimes)} vs {n})."],
            )

        capacity_usd = avg_5m_volume_usd * self.max_capacity_pct
        capacity_exceeded = proposed_allocation_usd > capacity_usd

        normal_correlations: Dict[str, float] = {}
        stress_correlations: Dict[str, float] = {}
        max_norm_found = 0.0
        max_stress_found = 0.0

        if active_returns_by_strategy:
            for strat_id, act_rets in active_returns_by_strategy.items():
                if len(act_rets) != n or len(act_rets) < 30:
                    return StrategyGateResult.create_pending(
                        strategy_id=strategy_id,
                        strategy_version=strategy_version,
                        gate_type=gate_type,
                        dataset_fingerprint=ds_fp,
                        config_fingerprint=cfg_fp,
                        score=0.0,
                        threshold=self.max_normal_corr,
                        reasons=[f"Mismatched or insufficient return observations for active strategy '{strat_id}'. ({len(act_rets)} vs {n})"],
                    )

                c_norm = self._pearson_correlation(candidate_returns, act_rets)
                if c_norm is None:
                    return StrategyGateResult.create_pending(
                        strategy_id=strategy_id,
                        strategy_version=strategy_version,
                        gate_type=gate_type,
                        dataset_fingerprint=ds_fp,
                        config_fingerprint=cfg_fp,
                        score=0.0,
                        threshold=self.max_normal_corr,
                        reasons=[f"Normal correlation against {strat_id} cannot be computed (degenerate or zero variance)."],
                    )

                c_stress = c_norm
                if regimes:
                    stress_cand = [candidate_returns[i] for i in range(n) if str(regimes[i]).upper() in ("STRESS", "CRASH")]
                    stress_act = [act_rets[i] for i in range(n) if str(regimes[i]).upper() in ("STRESS", "CRASH")]
                    if stress_cand:
                        if len(stress_cand) < 10:
                            return StrategyGateResult.create_pending(
                                strategy_id=strategy_id,
                                strategy_version=strategy_version,
                                gate_type=gate_type,
                                dataset_fingerprint=ds_fp,
                                config_fingerprint=cfg_fp,
                                score=0.0,
                                threshold=self.max_stress_corr,
                                reasons=["Insufficient stress regime samples (< 10) to evaluate stress correlation."],
                            )
                        c_s = self._pearson_correlation(stress_cand, stress_act)
                        if c_s is None:
                            return StrategyGateResult.create_pending(
                                strategy_id=strategy_id,
                                strategy_version=strategy_version,
                                gate_type=gate_type,
                                dataset_fingerprint=ds_fp,
                                config_fingerprint=cfg_fp,
                                score=0.0,
                                threshold=self.max_stress_corr,
                                reasons=[f"Stress correlation against {strat_id} cannot be computed (degenerate or zero variance)."],
                            )
                        c_stress = c_s
                    else:
                        # Multi-regime check across distinct regime slices
                        for reg in set(regimes):
                            slice_c = [candidate_returns[i] for i in range(n) if regimes[i] == reg]
                            slice_a = [act_rets[i] for i in range(n) if regimes[i] == reg]
                            corr_reg = self._pearson_correlation(slice_c, slice_a)
                            if corr_reg is not None and abs(corr_reg) > max_norm_found:
                                max_norm_found = abs(corr_reg)

                normal_correlations[strat_id] = c_norm
                stress_correlations[strat_id] = c_stress
                max_norm_found = max(max_norm_found, abs(c_norm))
                max_stress_found = max(max_stress_found, abs(c_stress))

        corr_breach_normal = max_norm_found > self.max_normal_corr
        corr_breach_stress = max_stress_found > self.max_stress_corr

        cluster_overlap: List[str] = []
        if active_event_clusters:
            if candidate_event_clusters is None:
                return StrategyGateResult.create_pending(
                    strategy_id=strategy_id,
                    strategy_version=strategy_version,
                    gate_type=gate_type,
                    dataset_fingerprint=ds_fp,
                    config_fingerprint=cfg_fp,
                    score=0.0,
                    threshold=self.max_normal_corr,
                    reasons=["candidate_event_clusters must be provided when active strategies have event clusters."],
                )
            cand_set = set(candidate_event_clusters)
            for s_id, s_clusters in active_event_clusters.items():
                overlap = cand_set.intersection(set(s_clusters))
                if overlap:
                    cluster_overlap.extend([f"{s_id}:{c}" for c in overlap])

        diagnostics = {
            "proposed_allocation_usd": proposed_allocation_usd,
            "market_5m_volume_usd": avg_5m_volume_usd,
            "capacity_ceiling_usd": capacity_usd,
            "capacity_exceeded": capacity_exceeded,
            "max_normal_correlation": max_norm_found,
            "max_stress_correlation": max_stress_found,
            "normal_correlations": normal_correlations,
            "stress_correlations": stress_correlations,
            "cluster_overlaps": cluster_overlap,
        }
        metrics = {
            "max_normal_correlation": max_norm_found,
            "max_stress_correlation": max_stress_found,
            "proposed_allocation_usd": proposed_allocation_usd,
            "capacity_ceiling_usd": capacity_usd,
        }
        thresholds = {
            "max_normal_correlation": self.max_normal_corr,
            "max_stress_correlation": self.max_stress_corr,
            "capacity_ceiling_usd": capacity_usd,
        }

        failures: List[str] = []
        if capacity_exceeded:
            failures.append(
                f"Proposed allocation ${proposed_allocation_usd:,.2f} exceeds 1% 5m volume capacity ${capacity_usd:,.2f}."
            )
        if corr_breach_normal:
            failures.append(
                f"Normal correlation ({max_norm_found:.2f}) breaches threshold ({self.max_normal_corr:.2f})."
            )
        if corr_breach_stress:
            failures.append(
                f"Stress correlation ({max_stress_found:.2f}) breaches threshold ({self.max_stress_corr:.2f})."
            )
        if cluster_overlap:
            failures.append(
                f"Event cluster overlap detected with active strategies: {', '.join(cluster_overlap)}."
            )

        criteria = {
            "capacity_within_limit": not capacity_exceeded,
            "normal_correlation_acceptable": not corr_breach_normal,
            "stress_correlation_acceptable": not corr_breach_stress,
            "no_cluster_overlap": len(cluster_overlap) == 0,
        }

        if failures:
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=max_norm_found,
                threshold=self.max_normal_corr,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                experiment_ids=experiment_ids or [],
                reasons=failures,
                falsification_evidence=" ".join(failures),
                diagnostics=diagnostics,
            )

        if not dataset_fingerprint or not config_fingerprint or ds_fp in FORBIDDEN_PASS_FINGERPRINTS:
            return StrategyGateResult.create_pending(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=max_norm_found,
                threshold=self.max_normal_corr,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                experiment_ids=experiment_ids or [],
                reasons=["Provenance unverified: dataset_fingerprint and config_fingerprint must be specified."],
                diagnostics=diagnostics,
            )

        return StrategyGateResult.create_pass(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            dataset_fingerprint=ds_fp,
            config_fingerprint=cfg_fp,
            criteria_evaluations=criteria,
            score=max_norm_found,
            threshold=self.max_normal_corr,
            metrics=metrics,
            thresholds=thresholds,
            experiment_ids=experiment_ids or [],
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate Orchestrator & Strict Bundle Validator
# ============================================================================

def validate_gate_bundle(
    bundle: Union[Dict[str, StrategyGateResult], List[StrategyGateResult]]
) -> Tuple[bool, List[str]]:
    """
    Strictly validates a 4-gate evidence bundle for portfolio promotion.
    Rules:
    1. Must contain exactly 4 canonical gates (A, B, C, D).
    2. All 4 must have status == GateStatus.PASS.
    3. Exact provenance match: all 4 must share identical strategy_id, strategy_version,
       dataset_fingerprint, and config_fingerprint.
    4. Disallows placeholder fingerprints (ds_prov_unspecified, cfg_prov_unspecified, etc.).
    5. Rejects non-finite metrics, thresholds, or scores.
    """
    reasons: List[str] = []
    if not bundle:
        return False, ["Gate bundle is empty."]

    if isinstance(bundle, dict):
        raw_items = list(bundle.values())
    elif isinstance(bundle, (list, tuple)):
        raw_items = list(bundle)
    else:
        return False, [f"Invalid bundle type: {type(bundle).__name__}"]

    if len(raw_items) != 4:
        return False, [f"Gate bundle must contain exactly 4 gates, found {len(raw_items)}."]

    gate_by_letter: Dict[str, StrategyGateResult] = {}
    for r in raw_items:
        if not isinstance(r, StrategyGateResult):
            return False, [f"Item in bundle is not a StrategyGateResult: {type(r).__name__}"]
        gt = r.gate_type.upper()
        found_letter = None
        for letter, canon_type in CANONICAL_GATE_TYPES.items():
            if canon_type in gt or letter == r.gate_name:
                found_letter = letter
                break
        if not found_letter and r.gate_name and r.gate_name.upper().startswith("GATE "):
            letter_cand = r.gate_name.split()[1][:1].upper()
            if letter_cand in CANONICAL_GATE_TYPES:
                found_letter = letter_cand

        if not found_letter:
            return False, [f"Unrecognized gate type in bundle: {r.gate_type}"]
        if found_letter in gate_by_letter:
            return False, [f"Duplicate gate '{found_letter}' in bundle."]
        gate_by_letter[found_letter] = r

    for letter in ("A", "B", "C", "D"):
        if letter not in gate_by_letter:
            return False, [f"Missing canonical Gate {letter} ({CANONICAL_GATE_TYPES[letter]}) in bundle."]

    first_res = gate_by_letter["A"]
    ref_strat_id = first_res.strategy_id
    ref_version = first_res.strategy_version
    ref_ds_fp = first_res.dataset_fingerprint
    ref_cfg_fp = first_res.config_fingerprint

    for letter, res in gate_by_letter.items():
        if res.status != GateStatus.PASS:
            reasons.append(f"Gate {letter} has status {res.status.value}, expected PASS.")
        if res.strategy_id != ref_strat_id:
            reasons.append(f"Gate {letter} strategy_id '{res.strategy_id}' does not match '{ref_strat_id}'.")
        if res.strategy_version != ref_version:
            reasons.append(f"Gate {letter} strategy_version '{res.strategy_version}' does not match '{ref_version}'.")
        if res.dataset_fingerprint != ref_ds_fp:
            reasons.append(f"Gate {letter} dataset_fingerprint '{res.dataset_fingerprint}' does not match '{ref_ds_fp}'.")
        if res.config_fingerprint != ref_cfg_fp:
            reasons.append(f"Gate {letter} config_fingerprint '{res.config_fingerprint}' does not match '{ref_cfg_fp}'.")

        if res.dataset_fingerprint in FORBIDDEN_PASS_FINGERPRINTS or not res.dataset_fingerprint.strip():
            reasons.append(f"Gate {letter} contains invalid or placeholder dataset_fingerprint: '{res.dataset_fingerprint}'.")
        if res.config_fingerprint in FORBIDDEN_PASS_FINGERPRINTS or not res.config_fingerprint.strip():
            reasons.append(f"Gate {letter} contains invalid or placeholder config_fingerprint: '{res.config_fingerprint}'.")

        if math.isnan(res.score) or math.isinf(res.score):
            reasons.append(f"Gate {letter} score is non-finite: {res.score}")
        if math.isnan(res.threshold) or math.isinf(res.threshold):
            reasons.append(f"Gate {letter} threshold is non-finite: {res.threshold}")
        for m_name, m_val in res.metrics.items():
            if isinstance(m_val, (int, float)) and (math.isnan(m_val) or math.isinf(m_val)):
                reasons.append(f"Gate {letter} metric '{m_name}' is non-finite: {m_val}")
        for t_name, t_val in res.thresholds.items():
            if isinstance(t_val, (int, float)) and (math.isnan(t_val) or math.isinf(t_val)):
                reasons.append(f"Gate {letter} threshold '{t_name}' is non-finite: {t_val}")

    if reasons:
        return False, reasons
    return True, []


def all_gates_pass(gate_results: Union[Dict[str, StrategyGateResult], List[StrategyGateResult]]) -> bool:
    """Thin strict wrapper over validate_gate_bundle."""
    is_valid, _ = validate_gate_bundle(gate_results)
    return is_valid
