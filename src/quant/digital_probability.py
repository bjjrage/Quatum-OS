"""Digital call probability and strike derivative calculations under volatility skew.

Mathematical Derivation:
------------------------
For a discounted Black-76 call price with strike-dependent volatility sigma(K):
    C(K, sigma(K)) = exp(-r*T) * [F * N(d1) - K * N(d2)]

Differentiating with respect to strike K by the chain rule:
    dC/dK = (dC/dK)|_sigma + (dC/dsigma)|_K * (dsigma/dK)

Because F * phi(d1) = K * phi(d2), the inner partial derivative simplifies to:
    (dC/dK)|_sigma = -exp(-r*T) * N(d2)

And the vega term is:
    Vega = (dC/dsigma)|_K = exp(-r*T) * F * phi(d1) * sqrt(T)

Therefore, the exact total strike derivative is:
    dC/dK = -exp(-r*T) * N(d2) + Vega * (dsigma/dK)
          = -exp(-r*T) * [N(d2) - F * phi(d1) * sqrt(T) * (dsigma/dK)]

By Breeden-Litzenberger (1978), the undiscounted risk-neutral digital call probability is:
    P_RN(S_T >= K) = -exp(r*T) * (dC/dK)
                   = N(d2) - F * phi(d1) * sqrt(T) * (dsigma/dK)

When dsigma/dK = 0 (flat volatility), this strictly reduces to N(d2).
"""

import math
from typing import Callable, List, Dict, Any, Tuple
from src.quant.black76 import calc_d1_d2, norm_cdf, norm_pdf, vega


def strike_derivative_analytic(
    F: float,
    K: float,
    sigma: float,
    dsigma_dK: float,
    T: float,
    r: float = 0.0,
) -> float:
    """Calculate the exact analytical first derivative of discounted call price w.r.t strike K.
    
    dC/dK = -exp(-r*T) * N(d2) + Vega * dsigma/dK
    
    Args:
        F: Forward price
        K: Strike price
        sigma: Implied volatility at strike K
        dsigma_dK: First derivative of implied volatility w.r.t strike K
        T: Time to expiration in years
        r: Risk-free rate
        
    Returns:
        dC/dK (strictly negative for non-arbitrage call surfaces)
    """
    _, d2 = calc_d1_d2(F, K, sigma, T)
    v = vega(F, K, sigma, T, r=r)
    discount = math.exp(-r * T)
    
    return -discount * norm_cdf(d2) + v * dsigma_dK


def digital_call_prob_analytic(
    F: float,
    K: float,
    sigma: float,
    dsigma_dK: float,
    T: float,
    r: float = 0.0,
) -> float:
    """Calculate undiscounted risk-neutral probability P_RN(S_T >= K) analytically.
    
    P_RN = -exp(r*T) * (dC/dK) = N(d2) - F * phi(d1) * sqrt(T) * dsigma/dK
    
    Args:
        F: Forward price
        K: Strike price
        sigma: Implied volatility at strike K
        dsigma_dK: First derivative of implied volatility w.r.t strike K
        T: Time to expiration in years
        r: Risk-free rate
        
    Returns:
        Risk-neutral probability in [0, 1]
    """
    d1, d2 = calc_d1_d2(F, K, sigma, T)
    sqrt_T = math.sqrt(T)
    skew_correction = F * norm_pdf(d1) * sqrt_T * dsigma_dK
    return norm_cdf(d2) - skew_correction


def strike_derivative_numeric(
    pricing_fn: Callable[[float], float],
    K: float,
    epsilon: float,
) -> float:
    """Calculate central finite difference approximation of dC/dK.
    
    dC/dK ≈ [C(K + epsilon) - C(K - epsilon)] / (2 * epsilon)
    
    Args:
        pricing_fn: Callable taking strike K and returning discounted call price C(K)
        K: Center strike price
        epsilon: Perturbation step size
        
    Returns:
        Approximated dC/dK
    """
    if epsilon <= 0:
        raise ValueError(f"Epsilon must be positive, got {epsilon}")
    if K - epsilon <= 0:
        raise ValueError(f"K - epsilon must be positive, got K={K}, eps={epsilon}")
        
    c_plus = pricing_fn(K + epsilon)
    c_minus = pricing_fn(K - epsilon)
    return (c_plus - c_minus) / (2.0 * epsilon)


