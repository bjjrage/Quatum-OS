"""
STR-002 v2 — Liquidity Shock Reversal Research Framework.

Core Quantitative Specification:
- 2-Factor Residual Model: r_alt = beta_BTC * r_BTC + gamma_ETH * eta_ETH + epsilon
- Ridge-regularized orthogonalized factor regression with asymmetric downside beta.
- BTC State Module & Decision Matrix (FLAT, UP, DOWN, RUNNING_HARD).
- Pluggable First Reversal Detectors (Aggressor Flow Flip, Book Replenishment, Microstructure Higher Low).
- Reference Price Exits (Pre-shock VWAP, Origin Price, Half-Retracement, Time Decay).
- STRICT INVARIANT: Execution is LONG-ONLY. Short side is RESEARCH-ONLY ($0 capital, 0 orders).
- RegimeSnapshot logging for every candidate trade.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class BtcState(str, Enum):
    FLAT = "FLAT"
    UP = "UP"
    DOWN = "DOWN"
    RUNNING_HARD_DOWN = "RUNNING_HARD_DOWN"
    RUNNING_HARD_UP = "RUNNING_HARD_UP"


class FirstReversalType(str, Enum):
    AGGRESSOR_FLOW_FLIP = "AGGRESSOR_FLOW_FLIP"
    BOOK_REPLENISHMENT = "BOOK_REPLENISHMENT"
    MICROSTRUCTURE_HIGHER_LOW = "MICROSTRUCTURE_HIGHER_LOW"


class ExitTargetType(str, Enum):
    PRE_SHOCK_VWAP = "PRE_SHOCK_VWAP"
    PRE_SHOCK_ORIGIN = "PRE_SHOCK_ORIGIN"
    HALF_RETRACEMENT = "HALF_RETRACEMENT"
    TIME_DECAY_STOP = "TIME_DECAY_STOP"


from src.portfolio.regime import RegimeSnapshot


class TwoFactorResidualEstimator:
    """Estimates altcoin residual shock after removing BTC and orthogonalized ETH systematic return.
    
    Uses Ridge regularization (lambda = 0.01) and asymmetric beta:
    - beta_down applied when r_BTC < 0
    - beta_up applied when r_BTC >= 0
    """

    def __init__(self, ridge_lambda: float = 0.01):
        self.ridge_lambda = ridge_lambda

    def fit_and_residualize(
        self,
        r_alt: List[float],
        r_btc: List[float],
        r_eth: List[float],
    ) -> Tuple[float, float, float, List[float], float]:
        """Fit factor coefficients and return (beta_down, beta_up, gamma_eth, residuals, sigma_epsilon)."""
        n = min(len(r_alt), len(r_btc), len(r_eth))
        if n < 10:
            return 1.0, 1.0, 0.0, [0.0] * n, 0.01

        # 1. Orthogonalize ETH against BTC: r_ETH = delta * r_BTC + eta
        sum_btc_sq = sum(r_btc[i] ** 2 for i in range(n))
        sum_btc_eth = sum(r_btc[i] * r_eth[i] for i in range(n))
        delta = sum_btc_eth / (sum_btc_sq + self.ridge_lambda)

        eta = [r_eth[i] - delta * r_btc[i] for i in range(n)]

        # 2. Asymmetric BTC beta estimation
        down_idx = [i for i in range(n) if r_btc[i] < 0]
        up_idx = [i for i in range(n) if r_btc[i] >= 0]

        if down_idx:
            down_btc_sq = sum(r_btc[i] ** 2 for i in down_idx)
            down_alt_btc = sum(r_alt[i] * r_btc[i] for i in down_idx)
            beta_down = down_alt_btc / (down_btc_sq + self.ridge_lambda)
        else:
            beta_down = 1.0

        if up_idx:
            up_btc_sq = sum(r_btc[i] ** 2 for i in up_idx)
            up_alt_btc = sum(r_alt[i] * r_btc[i] for i in up_idx)
            beta_up = up_alt_btc / (up_btc_sq + self.ridge_lambda)
        else:
            beta_up = 1.0

        # 3. Regularized ETH residual factor gamma
        sum_eta_sq = sum(eta[i] ** 2 for i in range(n))
        sum_alt_eta = sum(r_alt[i] * eta[i] for i in range(n))
        gamma_eth = sum_alt_eta / (sum_eta_sq + self.ridge_lambda)

        # 4. Compute residual series epsilon
        residuals: List[float] = []
        for i in range(n):
            b = beta_down if r_btc[i] < 0 else beta_up
            eps = r_alt[i] - (b * r_btc[i] + gamma_eth * eta[i])
            residuals.append(eps)

        # 5. Residual standard deviation sigma_epsilon
        mean_eps = sum(residuals) / n
        var_eps = sum((e - mean_eps) ** 2 for e in residuals) / max(1, n - 1)
        sigma_eps = math.sqrt(var_eps) if var_eps > 1e-12 else 0.01

        return beta_down, beta_up, gamma_eth, residuals, sigma_eps


class BtcStateClassifier:
    """Classifies BTC market state and evaluates the BTC Decision Matrix."""

    @staticmethod
    def classify(
        ret_1m: float,
        ret_5m: float,
        ret_15m: float,
        btc_realized_vol_5m: float = 0.002,  # Provisional research prior
        vol_5m_ratio: float = 1.0,
    ) -> BtcState:
        """Classify BTC state based on multi-horizon returns normalized by realized volatility.
        
        Provisional research priors:
        - Running hard: |ret_5m| >= 3.0 * sigma (or 2.0 * sigma with volume expansion > 2.0)
        - Trend (UP/DOWN): |ret_5m| >= 1.0 * sigma
        - FLAT: |ret_5m| < 1.0 * sigma
        """
        sigma = max(1e-5, btc_realized_vol_5m)
        # Running hard down: severe drop or high velocity liquidation cascade
        if ret_5m <= -3.0 * sigma or (ret_5m <= -2.0 * sigma and vol_5m_ratio > 2.0):
            return BtcState.RUNNING_HARD_DOWN

        # Running hard up: severe rip or high velocity market dislocation
        if ret_5m >= 3.0 * sigma or (ret_5m >= 2.0 * sigma and vol_5m_ratio > 2.0):
            return BtcState.RUNNING_HARD_UP

        if ret_5m <= -1.0 * sigma:
            return BtcState.DOWN

        if ret_5m >= 1.0 * sigma:
            return BtcState.UP

        return BtcState.FLAT

    @staticmethod
    def evaluate_decision_matrix(
        btc_state: BtcState,
        z_score: float,
    ) -> Tuple[bool, float, str]:
        """Evaluate action, sizing, and exit behavior from the BTC Decision Matrix.
        
        Authoritative rules:
        - BTC FLAT: candidate may proceed normally if other filters pass (100% sizing)
        - BTC UP: candidate may proceed normally (120% sizing, trail runner)
        - BTC DOWN: block new entry or force early exit (0% sizing)
        - BTC RUNNING_HARD_DOWN: strictly blocked (systemic liquidation cascade, 0% sizing)
        - BTC RUNNING_HARD_UP: blocked (market dislocation/high dispersion, 0% sizing)
        
        Returns:
            (is_allowed, sizing_multiplier, behavior_description)
        """
        # Shock must be statistically significant (z_score <= -3.0)
        if z_score > -3.0:
            return False, 0.0, "NO_SHOCK: z-score does not breach -3.0 sigma threshold"

        if btc_state == BtcState.FLAT:
            return True, 1.0, "TARGET_REFERENCE_PRICE: 100% sizing, standard reference target"

        elif btc_state == BtcState.UP:
            return True, 1.2, "TARGET_REFERENCE_PRICE_TRAIL_RUNNER: 120% sizing, trail runner"

        elif btc_state == BtcState.DOWN:
            return False, 0.0, "BLOCKED_BTC_DOWN: Block new entry when BTC is down (early exit if in position)"

        elif btc_state == BtcState.RUNNING_HARD_DOWN:
            return False, 0.0, "STRICTLY_BLOCKED: Systemic liquidation cascade, knife catch forbidden"

        elif btc_state == BtcState.RUNNING_HARD_UP:
            return False, 0.0, "BLOCKED_BTC_RUNNING_HARD_UP: Market dislocation / high dispersion, abstain from chasing/knife-catching"

        return False, 0.0, "UNKNOWN_STATE"


class FirstReversalDetector:
    """Pluggable detector validating that mechanical selling pressure has exhausted."""

    @staticmethod
    def check_aggressor_flow(delta_5s: float) -> bool:
        """Delta (buy vol - sell vol) over 5 seconds turns positive."""
        return delta_5s > 0.0

    @staticmethod
    def check_book_replenishment(current_bid_depth_0_5pct: float, pre_shock_median_depth: float) -> Tuple[bool, float]:
        """Bid depth within 0.5% recovers to > 50% of pre-shock median."""
        if pre_shock_median_depth <= 0:
            return False, 0.0
        ratio = current_bid_depth_0_5pct / pre_shock_median_depth
        return ratio >= 0.50, ratio

    @staticmethod
    def check_microstructure_higher_low(
        recent_1s_lows: List[float],
    ) -> bool:
        """Higher low on 1-second bar structure after impulse bottom."""
        if len(recent_1s_lows) < 3:
            return False
        # Last low is higher than preceding minimum low
        min_prev = min(recent_1s_lows[:-1])
        return recent_1s_lows[-1] > min_prev

    @classmethod
    def evaluate(
        cls,
        delta_5s: float,
        current_bid_depth_0_5pct: float,
        pre_shock_median_depth: float,
        recent_1s_lows: List[float],
    ) -> Tuple[bool, Optional[FirstReversalType], float]:
        """Evaluate all pluggable detectors. At least one must trigger before entry."""
        replenished, ratio = cls.check_book_replenishment(current_bid_depth_0_5pct, pre_shock_median_depth)
        if replenished:
            return True, FirstReversalType.BOOK_REPLENISHMENT, ratio

        if cls.check_aggressor_flow(delta_5s):
            return True, FirstReversalType.AGGRESSOR_FLOW_FLIP, ratio

        if cls.check_microstructure_higher_low(recent_1s_lows):
            return True, FirstReversalType.MICROSTRUCTURE_HIGHER_LOW, ratio

        return False, None, ratio


class ReferencePriceExitCalculator:
    """Calculates non-arbitrary equilibrium exit targets."""

    @staticmethod
    def calculate_targets(
        entry_price: float,
        pre_shock_origin: float,
        pre_shock_vwap: float,
    ) -> Dict[str, float]:
        """Calculate primary and partial exit prices."""
        shock_magnitude = max(0.0, pre_shock_origin - entry_price)
        half_retracement = entry_price + 0.5 * shock_magnitude

        return {
            "half_retracement": half_retracement,
            "pre_shock_origin": pre_shock_origin,
            "pre_shock_vwap": pre_shock_vwap,
        }


class Str002V2Strategy:
    """Complete STR-002 v2 Liquidity Shock Reversal research engine.
    
    INVARIANTS:
    - STRICTLY LONG ONLY: short impulses are research-only ($0 capital, 0 orders).
    - Only trades forced liquidation shocks, not informative fundamental moves.
    - Requires BTC Decision Matrix clearance.
    - Requires First Reversal confirmation.
    """

    def __init__(
        self,
        z_score_threshold: float = -3.0,
        max_holding_seconds: int = 900,  # 15 minutes max
    ):
        self.z_score_threshold = z_score_threshold
        self.max_holding_seconds = max_holding_seconds
        self.factor_estimator = TwoFactorResidualEstimator()
        self.btc_classifier = BtcStateClassifier()
        self.reversal_detector = FirstReversalDetector()
        self.exit_calculator = ReferencePriceExitCalculator()

    def generate_signal(
        self,
        symbol: str,
        timestamp_ns: int,
        r_alt_series: List[float],
        r_btc_series: List[float],
        r_eth_series: List[float],
        btc_returns_1m_5m_15m: Tuple[float, float, float],
        btc_vol_5m_ratio: float,
        current_price: float,
        pre_shock_origin: float,
        pre_shock_vwap: float,
        delta_5s: float,
        bid_depth_0_5pct: float,
        pre_shock_median_depth: float,
        recent_1s_lows: List[float],
        btc_realized_vol_5m: float = 0.002,
        is_short_side_hypothesis: bool = False,
    ) -> Tuple[bool, Optional[RegimeSnapshot], Dict[str, Any]]:
        """Evaluate STR-002 v2 signal and generate trade decision.
        
        Returns:
            (should_execute, regime_snapshot, diagnostic_metadata)
        """
        # INVARIANT: Strict LONG-ONLY execution
        if is_short_side_hypothesis:
            diagnostics = {
                "decision": "BLOCKED",
                "reason": "SHORT_SIDE_RESEARCH_ONLY: Short-side crypto execution is strictly forbidden ($0 live risk).",
                "is_long_only_enforced": True,
            }
            return False, None, diagnostics

        # 1. 2-Factor Residual Estimation
        beta_down, beta_up, gamma_eth, residuals, sigma_eps = self.factor_estimator.fit_and_residualize(
            r_alt=r_alt_series,
            r_btc=r_btc_series,
            r_eth=r_eth_series,
        )

        current_eps = residuals[-1] if residuals else 0.0
        z_score = current_eps / sigma_eps if sigma_eps > 0 else 0.0

        # 2. BTC State and Decision Matrix
        btc_state = self.btc_classifier.classify(
            ret_1m=btc_returns_1m_5m_15m[0],
            ret_5m=btc_returns_1m_5m_15m[1],
            ret_15m=btc_returns_1m_5m_15m[2],
            btc_realized_vol_5m=btc_realized_vol_5m,
            vol_5m_ratio=btc_vol_5m_ratio,
        )

        matrix_allowed, sizing_mult, behavior = self.btc_classifier.evaluate_decision_matrix(
            btc_state=btc_state,
            z_score=z_score,
        )

        if not matrix_allowed:
            diagnostics = {
                "decision": "BLOCKED",
                "reason": f"BTC Decision Matrix blocked entry: {behavior}",
                "btc_state": btc_state.value,
                "z_score": z_score,
            }
            return False, None, diagnostics

        # 3. First Reversal Verification
        reversal_confirmed, rev_type, replenishment_ratio = self.reversal_detector.evaluate(
            delta_5s=delta_5s,
            current_bid_depth_0_5pct=bid_depth_0_5pct,
            pre_shock_median_depth=pre_shock_median_depth,
            recent_1s_lows=recent_1s_lows,
        )

        if not reversal_confirmed:
            diagnostics = {
                "decision": "WAITING_CONFIRMATION",
                "reason": "First reversal not detected; knife-catch prevented.",
                "replenishment_ratio": replenishment_ratio,
                "z_score": z_score,
            }
            return False, None, diagnostics

        # 4. Exit targets
        exit_targets = self.exit_calculator.calculate_targets(
            entry_price=current_price,
            pre_shock_origin=pre_shock_origin,
            pre_shock_vwap=pre_shock_vwap,
        )

        # 5. Snapshot creation with complete 23+ fields
        snapshot = RegimeSnapshot(
            timestamp_ns=timestamp_ns,
            regime_snapshot_id=f"regime_{timestamp_ns}_{symbol}",
            btc_state_1m=self.btc_classifier.classify(btc_returns_1m_5m_15m[0], btc_returns_1m_5m_15m[0], btc_returns_1m_5m_15m[0], btc_realized_vol_5m).value,
            btc_state_5m=btc_state.value,
            btc_state_15m=self.btc_classifier.classify(btc_returns_1m_5m_15m[2], btc_returns_1m_5m_15m[2], btc_returns_1m_5m_15m[2], btc_realized_vol_5m).value,
            btc_realized_vol_1h=btc_realized_vol_5m * math.sqrt(12.0),
            market_regime="NORMAL",
            symbol=symbol,
            btc_state=btc_state,
            alt_residual_shock=current_eps,
            alt_z_score=z_score,
            beta_down=beta_down,
            beta_up=beta_up,
            gamma_eth=gamma_eth,
            reversal_detector_triggered=rev_type.value if rev_type else None,
            book_replenishment_ratio=replenishment_ratio,
            pre_shock_vwap=pre_shock_vwap,
            pre_shock_origin=pre_shock_origin,
            entry_price=current_price,
        )

        diagnostics = {
            "decision": "EXECUTE_LONG",
            "sizing_multiplier": sizing_mult,
            "behavior": behavior,
            "exit_targets": exit_targets,
            "reversal_type": rev_type.value if rev_type else None,
            "max_holding_seconds": self.max_holding_seconds,
        }

        return True, snapshot, diagnostics


def get_str002_model_variants() -> List[Dict[str, Any]]:
    """Isolated evidence ladder specifications M0 through M7 for STR-002 v2.
    
    Each model must demonstrate incremental out-of-sample economic value.
    No later model inherits validated status from an earlier model.
    """
    return [
        {
            "variant_id": "M0",
            "name": "Raw Shock Reversal",
            "description": "Baseline breakout / unadjusted price drop overshoot",
            "factor_model": "NONE",
            "btc_conditioning": False,
            "reversal_filter": False,
            "status": "UNVALIDATED",
        },
        {
            "variant_id": "M1",
            "name": "BTC Residual",
            "description": "Volume surge and 1-factor BTC residualization",
            "factor_model": "1_FACTOR_BTC",
            "btc_conditioning": False,
            "reversal_filter": False,
            "status": "UNVALIDATED",
        },
        {
            "variant_id": "M2",
            "name": "BTC + ETH Orthogonalized",
            "description": "2-factor residual with orthogonalized ETH component",
            "factor_model": "2_FACTOR_ORTHOGONAL_ETH",
            "btc_conditioning": False,
            "reversal_filter": False,
            "status": "UNVALIDATED",
        },
        {
            "variant_id": "M3",
            "name": "Asymmetric Downside Beta",
            "description": "Ridge-regularized asymmetric downside beta estimation",
            "factor_model": "2_FACTOR_ASYM_BETA",
            "btc_conditioning": False,
            "reversal_filter": False,
            "status": "UNVALIDATED",
        },
        {
            "variant_id": "M4",
            "name": "BTC Regime Decision Matrix",
            "description": "Multi-horizon BTC state classification and directional gating",
            "factor_model": "2_FACTOR_ASYM_BETA",
            "btc_conditioning": True,
            "reversal_filter": False,
            "status": "UNVALIDATED",
        },
        {
            "variant_id": "M5",
            "name": "First Reversal Confirmation",
            "description": "Exhaustion detection via delta flip, replenishment, or micro HL",
            "factor_model": "2_FACTOR_ASYM_BETA",
            "btc_conditioning": True,
            "reversal_filter": True,
            "status": "UNVALIDATED",
        },
        {
            "variant_id": "M6",
            "name": "Regime-Conditioned Exits",
            "description": "Dynamic holding period and reference price exits",
            "factor_model": "2_FACTOR_ASYM_BETA",
            "btc_conditioning": True,
            "reversal_filter": True,
            "status": "UNVALIDATED",
        },
        {
            "variant_id": "M7",
            "name": "Microstructure Confirmation",
            "description": "Multi-timeframe confirmation with book depth replenishment ratio",
            "factor_model": "2_FACTOR_ASYM_BETA",
            "btc_conditioning": True,
            "reversal_filter": True,
            "status": "UNVALIDATED",
        },
    ]
