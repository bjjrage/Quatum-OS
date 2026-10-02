"""Tests for Black-76 core pricing model and greeks."""

import math
import pytest
from src.quant.black76 import (
    calc_d1_d2,
    norm_cdf,
    norm_pdf,
    call_price,
    put_price,
    vega,
    flat_vol_digital_call_prob,
)


def test_norm_cdf_and_pdf():
    """Verify standard normal CDF and PDF against mathematical identities."""
    # N(0) == 0.5
    assert abs(norm_cdf(0.0) - 0.5) < 1e-15
    # Symmetry: N(x) + N(-x) == 1.0
    for x in [0.5, 1.0, 1.96, 2.58, 3.0]:
        assert abs(norm_cdf(x) + norm_cdf(-x) - 1.0) < 1e-15
    
    # PDF at x=0 is 1/sqrt(2*pi)
    expected_phi_0 = 1.0 / math.sqrt(2.0 * math.pi)
    assert abs(norm_pdf(0.0) - expected_phi_0) < 1e-15
    
    # 95% critical value
    assert abs(norm_cdf(1.959963984540054) - 0.975) < 1e-6


def test_calc_d1_d2():
    """Verify d1 and d2 calculations."""
    F = 100.0
    K = 100.0
    sigma = 0.20
    T = 1.0
    
    d1, d2 = calc_d1_d2(F, K, sigma, T)
    # At ATM (F=K), d1 = (0.5 * sigma^2 * T) / (sigma * sqrt(T)) = 0.5 * 0.20 * 1 = 0.10
    assert abs(d1 - 0.10) < 1e-12
    # d2 = d1 - sigma * sqrt(T) = 0.10 - 0.20 = -0.10
    assert abs(d2 - (-0.10)) < 1e-12
    assert abs((d1 - d2) - sigma * math.sqrt(T)) < 1e-12


def test_black76_known_benchmark():
    """Verify call and put prices against known analytical Black-76 benchmark.
    
    Benchmark:
    F = 100.0, K = 100.0, sigma = 0.20, T = 1.0, r = 0.05
    d1 = 0.10, d2 = -0.10
    discount = exp(-0.05) ≈ 0.9512294245
    N(0.10) ≈ 0.53982783724
    N(-0.10) ≈ 0.46017216275
    C = discount * 100 * (N(0.10) - N(-0.10)) = 0.9512294245 * 100 * 0.07965567448 ≈ 7.5770857
    """
    F = 100.0
    K = 100.0
    sigma = 0.20
    T = 1.0
    r = 0.05
    
    c = call_price(F, K, sigma, T, r=r)
    p = put_price(F, K, sigma, T, r=r)
    
    # Expected call: 7.57708215
    assert abs(c - 7.57708215) < 1e-6
    # For ATM (F=K), call and put prices must be identical
    assert abs(c - p) < 1e-12


def test_put_call_parity():
    """Verify Black-76 put-call parity: C - P = exp(-r*T) * (F - K)."""
    test_cases = [
        (100.0, 100.0, 0.25, 0.5, 0.04),   # ATM
        (100.0, 80.0, 0.30, 1.0, 0.05),    # ITM Call / OTM Put
        (100.0, 120.0, 0.20, 0.25, 0.03),  # OTM Call / ITM Put
        (70000.0, 65000.0, 0.55, 0.1, 0.0), # BTC scale, zero rate
        (70000.0, 85000.0, 0.60, 0.25, 0.02),
    ]
    for F, K, sigma, T, r in test_cases:
        c = call_price(F, K, sigma, T, r=r)
        p = put_price(F, K, sigma, T, r=r)
        expected_diff = math.exp(-r * T) * (F - K)
        actual_diff = c - p
        assert abs(actual_diff - expected_diff) < 1e-11, (
            f"Put-call parity failed for F={F}, K={K}, diff={actual_diff - expected_diff}"
        )


def test_vega_matches_finite_difference():
    """Verify analytic Vega against central finite difference w.r.t sigma."""
    F = 70000.0
    K = 72000.0
    sigma = 0.55
    T = 0.25
    r = 0.03
    eps = 1e-5
    
    v_analytic = vega(F, K, sigma, T, r=r)
    c_plus = call_price(F, K, sigma + eps, T, r=r)
    c_minus = call_price(F, K, sigma - eps, T, r=r)
    v_numeric = (c_plus - c_minus) / (2.0 * eps)
    
    # Relative error should be < 1e-7 due to O(eps^2) convergence
    rel_error = abs(v_analytic - v_numeric) / v_analytic
    assert rel_error < 1e-7


def test_flat_vol_digital_call_prob():
    """Verify flat-vol digital call probability strictly equals N(d2)."""
    test_cases = [
        (70000.0, 70000.0, 0.50, 0.1),
        (70000.0, 60000.0, 0.50, 0.25),
        (70000.0, 80000.0, 0.50, 0.25),
        (100.0, 150.0, 0.20, 1.0),
    ]
    for F, K, sigma, T in test_cases:
        _, d2 = calc_d1_d2(F, K, sigma, T)
        expected = norm_cdf(d2)
        prob = flat_vol_digital_call_prob(F, K, sigma, T)
        assert abs(prob - expected) < 1e-15
        assert 0.0 <= prob <= 1.0


def test_invalid_parameters():
    """Verify that negative or zero parameters raise ValueError."""
    with pytest.raises(ValueError):
        calc_d1_d2(0, 100, 0.2, 1.0)
    with pytest.raises(ValueError):
        calc_d1_d2(100, -1, 0.2, 1.0)
    with pytest.raises(ValueError):
        calc_d1_d2(100, 100, 0, 1.0)
    with pytest.raises(ValueError):
        calc_d1_d2(100, 100, 0.2, -0.5)
