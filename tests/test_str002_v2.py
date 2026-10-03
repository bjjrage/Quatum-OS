"""Unit tests for STR-002 v2 Liquidity Shock Reversal Research Framework."""

import pytest
from src.strategies.str002_v2 import (
    BtcState,
    FirstReversalType,
    ExitTargetType,
    RegimeSnapshot,
    TwoFactorResidualEstimator,
    BtcStateClassifier,
    FirstReversalDetector,
    ReferencePriceExitCalculator,
    Str002V2Strategy,
)


def test_two_factor_residualization_and_asymmetric_beta():
    """Verify 2-factor residualization, ETH orthogonalization, and asymmetric beta."""
    estimator = TwoFactorResidualEstimator(ridge_lambda=1e-4)

    # Synthetic series (50 periods)
    # BTC moves down on even indices, up on odd indices
    r_btc = [-0.02 if i % 2 == 0 else +0.01 for i in range(50)]
    # ETH is correlated with BTC
    r_eth = [0.8 * r_btc[i] + 0.001 * (i % 3) for i in range(50)]
    # Altcoin drops much harder when BTC is down (beta_down ~ 2.0), modest when BTC up (beta_up ~ 1.0)
    # On the last candle, add an extreme idiosyncratic liquidity shock (-0.08)
    r_alt = []
    for i in range(50):
        if r_btc[i] < 0:
            ret = 2.0 * r_btc[i]
        else:
            ret = 1.0 * r_btc[i]
        if i == 49:
            ret -= 0.08  # Severe idiosyncratic liquidation cascade
        r_alt.append(ret)

    beta_down, beta_up, gamma_eth, residuals, sigma_eps = estimator.fit_and_residualize(
        r_alt=r_alt,
        r_btc=r_btc,
        r_eth=r_eth,
    )

    # Invariant: Asymmetric beta reflects heavier downside beta
    assert beta_down > beta_up
    assert beta_down > 1.5
    # Invariant: Last candle residual captures idiosyncratic shock
    assert residuals[-1] < -0.05
    z_score = residuals[-1] / sigma_eps
    assert z_score < -3.0


def test_btc_decision_matrix_all_cells():
    """Verify that EVERY single cell in the BTC decision matrix adheres to authoritative v2 spec."""
    # 1. Flat state -> Allowed (100% sizing)
    s_flat = BtcState.FLAT
    ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(s_flat, z_score=-3.5)
    assert ok is True
    assert sizing == 1.0
    assert "TARGET_REFERENCE_PRICE" in beh

    # 2. Up state -> Allowed (120% sizing, runner profile)
    s_up = BtcState.UP
    ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(s_up, z_score=-3.5)
    assert ok is True
    assert sizing == 1.2
    assert "TRAIL_RUNNER" in beh

    # 3. Down state -> BLOCKED (0% sizing)
    s_down = BtcState.DOWN
    ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(s_down, z_score=-3.5)
    assert ok is False
    assert sizing == 0.0
    assert "BLOCKED_BTC_DOWN" in beh

    # 4. Running hard down (liquidation cascade) -> STRICTLY BLOCKED (0% sizing)
    s_running_down = BtcState.RUNNING_HARD_DOWN
    ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(s_running_down, z_score=-3.5)
    assert ok is False
    assert sizing == 0.0
    assert "STRICTLY_BLOCKED" in beh

    # 5. Running hard up (market dislocation / high dispersion) -> BLOCKED (0% sizing)
    s_running_up = BtcState.RUNNING_HARD_UP
    ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(s_running_up, z_score=-3.5)
    assert ok is False
    assert sizing == 0.0
    assert "BLOCKED_BTC_RUNNING_HARD_UP" in beh

    # 6. Weak shock (|z_score| < 3.0) -> BLOCKED across all states
    for state in BtcState:
        ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(state, z_score=-2.5)
        assert ok is False
        assert sizing == 0.0
        assert "NO_SHOCK" in beh


def test_btc_state_classification_vol_normalized():
    """Verify BTC state classification normalizes thresholds by realized volatility."""
    # Base vol = 0.002
    sigma = 0.002
    # ret_5m = 0.001 is < 1.0 * sigma -> FLAT
    assert BtcStateClassifier.classify(0.0, 0.001, 0.0, btc_realized_vol_5m=sigma) == BtcState.FLAT
    # ret_5m = 0.003 is > 1.0 * sigma -> UP
    assert BtcStateClassifier.classify(0.0, 0.003, 0.0, btc_realized_vol_5m=sigma) == BtcState.UP
    # ret_5m = -0.003 is < -1.0 * sigma -> DOWN
    assert BtcStateClassifier.classify(0.0, -0.003, 0.0, btc_realized_vol_5m=sigma) == BtcState.DOWN
    # ret_5m = -0.007 is < -3.0 * sigma -> RUNNING_HARD_DOWN
    assert BtcStateClassifier.classify(0.0, -0.007, 0.0, btc_realized_vol_5m=sigma) == BtcState.RUNNING_HARD_DOWN
    # ret_5m = +0.007 is > +3.0 * sigma -> RUNNING_HARD_UP
    assert BtcStateClassifier.classify(0.0, +0.007, 0.0, btc_realized_vol_5m=sigma) == BtcState.RUNNING_HARD_UP

    # Higher volatility regime (sigma = 0.010)
    # ret_5m = 0.005 was UP under sigma=0.002, but is now FLAT under sigma=0.010
    assert BtcStateClassifier.classify(0.0, 0.005, 0.0, btc_realized_vol_5m=0.010) == BtcState.FLAT