def digital_call_prob_numeric(
    pricing_fn: Callable[[float], float],
    K: float,
    epsilon: float,
    r: float = 0.0,
    T: float = 1.0,
) -> float:
    """Calculate undiscounted risk-neutral probability via central finite differences.
    
    P_numeric = -exp(r*T) * [C(K + epsilon) - C(K - epsilon)] / (2 * epsilon)
    
    Args:
        pricing_fn: Callable taking strike K and returning discounted call price C(K)
        K: Center strike price
        epsilon: Perturbation step size
        r: Risk-free rate
        T: Time to expiration in years
        
    Returns:
        Approximated risk-neutral probability
    """
    dC_dK = strike_derivative_numeric(pricing_fn, K, epsilon)
    return -math.exp(r * T) * dC_dK


def second_strike_derivative_numeric(
    pricing_fn: Callable[[float], float],
    K: float,
    epsilon: float,
) -> float:
    """Calculate central finite difference approximation of d²C/dK².
    
    d²C/dK² ≈ [C(K + epsilon) - 2 * C(K) + C(K - epsilon)] / (epsilon^2)
    
    Args:
        pricing_fn: Callable taking strike K and returning discounted call price C(K)
        K: Center strike price
        epsilon: Perturbation step size
        
    Returns:
        Approximated d²C/dK² (convexity)
    """
    if epsilon <= 0:
        raise ValueError(f"Epsilon must be positive, got {epsilon}")
    if K - epsilon <= 0:
        raise ValueError(f"K - epsilon must be positive, got K={K}, eps={epsilon}")

    c_plus = pricing_fn(K + epsilon)
    c_center = pricing_fn(K)
    c_minus = pricing_fn(K - epsilon)
    return (c_plus - 2.0 * c_center + c_minus) / (epsilon * epsilon)


def risk_neutral_density_numeric(
    pricing_fn: Callable[[float], float],
    K: float,
    epsilon: float,
    r: float = 0.0,
    T: float = 1.0,
) -> float:
    """Calculate Breeden-Litzenberger risk-neutral density q(K) = exp(r*T) * d²C/dK².
    
    Args:
        pricing_fn: Callable taking strike K and returning discounted call price C(K)
        K: Center strike price
        epsilon: Perturbation step size
        r: Risk-free rate
        T: Time to expiration in years
        
    Returns:
        Risk-neutral density q(K) >= 0
    """
    d2C_dK2 = second_strike_derivative_numeric(pricing_fn, K, epsilon)
    return math.exp(r * T) * d2C_dK2


def check_finite_difference_convergence(
    analytic_prob: float,
    pricing_fn: Callable[[float], float],
    K: float,
    epsilons: List[float],
    r: float = 0.0,
    T: float = 1.0,
) -> List[Dict[str, Any]]:
    """Test convergence of numerical central finite difference against analytic value across multiple epsilons.
    
    Verifies that errors decrease quadratically O(epsilon^2) as epsilon decreases,
    before machine roundoff limits are reached.
    """
    results = []
    for eps in epsilons:
        num_prob = digital_call_prob_numeric(pricing_fn, K, eps, r=r, T=T)
        abs_err = abs(num_prob - analytic_prob)
        rel_err = abs_err / abs(analytic_prob) if analytic_prob != 0 else abs_err
        results.append({
            "epsilon": eps,
            "numeric_prob": num_prob,
            "analytic_prob": analytic_prob,
            "abs_error": abs_err,
            "rel_error": rel_err,
        })
    return results
