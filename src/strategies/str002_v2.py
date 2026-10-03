"""
STR-002 v2 — Liquidity Shock Reversal Research Framework.

Core Quantitative Specification:
- 2-Factor Residual Model: r_alt = alpha_alt + beta_BTC * r_BTC + gamma_ETH * eta_ETH + epsilon
- Ridge-regularized or OLS orthogonalized factor regression with asymmetric downside beta.
- Pre-shock parameter estimation strictly on history 0..t-1 with frozen parameter evaluation at bar t.
- BTC State Module & Decision Matrix (FLAT, UP, DOWN, RUNNING_HARD_DOWN, RUNNING_HARD_UP, STATE_UNKNOWN).
- Shock State Machine: IDLE -> SHOCK_DETECTED -> WAITING_FOR_REVERSAL -> REVERSAL_CONFIRMED -> SIGNAL_EMITTED -> COOLDOWN.
- Pluggable First Reversal Detectors (Aggressor Flow Flip, Book Replenishment, Microstructure Higher Low).
- Mandatory Hard Stop Loss on every signal (positive, below entry, non-zero risk distance).
- Unit error elimination: sizing multiplier strictly capped at <= 1.0.
- Risk-budget sizing derived from allowed_risk_usd / risk_distance.
- STRICT INVARIANT: Execution is LONG-ONLY. Short side is RESEARCH-ONLY ($0 capital, 0 orders).
- RegimeSnapshot logging for every candidate trade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from src.portfolio.regime import RegimeSnapshot


class BtcState(str, Enum):
    FLAT = "FLAT"
    UP = "UP"
    DOWN = "DOWN"
    RUNNING_HARD_DOWN = "RUNNING_HARD_DOWN"
    RUNNING_HARD_UP = "RUNNING_HARD_UP"
    STATE_UNKNOWN = "STATE_UNKNOWN"


class FirstReversalType(str, Enum):
    AGGRESSOR_FLOW_FLIP = "AGGRESSOR_FLOW_FLIP"
    BOOK_REPLENISHMENT = "BOOK_REPLENISHMENT"
    MICROSTRUCTURE_HIGHER_LOW = "MICROSTRUCTURE_HIGHER_LOW"


class ExitTargetType(str, Enum):
    PRE_SHOCK_VWAP = "PRE_SHOCK_VWAP"
    PRE_SHOCK_ORIGIN = "PRE_SHOCK_ORIGIN"
    HALF_RETRACEMENT = "HALF_RETRACEMENT"
    TIME_DECAY_STOP = "TIME_DECAY_STOP"
    HARD_STOP_LOSS = "HARD_STOP_LOSS"


class ModelStatus(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    INVALID = "INVALID"


class ShockState(str, Enum):
    IDLE = "IDLE"
    SHOCK_DETECTED = "SHOCK_DETECTED"
    WAITING_FOR_REVERSAL = "WAITING_FOR_REVERSAL"
    REVERSAL_CONFIRMED = "REVERSAL_CONFIRMED"
    SIGNAL_EMITTED = "SIGNAL_EMITTED"
    EXPIRED = "EXPIRED"
    COOLDOWN = "COOLDOWN"


@dataclass
class FactorModelFit:
    """Encapsulates fitted parameters from pre-shock estimation window."""
    status: ModelStatus
    beta_down: float = 1.0
    beta_up: float = 1.0
    gamma_eth: float = 0.0
    delta_eth: float = 0.0
    alpha_alt: float = 0.0
    alpha_eth: float = 0.0
    sigma_eps: float = 0.01
    pre_residuals: List[float] = field(default_factory=list)
    n_samples: int = 0
    error_message: Optional[str] = None


class TwoFactorResidualEstimator:
    """Estimates altcoin residual shock after removing BTC and orthogonalized ETH systematic return.
    
    Adheres strictly to:
    - Minimum sample size (N >= min_samples, default 30, else ModelStatus.NOT_READY).
    - Degenerate input detection (NaN, Inf, zero variance in BTC, timestamp disorder -> ModelStatus.INVALID).
    - Mean-centered regression with intercept support for exact beta recovery.
    - Properly-scaled Ridge regularization or exact OLS (ridge_lambda=0.0).
    - Strict pre-shock estimation (fit on 0..t-1, evaluate shock at t with frozen parameters).
    """

    def __init__(self, ridge_lambda: float = 0.0, min_samples: int = 30):
        self.ridge_lambda = ridge_lambda
        self.min_samples = min_samples

    def fit_pre_shock(
        self,
        r_alt: List[float],
        r_btc: List[float],
        r_eth: List[float],
        timestamps: Optional[List[int]] = None,
    ) -> FactorModelFit:
        """Fit factor model parameters strictly on pre-shock observations."""
        n = min(len(r_alt), len(r_btc), len(r_eth))

        # 1. Sample size check
        if n < self.min_samples:
            return FactorModelFit(
                status=ModelStatus.NOT_READY,
                n_samples=n,
                error_message=f"Insufficient pre-shock samples: {n} < {self.min_samples}",
            )

        # 2. Degenerate input checks (NaN, Inf)
        for i in range(n):
            if math.isnan(r_alt[i]) or math.isinf(r_alt[i]) or \
               math.isnan(r_btc[i]) or math.isinf(r_btc[i]) or \
               math.isnan(r_eth[i]) or math.isinf(r_eth[i]):
                return FactorModelFit(
                    status=ModelStatus.INVALID,
                    n_samples=n,
                    error_message=f"Non-finite return detected at index {i}",
                )

        # Timestamp monotonicity check
        if timestamps is not None and len(timestamps) >= n:
            for i in range(1, n):
                if timestamps[i] <= timestamps[i - 1]:
                    return FactorModelFit(
                        status=ModelStatus.INVALID,
                        n_samples=n,
                        error_message=f"Timestamp disorder at index {i}: {timestamps[i]} <= {timestamps[i-1]}",
                    )

        # Check zero-variance in BTC returns
        mean_btc = sum(r_btc[:n]) / n
        var_btc = sum((r_btc[i] - mean_btc) ** 2 for i in range(n)) / max(1, n - 1)
        s_xx_btc = sum(r_btc[i] ** 2 for i in range(n))
        if var_btc < 1e-12 or s_xx_btc < 1e-12:
            return FactorModelFit(
                status=ModelStatus.INVALID,
                n_samples=n,
                error_message="Zero variance in BTC factor returns; degenerate regression",
            )

        # 3. Exact Gram-Schmidt orthogonalization of ETH against BTC: r_ETH = alpha_eth + delta * r_BTC + eta
        mean_eth = sum(r_eth[:n]) / n
        s_xx_btc_var = sum((r_btc[i] - mean_btc) ** 2 for i in range(n))
        s_xy_btc_eth = sum((r_btc[i] - mean_btc) * (r_eth[i] - mean_eth) for i in range(n))
        delta = s_xy_btc_eth / s_xx_btc_var if s_xx_btc_var > 1e-12 else 0.0
        alpha_eth = mean_eth - delta * mean_btc
        eta = [r_eth[i] - (alpha_eth + delta * r_btc[i]) for i in range(n)]

        # 4. Altcoin loading on orthogonalized ETH factor eta
        mean_alt = sum(r_alt[:n]) / n
        mean_eta = sum(eta) / n
        s_eta_sq = sum((eta[i] - mean_eta) ** 2 for i in range(n))
        s_alt_eta = sum((r_alt[i] - mean_alt) * (eta[i] - mean_eta) for i in range(n))

        if s_eta_sq > 1e-12:
            gamma_eth_ols = s_alt_eta / s_eta_sq
            gamma_eth = gamma_eth_ols / (1.0 + self.ridge_lambda)
        else:
            gamma_eth_ols = 0.0
            gamma_eth = 0.0

        # Purify altcoin returns of orthogonalized ETH component
        r_alt_clean = [r_alt[i] - gamma_eth_ols * eta[i] for i in range(n)]

        # 5. Asymmetric BTC beta estimation via conditional subsets on purified returns
        down_idx = [i for i in range(n) if r_btc[i] < 0]
        up_idx = [i for i in range(n) if r_btc[i] >= 0]

        # Downside beta
        if len(down_idx) >= 3:
            mean_btc_down = sum(r_btc[i] for i in down_idx) / len(down_idx)
            mean_alt_down = sum(r_alt_clean[i] for i in down_idx) / len(down_idx)
            s_xx_down = sum((r_btc[i] - mean_btc_down) ** 2 for i in down_idx)
            s_xy_down = sum((r_btc[i] - mean_btc_down) * (r_alt_clean[i] - mean_alt_down) for i in down_idx)

            if s_xx_down > 1e-12:
                beta_down = s_xy_down / (s_xx_down * (1.0 + self.ridge_lambda))
            else:
                down_sq = sum(r_btc[i] ** 2 for i in down_idx)
                down_xy = sum(r_alt_clean[i] * r_btc[i] for i in down_idx)
                beta_down = down_xy / (down_sq * (1.0 + self.ridge_lambda)) if down_sq > 1e-12 else 1.0
        else:
            beta_down = 1.0

        # Upside beta
        if len(up_idx) >= 3:
            mean_btc_up = sum(r_btc[i] for i in up_idx) / len(up_idx)
            mean_alt_up = sum(r_alt_clean[i] for i in up_idx) / len(up_idx)
            s_xx_up = sum((r_btc[i] - mean_btc_up) ** 2 for i in up_idx)
            s_xy_up = sum((r_btc[i] - mean_btc_up) * (r_alt_clean[i] - mean_alt_up) for i in up_idx)

            if s_xx_up > 1e-12:
                beta_up = s_xy_up / (s_xx_up * (1.0 + self.ridge_lambda))
            else:
                up_sq = sum(r_btc[i] ** 2 for i in up_idx)
                up_xy = sum(r_alt_clean[i] * r_btc[i] for i in up_idx)
                beta_up = up_xy / (up_sq * (1.0 + self.ridge_lambda)) if up_sq > 1e-12 else 1.0
        else:
            beta_up = 1.0

        # 6. Overall altcoin intercept alpha_alt
        pred_no_alpha = [
            (beta_down if r_btc[i] < 0 else beta_up) * r_btc[i] + gamma_eth * eta[i]
            for i in range(n)
        ]
        alpha_alt = sum(r_alt[i] - pred_no_alpha[i] for i in range(n)) / n

        # 7. Pre-shock residuals and volatility sigma_eps
        residuals = [
            r_alt[i] - (alpha_alt + pred_no_alpha[i])
            for i in range(n)
        ]
        mean_res = sum(residuals) / n
        var_res = sum((e - mean_res) ** 2 for e in residuals) / max(1, n - 1)
        sigma_eps = math.sqrt(var_res) if var_res > 1e-12 else 0.001

        return FactorModelFit(
            status=ModelStatus.READY,
            beta_down=beta_down,
            beta_up=beta_up,
            gamma_eth=gamma_eth,
            delta_eth=delta,
            alpha_alt=alpha_alt,
            alpha_eth=alpha_eth,
            sigma_eps=sigma_eps,
            pre_residuals=residuals,
            n_samples=n,
        )

    def evaluate_shock_at_t(
        self,
        fit: FactorModelFit,
        r_alt_t: float,
        r_btc_t: float,
        r_eth_t: float,
    ) -> Tuple[float, float]:
        """Evaluate idiosyncratic residual and z-score at candidate shock bar t using frozen pre-shock parameters."""
        if fit.status != ModelStatus.READY:
            return 0.0, 0.0

        # Compute orthogonalized ETH at t using frozen delta and alpha
        eta_t = r_eth_t - (fit.alpha_eth + fit.delta_eth * r_btc_t)

        # Select asymmetric beta based on sign of BTC return at t
        b_t = fit.beta_down if r_btc_t < 0 else fit.beta_up

        # Expected return under systemic factors
        exp_return_t = fit.alpha_alt + b_t * r_btc_t + fit.gamma_eth * eta_t

        # Idiosyncratic residual and standardized z-score
        residual_t = r_alt_t - exp_return_t
        z_score_t = residual_t / fit.sigma_eps if fit.sigma_eps > 0 else 0.0

        return residual_t, z_score_t

    def fit_and_residualize(
        self,
        r_alt: List[float],
        r_btc: List[float],
        r_eth: List[float],
    ) -> Tuple[float, float, float, List[float], float]:
        """Fit factor coefficients and return (beta_down, beta_up, gamma_eth, residuals, sigma_epsilon).
        
        Provides backward compatibility with callers expecting 5-tuple output.
        """
        fit = self.fit_pre_shock(r_alt, r_btc, r_eth)
        if fit.status != ModelStatus.READY:
            n = min(len(r_alt), len(r_btc), len(r_eth))
            return 1.0, 1.0, 0.0, [0.0] * n, 0.01

        return (
            fit.beta_down,
            fit.beta_up,
            fit.gamma_eth,
            fit.pre_residuals,
            fit.sigma_eps,
        )


class BtcStateClassifier:
    """Classifies BTC market state and evaluates the BTC Decision Matrix."""

    @staticmethod
    def classify(
        ret_1m: Optional[float],
        ret_5m: Optional[float],
        ret_15m: Optional[float],
        btc_realized_vol_5m: Optional[float] = 0.002,
        vol_5m_ratio: Optional[float] = 1.0,
    ) -> BtcState:
        """Classify BTC state based on multi-horizon returns normalized by realized volatility.
        
        Fail-Closed Invariants:
        - If inputs are None, NaN, Inf, or volatility <= 0 -> STATE_UNKNOWN.
        """
        if (
            ret_5m is None
            or math.isnan(ret_5m)
            or math.isinf(ret_5m)
            or btc_realized_vol_5m is None
            or math.isnan(btc_realized_vol_5m)
            or math.isinf(btc_realized_vol_5m)
            or btc_realized_vol_5m <= 0.0
            or vol_5m_ratio is None
            or math.isnan(vol_5m_ratio)
            or math.isinf(vol_5m_ratio)
        ):
            return BtcState.STATE_UNKNOWN

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
        - STATE_UNKNOWN: fail-closed, blocked (0% sizing)
        - BTC FLAT: candidate may proceed normally if other filters pass (100% sizing, multiplier = 1.0)
        - BTC UP: candidate may proceed normally (100% sizing, multiplier = 1.0; capped at <= 1.0)
        - BTC DOWN: block new entry or force early exit (0% sizing)
        - BTC RUNNING_HARD_DOWN: strictly blocked (systemic liquidation cascade, 0% sizing)
        - BTC RUNNING_HARD_UP: blocked (market dislocation/high dispersion, 0% sizing)
        
        Returns:
            (is_allowed, sizing_multiplier, behavior_description)
        """
        # Shock must be statistically significant (z_score <= -3.0)
        if z_score > -3.0:
            return False, 0.0, "NO_SHOCK: z-score does not breach -3.0 sigma threshold"

        # Unknown state fails closed
        if btc_state == BtcState.STATE_UNKNOWN:
            return False, 0.0, "BLOCKED_BTC_UNKNOWN: BTC state is unknown or unverified; fail-closed."

        if btc_state == BtcState.FLAT:
            return True, 1.0, "TARGET_REFERENCE_PRICE: 100% sizing, standard reference target"

        elif btc_state == BtcState.UP:
            # Multiplier capped at 1.0 to eliminate unit scaling errors (>100% prohibited)
            return True, 1.0, "TARGET_REFERENCE_PRICE_TRAIL_RUNNER: 100% sizing, trail runner"

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