def test_str002_model_variants_m0_to_m7_isolated():
    """Verify evidence ladder variants M0-M7 are isolated and start UNVALIDATED."""
    from src.strategies.str002_v2 import get_str002_model_variants
    variants = get_str002_model_variants()
    assert len(variants) == 8
    expected_ids = ["M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]
    assert [v["variant_id"] for v in variants] == expected_ids
    # Invariant: No variant inherits validated status
    for v in variants:
        assert v["status"] == "UNVALIDATED"


def test_first_reversal_pluggable_detectors():
    """Verify each pluggable detector can trigger entry confirmation."""
    # 1. Book replenishment triggers (> 50% median)
    ok_book, rev_type, ratio = FirstReversalDetector.evaluate(
        delta_5s=-10.0,
        current_bid_depth_0_5pct=60_000.0,
        pre_shock_median_depth=100_000.0,  # 60%
        recent_1s_lows=[10.0, 9.5, 9.0],
    )
    assert ok_book is True
    assert rev_type == FirstReversalType.BOOK_REPLENISHMENT
    assert ratio == 0.60

    # 2. Aggressor flow flip triggers (delta > 0)
    ok_flow, rev_type, _ = FirstReversalDetector.evaluate(
        delta_5s=500.0,
        current_bid_depth_0_5pct=20_000.0,
        pre_shock_median_depth=100_000.0,  # 20%
        recent_1s_lows=[10.0, 9.5, 9.0],
    )
    assert ok_flow is True
    assert rev_type == FirstReversalType.AGGRESSOR_FLOW_FLIP

    # 3. Microstructure higher low triggers
    ok_hl, rev_type, _ = FirstReversalDetector.evaluate(
        delta_5s=-50.0,
        current_bid_depth_0_5pct=20_000.0,
        pre_shock_median_depth=100_000.0,
        recent_1s_lows=[10.0, 8.8, 9.1],  # 9.1 > 8.8
    )
    assert ok_hl is True
    assert rev_type == FirstReversalType.MICROSTRUCTURE_HIGHER_LOW

    # 4. None triggers -> blocked (knife-catch prevented)
    ok_none, rev_type, _ = FirstReversalDetector.evaluate(
        delta_5s=-50.0,
        current_bid_depth_0_5pct=20_000.0,
        pre_shock_median_depth=100_000.0,
        recent_1s_lows=[10.0, 9.5, 8.9],
    )
    assert ok_none is False
    assert rev_type is None


def test_reference_price_exit_targets():
    """Verify reference price equilibrium exit targets."""
    entry = 80.0
    origin = 100.0
    vwap = 102.0

    targets = ReferencePriceExitCalculator.calculate_targets(
        entry_price=entry,
        pre_shock_origin=origin,
        pre_shock_vwap=vwap,
    )

    assert targets["half_retracement"] == 90.0
    assert targets["pre_shock_origin"] == 100.0
    assert targets["pre_shock_vwap"] == 102.0


def test_strictly_long_only_execution_invariant():
    """Verify strict OS invariant: Short-side crypto execution is strictly blocked ($0 risk)."""
    strat = Str002V2Strategy()

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="SOLUSDT",
        timestamp_ns=1700000000_000000000,
        r_alt_series=[0.01] * 50,
        r_btc_series=[0.01] * 50,
        r_eth_series=[0.01] * 50,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=100.0,
        pre_shock_origin=90.0,
        pre_shock_vwap=92.0,
        delta_5s=-10.0,
        bid_depth_0_5pct=100.0,
        pre_shock_median_depth=100.0,
        recent_1s_lows=[90.0, 91.0],
        is_short_side_hypothesis=True,  # Attempting short execution
    )

    assert should_exec is False
    assert snapshot is None
    assert diag["decision"] == "BLOCKED"
    assert "SHORT_SIDE_RESEARCH_ONLY" in diag["reason"]
    assert diag["is_long_only_enforced"] is True


def test_complete_str002_v2_signal_and_regime_snapshot():
    """Verify end-to-end STR-002 v2 execution and complete RegimeSnapshot logging."""
    strat = Str002V2Strategy()

    # Create 40-step series with extreme altcoin drop on last step
    r_btc = [0.0002] * 40
    r_eth = [0.0002] * 40
    r_alt = [0.0002] * 39 + [-0.07]  # Shock drop

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="DOGEUSDT",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0001, 0.0003, 0.0005),  # FLAT
        btc_vol_5m_ratio=1.0,
        current_price=0.150,
        pre_shock_origin=0.165,
        pre_shock_vwap=0.166,
        delta_5s=500.0,  # Aggressor flow flip
        bid_depth_0_5pct=60_000.0,
        pre_shock_median_depth=100_000.0,  # 60% replenishment
        recent_1s_lows=[0.148, 0.147, 0.149],
    )

    assert should_exec is True
    assert diag["decision"] == "EXECUTE_LONG"
    assert diag["sizing_multiplier"] == 1.0

    # Verify complete RegimeSnapshot recorded
    assert snapshot is not None
    assert snapshot.symbol == "DOGEUSDT"
    assert snapshot.btc_state == BtcState.FLAT
    assert snapshot.alt_z_score < -3.0
    assert snapshot.reversal_detector_triggered in (
        FirstReversalType.BOOK_REPLENISHMENT,
        FirstReversalType.AGGRESSOR_FLOW_FLIP,
    )
    assert snapshot.pre_shock_vwap == 0.166
    assert snapshot.entry_price == 0.150
