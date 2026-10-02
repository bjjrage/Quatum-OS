"""Deribit inverse-option treatment, numéraire transformation proof, and normalized inputs.

MATHEMATICAL FOUNDATION & NUMÉRAIRE PROOF
=========================================

1. DERIBIT CONTRACT SPECIFICATION:
   - Underlying: BTC or ETH spot index (USD per coin).
   - Strike Price K: Quoted in USD (e.g., $70,000).
   - Option Premium C_coin: Quoted in underlying cryptocurrency (e.g., 0.05 BTC).
   - Settlement Currency: BTC (coin-margined).
   - Settlement Price S_T: Deribit 30-minute TWAP index in USD at expiration T.

2. TERMINAL PAYOFF CONVENTION:
   At expiration T, the European call payoff delivered in BTC is:
       Pi_T^{call, BTC} = max((S_T - K) / S_T, 0)   [units: BTC]
   
   To convert this terminal payoff to USD at time T, multiply by the spot settlement price S_T (USD/BTC):
       Pi_T^{call, USD} = Pi_T^{call, BTC} * S_T
                        = max((S_T - K) / S_T, 0) * S_T
                        = max(S_T - K, 0)           [units: USD]

   THEOREM 1 (Terminal Payoff Equivalence):
   The USD cash value of the Deribit inverse option at expiration T is IDENTICAL
   to a standard vanilla European option in USD.

3. VALUATION & CHANGE OF NUMÉRAIRE:
   Let Q be the USD risk-neutral measure with domestic money-market account B_t = exp(r*t).
   The time-t USD value of the terminal payoff is:
       V_t^{USD} = exp(-r*(T - t)) * E^Q [ max(S_T - K, 0) | F_t ]
                 = C_B76(F, K, sigma, T - t, r)

   Now consider the BTC measure Q^{BTC} with the coin S_t as numéraire.
   By the Change of Numéraire theorem (Radon-Nikodym derivative dQ^{BTC}/dQ = S_T * exp(-r*(T-t)) / S_t):
       C_coin(t) = E^{Q^{BTC}} [ Pi_T^{call, BTC} | F_t ]
                 = E^Q [ (S_T * exp(-r*(T-t)) / S_t) * (max(S_T - K, 0) / S_T) | F_t ]
                 = (exp(-r*(T-t)) / S_t) * E^Q [ max(S_T - K, 0) | F_t ]
                 = V_t^{USD} / S_t

   Multiplying both sides by S_t:
       V_t^{USD} = C_coin(t) * S_t

   THEOREM 2 (Law of One Price):
   Converting coin premium to USD via V_t^{USD} = C_coin(t) * S_t is mathematically exact
   under both domestic and foreign/crypto risk-neutral measures.

4. DERIBIT PRICING ENGINE CONVENTIONS (Forward vs Spot):
   Deribit quotes implied volatility sigma using the Black-76 formula with rate r = 0:
       C_coin = C_B76(F, K, sigma, T, r=0) / F
   where F is the underlying forward price of the specific expiry (quoted as `underlying_price`),
   and S is the spot index (quoted as `underlying_index_price`).
   
   Multiplying Deribit's mark_price (in BTC) by forward F:
       C_USD(K) = mark_price * F = F * N(d1) - K * N(d2)
   
   If one multiplies by spot S instead of forward F when F != S, an unhedged basis distortion
   of (F - S)/S is introduced.
   
   COROLLARY (Basis Consistency):
   To price in forward space, the canonical USD price is:
       C_USD = mark_price_coin * forward_price
   
5. NUMÉRAIRE INVARIANCE OF IMPLIED VOLATILITY:
   Implied volatility sigma is dimensionless (annualized standard deviation of log returns).
   Because Deribit's published mark_iv is already the standard deviation of ln(S_T / F),
   it is NUMÉRAIRE-INVARIANT.
   
   Calibrating a volatility surface directly in (K, sigma(K)) space:
       Deribit quotes -> mark_iv -> smooth smile sigma(K) -> P_RN
   completely bypasses coin/USD conversion distortions and directly produces
   the USD cash-or-nothing digital probability needed for Polymarket fair value.
"""