class ShockStateMachine:
    """State machine governing shock lifecycle, single-signal enforcement, and cooldown."""

    def __init__(self, max_wait_bars: int = 5, cooldown_bars: int = 10):
        self.max_wait_bars = max_wait_bars
        self.cooldown_bars = cooldown_bars
        self.state: ShockState = ShockState.IDLE
        self.active_shock_id: Optional[str] = None
        self.shock_bottom_price: float = 0.0
        self.shock_origin_price: float = 0.0
        self.shock_z_score: float = 0.0
        self.bars_waiting: int = 0
        self.bars_cooldown: int = 0
        self.signal_emitted_for_shock: bool = False

    def step(
        self,
        z_score: float,
        current_price: float,
        reversal_confirmed: bool,
        btc_state_allowed: bool,
        bar_index: int,
        origin_price: float = 0.0,
    ) -> bool:
        """Advance the shock state machine by one bar.
        
        Returns:
            should_emit_signal (True exactly once per qualifying shock)
        """
        # 1. Cooldown state
        if self.state == ShockState.COOLDOWN:
            self.bars_cooldown -= 1
            if self.bars_cooldown <= 0:
                self.state = ShockState.IDLE
                self.active_shock_id = None
                self.signal_emitted_for_shock = False
            return False

        # 2. Idle state: monitor for initial shock breach
        if self.state == ShockState.IDLE:
            if z_score <= -3.0 and btc_state_allowed:
                self.state = ShockState.SHOCK_DETECTED
                self.active_shock_id = f"shock_{bar_index}"
                self.shock_bottom_price = current_price
                self.shock_origin_price = origin_price
                self.shock_z_score = z_score
                self.bars_waiting = 0
                self.signal_emitted_for_shock = False

                if reversal_confirmed:
                    self.state = ShockState.SIGNAL_EMITTED
                    self.signal_emitted_for_shock = True
                    self.bars_cooldown = self.cooldown_bars
                    return True
                else:
                    self.state = ShockState.WAITING_FOR_REVERSAL
                    self.bars_waiting = 1
                    return False
            return False

        # 3. Waiting for reversal confirmation
        if self.state == ShockState.WAITING_FOR_REVERSAL:
            # Track lowest price observed during liquidation plunge
            self.shock_bottom_price = min(self.shock_bottom_price, current_price)

            if reversal_confirmed:
                if not self.signal_emitted_for_shock:
                    self.state = ShockState.SIGNAL_EMITTED
                    self.signal_emitted_for_shock = True
                    self.bars_cooldown = self.cooldown_bars
                    return True
                else:
                    self.state = ShockState.COOLDOWN
                    self.bars_cooldown = self.cooldown_bars
                    return False

            self.bars_waiting += 1
            if self.bars_waiting >= self.max_wait_bars:
                # Wait window expired without reversal confirmation: unreversed knife-catch prevented
                self.state = ShockState.EXPIRED
                self.bars_cooldown = self.cooldown_bars
                return False

            return False

        # 4. Signal emitted or expired -> transition into cooldown
        if self.state in (ShockState.SIGNAL_EMITTED, ShockState.EXPIRED):
            self.state = ShockState.COOLDOWN
            self.bars_cooldown = max(1, self.bars_cooldown - 1)
            return False

        return False


