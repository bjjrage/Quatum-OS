"""Synthetic smile functions and arbitrage consistency validation for call curves.

NOTE: This module contains TEST / VALIDATION infrastructure for the mathematical spike.
It is NOT a production SVI surface calibrator.

Arbitrage Conditions Verified:
1. Call Price Monotonicity: dC/dK <= 0 (call price decreases with strike).
2. Call Price Convexity: d²C/dK² >= 0 (butterfly spread payoff is non-negative).
3. Risk-Neutral Density: q(K) = exp(r*T) * d²C/dK² >= -tol (non-negative probability density).
4. Probability Bounds: 0 <= P_RN(S_T >= K) <= 1.

Fails loudly with ArbitrageViolationError if any condition is violated beyond numerical tolerance.
"""

import math
from typing import Protocol, List, Dict, Any, Callable
from src.quant.black76 import call_price
from src.quant.digital_probability import (
    strike_derivative_analytic,
    strike_derivative_numeric,
    digital_call_prob_analytic,
    digital_call_prob_numeric,
    second_strike_derivative_numeric,
    risk_neutral_density_numeric,
)


class ArbitrageViolationError(Exception):
    """Raised when an option surface violates no-arbitrage bounds (monotonicity, convexity, density)."""
    pass


class VolatilitySmile(Protocol):
    """Protocol for volatility smile models."""
    def vol(self, K: float) -> float:
        ...
    def dvol_dK(self, K: float) -> float:
        ...


class FlatVolSmile:
    """Flat volatility surface (constant volatility for all strikes)."""
    def __init__(self, sigma: float):
        if sigma <= 0:
            raise ValueError(f"sigma must be positive, got {sigma}")
        self.sigma = sigma

    def vol(self, K: float) -> float:
        return self.sigma

    def dvol_dK(self, K: float) -> float:
        return 0.0


class LinearSkewSmile:
    """Linear volatility skew around reference strike K0.
    
    sigma(K) = sigma_0 + slope * ((K - K0) / K0)
    dsigma/dK = slope / K0
    """
    def __init__(self, sigma_0: float, slope: float, K0: float):
        if sigma_0 <= 0:
            raise ValueError(f"sigma_0 must be positive, got {sigma_0}")
        if K0 <= 0:
            raise ValueError(f"K0 must be positive, got {K0}")
        self.sigma_0 = sigma_0
        self.slope = slope
        self.K0 = K0

    def vol(self, K: float) -> float:
        v = self.sigma_0 + self.slope * ((K - self.K0) / self.K0)
        if v <= 0:
            raise ValueError(f"Volatility became non-positive ({v}) at K={K}")
        return v

    def dvol_dK(self, K: float) -> float:
        return self.slope / self.K0


class QuadraticSmile:
    """Smooth quadratic volatility smile around reference strike K0.
    
    sigma(K) = sigma_0 + skew * ((K - K0) / K0) + curvature * ((K - K0) / K0)^2
    dsigma/dK = skew / K0 + 2 * curvature * (K - K0) / (K0^2)
    """
    def __init__(self, sigma_0: float, skew: float, curvature: float, K0: float):
        if sigma_0 <= 0:
            raise ValueError(f"sigma_0 must be positive, got {sigma_0}")
        if K0 <= 0:
            raise ValueError(f"K0 must be positive, got {K0}")
        self.sigma_0 = sigma_0
        self.skew = skew
        self.curvature = curvature
        self.K0 = K0

    def vol(self, K: float) -> float:
        norm_m = (K - self.K0) / self.K0
        v = self.sigma_0 + self.skew * norm_m + self.curvature * (norm_m ** 2)
        if v <= 0:
            raise ValueError(f"Volatility became non-positive ({v}) at K={K}")
        return v

    def dvol_dK(self, K: float) -> float:
        norm_m = (K - self.K0) / self.K0
        return (self.skew + 2.0 * self.curvature * norm_m) / self.K0


def make_pricing_fn(
    smile: VolatilitySmile,
    F: float,
    T: float,
    r: float = 0.0,
) -> Callable[[float], float]:
    """Create a single-argument pricing function C(K) given a smile and market parameters."""
    return lambda K: call_price(F, K, smile.vol(K), T, r=r)


def check_call_monotonicity(
    pricing_fn: Callable[[float], float],
    strikes: List[float],
    tol: float = 1e-12,
) -> bool:
    """Verify that call prices are strictly non-increasing with strike: C(K1) >= C(K2) for K1 < K2.
    
    Fails loudly with ArbitrageViolationError if a violation is detected.
    """
    sorted_strikes = sorted(strikes)
    prev_c = None
    prev_k = None
    for k in sorted_strikes:
        c = pricing_fn(k)
        if prev_c is not None:
            # Monotonicity requires c <= prev_c + tol
            if c > prev_c + tol:
                raise ArbitrageViolationError(
                    f"Monotonicity violated: Call price increased from {prev_c:.8f} at K={prev_k} "
                    f"to {c:.8f} at K={k} (diff = {c - prev_c:.8e})"
                )
        prev_c = c
        prev_k = k
    return True


def check_call_convexity(
    pricing_fn: Callable[[float], float],
    strikes: List[float],
    epsilon: float,
    tol: float = 1e-10,
) -> bool:
    """Verify that the call curve is convex: d²C/dK² >= -tol.
    
    Fails loudly with ArbitrageViolationError if negative convexity (butterfly arbitrage) is detected.
    """
    for k in strikes:
        d2c = second_strike_derivative_numeric(pricing_fn, k, epsilon)
        if d2c < -tol:
            raise ArbitrageViolationError(
                f"Convexity violated at K={k}: d²C/dK² = {d2c:.8e} < -{tol}"
            )
    return True


def check_risk_neutral_density(
    pricing_fn: Callable[[float], float],
    strikes: List[float],
    epsilon: float,
    r: float = 0.0,
    T: float = 1.0,
    tol: float = 1e-10,
) -> bool:
    """Verify that Breeden-Litzenberger risk-neutral density q(K) >= -tol across strikes.
    
    Fails loudly with ArbitrageViolationError if negative density is detected.
    """
    for k in strikes:
        density = risk_neutral_density_numeric(pricing_fn, k, epsilon, r=r, T=T)
        if density < -tol:
            raise ArbitrageViolationError(
                f"Negative risk-neutral density at K={k}: q(K) = {density:.8e} < -{tol}"
            )
    return True


def check_probability_bounds(
    prob_fn: Callable[[float], float],
    strikes: List[float],
    tol: float = 1e-6,
) -> bool:
    """Verify that digital probabilities P(S_T >= K) lie strictly in [0.0 - tol, 1.0 + tol].
    
    Fails loudly with ArbitrageViolationError if probability bounds are breached.
    """
    for k in strikes:
        p = prob_fn(k)
        if p < -tol or p > 1.0 + tol:
            raise ArbitrageViolationError(
                f"Probability out of bounds at K={k}: P = {p:.8f} (tol={tol})"
            )
    return True
