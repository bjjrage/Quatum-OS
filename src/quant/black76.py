"""Black-76 reference implementation for options on forwards/futures.

Pure mathematical reference functions for:
- d1, d2
- norm_cdf, norm_pdf
- call_price, put_price
- vega
- flat_vol_digital_call_prob
"""

import math
from typing import Tuple


def norm_cdf(x: float) -> float:
    """Standard normal cumulative distribution function N(x).
    
    Uses math.erf: N(x) = 0.5 * (1 + erf(x / sqrt(2))).
    Precision matches IEEE 754 double precision (~1e-15).
    """
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_pdf(x: float) -> float:
    """Standard normal probability density function phi(x) = 1/sqrt(2*pi) * exp(-0.5 * x^2)."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def calc_d1_d2(F: float, K: float, sigma: float, T: float) -> Tuple[float, float]:
    """Calculate Black-76 d1 and d2.
    
    Args:
        F: Forward price (F > 0)
        K: Strike price (K > 0)
        sigma: Annualized volatility (sigma > 0)
        T: Time to expiration in years (T > 0)
        
    Returns:
        Tuple (d1, d2)
    """
    if F <= 0:
        raise ValueError(f"Forward price F must be positive, got {F}")
    if K <= 0:
        raise ValueError(f"Strike price K must be positive, got {K}")
    if sigma <= 0:
        raise ValueError(f"Volatility sigma must be positive, got {sigma}")
    if T <= 0:
        raise ValueError(f"Time to expiration T must be positive, got {T}")

    sqrt_T = math.sqrt(T)
    sigma_sqrt_T = sigma * sqrt_T
    d1 = (math.log(F / K) + 0.5 * sigma * sigma * T) / sigma_sqrt_T
    d2 = d1 - sigma_sqrt_T
    return d1, d2


def call_price(F: float, K: float, sigma: float, T: float, r: float = 0.0) -> float:
    """Calculate Black-76 discounted European call option price.
    
    C(F, K, sigma, T, r) = exp(-r*T) * [F * N(d1) - K * N(d2)]
    
    Args:
        F: Forward price
        K: Strike price
        sigma: Implied volatility
        T: Time to expiration in years
        r: Risk-free rate (annualized, continuous compounding)
    """
    d1, d2 = calc_d1_d2(F, K, sigma, T)
    discount = math.exp(-r * T)
    return discount * (F * norm_cdf(d1) - K * norm_cdf(d2))


def put_price(F: float, K: float, sigma: float, T: float, r: float = 0.0) -> float:
    """Calculate Black-76 discounted European put option price.
    
    P(F, K, sigma, T, r) = exp(-r*T) * [K * N(-d2) - F * N(-d1)]
    
    Args:
        F: Forward price
        K: Strike price
        sigma: Implied volatility
        T: Time to expiration in years
        r: Risk-free rate
    """
    d1, d2 = calc_d1_d2(F, K, sigma, T)
    discount = math.exp(-r * T)
    return discount * (K * norm_cdf(-d2) - F * norm_cdf(-d1))


def vega(F: float, K: float, sigma: float, T: float, r: float = 0.0) -> float:
    """Calculate Black-76 option Vega (dC/dsigma).
    
    Vega = exp(-r*T) * F * phi(d1) * sqrt(T)
         = exp(-r*T) * K * phi(d2) * sqrt(T)
         
    Args:
        F: Forward price
        K: Strike price
        sigma: Implied volatility
        T: Time to expiration in years
        r: Risk-free rate
    """
    d1, _ = calc_d1_d2(F, K, sigma, T)
    discount = math.exp(-r * T)
    return discount * F * norm_pdf(d1) * math.sqrt(T)


def flat_vol_digital_call_prob(F: float, K: float, sigma: float, T: float, r: float = 0.0) -> float:
    """Undiscounted risk-neutral digital call probability under flat volatility.
    
    Under flat volatility, dSigma/dK = 0, so:
    P_RN(S_T >= K) = -exp(r*T) * dC/dK = N(d2).
    
    Args:
        F: Forward price
        K: Strike price
        sigma: Flat implied volatility
        T: Time to expiration in years
        r: Risk-free rate (unused in N(d2) because discounting cancels)
    """
    _, d2 = calc_d1_d2(F, K, sigma, T)
    return norm_cdf(d2)