class ReferencePriceExitCalculator:
    """Calculates non-arbitrary equilibrium exit targets and mandatory hard stop loss."""

    @staticmethod
    def calculate_targets(
        entry_price: float,
        pre_shock_origin: float,
        pre_shock_vwap: float,
        shock_bottom: Optional[float] = None,
        stop_buffer_pct: float = 0.005,  # 50 bps minimum buffer below shock bottom
    ) -> Dict[str, Any]:
        """Calculate primary and partial exit prices along with mandatory hard stop loss.
        
        INVARIANTS:
        - stop_loss MUST be strictly positive (> 0)
        - stop_loss MUST be strictly less than entry_price
        - risk_distance = entry_price - stop_loss > 0
        - risk_pct = risk_distance / entry_price in (0, 1.0)
        """
        shock_magnitude = max(0.0, pre_shock_origin - entry_price)
        half_retracement = entry_price + 0.5 * shock_magnitude

        # Hard stop calculation
        bottom = shock_bottom if shock_bottom is not None else entry_price
        bottom = min(bottom, entry_price)

        # Buffer is max of fixed pct (e.g. 50 bps) or 10% of shock magnitude
        buffer = max(entry_price * stop_buffer_pct, shock_magnitude * 0.10)
        stop_price = bottom - buffer

        if stop_price <= 0.0 or stop_price >= entry_price:
            stop_price = max(1e-6, entry_price * 0.98)

        risk_distance = entry_price - stop_price
        risk_pct = risk_distance / entry_price

        return {
            "half_retracement": half_retracement,
            "pre_shock_origin": pre_shock_origin,
            "pre_shock_vwap": pre_shock_vwap,
            "stop_loss": stop_price,
            "risk_distance": risk_distance,
            "risk_pct": risk_pct,
            "invalidation_reason": "NEW_LOW_BELOW_SHOCK_BOTTOM: Price pierced below shock exhaustion bottom minus buffer",
        }


