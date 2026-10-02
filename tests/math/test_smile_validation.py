"""Comprehensive test cases A through H for smile validation, arbitrage detection, and risk-neutral density."""

import math
import pytest
from src.quant.black76 import call_price
from src.quant.digital_probability import (
    digital_call_prob_analytic,
    digital_call_prob_numeric,
    risk_neutral_density_numeric,
)
from src.quant.smile_validation import (
    FlatVolSmile,
    LinearSkewSmile,
    QuadraticSmile,
    make_pricing_fn,
    check_call_monotonicity,
    check_call_convexity,
    check_risk_neutral_density,
    check_probability_bounds,
    ArbitrageViolationError,
)


# ==============================================================================
# CASES A - H: Comprehensive Scenarios
# ==============================================================================

def test_case_a_atm_flat_vol():
    """CASE A: ATM flat volatility."""
    F = 70000.0
    K = 70000.0
    sigma = 0.50
    T = 0.25
    r = 0.03
    
    smile = FlatVolSmile(sigma)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, sigma, 0.0, T, r)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-6
    assert 0.0 < p_analytic < 1.0


def test_case_b_otm_flat_vol():
    """CASE B: OTM call flat volatility (K > F)."""
    F = 70000.0
    K = 85000.0
    sigma = 0.50
    T = 0.25
    r = 0.03
    
    smile = FlatVolSmile(sigma)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, sigma, 0.0, T, r)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-6
    assert 0.0 < p_analytic < 0.50


def test_case_c_itm_flat_vol():
    """CASE C: ITM call flat volatility (K < F)."""
    F = 70000.0
    K = 55000.0
    sigma = 0.50
    T = 0.25
    r = 0.03
    
    smile = FlatVolSmile(sigma)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, sigma, 0.0, T, r)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-6
    assert 0.50 < p_analytic < 1.0


def test_case_d_negative_skew():
    """CASE D: Negative skew (dsigma/dK < 0)."""
    F = 70000.0
    K = 70000.0
    sigma_0 = 0.55
    slope = -0.12  # Crypto downside puts trade at higher IV
    T = 0.25
    r = 0.0
    
    smile = LinearSkewSmile(sigma_0, slope, K0=F)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, smile.vol(K), smile.dvol_dK(K), T, r)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-5
    # Negative skew increases digital call prob relative to flat
    p_flat = digital_call_prob_analytic(F, K, sigma_0, 0.0, T, r)
    assert p_analytic > p_flat


def test_case_e_positive_skew():
    """CASE E: Positive skew (dsigma/dK > 0)."""
    F = 70000.0
    K = 70000.0
    sigma_0 = 0.50
    slope = 0.12
    T = 0.25
    r = 0.0
    
    smile = LinearSkewSmile(sigma_0, slope, K0=F)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, smile.vol(K), smile.dvol_dK(K), T, r)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-5
    p_flat = digital_call_prob_analytic(F, K, sigma_0, 0.0, T, r)
    assert p_analytic < p_flat


def test_case_f_short_maturity():
    """CASE F: Short maturity (T = 1 day = 1/365 year ≈ 0.00274)."""
    F = 70000.0
    K = 70200.0
    sigma = 0.50
    T = 1.0 / 365.0
    r = 0.0
    
    smile = FlatVolSmile(sigma)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, sigma, 0.0, T, r)
    # For small T, central difference epsilon must be scaled appropriately (e.g. 0.1)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=0.1, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-5
    assert 0.0 <= p_analytic <= 1.0


def test_case_g_longer_maturity():
    """CASE G: Longer maturity (T = 2.0 years)."""
    F = 70000.0
    K = 80000.0
    sigma = 0.65
    T = 2.0
    r = 0.04
    
    smile = QuadraticSmile(sigma_0=sigma, skew=-0.08, curvature=0.05, K0=F)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, smile.vol(K), smile.dvol_dK(K), T, r)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-5
    assert 0.0 <= p_analytic <= 1.0


def test_case_h_strike_grid():
    """CASE H: Multiple strikes across an extensive grid (moneyness 0.6 to 1.4)."""
    F = 70000.0
    T = 0.25
    r = 0.03
    smile = QuadraticSmile(sigma_0=0.55, skew=-0.10, curvature=0.08, K0=F)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    strikes = [F * m for m in [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]]
    
    for K in strikes:
        p_analytic = digital_call_prob_analytic(F, K, smile.vol(K), smile.dvol_dK(K), T, r)
        p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
        
        # Absolute difference between analytic and numeric across entire grid
        assert abs(p_analytic - p_numeric) < 1e-5, f"Discrepancy at K={K}: analytic={p_analytic}, num={p_numeric}"
        assert 0.0 <= p_analytic <= 1.0


# ==============================================================================
# ARBITRAGE CONDITIONS & DENSITY TESTS
# ==============================================================================

def test_arbitrage_checks_pass_on_valid_surface():
    """Verify that a well-behaved quadratic smile passes monotonicity, convexity, and density checks."""
    F = 70000.0
    T = 0.5
    r = 0.02
    smile = QuadraticSmile(sigma_0=0.50, skew=-0.05, curvature=0.04, K0=F)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    strikes = [F * m for m in [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]]
    
    assert check_call_monotonicity(pricing_fn, strikes) is True
    assert check_call_convexity(pricing_fn, strikes, epsilon=1.0) is True
    assert check_risk_neutral_density(pricing_fn, strikes, epsilon=1.0, r=r, T=T) is True
    
    prob_fn = lambda k: digital_call_prob_analytic(F, k, smile.vol(k), smile.dvol_dK(k), T, r)
    assert check_probability_bounds(prob_fn, strikes) is True


def test_arbitrage_violation_monotonicity_fails_loudly():
    """Verify that an inverted/arbitrage call curve raises ArbitrageViolationError loudly."""
    # Arbitrary non-monotonic function where price increases with strike
    invalid_pricing_fn = lambda K: 100.0 + 0.1 * K
    strikes = [50000.0, 60000.0, 70000.0]
    
    with pytest.raises(ArbitrageViolationError, match="Monotonicity violated"):
        check_call_monotonicity(invalid_pricing_fn, strikes)


def test_arbitrage_violation_negative_convexity_fails_loudly():
    """Verify that negative convexity (butterfly arbitrage) raises ArbitrageViolationError loudly."""
    # Concave pricing function: C(K) = - (K - 70000)^2 -> d²C/dK² < 0
    invalid_pricing_fn = lambda K: 1000.0 - 0.001 * ((K - 70000.0) ** 2)
    strikes = [70000.0]
    
    with pytest.raises(ArbitrageViolationError, match="Convexity violated"):
        check_call_convexity(invalid_pricing_fn, strikes, epsilon=1.0)


def test_arbitrage_violation_negative_density_fails_loudly():
    """Verify that negative risk-neutral density raises ArbitrageViolationError loudly."""
    invalid_pricing_fn = lambda K: 1000.0 - 0.001 * ((K - 70000.0) ** 2)
    strikes = [70000.0]
    
    with pytest.raises(ArbitrageViolationError, match="Negative risk-neutral density"):
        check_risk_neutral_density(invalid_pricing_fn, strikes, epsilon=1.0, r=0.0, T=1.0)
