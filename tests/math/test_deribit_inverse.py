"""Tests for Deribit inverse option pricing, numéraire transformation, and normalized inputs."""

import pytest
from src.quant.deribit_inverse import (
    deribit_coin_to_usd_price,
    verify_deribit_numeraire_equivalence,
    parse_deribit_instrument_name,
    extract_normalized_pricing_inputs,
)
from src.quant.black76 import call_price


def test_deribit_numeraire_equivalence_identity():
    """Verify that c_coin * F identically reconstructs the USD Black-76 call price."""
    test_cases = [
        (70000.0, 70000.0, 0.55, 0.25, 0.0),    # BTC ATM
        (70000.0, 60000.0, 0.60, 0.10, 0.0),    # BTC ITM
        (70000.0, 85000.0, 0.50, 0.50, 0.0),    # BTC OTM
        (3500.0, 3600.0, 0.70, 0.08, 0.0),      # ETH
    ]
    for F, K, sigma, T, r in test_cases:
        res = verify_deribit_numeraire_equivalence(F, K, sigma, T, r)
        assert res["discrepancy"] < 1e-12, (
            f"Numéraire discrepancy too large for F={F}, K={K}: {res['discrepancy']}"
        )
        assert res["reconstructed_usd"] == pytest.approx(res["c_usd"], rel=1e-12)


def test_basis_consistency_forward_vs_spot():
    """Demonstrate why multiplying by Forward F rather than Spot S is essential when basis != 0.
    
    In crypto options, forward F can trade at a basis (contango/backwardation) to spot S.
    Deribit computes mark IV relative to forward F.
    """
    S = 70000.0
    F = 71000.0  # $1000 basis (contango)
    K = 70000.0
    sigma = 0.55
    T = 0.25
    r = 0.0
    
    # Ground truth forward USD call price
    c_usd_true = call_price(F, K, sigma, T, r)
    
    # Deribit quotes option in coin: c_coin = c_usd / F
    c_coin = c_usd_true / F
    
    # Multiplying by forward F recovers exact price
    c_usd_from_F = deribit_coin_to_usd_price(c_coin, F)
    assert abs(c_usd_from_F - c_usd_true) < 1e-12
    
    # Multiplying by spot S introduces a basis error proportional to (S - F)/F
    c_usd_from_S = deribit_coin_to_usd_price(c_coin, S)
    basis_error = c_usd_true - c_usd_from_S
    expected_error = c_usd_true * ((F - S) / F)
    assert abs(basis_error - expected_error) < 1e-10
    assert basis_error > 0  # spot multiplication would understate the forward option value


def test_parse_deribit_instrument_name():
    """Verify parsing of standard Deribit option instrument names."""
    parsed = parse_deribit_instrument_name("BTC-27MAR26-100000-C")
    assert parsed["currency"] == "BTC"
    assert parsed["expiry_str"] == "27MAR26"
    assert parsed["strike"] == 100000.0
    assert parsed["option_type"] == "C"

    parsed_put = parse_deribit_instrument_name("ETH-26DEC25-3000-P")
    assert parsed_put["currency"] == "ETH"
    assert parsed_put["strike"] == 3000.0
    assert parsed_put["option_type"] == "P"

    with pytest.raises(ValueError):
        parse_deribit_instrument_name("INVALID-NAME")


def test_extract_normalized_pricing_inputs():
    """Verify extraction of normalized pricing inputs from a Deribit metrics dictionary."""
    mock_metrics = {
        "instrument_name": "BTC-27JUN25-75000-C",
        "underlying_price": 72500.0,        # F
        "underlying_index_price": 72000.0,  # S
        "mark_price": 0.0825,               # BTC
        "mark_iv": 58.4,                    # 58.4%
        "delta": 0.45,
        "gamma": 0.00002,
        "vega": 45.0,
        "theta": -35.0,
        "dvol_index": 56.1,
    }
    inputs = extract_normalized_pricing_inputs(mock_metrics)
    assert inputs["F"] == 72500.0
    assert inputs["S"] == 72000.0
    assert inputs["K"] == 75000.0
    assert abs(inputs["sigma"] - 0.584) < 1e-6
    assert inputs["mark_price_coin"] == 0.0825
    assert abs(inputs["c_usd"] - (0.0825 * 72500.0)) < 1e-8
    assert inputs["option_type"] == "C"


def test_real_recorded_deribit_row_normalization():
    """Verify normalization against actual recorded Batch 0 Deribit parquet row."""
    # Actual row captured from live Deribit WS during smoke test
    real_sample_row = {
        "ts_exchange_ns": 1790978245958000000,
        "ts_received_utc_ns": 1790978243918110400,
        "ts_received_mono_ns": 1217625000000,
        "instrument_name": "ETH-16OCT26-3400-C",
        "underlying_price": 2668.74,
        "mark_price": 0.0008,
        "mark_iv": 59.72,
        "bid_iv": 58.57,
        "ask_iv": 60.75,
        "delta": 0.01981,
        "gamma": 0.00016,
        "vega": 0.24573,
        "theta": -0.54679,
        "underlying_index_price": 2665.0,
        "dvol_index": 55.0,
    }
    inputs = extract_normalized_pricing_inputs(real_sample_row)
    assert inputs["F"] == 2668.74
    assert inputs["K"] == 3400.0
    assert inputs["sigma"] == 0.5972
    assert inputs["mark_price_coin"] == 0.0008
    assert abs(inputs["c_usd"] - (0.0008 * 2668.74)) < 1e-8
    assert inputs["option_type"] == "C"

