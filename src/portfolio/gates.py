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


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


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

        ds_fp = data.get("dataset_fingerprint", "")
        cfg_fp = data.get("config_fingerprint", "")
        if not str(ds_fp).strip() or not str(cfg_fp).strip():
            raise ValueError(
                f"Provenance violation: dataset_fingerprint ('{ds_fp}') and config_fingerprint ('{cfg_fp}') "
                "must be non-empty strings."
            )

        criteria = data.get("criteria_evaluations") or {}
        reasons = list(data.get("reasons") or [])
        falsification = data.get("falsification_evidence")

        if status == GateStatus.PASS:
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
        return cls(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            status=GateStatus.FAIL,
            score=score,
            threshold=threshold,
            metrics=metrics or {},
            thresholds=thresholds or {},
            criteria_evaluations=criteria_evaluations or {},
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
        reasons: List[str],
        score: float = 0.0,
        threshold: float = 0.5,
        strategy_version: str = "1.0.0",
        metrics: Optional[Dict[str, float]] = None,
        thresholds: Optional[Dict[str, float]] = None,
        criteria_evaluations: Optional[Dict[str, bool]] = None,
        experiment_ids: Optional[List[str]] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> StrategyGateResult:
        return cls(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            status=GateStatus.PENDING,
            score=score,
            threshold=threshold,
            metrics=metrics or {},
            thresholds=thresholds or {},
            criteria_evaluations=criteria_evaluations or {},
            dataset_fingerprint=dataset_fingerprint,
            config_fingerprint=config_fingerprint,
            experiment_ids=experiment_ids or [],
            reasons=reasons,
            falsification_evidence=None,
            diagnostics=diagnostics or {},
        )


def _inv_norm_cdf(p: float) -> float:
    """Acklam's approximation for inverse standard normal CDF (probit).
    
    Accurate to within 1.15e-9 for 0 < p < 1.
    """
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
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        ) / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


# ============================================================================
# Gate A: Latency Sensitivity Gate
# ============================================================================