class Str002V2Strategy:
    """Complete STR-002 v2 Liquidity Shock Reversal research engine.
    
    INVARIANTS:
    - STRICTLY LONG ONLY: short impulses are research-only ($0 capital, 0 orders).
    - Only trades forced liquidation shocks, not informative fundamental moves.
    - Requires BTC Decision Matrix clearance.
    - Requires First Reversal confirmation.
    - Exactly 1 signal per shock via ShockStateMachine.
    - Every signal has a finite positive hard stop loss.
    - Sizing multiplier capped at <= 1.0.
    """

    def __init__(
        self,
        z_score_threshold: float = -3.0,
        max_holding_seconds: int = 900,  # 15 minutes max
        max_wait_bars: int = 5,
        cooldown_bars: int = 10,
        default_allowed_risk_usd: float = 100.0,
    ):
        self.z_score_threshold = z_score_threshold
        self.max_holding_seconds = max_holding_seconds
        self.max_wait_bars = max_wait_bars
        self.cooldown_bars = cooldown_bars
        self.default_allowed_risk_usd = default_allowed_risk_usd

        self.factor_estimator = TwoFactorResidualEstimator(ridge_lambda=0.0, min_samples=30)
        self.btc_classifier = BtcStateClassifier()
        self.reversal_detector = FirstReversalDetector()
        self.exit_calculator = ReferencePriceExitCalculator()
        self.state_machines: Dict[str, ShockStateMachine] = {}
        self._bar_counters: Dict[str, int] = {}

    def get_state_machine(self, symbol: str) -> ShockStateMachine:
        """Retrieve or initialize the shock state machine for a symbol."""
        if symbol not in self.state_machines:
            self.state_machines[symbol] = ShockStateMachine(
                max_wait_bars=self.max_wait_bars,
                cooldown_bars=self.cooldown_bars,
            )
            self._bar_counters[symbol] = 0
        return self.state_machines[symbol]

    def reset_state(self, symbol: Optional[str] = None) -> None:
        """Reset state machine for testing or lifecycle reset."""
        if symbol:
            self.state_machines.pop(symbol, None)
            self._bar_counters.pop(symbol, None)
        else:
            self.state_machines.clear()
            self._bar_counters.clear()

    def generate_signal(
        self,
        symbol: str,
        timestamp_ns: int,
        r_alt_series: List[float],
        r_btc_series: List[float],
        r_eth_series: List[float],
        btc_returns_1m_5m_15m: Tuple[Optional[float], Optional[float], Optional[float]],
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
        allowed_risk_usd: Optional[float] = None,
        timestamps_series: Optional[List[int]] = None,
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

        sm = self.get_state_machine(symbol)
        self._bar_counters[symbol] += 1
        bar_idx = self._bar_counters[symbol]

        # 1. 2-Factor Residual Estimation (Pre-shock history vs candidate bar t)
        # Partition series into pre-shock (0..N-2) and candidate shock bar (N-1)
        n = min(len(r_alt_series), len(r_btc_series), len(r_eth_series))
        if n < 31:
            diagnostics = {
                "decision": "MODEL_NOT_READY",
                "reason": f"Insufficient pre-shock history: {n-1} < 30 required observations.",
                "model_status": ModelStatus.NOT_READY.value,
            }
            return False, None, diagnostics

        r_alt_pre = r_alt_series[: n - 1]
        r_btc_pre = r_btc_series[: n - 1]
        r_eth_pre = r_eth_series[: n - 1]
        ts_pre = timestamps_series[: n - 1] if timestamps_series else None

        fit = self.factor_estimator.fit_pre_shock(
            r_alt=r_alt_pre,
            r_btc=r_btc_pre,
            r_eth=r_eth_pre,
            timestamps=ts_pre,
        )

        if fit.status == ModelStatus.INVALID:
            diagnostics = {
                "decision": "MODEL_INVALID",
                "reason": f"Degenerate factor inputs: {fit.error_message}",
                "model_status": ModelStatus.INVALID.value,
            }
            return False, None, diagnostics
        elif fit.status == ModelStatus.NOT_READY:
            diagnostics = {
                "decision": "MODEL_NOT_READY",
                "reason": f"Pre-shock model not ready: {fit.error_message}",
                "model_status": ModelStatus.NOT_READY.value,
            }
            return False, None, diagnostics

        # Evaluate candidate bar t using frozen pre-shock parameters
        current_eps, z_score = self.factor_estimator.evaluate_shock_at_t(
            fit=fit,
            r_alt_t=r_alt_series[-1],
            r_btc_t=r_btc_series[-1],
            r_eth_t=r_eth_series[-1],
        )

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

        # 3. First Reversal Verification
        reversal_confirmed, rev_type, replenishment_ratio = self.reversal_detector.evaluate(
            delta_5s=delta_5s,
            current_bid_depth_0_5pct=bid_depth_0_5pct,
            pre_shock_median_depth=pre_shock_median_depth,
            recent_1s_lows=recent_1s_lows,
        )

        # 4. Advance Shock State Machine
        should_emit = sm.step(
            z_score=z_score,
            current_price=current_price,
            reversal_confirmed=reversal_confirmed,
            btc_state_allowed=matrix_allowed,
            bar_index=bar_idx,
            origin_price=pre_shock_origin,
        )

        # Handle non-emitting states
        if not should_emit:
            if sm.state == ShockState.COOLDOWN:
                decision_state = "COOLDOWN"
                reason_str = f"In cooldown ({sm.bars_cooldown} bars remaining) following shock {sm.active_shock_id}"
            elif sm.state == ShockState.WAITING_FOR_REVERSAL:
                decision_state = "WAITING_CONFIRMATION"
                reason_str = f"Shock detected ({sm.active_shock_id}); waiting for first reversal confirmation ({sm.bars_waiting}/{sm.max_wait_bars} bars)"
            elif sm.state == ShockState.EXPIRED:
                decision_state = "EXPIRED"
                reason_str = f"Wait window expired without reversal confirmation; knife-catch avoided."
            elif z_score > -3.0:
                decision_state = "NO_SHOCK"
                reason_str = f"No shock detected (z-score: {z_score:.2f} > -3.0 sigma)"
            elif not matrix_allowed:
                decision_state = "BLOCKED"
                reason_str = f"BTC Decision Matrix blocked entry: {behavior}"
            else:
                decision_state = "BLOCKED"
                reason_str = f"Blocked: {behavior}"

            diagnostics = {
                "decision": decision_state,
                "reason": reason_str,
                "btc_state": btc_state.value,
                "z_score": z_score,
                "state_machine_state": sm.state.value,
                "shock_id": sm.active_shock_id,
                "replenishment_ratio": replenishment_ratio,
            }
            return False, None, diagnostics

        # 5. Calculate exit targets and mandatory Hard Stop Loss
        exit_targets = self.exit_calculator.calculate_targets(
            entry_price=current_price,
            pre_shock_origin=pre_shock_origin,
            pre_shock_vwap=pre_shock_vwap,
            shock_bottom=sm.shock_bottom_price,
        )

        # 6. Risk-budget position sizing
        risk_budget = allowed_risk_usd if allowed_risk_usd is not None else self.default_allowed_risk_usd
        risk_dist = exit_targets["risk_distance"]
        if risk_dist <= 0:
            diagnostics = {
                "decision": "BLOCKED",
                "reason": "Invalid risk distance <= 0",
            }
            return False, None, diagnostics

        raw_qty = risk_budget / risk_dist
        final_qty = raw_qty * sizing_mult
        notional_usd = final_qty * current_price

        # 7. RegimeSnapshot creation with complete 23+ fields and Hard Stop
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
            beta_down=fit.beta_down,
            beta_up=fit.beta_up,
            gamma_eth=fit.gamma_eth,
            reversal_detector_triggered=rev_type.value if rev_type else None,
            book_replenishment_ratio=replenishment_ratio,
            pre_shock_vwap=pre_shock_vwap,
            pre_shock_origin=pre_shock_origin,
            entry_price=current_price,
            stop_price=exit_targets["stop_loss"],
            risk_distance=risk_dist,
        )

        diagnostics = {
            "decision": "EXECUTE_LONG",
            "sizing_multiplier": sizing_mult,
            "behavior": behavior,
            "exit_targets": exit_targets,
            "stop_loss": exit_targets["stop_loss"],
            "risk_distance": risk_dist,
            "risk_pct": exit_targets["risk_pct"],
            "allowed_risk_usd": risk_budget,
            "position_quantity": final_qty,
            "notional_usd": notional_usd,
            "reversal_type": rev_type.value if rev_type else None,
            "max_holding_seconds": self.max_holding_seconds,
            "shock_id": sm.active_shock_id,
            "state_machine_state": sm.state.value,
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
