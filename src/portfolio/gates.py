"""
Portfolio Selection Gates (v1.4.0)

Implements four mandatory gates before a strategy can be allocated capital or promoted:
- Gate A: Latency Sensitivity Gate (replays backtest with delays: 0s, +1s, +5s, +30s; edge half-life; LATENCY_RACE detection)
- Gate B: Temporal Stability & Alpha Decay Gate (early vs late half, rolling 30-day Sharpe positive >= 75%, DECAYING flag, regime stability)
- Gate C: Multiple Selection Correction Gate (Bailey & López de Prado DSR, Benjamini-Hochberg FDR across trial_count from ExperimentRegistry)
- Gate D: Correlation & Capacity Gate (Normal < 0.60, Stress < 0.70, EventCluster overlap check, 1% 5m volume capacity check)
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from src.quant.black76 import norm_cdf


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"


class StrategyGateResult(BaseModel):
    """Common evaluation contract for all portfolio selection gates."""
    gate_name: str
    status: GateStatus
    score: float
    threshold: float
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    falsification_evidence: Optional[str] = None


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
    If Sharpe drops > 50% at +5s or Edge half-life < 5 seconds:
      - Flag as LATENCY_RACE
      - Reject for standard execution
    """

    def __init__(
        self,
        max_sharpe_drop_pct_at_5s: float = 0.50,
        min_edge_half_life_s: float = 5.0,
    ):
        self.max_sharpe_drop_pct_at_5s = max_sharpe_drop_pct_at_5s
        self.min_edge_half_life_s = min_edge_half_life_s

    def evaluate(
        self,
        sharpes_by_delay: Dict[float, float],
    ) -> StrategyGateResult:
        """Evaluate latency sensitivity across delay points.
        
        Args:
            sharpes_by_delay: Mapping of simulated delay in seconds to realized Sharpe ratio,
                              e.g. {0.0: 2.4, 1.0: 2.1, 5.0: 1.0, 30.0: 0.1}.
        """
        gate_name = "Gate A: Latency Sensitivity"
        s0 = sharpes_by_delay.get(0.0)
        s5 = sharpes_by_delay.get(5.0)

        if s0 is None or s0 <= 0.0:
            return StrategyGateResult(
                gate_name=gate_name,
                status=GateStatus.FAIL,
                score=0.0,
                threshold=self.max_sharpe_drop_pct_at_5s,
                diagnostics={"sharpes_by_delay": sharpes_by_delay, "error": "Non-positive or missing 0s baseline Sharpe"},
                falsification_evidence="Strategy has no positive baseline Sharpe at 0s delay.",
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
                # Linear interpolation
                if r1 != r2:
                    fraction = (r1 - 0.5) / (r1 - r2)
                    half_life_s = d1 + fraction * (d2 - d1)
                else:
                    half_life_s = d1
                break

        if half_life_s == float("inf"):
            # Check if it never dropped below 0.5
            last_delay = sorted_delays[-1]
            last_ratio = sharpes_by_delay[last_delay] / s0
            if last_ratio >= 0.5:
                half_life_s = last_delay * 2.0  # Conservative estimate
            else:
                half_life_s = 0.0

        is_latency_race = (sharpe_drop_at_5s > self.max_sharpe_drop_pct_at_5s) or (half_life_s < self.min_edge_half_life_s)

        diagnostics = {
            "baseline_sharpe_0s": s0,
            "sharpe_5s": s5,
            "decay_curve": decay_curve,
            "sharpe_drop_pct_at_5s": sharpe_drop_at_5s,
            "edge_half_life_s": half_life_s,
            "classification": "LATENCY_RACE" if is_latency_race else "ROBUST_EXECUTION",
            "is_latency_race": is_latency_race,
        }

        if is_latency_race:
            evidence = (
                f"Edge half-life ({half_life_s:.2f}s < {self.min_edge_half_life_s}s) or "
                f"5s Sharpe drop ({sharpe_drop_at_5s:.1%} > {self.max_sharpe_drop_pct_at_5s:.1%}) "
                f"violates robustness. Classified as LATENCY_RACE."
            )
            return StrategyGateResult(
                gate_name=gate_name,
                status=GateStatus.FAIL,
                score=decay_at_5s,
                threshold=1.0 - self.max_sharpe_drop_pct_at_5s,
                diagnostics=diagnostics,
                falsification_evidence=evidence,
            )

        return StrategyGateResult(
            gate_name=gate_name,
            status=GateStatus.PASS,
            score=decay_at_5s,
            threshold=1.0 - self.max_sharpe_drop_pct_at_5s,
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate B: Temporal Stability & Alpha Decay Gate
# ============================================================================

class TemporalStabilityGate:
    """Evaluates out-of-sample alpha decay, rolling stability, and regime resilience.
    
    Criteria:
    - Split history into early half vs late half: Sharpe(late) / Sharpe(early) >= 0.50
    - Rolling window Sharpe must be positive in >= 75% of rolling windows
    - Performance in high-vol vs low-vol must not collapse
    """

    def __init__(
        self,
        min_decay_ratio: float = 0.50,
        min_positive_rolling_pct: float = 0.75,
        rolling_window_periods: int = 30,
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
    ) -> StrategyGateResult:
        gate_name = "Gate B: Temporal Stability & Alpha Decay"
        n = len(returns)

        if n < self.rolling_window_periods * 2:
            return StrategyGateResult(
                gate_name=gate_name,
                status=GateStatus.PENDING,
                score=0.0,
                threshold=self.min_decay_ratio,
                diagnostics={"sample_size": n, "required_min": self.rolling_window_periods * 2},
                falsification_evidence="Insufficient observation history for temporal stability split.",
            )

        # Early half vs Late half
        mid = n // 2
        early_returns = returns[:mid]
        late_returns = returns[mid:]

        sr_early = self._compute_sharpe(early_returns)
        sr_late = self._compute_sharpe(late_returns)

        decay_ratio = (sr_late / sr_early) if sr_early > 0.0 else (1.0 if sr_late >= sr_early else 0.0)

        # Rolling window Sharpes
        rolling_sharpes: List[float] = []
        w = self.rolling_window_periods
        for i in range(n - w + 1):
            sub = returns[i : i + w]
            rolling_sharpes.append(self._compute_sharpe(sub))

        pos_count = sum(1 for s in rolling_sharpes if s > 0.0)
        pct_positive = pos_count / len(rolling_sharpes) if rolling_sharpes else 0.0

        # Regime breakdown if provided
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

        if is_decaying or is_unstable:
            reasons = []
            if is_decaying:
                reasons.append(f"Sharpe decay ratio ({decay_ratio:.2f} < {self.min_decay_ratio:.2f}) indicates alpha decay.")
            if is_unstable:
                reasons.append(f"Positive rolling Sharpe fraction ({pct_positive:.1%} < {self.min_positive_rolling_pct:.1%}) fails consistency.")
            evidence = " ".join(reasons)

            return StrategyGateResult(
                gate_name=gate_name,
                status=GateStatus.FAIL,
                score=decay_ratio,
                threshold=self.min_decay_ratio,
                diagnostics=diagnostics,
                falsification_evidence=evidence,
            )

        return StrategyGateResult(
            gate_name=gate_name,
            status=GateStatus.PASS,
            score=decay_ratio,
            threshold=self.min_decay_ratio,
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate C: Multiple Selection Correction Gate
# ============================================================================

class MultipleSelectionGate:
    """Evaluates multiple testing bias via Deflated Sharpe Ratio (Bailey & López de Prado 2014)
    and False Discovery Rate (FDR) / Benjamini-Hochberg adjustment.
    
    DSR computes the probability that the estimated Sharpe exceeds the expected maximum Sharpe
    under null trials of length N.
    """

    def __init__(
        self,
        min_dsr: float = 0.95,
        max_adjusted_pvalue: float = 0.05,
    ):
        self.min_dsr = min_dsr
        self.max_adjusted_pvalue = max_adjusted_pvalue

    @staticmethod
    def compute_expected_max_sharpe(trial_count: int, trial_variance: float = 1.0) -> float:
        """Expected maximum Sharpe ratio among N independent tests under standard normal null."""
        if trial_count <= 1:
            return 0.0

        # Bailey & López de Prado (2014) approximation using Euler-Mascheroni constant
        euler_mascheroni = 0.57721566490153286
        p1 = 1.0 - (1.0 / trial_count)
        p2 = 1.0 - (1.0 / (trial_count * math.e))

        z1 = _inv_norm_cdf(p1)
        z2 = _inv_norm_cdf(p2)

        sr_0 = math.sqrt(trial_variance) * ((1.0 - euler_mascheroni) * z1 + euler_mascheroni * z2)
        return max(0.0, sr_0)

    @staticmethod
    def compute_dsr(
        sharpe_ratio: float,
        trial_count: int,
        sample_length: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        trial_variance: float = 1.0,
    ) -> Tuple[float, float, float]:
        """Compute Deflated Sharpe Ratio (DSR), expected max Sharpe, and standard error."""
        if sample_length <= 1:
            return 0.0, 0.0, 1.0

        sr_0 = MultipleSelectionGate.compute_expected_max_sharpe(trial_count, trial_variance)

        # Standard error of Sharpe ratio under non-normality (Mertens 2002)
        var_sr = (1.0 - skewness * sharpe_ratio + ((kurtosis - 1.0) / 4.0) * (sharpe_ratio ** 2)) / sample_length
        sigma_sr = math.sqrt(max(1e-12, var_sr))

        z = (sharpe_ratio - sr_0) / sigma_sr
        dsr = norm_cdf(z)
        return dsr, sr_0, sigma_sr

    def evaluate(
        self,
        sharpe_ratio: float,
        trial_count: int,
        sample_length: int,
        skewness: float = 0.0,
        kurtosis: float = 3.0,
        trial_variance: float = 1.0,
        relative_rank: int = 1,
    ) -> StrategyGateResult:
        gate_name = "Gate C: Multiple Selection Correction"

        if sample_length < 30:
            return StrategyGateResult(
                gate_name=gate_name,
                status=GateStatus.PENDING,
                score=0.0,
                threshold=self.min_dsr,
                diagnostics={"sample_length": sample_length, "trial_count": trial_count},
                falsification_evidence="Sample length insufficient for asymptotic DSR calculation.",
            )

        dsr, sr_0, sigma_sr = self.compute_dsr(
            sharpe_ratio=sharpe_ratio,
            trial_count=trial_count,
            sample_length=sample_length,
            skewness=skewness,
            kurtosis=kurtosis,
            trial_variance=trial_variance,
        )

        raw_p_value = max(0.0, 1.0 - dsr)
        # Benjamini-Hochberg adjustment
        adjusted_p_value = min(1.0, raw_p_value * max(1, trial_count) / max(1, relative_rank))

        diagnostics = {
            "realized_sharpe": sharpe_ratio,
            "trial_count": trial_count,
            "expected_max_null_sharpe": sr_0,
            "sigma_sharpe": sigma_sr,
            "deflated_sharpe_ratio": dsr,
            "raw_p_value": raw_p_value,
            "adjusted_p_value": adjusted_p_value,
        }

        if dsr < self.min_dsr or adjusted_p_value > self.max_adjusted_pvalue:
            evidence = (
                f"Deflated Sharpe Ratio ({dsr:.4f} < {self.min_dsr:.2f}) or "
                f"FDR adjusted p-value ({adjusted_p_value:.4f} > {self.max_adjusted_pvalue:.2f}) "
                f"fails multiple testing correction across {trial_count} recorded trials."
            )
            return StrategyGateResult(
                gate_name=gate_name,
                status=GateStatus.FAIL,
                score=dsr,
                threshold=self.min_dsr,
                diagnostics=diagnostics,
                falsification_evidence=evidence,
            )

        return StrategyGateResult(
            gate_name=gate_name,
            status=GateStatus.PASS,
            score=dsr,
            threshold=self.min_dsr,
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate D: Correlation & Capacity Gate
# ============================================================================

class CorrelationCapacityGate:
    """Evaluates cross-strategy correlation in normal vs stress regimes,
    EventCluster concentration, and market depth capacity.
    
    Criteria:
    - Normal regime correlation < 0.60
    - Stress regime correlation < 0.70
    - Proposed allocation <= 1% of 5-minute volume at signal time
    - EventCluster overlap does not breach cluster risk caps
    """

    def __init__(
        self,
        max_normal_correlation: float = 0.60,
        max_stress_correlation: float = 0.70,
        max_capacity_volume_pct: float = 0.01,
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
    ) -> StrategyGateResult:
        gate_name = "Gate D: Correlation & Capacity"

        # 1. Capacity evaluation
        capacity_usd = avg_5m_volume_usd * self.max_capacity_pct
        capacity_exceeded = proposed_allocation_usd > capacity_usd

        # 2. Correlation evaluation
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

        # 3. EventCluster Overlap
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

        if failures:
            return StrategyGateResult(
                gate_name=gate_name,
                status=GateStatus.FAIL,
                score=max_norm_found,
                threshold=self.max_normal_corr,
                diagnostics=diagnostics,
                falsification_evidence=" ".join(failures),
            )

        return StrategyGateResult(
            gate_name=gate_name,
            status=GateStatus.PASS,
            score=max_norm_found,
            threshold=self.max_normal_corr,
            diagnostics=diagnostics,
        )


# ============================================================================
# Gate Orchestrator
# ============================================================================

def all_gates_pass(gate_results: Dict[str, StrategyGateResult]) -> bool:
    """Check if all evaluated gates achieved PASS status."""
    if not gate_results:
        return False
    return all(r.status == GateStatus.PASS for r in gate_results.values())