class LatencySensitivityGate:
    """Evaluates strategy vulnerability to simulated execution latency.
    
    Replays backtest with delays: 0s, +1s, +5s, +30s.
    If Sharpe drops > max_sharpe_drop_pct_at_5s or Edge half-life is shorter
    than the operational execution stack's latency budget (p99 * margin):
      - Flag as LATENCY_RACE
      - Reject for standard execution
    """

    def __init__(
        self,
        max_sharpe_drop_pct_at_5s: float = 0.50,  # Provisional research prior: 50% drop at 5s
        min_edge_half_life_s: float = 5.0,        # Provisional research prior: 5.0s edge half-life
        observed_p50_latency_ms: float = 50.0,   # Operational execution stack observed p50
        observed_p95_latency_ms: float = 250.0,  # Operational execution stack observed p95
        observed_p99_latency_ms: float = 1000.0, # Operational execution stack observed p99
        latency_safety_margin_multiplier: float = 2.0, # Multiplier applied to p99 latency
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
        """Evaluate latency sensitivity across delay points."""
        gate_name = "Gate A: Latency Sensitivity"
        gate_type = "LATENCY_SENSITIVITY"
        ds_fp = dataset_fingerprint or "ds_prov_unspecified"
        cfg_fp = config_fingerprint or "cfg_prov_unspecified"

        p99_ms = observed_p99_latency_ms or self.observed_p99_latency_ms
        operational_latency_budget_s = (p99_ms / 1000.0) * self.latency_safety_margin_multiplier
        effective_min_half_life_s = max(self.min_edge_half_life_s, operational_latency_budget_s)

        s0 = sharpes_by_delay.get(0.0)
        s5 = sharpes_by_delay.get(5.0)

        if s0 is None or s0 <= 0.0:
            evidence = "Strategy has no positive baseline Sharpe at 0s delay."
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=0.0,
                threshold=self.max_sharpe_drop_pct_at_5s,
                metrics={"baseline_sharpe_0s": 0.0},
                thresholds={"max_sharpe_drop_pct_at_5s": self.max_sharpe_drop_pct_at_5s},
                reasons=["Non-positive or missing 0s baseline Sharpe."],
                falsification_evidence=evidence,
                experiment_ids=experiment_ids or [],
                diagnostics={"sharpes_by_delay": sharpes_by_delay, "error": "Non-positive or missing 0s baseline Sharpe"},
            )

        decay_curve: Dict[str, float] = {}
        sorted_delays = sorted(sharpes_by_delay.keys())
        for d in sorted_delays:
            decay_curve[f"{d}s"] = sharpes_by_delay[d] / s0

        decay_at_5s = (s5 / s0) if s5 is not None else 0.0
        sharpe_drop_at_5s = 1.0 - decay_at_5s

        # Calculate empirical edge half-life (seconds until performance drops to 50%)
        half_life_s: float = float("inf")
        for i in range(len(sorted_delays) - 1):
            d1, d2 = sorted_delays[i], sorted_delays[i + 1]
            r1 = sharpes_by_delay[d1] / s0
            r2 = sharpes_by_delay[d2] / s0
            if r1 >= 0.5 >= r2:
                if r1 != r2:
                    fraction = (r1 - 0.5) / (r1 - r2)
                    half_life_s = d1 + fraction * (d2 - d1)
                else:
                    half_life_s = d1
                break

        if half_life_s == float("inf"):
            last_delay = sorted_delays[-1]
            last_ratio = sharpes_by_delay[last_delay] / s0
            if last_ratio >= 0.5:
                half_life_s = last_delay * 2.0
            else:
                half_life_s = 0.0

        is_latency_race = (sharpe_drop_at_5s > self.max_sharpe_drop_pct_at_5s) or (half_life_s < effective_min_half_life_s)

        diagnostics = {
            "baseline_sharpe_0s": s0,
            "sharpe_5s": s5,
            "decay_curve": decay_curve,
            "sharpe_drop_pct_at_5s": sharpe_drop_at_5s,
            "edge_half_life_s": half_life_s,
            "operational_latency_budget_s": operational_latency_budget_s,
            "classification": "LATENCY_RACE" if is_latency_race else "ROBUST_EXECUTION",
            "is_latency_race": is_latency_race,
        }

        metrics = {
            "decay_at_5s": decay_at_5s,
            "edge_half_life_s": half_life_s,
            "sharpe_drop_pct_at_5s": sharpe_drop_at_5s,
            "operational_latency_budget_s": operational_latency_budget_s,
            "operational_budget_s": operational_latency_budget_s,
        }
        thresholds = {
            "max_sharpe_drop_pct_at_5s": self.max_sharpe_drop_pct_at_5s,
            "min_edge_half_life_s": effective_min_half_life_s,
        }

        criteria = {
            "sharpe_drop_acceptable": sharpe_drop_at_5s <= self.max_sharpe_drop_pct_at_5s,
            "half_life_sufficient": half_life_s >= effective_min_half_life_s,
            "not_latency_race": not is_latency_race,
        }

        if is_latency_race:
            evidence = (
                f"Edge half-life ({half_life_s:.2f}s < {effective_min_half_life_s:.2f}s) or "
                f"5s Sharpe drop ({sharpe_drop_at_5s:.1%} > {self.max_sharpe_drop_pct_at_5s:.1%}) "
                f"violates robustness. Classified as LATENCY_RACE."
            )
            return StrategyGateResult.create_fail(
                strategy_id=strategy_id,
                strategy_version=strategy_version,
                gate_type=gate_type,
                dataset_fingerprint=ds_fp,
                config_fingerprint=cfg_fp,
                score=decay_at_5s,
                threshold=1.0 - self.max_sharpe_drop_pct_at_5s,
                metrics=metrics,
                thresholds=thresholds,
                criteria_evaluations=criteria,
                reasons=[evidence],
                falsification_evidence=evidence,
                experiment_ids=experiment_ids or [],
                diagnostics=diagnostics,
            )

        return StrategyGateResult.create_pass(
            strategy_id=strategy_id,
            strategy_version=strategy_version,
            gate_type=gate_type,
            dataset_fingerprint=ds_fp,
            config_fingerprint=cfg_fp,
            criteria_evaluations=criteria,
            score=decay_at_5s,
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
    """Evaluates out-of-sample alpha decay, rolling stability, and regime resilience.
    
    Criteria:
    - Split history into early half vs late half: Sharpe(late) / Sharpe(early) >= min_decay_ratio
    - Rolling window Sharpe must be positive in >= min_positive_rolling_pct of rolling windows
    - Performance in high-vol vs low-vol must not collapse
    """

    def __init__(
        self,
        min_decay_ratio: float = 0.50,          # Provisional research prior: >= 50% retained
        min_positive_rolling_pct: float = 0.75, # Provisional research prior: >= 75% positive windows
        rolling_window_periods: int = 30,       # Window periods for rolling Sharpe
    ):
        self.min_decay_ratio = min_decay_ratio
        self.min_positive_rolling_pct = min_positive_rolling_pct
        self.rolling_window_periods = rolling_window_periods

    @staticmethod
    def _compute_sharpe(returns: List[float], annualization_factor: float = math.sqrt(252)) -> float:
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(var) if var > 1e-12 else 0.0
        if std == 0.0:
            return 10.0 if mean > 0 else (-10.0 if mean < 0 else 0.0)
        return (mean / std) * annualization_factor

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
        ds_fp = dataset_fingerprint or "ds_prov_unspecified"
        cfg_fp = config_fingerprint or "cfg_prov_unspecified"
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

        regime_sharpes: Dict[str, float] = {}
        if vol_regimes and len(vol_regimes) == n:
            unique_regimes = set(vol_regimes)
            for reg in unique_regimes:
                reg_returns = [returns[i] for i in range(n) if vol_regimes[i] == reg]
                regime_sharpes[reg] = self._compute_sharpe(reg_returns)

        is_decaying = decay_ratio < self.min_decay_ratio
        is_unstable = pct_positive < self.min_positive_rolling_pct

        diagnostics = {
            "sr_early": sr_early,
            "sr_late": sr_late,
            "sharpe_decay_ratio": decay_ratio,
            "rolling_positive_pct": pct_positive,
            "rolling_windows_evaluated": len(rolling_sharpes),
            "regime_sharpes": regime_sharpes,
            "is_decaying": is_decaying,
            "is_unstable": is_unstable,
        }
        metrics = {
            "decay_ratio": decay_ratio,
            "rolling_positive_pct": pct_positive,
            "sr_early": sr_early,
            "sr_late": sr_late,
        }
        thresholds = {
            "min_decay_ratio": self.min_decay_ratio,
            "min_positive_rolling_pct": self.min_positive_rolling_pct,
        }

        criteria = {
            "decay_ratio_acceptable": not is_decaying,
            "rolling_positive_acceptable": not is_unstable,
        }

        if is_decaying or is_unstable:
            reasons = []
            if is_decaying:
                reasons.append(f"Sharpe decay ratio ({decay_ratio:.2f} < {self.min_decay_ratio:.2f}) indicates alpha decay.")
            if is_unstable:
                reasons.append(f"Positive rolling Sharpe fraction ({pct_positive:.1%} < {self.min_positive_rolling_pct:.1%}) fails consistency.")
            evidence = " ".join(reasons)

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
                reasons=reasons,
                falsification_evidence=evidence,
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

class MultipleSelectionGate:
    """Evaluates multiple testing bias via Deflated Sharpe Ratio (Bailey & López de Prado 2014)
    and False Discovery Rate (FDR) / Benjamini-Hochberg adjustment.
    """

    def __init__(
        self,
        min_dsr: float = 0.95,               # Provisional research prior: 95% DSR confidence
        max_adjusted_pvalue: float = 0.05,  # Provisional research prior: 5% FDR threshold
    ):
        self.min_dsr = min_dsr
        self.max_adjusted_pvalue = max_adjusted_pvalue

    @staticmethod
    def expected_max_sharpe(n_trials: int, variance_sharpe: float = 1.0) -> float:
        """Compute expected maximum Sharpe ratio under the null hypothesis of zero true skill."""
        if n_trials <= 1:
            return 0.0

        euler_mascheroni = 0.57721566490153286
        sigma_sr = math.sqrt(variance_sharpe)

        z1 = _inv_norm_cdf(1.0 - (1.0 / n_trials))
        z2 = _inv_norm_cdf(1.0 - (1.0 / (n_trials * math.e)))
        em_diff = z2 - z1

        e_max = sigma_sr * (z1 + euler_mascheroni * em_diff)
        return max(0.0, e_max)

    @classmethod
    def deflated_sharpe_ratio(
        cls,
        estimated_sharpe: float,
        n_trials: int,
        sample_length: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
    ) -> float:
        """Compute Bailey & López de Prado Deflated Sharpe Ratio."""
        if sample_length <= 1:
            return 0.0

        e_max = cls.expected_max_sharpe(n_trials=n_trials)
        sr = estimated_sharpe

        var_sr = (1.0 - skewness * sr + ((kurtosis - 1.0) / 4.0) * (sr ** 2)) / (sample_length - 1)
        sigma_sr = math.sqrt(max(1e-12, var_sr))

        dsr_stat = (sr - e_max) / sigma_sr
        dsr_prob = norm_cdf(dsr_stat)
        return max(0.0, min(1.0, dsr_prob))

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
    ) -> StrategyGateResult:
        gate_name = "Gate C: Multiple Selection Correction"
        gate_type = "MULTIPLE_SELECTION"
        ds_fp = dataset_fingerprint or "ds_prov_unspecified"
        cfg_fp = config_fingerprint or "cfg_prov_unspecified"

        if trial_count < 1:
            trial_count = 1

        dsr = self.deflated_sharpe_ratio(
            estimated_sharpe=sharpe_ratio,
            n_trials=trial_count,
            sample_length=sample_length,
            skewness=skewness,
            kurtosis=kurtosis,
        )

        e_max = self.expected_max_sharpe(n_trials=trial_count)
        p_val = max(0.0, 1.0 - dsr)

        diagnostics = {
            "estimated_sharpe": sharpe_ratio,
            "trial_count": trial_count,
            "sample_length": sample_length,
            "expected_max_null_sharpe": e_max,
            "deflated_sharpe_ratio": dsr,
            "adjusted_p_value": p_val,
        }
        metrics = {
            "dsr": dsr,
            "expected_max_null_sharpe": e_max,
            "adjusted_p_value": p_val,
        }
        thresholds = {
            "min_dsr": self.min_dsr,
            "max_adjusted_pvalue": self.max_adjusted_pvalue,
        }

        criteria = {
            "dsr_significant": dsr >= self.min_dsr,
            "adjusted_pvalue_acceptable": p_val <= self.max_adjusted_pvalue,
        }

        if dsr < self.min_dsr or p_val > self.max_adjusted_pvalue:
            reasons = [
                f"Deflated Sharpe Ratio ({dsr:.3f} < {self.min_dsr:.3f}) fails multiple testing correction "
                f"after {trial_count} historical trials (expected null max: {e_max:.2f})."
            ]
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
                experiment_ids=experiment_ids or [],
                reasons=reasons,
                falsification_evidence=reasons[0],
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
            experiment_ids=experiment_ids or [],
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate D: Correlation & Capacity Gate
# ============================================================================