from typing import Dict, Any, Optional
from src.quant.black76 import call_price, calc_d1_d2
from src.quant.digital_probability import digital_call_prob_analytic


def deribit_coin_to_usd_price(mark_price_coin: float, forward_price: float) -> float:
    """Convert Deribit coin-denominated option price to USD-equivalent forward option price.
    
    Args:
        mark_price_coin: Option price denominated in BTC/ETH (from Deribit ticker)
        forward_price: Underlying forward price F in USD (from Deribit underlying_price)
        
    Returns:
        C_USD: Option price in USD
    """
    if mark_price_coin < 0:
        raise ValueError(f"mark_price_coin must be non-negative, got {mark_price_coin}")
    if forward_price <= 0:
        raise ValueError(f"forward_price must be positive, got {forward_price}")
    return mark_price_coin * forward_price


def verify_deribit_numeraire_equivalence(
    F: float,
    K: float,
    sigma: float,
    T: float,
    r: float = 0.0,
) -> Dict[str, float]:
    """Verify that the coin-margined expectation matches the USD Black-76 price.
    
    Returns a dictionary of:
    - c_usd: Black-76 USD price
    - c_coin: Deribit coin price = c_usd / F
    - reconstructed_usd: c_coin * F
    - discrepancy: |reconstructed_usd - c_usd|
    """
    c_usd = call_price(F, K, sigma, T, r=r)
    # Coin price under forward numéraire
    c_coin = c_usd / F
    reconstructed_usd = c_coin * F
    
    return {
        "c_usd": c_usd,
        "c_coin": c_coin,
        "reconstructed_usd": reconstructed_usd,
        "discrepancy": abs(reconstructed_usd - c_usd),
    }


def parse_deribit_instrument_name(instrument_name: str) -> Dict[str, Any]:
    """Parse a Deribit instrument name like 'BTC-27MAR26-100000-C'.
    
    Returns:
        Dict with 'currency', 'expiry_str', 'strike', 'option_type' ('C' or 'P')
    """
    parts = instrument_name.split("-")
    if len(parts) != 4:
        raise ValueError(f"Invalid Deribit option instrument name: {instrument_name}")
    
    currency = parts[0]
    expiry_str = parts[1]
    strike = float(parts[2])
    option_type = parts[3].upper()
    if option_type not in ("C", "P"):
        raise ValueError(f"Invalid option type: {option_type} in {instrument_name}")
        
    return {
        "currency": currency,
        "expiry_str": expiry_str,
        "strike": strike,
        "option_type": option_type,
    }


def extract_normalized_pricing_inputs(metrics: Dict[str, Any]) -> Dict[str, float]:
    """Extract and validate normalized Black-76 inputs from a DeribitMetrics record.
    
    Deribit fields:
    - underlying_price -> F (Forward)
    - underlying_index_price -> S (Spot Index)
    - mark_price -> C_coin (BTC)
    - mark_iv -> sigma_iv (in percent, e.g. 55.4 -> 0.554)
    """
    inst = parse_deribit_instrument_name(metrics["instrument_name"])
    
    F = float(metrics["underlying_price"])
    S = float(metrics.get("underlying_index_price", F))
    K = float(inst["strike"])
    
    # Deribit mark_iv is expressed as percentage (e.g. 55.2 meaning 55.2%)
    raw_iv = float(metrics["mark_iv"])
    sigma = raw_iv / 100.0 if raw_iv > 2.0 else raw_iv
    
    mark_price_coin = float(metrics["mark_price"])
    c_usd = deribit_coin_to_usd_price(mark_price_coin, F)
    
    return {
        "F": F,
        "S": S,
        "K": K,
        "sigma": sigma,
        "mark_price_coin": mark_price_coin,
        "c_usd": c_usd,
        "option_type": inst["option_type"],
    }
