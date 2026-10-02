"""Tests for digital call probability, analytic strike derivative with skew, and finite difference convergence."""

import math
import pytest
from src.quant.black76 import calc_d1_d2, norm_cdf, call_price
from src.quant.digital_probability import (
    strike_derivative_analytic,
    digital_call_prob_analytic,
    strike_derivative_numeric,
    digital_call_prob_numeric,
    check_finite_difference_convergence,
)
from src.quant.smile_validation import LinearSkewSmile, FlatVolSmile, make_pricing_fn


def test_flat_vol_reduces_to_norm_cdf_d2():
    """HARD PASS REQUIREMENT: If dsigma/dK = 0, P_RN MUST reduce to N(d2)."""
    test_cases = [
        (70000.0, 70000.0, 0.55, 0.1, 0.0),
        (70000.0, 65000.0, 0.60, 0.25, 0.04),
        (70000.0, 80000.0, 0.50, 0.5, 0.02),
        (100.0, 105.0, 0.20, 1.0, 0.05),
    ]
    for F, K, sigma, T, r in test_cases:
        _, d2 = calc_d1_d2(F, K, sigma, T)
        expected_prob = norm_cdf(d2)
        
        # Analytic digital probability with zero skew
        p_analytic = digital_call_prob_analytic(F, K, sigma, dsigma_dK=0.0, T=T, r=r)
        
        assert abs(p_analytic - expected_prob) < 1e-15, (
            f"Flat vol digital probability {p_analytic} did not match N(d2) {expected_prob}"
        )


def test_analytic_vs_numeric_zero_skew():
    """Verify analytic derivative against central finite difference under zero skew."""
    F = 70000.0
    K = 72000.0
    sigma = 0.50
    T = 0.25
    r = 0.03
    
    smile = FlatVolSmile(sigma)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, sigma, dsigma_dK=0.0, T=T, r=r)
    
    # Epsilon = 1.0 on a 70k strike (~1.4e-5 relative)
    eps = 1.0
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=eps, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-6


def test_analytic_vs_numeric_negative_skew():
    """Verify analytic derivative against central finite difference with negative skew (dsigma/dK < 0)."""
    F = 70000.0
    K = 70000.0
    sigma_0 = 0.55
    slope = -0.10  # negative skew: vol decreases as strike increases
    K0 = 70000.0
    T = 0.25
    r = 0.0
    
    smile = LinearSkewSmile(sigma_0=sigma_0, slope=slope, K0=K0)
    dsigma_dK = smile.dvol_dK(K)
    sigma_at_K = smile.vol(K)
    
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, sigma_at_K, dsigma_dK=dsigma_dK, T=T, r=r)
    
    # Check numeric derivative across multiple epsilons
    for eps in [5.0, 1.0, 0.5, 0.1]:
        p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=eps, r=r, T=T)
        assert abs(p_analytic - p_numeric) < 1e-5


def test_analytic_vs_numeric_positive_skew():
    """Verify analytic derivative against central finite difference with positive skew (dsigma/dK > 0)."""
    F = 70000.0
    K = 75000.0
    sigma_0 = 0.50
    slope = 0.15  # positive skew
    K0 = 70000.0
    T = 0.5
    r = 0.02
    
    smile = LinearSkewSmile(sigma_0=sigma_0, slope=slope, K0=K0)
    dsigma_dK = smile.dvol_dK(K)
    sigma_at_K = smile.vol(K)
    
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(F, K, sigma_at_K, dsigma_dK=dsigma_dK, T=T, r=r)
    p_numeric = digital_call_prob_numeric(pricing_fn, K, epsilon=1.0, r=r, T=T)
    
    assert abs(p_analytic - p_numeric) < 1e-5


def test_skew_sign_direction_verification():
    """Verify empirical impact of skew sign on digital call probability.
    
    Formula: P_RN = N(d2) - F * phi(d1) * sqrt(T) * dsigma/dK
    When dsigma/dK < 0, the correction term is POSITIVE:
        P_RN > N(d2)
    When dsigma/dK > 0, the correction term is NEGATIVE:
        P_RN < N(d2)
    """
    F = 70000.0
    K = 70000.0
    sigma_0 = 0.50
    T = 0.25
    r = 0.0
    
    _, d2 = calc_d1_d2(F, K, sigma_0, T)
    flat_prob = norm_cdf(d2)
    
    # Negative skew
    neg_smile = LinearSkewSmile(sigma_0=sigma_0, slope=-0.15, K0=F)
    p_neg_analytic = digital_call_prob_analytic(F, K, sigma_0, neg_smile.dvol_dK(K), T, r)
    p_neg_numeric = digital_call_prob_numeric(make_pricing_fn(neg_smile, F, T, r), K, epsilon=1.0, r=r, T=T)
    
    # Both analytic and numeric MUST be strictly greater than flat_prob
    assert p_neg_analytic > flat_prob
    assert p_neg_numeric > flat_prob
    assert abs(p_neg_analytic - p_neg_numeric) < 1e-5
    
    # Positive skew
    pos_smile = LinearSkewSmile(sigma_0=sigma_0, slope=0.15, K0=F)
    p_pos_analytic = digital_call_prob_analytic(F, K, sigma_0, pos_smile.dvol_dK(K), T, r)
    p_pos_numeric = digital_call_prob_numeric(make_pricing_fn(pos_smile, F, T, r), K, epsilon=1.0, r=r, T=T)
    
    # Both analytic and numeric MUST be strictly less than flat_prob
    assert p_pos_analytic < flat_prob
    assert p_pos_numeric < flat_prob
    assert abs(p_pos_analytic - p_pos_numeric) < 1e-5


def test_finite_difference_convergence_rates():
    """Test convergence of central finite difference across 5 orders of epsilon.
    
    For central differences, error is O(epsilon^2):
    halving epsilon reduces error by ~4x (slope = 2 in log-log space).
    """
    F = 70000.0
    K = 70000.0
    sigma_0 = 0.55
    slope = -0.08
    K0 = 70000.0
    T = 0.25
    r = 0.04
    
    smile = LinearSkewSmile(sigma_0=sigma_0, slope=slope, K0=K0)
    pricing_fn = make_pricing_fn(smile, F, T, r=r)
    
    p_analytic = digital_call_prob_analytic(
        F, K, smile.vol(K), smile.dvol_dK(K), T=T, r=r
    )
    
    # Test epsilons spanning 4 orders of magnitude: 100, 10, 1, 0.1, 0.01
    epsilons = [100.0, 10.0, 1.0, 0.1, 0.01]
    results = check_finite_difference_convergence(
        p_analytic, pricing_fn, K, epsilons, r=r, T=T
    )
    
    # 1. In the asymptotic regime (eps = 100 -> 10 -> 1), error is dominated by O(eps^2) truncation
    for i in range(2):
        err_current = results[i]["abs_error"]
        err_next = results[i + 1]["abs_error"]
        assert err_next < err_current, f"Error did not decrease from eps={epsilons[i]} to eps={epsilons[i+1]}"
        # For a 10x drop in epsilon, O(eps^2) predicts ~100x drop in error
        ratio = err_current / max(err_next, 1e-15)
        assert ratio > 80.0, f"Expected ~100x error reduction for 10x epsilon step, got {ratio:.1f}x"
    
    # 2. At eps = 0.1, error reaches machine-precision floor (< 1e-11)
    assert results[3]["abs_error"] < 1e-11
    # 3. Across all reasonable epsilons in [10, 1, 0.1], absolute error is strictly < 1e-7
    for res in results[1:4]:
        assert res["abs_error"] < 1e-7