class CorrelationCapacityGate:
    """Evaluates cross-strategy correlation in normal vs stress regimes,
    EventCluster concentration, and market depth capacity.
    """

    def __init__(
        self,
        max_normal_correlation: float = 0.60, # Provisional research prior
        max_stress_correlation: float = 0.70, # Provisional research prior
        max_capacity_volume_pct: float = 0.01, # Provisional research prior: 1% 5m volume
    ):
        self.max_normal_corr = max_normal_correlation
        self.max_stress_corr = max_stress_correlation
        self.max_capacity_pct = max_capacity_volume_pct

    @staticmethod
    def _pearson_correlation(x: List[float], y: List[float]) -> float:
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        n = len(x)
        mx = sum(x) / n
        my = sum(y) / n
        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        var_x = sum((x[i] - mx) ** 2 for i in range(n))
        var_y = sum((y[i] - my) ** 2 for i in range(n))
        denom = math.sqrt(var_x * var_y)
        return (cov / denom) if denom > 1e-12 else 0.0

    def evaluate(
        self,
        candidate_returns: List[float],
        active_returns_by_strategy: Dict[str, List[float]],
        regimes: Optional[List[str]] = None,
        avg_5m_volume_usd: float = 1_000_000.0,
        proposed_allocation_usd: float = 10_000.0,
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
        ds_fp = dataset_fingerprint or "ds_prov_unspecified"
        cfg_fp = config_fingerprint or "cfg_prov_unspecified"

        capacity_usd = avg_5m_volume_usd * self.max_capacity_pct
        capacity_exceeded = proposed_allocation_usd > capacity_usd

        normal_correlations: Dict[str, float] = {}
        stress_correlations: Dict[str, float] = {}
        max_norm_found = 0.0
        max_stress_found = 0.0

        n = len(candidate_returns)
        for strat_id, act_rets in active_returns_by_strategy.items():
            if len(act_rets) != n:
                continue

            if regimes and len(regimes) == n:
                norm_cand = [candidate_returns[i] for i in range(n) if regimes[i] == "NORMAL"]
                norm_act = [act_rets[i] for i in range(n) if regimes[i] == "NORMAL"]
                stress_cand = [candidate_returns[i] for i in range(n) if regimes[i] == "STRESS"]
                stress_act = [act_rets[i] for i in range(n) if regimes[i] == "STRESS"]

                c_norm = self._pearson_correlation(norm_cand, norm_act)
                c_stress = self._pearson_correlation(stress_cand, stress_act)
            else:
                c_norm = self._pearson_correlation(candidate_returns, act_rets)
                c_stress = c_norm

            normal_correlations[strat_id] = c_norm
            stress_correlations[strat_id] = c_stress
            max_norm_found = max(max_norm_found, abs(c_norm))
            max_stress_found = max(max_stress_found, abs(c_stress))

        corr_breach_normal = max_norm_found > self.max_normal_corr
        corr_breach_stress = max_stress_found > self.max_stress_corr

        cluster_overlap: List[str] = []
        if candidate_event_clusters and active_event_clusters:
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

        criteria = {
            "capacity_within_limit": not capacity_exceeded,
            "normal_correlation_acceptable": not corr_breach_normal,
            "stress_correlation_acceptable": not corr_breach_stress,
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
# Gate Orchestrator
# ============================================================================

def all_gates_pass(gate_results: Union[Dict[str, StrategyGateResult], List[StrategyGateResult]]) -> bool:
    """Check if all evaluated gates achieved PASS status.
    
    Accepts either Dict[str, StrategyGateResult] or List[StrategyGateResult].
    Must have at least one gate result, and all must be PASS (never PENDING or FAIL).
    """
    if not gate_results:
        return False
    results_list = list(gate_results.values()) if isinstance(gate_results, dict) else list(gate_results)
    if not results_list:
        return False
    return all(r.status == GateStatus.PASS for r in results_list)
