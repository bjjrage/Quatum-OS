import math
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

    # 2. Up state -> Allowed (100% sizing, runner profile capped at <= 1.0)
    s_up = BtcState.UP
    ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(s_up, z_score=-3.5)
    assert ok is True
    assert sizing == 1.0
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

    # Create 40-step series with non-degenerate flat market and extreme altcoin drop on last step
    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_alt = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [-0.07]  # Shock drop

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
    assert snapshot.stop_price is not None
    assert 0 < snapshot.stop_price < snapshot.entry_price
    assert snapshot.risk_distance > 0


# =============================================================================
# METHODOLOGICAL RISK CLASS 1: MODEL FORMULATION & PARAMETER RECOVERY
# =============================================================================

def test_strict_pre_shock_estimation_isolation():
    """A2: Parameters estimated on 0..t-1 MUST NOT change when bar t return changes."""
    estimator = TwoFactorResidualEstimator(ridge_lambda=0.0, min_samples=30)

    # 40 bars of pre-shock returns
    r_btc_pre = [0.001 * (1 if i % 2 == 0 else -1) for i in range(40)]
    r_eth_pre = [0.8 * r_btc_pre[i] for i in range(40)]
    r_alt_pre = [1.5 * r_btc_pre[i] + 0.0001 for i in range(40)]

    fit1 = estimator.fit_pre_shock(r_alt=r_alt_pre, r_btc=r_btc_pre, r_eth=r_eth_pre)
    assert fit1.status.value == "READY"

    # Evaluate bar t with mild shock (-5%)
    res1, z1 = estimator.evaluate_shock_at_t(fit1, r_alt_t=-0.05, r_btc_t=0.0, r_eth_t=0.0)

    # Evaluate bar t with extreme shock (-50%)
    res2, z2 = estimator.evaluate_shock_at_t(fit1, r_alt_t=-0.50, r_btc_t=0.0, r_eth_t=0.0)

    # Fit again with unchanged pre-shock series
    fit2 = estimator.fit_pre_shock(r_alt=r_alt_pre, r_btc=r_btc_pre, r_eth=r_eth_pre)

    # Invariant: Pre-shock parameters are 100% frozen and independent of bar t
    assert fit1.beta_down == fit2.beta_down
    assert fit1.beta_up == fit2.beta_up
    assert fit1.gamma_eth == fit2.gamma_eth
    assert fit1.sigma_eps == fit2.sigma_eps
    assert abs(z2) > abs(z1)
    assert res2 < res1


def test_beta_recovery_ols_and_scaled_ridge():
    """A3/A4: Beta recovery across {0.5, 1.0, 1.5, 2.0} with non-zero intercept and ETH factor."""
    true_betas = [0.5, 1.0, 1.5, 2.0]

    for beta_target in true_betas:
        # 60 synthetic periods with balanced positive and negative BTC returns
        r_btc = [0.01 * math.sin(i * 0.5) for i in range(60)]
        r_eth = [0.75 * r_btc[i] + 0.001 * math.cos(i) for i in range(60)]
        eta = [r_eth[i] - 0.75 * r_btc[i] for i in range(60)]
        # Altcoin returns with known true beta and intercept
        r_alt = [0.0005 + beta_target * r_btc[i] + 0.4 * eta[i] for i in range(60)]

        # 1. Exact OLS (ridge_lambda = 0.0)
        estimator_ols = TwoFactorResidualEstimator(ridge_lambda=0.0, min_samples=30)
        fit_ols = estimator_ols.fit_pre_shock(r_alt=r_alt, r_btc=r_btc, r_eth=r_eth)

        assert fit_ols.status.value == "READY"
        # OLS recovery error < 2%
        assert math.isclose(fit_ols.beta_down, beta_target, rel_tol=0.02)
        assert math.isclose(fit_ols.beta_up, beta_target, rel_tol=0.02)

        # 2. Properly-scaled Ridge (ridge_lambda = 0.05)
        ridge_lambda = 0.05
        estimator_ridge = TwoFactorResidualEstimator(ridge_lambda=ridge_lambda, min_samples=30)
        fit_ridge = estimator_ridge.fit_pre_shock(r_alt=r_alt, r_btc=r_btc, r_eth=r_eth)

        # Predictable shrinkage factor = 1 / (1 + lambda)
        expected_ridge_beta = beta_target / (1.0 + ridge_lambda)
        assert math.isclose(fit_ridge.beta_down, expected_ridge_beta, rel_tol=0.02)
        assert math.isclose(fit_ridge.beta_up, expected_ridge_beta, rel_tol=0.02)


def test_minimum_sample_requirement_fail_closed():
    """A5: Estimation fails closed (MODEL_NOT_READY) when N < 30."""
    estimator = TwoFactorResidualEstimator(min_samples=30)

    for n in [5, 15, 29]:
        r_btc = [0.001 * (1 if i % 2 == 0 else -1) for i in range(n)]
        r_eth = [0.001 * (1 if i % 2 == 0 else -1) for i in range(n)]
        r_alt = [0.001 * (1 if i % 2 == 0 else -1) for i in range(n)]

        fit = estimator.fit_pre_shock(r_alt, r_btc, r_eth)
        assert fit.status.value == "NOT_READY"
        assert "Insufficient" in fit.error_message

    # Test via Str002V2Strategy
    strat = Str002V2Strategy()
    short_series = [0.001] * 25
    should_exec, snapshot, diag = strat.generate_signal(
        symbol="BTCUSDT",
        timestamp_ns=1700000000_000000000,
        r_alt_series=short_series,
        r_btc_series=short_series,
        r_eth_series=short_series,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=100.0,
        pre_shock_origin=110.0,
        pre_shock_vwap=110.0,
        delta_5s=100.0,
        bid_depth_0_5pct=100.0,
        pre_shock_median_depth=100.0,
        recent_1s_lows=[95.0, 96.0],
    )
    assert should_exec is False
    assert snapshot is None
    assert diag["decision"] == "MODEL_NOT_READY"


def test_degenerate_inputs_fail_closed():
    """A6: Zero-variance BTC, NaN, Inf, and timestamp disorder return MODEL_INVALID."""
    estimator = TwoFactorResidualEstimator(min_samples=30)

    # 1. Zero-variance BTC returns
    r_zero_btc = [0.0] * 35
    r_valid = [0.001 * math.sin(i) for i in range(35)]
    fit_zero = estimator.fit_pre_shock(r_valid, r_zero_btc, r_valid)
    assert fit_zero.status.value == "INVALID"
    assert "Zero variance" in fit_zero.error_message

    # 2. NaN in series
    r_nan = [0.001] * 35
    r_nan[10] = float("nan")
    fit_nan = estimator.fit_pre_shock(r_nan, r_valid, r_valid)
    assert fit_nan.status.value == "INVALID"
    assert "Non-finite" in fit_nan.error_message

    # 3. Inf in series
    r_inf = [0.001] * 35
    r_inf[15] = float("inf")
    fit_inf = estimator.fit_pre_shock(r_valid, r_inf, r_valid)
    assert fit_inf.status.value == "INVALID"
    assert "Non-finite" in fit_inf.error_message

    # 4. Disordered timestamps
    timestamps = [1000 + i * 10 for i in range(35)]
    timestamps[20] = timestamps[19] - 5  # Inversion
    fit_ts = estimator.fit_pre_shock(r_valid, r_valid, r_valid, timestamps=timestamps)
    assert fit_ts.status.value == "INVALID"
    assert "Timestamp disorder" in fit_ts.error_message


# =============================================================================
# METHODOLOGICAL RISK CLASS 2: SHOCK STATE MACHINE & SCENARIO AUDIT
# =============================================================================

def test_shock_state_machine_lifecycle_and_single_signal():
    """B1/B2/B3: Enforce full state machine lifecycle and exactly one signal per shock."""
    from src.strategies.str002_v2 import ShockStateMachine, ShockState

    sm = ShockStateMachine(max_wait_bars=3, cooldown_bars=5)
    assert sm.state == ShockState.IDLE

    # Bar 1: Normal conditions -> IDLE
    assert sm.step(z_score=-1.0, current_price=100.0, reversal_confirmed=False, btc_state_allowed=True, bar_index=1) is False
    assert sm.state == ShockState.IDLE

    # Bar 2: Shock occurs (z = -3.5), but reversal not yet confirmed -> WAITING_FOR_REVERSAL
    assert sm.step(z_score=-3.5, current_price=90.0, reversal_confirmed=False, btc_state_allowed=True, bar_index=2) is False
    assert sm.state == ShockState.WAITING_FOR_REVERSAL
    assert sm.active_shock_id == "shock_2"

    # Bar 3: Shock deepens (z = -4.0), reversal confirms -> SIGNAL_EMITTED
    assert sm.step(z_score=-4.0, current_price=88.0, reversal_confirmed=True, btc_state_allowed=True, bar_index=3) is True
    assert sm.state == ShockState.SIGNAL_EMITTED
    assert sm.signal_emitted_for_shock is True

    # Bar 4: Shock continues (z = -4.2) -> MUST NOT RE-EMIT. Transitions to COOLDOWN
    assert sm.step(z_score=-4.2, current_price=87.0, reversal_confirmed=True, btc_state_allowed=True, bar_index=4) is False
    assert sm.state == ShockState.COOLDOWN

    # Bars 5-7: Severe shock continues, but machine remains in COOLDOWN
    for bar in range(5, 8):
        assert sm.step(z_score=-5.0, current_price=85.0, reversal_confirmed=True, btc_state_allowed=True, bar_index=bar) is False
        assert sm.state == ShockState.COOLDOWN

    # Bar 8: Cooldown expires -> transitions back to IDLE
    sm.step(z_score=-1.0, current_price=95.0, reversal_confirmed=False, btc_state_allowed=True, bar_index=8)
    assert sm.state == ShockState.IDLE


def test_synthetic_gaussian_noise_low_false_discovery():
    """B4: Synthetic Gaussian noise produces bounded false discovery rate (< 1.0%)."""
    import random
    random.seed(42)

    strat = Str002V2Strategy(max_wait_bars=3, cooldown_bars=10)

    # 1000 bars of pure Gaussian noise
    emitted_count = 0
    history_len = 40

    r_btc_stream = [random.gauss(0.0, 0.002) for _ in range(1040)]
    r_eth_stream = [0.8 * r_btc_stream[i] + random.gauss(0.0, 0.001) for i in range(1040)]
    r_alt_stream = [1.2 * r_btc_stream[i] + random.gauss(0.0, 0.003) for i in range(1040)]

    for t in range(history_len, 1040):
        r_alt_window = r_alt_stream[t - history_len : t + 1]
        r_btc_window = r_btc_stream[t - history_len : t + 1]
        r_eth_window = r_eth_stream[t - history_len : t + 1]

        should_exec, _, _ = strat.generate_signal(
            symbol="NOISE_TEST",
            timestamp_ns=1700000000_000000000 + t * 60_000_000_000,
            r_alt_series=r_alt_window,
            r_btc_series=r_btc_window,
            r_eth_series=r_eth_window,
            btc_returns_1m_5m_15m=(0.0001, 0.0001, 0.0001),
            btc_vol_5m_ratio=1.0,
            current_price=100.0,
            pre_shock_origin=102.0,
            pre_shock_vwap=101.5,
            delta_5s=10.0,
            bid_depth_0_5pct=50000.0,
            pre_shock_median_depth=80000.0,
            recent_1s_lows=[99.0, 98.8, 99.1],
        )
        if should_exec:
            emitted_count += 1

    # False discovery rate on 1000 noise bars must be <= 10 (<= 1.0%)
    assert emitted_count <= 10


# --- 8 CONTROLLED SHOCK SCENARIOS ---

def test_controlled_shock_scenario_1_clean_downward_shock():
    """Scenario 1: Clean downward idiosyncratic shock, BTC flat -> Signal emitted."""
    strat = Str002V2Strategy()
    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_alt = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [-0.07]  # Shock

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="SCENARIO_1",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0001, 0.0001, 0.0001),  # FLAT
        btc_vol_5m_ratio=1.0,
        current_price=10.0,
        pre_shock_origin=11.0,
        pre_shock_vwap=10.9,
        delta_5s=500.0,  # Reversal confirmed
        bid_depth_0_5pct=60000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.8, 9.7, 9.9],
    )
    assert should_exec is True
    assert diag["decision"] == "EXECUTE_LONG"
    assert snapshot.alt_z_score < -3.0


def test_controlled_shock_scenario_2_btc_wide_shock_blocked():
    """Scenario 2: BTC liquidation cascade (RUNNING_HARD_DOWN) -> strictly blocked."""
    strat = Str002V2Strategy()
    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_alt = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [-0.07]

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="SCENARIO_2",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(-0.01, -0.02, -0.03),  # RUNNING_HARD_DOWN
        btc_vol_5m_ratio=3.0,
        current_price=10.0,
        pre_shock_origin=11.0,
        pre_shock_vwap=10.9,
        delta_5s=500.0,
        bid_depth_0_5pct=60000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.8, 9.7, 9.9],
    )
    assert should_exec is False
    assert snapshot is None
    assert diag["decision"] == "BLOCKED"
    assert "STRICTLY_BLOCKED" in diag["reason"]


def test_controlled_shock_scenario_3_eth_residual_shock_no_action():
    """Scenario 3: Alt drop explained by ETH factor -> residual z-score does not breach threshold."""
    strat = Str002V2Strategy()
    # 40-step series where ETH has non-zero eta and Alt has gamma_eth ~ 0.8
    r_btc = [0.001 * math.sin(i * 0.5) for i in range(40)]
    eta_pre = [0.002 * math.cos(i * 0.7) for i in range(40)]
    r_eth = [0.8 * r_btc[i] + eta_pre[i] for i in range(40)]
    r_alt = [1.2 * r_btc[i] + 0.8 * eta_pre[i] for i in range(39)] + [1.2 * r_btc[39] + 0.8 * (-0.06)]
    # In bar 40 (last bar), ETH drops with eta = -0.06, alt drops proportionally with 0.8 * (-0.06)
    r_eth[39] = 0.8 * r_btc[39] - 0.06

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="SCENARIO_3",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=10.0,
        pre_shock_origin=11.0,
        pre_shock_vwap=10.9,
        delta_5s=500.0,
        bid_depth_0_5pct=60000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.8, 9.7, 9.9],
    )
    # Factor model explains the drop, so idiosyncratic z-score is modest
    assert should_exec is False
    assert diag["decision"] in ("NO_SHOCK", "BLOCKED")


def test_controlled_shock_scenario_4_btc_spike_proportional_eth():
    """Scenario 4: BTC and ETH rally up -> no downward shock."""
    strat = Str002V2Strategy()
    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [+0.05]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [+0.04]
    r_alt = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [+0.06]

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="SCENARIO_4",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.02, 0.03, 0.04),
        btc_vol_5m_ratio=1.0,
        current_price=12.0,
        pre_shock_origin=10.0,
        pre_shock_vwap=10.5,
        delta_5s=500.0,
        bid_depth_0_5pct=60000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[10.0, 11.0, 12.0],
    )
    assert should_exec is False
    assert diag["decision"] in ("NO_SHOCK", "BLOCKED")


def test_controlled_shock_scenario_5_fake_one_bar_noise():
    """Scenario 5: Minor dip (z = -1.0) fails statistical significance hurdle -> stays IDLE."""
    strat = Str002V2Strategy()
    r_btc = [0.002 * math.sin(i) for i in range(40)]
    r_eth = [0.002 * math.sin(i) for i in range(40)]
    r_alt = [0.002 * math.sin(i) for i in range(39)] + [0.002 * math.sin(39) - 0.0005]  # Minor dip ~ 0.5 sigma

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="SCENARIO_5",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=10.0,
        pre_shock_origin=10.1,
        pre_shock_vwap=10.05,
        delta_5s=500.0,
        bid_depth_0_5pct=60000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.9, 9.85, 9.95],
    )
    assert should_exec is False
    assert diag["decision"] == "NO_SHOCK"


def test_controlled_shock_scenario_6_unreversed_knife_catch_expired():
    """Scenario 6: Severe liquidation cascade without reversal confirmation -> EXPIRED, no signal."""
    strat = Str002V2Strategy(max_wait_bars=3, cooldown_bars=5)

    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_alt_shock = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [-0.08]

    # Bar 1: Shock occurs, no reversal
    exec1, _, diag1 = strat.generate_signal(
        symbol="KNIFE_CATCH",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=10.0,
        pre_shock_origin=12.0,
        pre_shock_vwap=11.9,
        delta_5s=-500.0,  # Continued heavy selling
        bid_depth_0_5pct=10000.0,  # 10% (not replenished)
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[10.5, 10.2, 9.9],  # Lower lows
    )
    assert exec1 is False
    assert diag1["decision"] == "WAITING_CONFIRMATION"

    # Bar 2: Selling continues
    exec2, _, diag2 = strat.generate_signal(
        symbol="KNIFE_CATCH",
        timestamp_ns=1700000000_000000000 + 60_000_000_000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=9.5,
        pre_shock_origin=12.0,
        pre_shock_vwap=11.9,
        delta_5s=-600.0,
        bid_depth_0_5pct=10000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.5, 9.0, 8.5],
    )
    assert exec2 is False
    assert diag2["decision"] == "WAITING_CONFIRMATION"

    # Bar 3: Wait window (3 bars) reached -> EXPIRED
    exec3, _, diag3 = strat.generate_signal(
        symbol="KNIFE_CATCH",
        timestamp_ns=1700000000_000000000 + 2 * 60_000_000_000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=9.0,
        pre_shock_origin=12.0,
        pre_shock_vwap=11.9,
        delta_5s=-600.0,
        bid_depth_0_5pct=10000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.0, 8.5, 8.0],
    )
    assert exec3 is False
    assert diag3["decision"] == "EXPIRED"

    # Bar 4: Transitions to COOLDOWN
    exec4, _, diag4 = strat.generate_signal(
        symbol="KNIFE_CATCH",
        timestamp_ns=1700000000_000000000 + 3 * 60_000_000_000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=8.5,
        pre_shock_origin=12.0,
        pre_shock_vwap=11.9,
        delta_5s=-600.0,
        bid_depth_0_5pct=10000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[8.5, 8.0, 7.5],
    )
    assert exec4 is False
    assert diag4["decision"] == "COOLDOWN"


def test_controlled_shock_scenario_7_delayed_reversal():
    """Scenario 7: Shock detected at bar t, waiting at t+1, reversal confirms at t+2 -> Signal emitted."""
    strat = Str002V2Strategy(max_wait_bars=5, cooldown_bars=5)

    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_alt_shock = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [-0.08]

    # Bar 1: Shock detected, no reversal yet
    exec1, _, diag1 = strat.generate_signal(
        symbol="DELAYED_REV",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=10.0,
        pre_shock_origin=12.0,
        pre_shock_vwap=11.9,
        delta_5s=-200.0,
        bid_depth_0_5pct=20000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[10.5, 10.2, 9.9],
    )
    assert exec1 is False
    assert diag1["decision"] == "WAITING_CONFIRMATION"

    # Bar 2: Reversal confirmed (flow flips positive, book replenishes)
    exec2, snapshot2, diag2 = strat.generate_signal(
        symbol="DELAYED_REV",
        timestamp_ns=1700000000_000000000 + 60_000_000_000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=10.1,
        pre_shock_origin=12.0,
        pre_shock_vwap=11.9,
        delta_5s=400.0,  # Flip!
        bid_depth_0_5pct=70000.0,  # 70% replenishment!
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.9, 9.8, 10.1],  # Higher low!
    )
    assert exec2 is True
    assert diag2["decision"] == "EXECUTE_LONG"
    assert snapshot2 is not None


def test_controlled_shock_scenario_8_independent_consecutive_shocks():
    """Scenario 8: Shock 1 completes cooldown, then Shock 2 occurs and emits its own signal."""
    strat = Str002V2Strategy(max_wait_bars=3, cooldown_bars=3)

    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_alt_shock = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [-0.07]
    r_alt_normal = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]

    # 1. Shock 1 fires immediately
    exec1, _, diag1 = strat.generate_signal(
        symbol="INDEPENDENT",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=10.0,
        pre_shock_origin=11.0,
        pre_shock_vwap=10.9,
        delta_5s=500.0,
        bid_depth_0_5pct=60000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[9.8, 9.7, 9.9],
    )
    assert exec1 is True
    shock1_id = diag1["shock_id"]

    # 2. Advance 3 bars of cooldown
    for bar in range(1, 4):
        exec_cd, _, _ = strat.generate_signal(
            symbol="INDEPENDENT",
            timestamp_ns=1700000000_000000000 + bar * 60_000_000_000,
            r_alt_series=r_alt_normal,
            r_btc_series=r_btc,
            r_eth_series=r_eth,
            btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
            btc_vol_5m_ratio=1.0,
            current_price=10.5,
            pre_shock_origin=11.0,
            pre_shock_vwap=10.9,
            delta_5s=0.0,
            bid_depth_0_5pct=50000.0,
            pre_shock_median_depth=100000.0,
            recent_1s_lows=[10.4, 10.3, 10.5],
        )
        assert exec_cd is False

    # 3. Bar 5: Shock 2 occurs after cooldown -> emits new signal with distinct shock_id
    exec2, _, diag2 = strat.generate_signal(
        symbol="INDEPENDENT",
        timestamp_ns=1700000000_000000000 + 5 * 60_000_000_000,
        r_alt_series=r_alt_shock,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=9.0,
        pre_shock_origin=10.5,
        pre_shock_vwap=10.4,
        delta_5s=600.0,
        bid_depth_0_5pct=70000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[8.9, 8.8, 9.0],
    )
    assert exec2 is True
    shock2_id = diag2["shock_id"]
    assert shock1_id != shock2_id


# =============================================================================
# METHODOLOGICAL RISK CLASS 3: BTC STATE MATRIX & REGIME LOGIC
# =============================================================================

def test_btc_state_matrix_unknown_state_fail_closed():
    """C1: Missing, NaN, or non-positive realized volatility yields STATE_UNKNOWN -> BLOCKED."""
    # NaN volatility
    s_nan = BtcStateClassifier.classify(0.0, 0.001, 0.0, btc_realized_vol_5m=float("nan"))
    assert s_nan == BtcState.STATE_UNKNOWN

    # None volatility
    s_none = BtcStateClassifier.classify(0.0, 0.001, 0.0, btc_realized_vol_5m=None)
    assert s_none == BtcState.STATE_UNKNOWN

    # Negative / zero volatility
    s_zero = BtcStateClassifier.classify(0.0, 0.001, 0.0, btc_realized_vol_5m=0.0)
    assert s_zero == BtcState.STATE_UNKNOWN

    # NaN 5m return
    s_nan_ret = BtcStateClassifier.classify(0.0, float("nan"), 0.0, btc_realized_vol_5m=0.002)
    assert s_nan_ret == BtcState.STATE_UNKNOWN

    # Evaluate decision matrix under STATE_UNKNOWN
    ok, sizing, beh = BtcStateClassifier.evaluate_decision_matrix(BtcState.STATE_UNKNOWN, z_score=-3.5)
    assert ok is False
    assert sizing == 0.0
    assert "BLOCKED_BTC_UNKNOWN" in beh


# =============================================================================
# METHODOLOGICAL RISK CLASS 4: HARD STOP LOSS & RISK-BUDGET SIZING
# =============================================================================

def test_hard_stop_loss_and_risk_budget_sizing():
    """D1/D2: Stop loss must be finite, positive, < entry; sizing must be derived from risk distance."""
    # 1. Direct ReferencePriceExitCalculator test
    targets = ReferencePriceExitCalculator.calculate_targets(
        entry_price=100.0,
        pre_shock_origin=110.0,
        pre_shock_vwap=109.5,
        shock_bottom=98.0,
        stop_buffer_pct=0.01,  # 1% buffer
    )

    stop_loss = targets["stop_loss"]
    risk_dist = targets["risk_distance"]
    risk_pct = targets["risk_pct"]

    # Invariants
    assert stop_loss > 0.0
    assert stop_loss < 100.0
    assert risk_dist > 0.0
    assert math.isclose(risk_dist, 100.0 - stop_loss)
    assert 0.0 < risk_pct < 1.0
    assert "NEW_LOW_BELOW_SHOCK_BOTTOM" in targets["invalidation_reason"]

    # 2. Risk budget sizing via Str002V2Strategy
    strat = Str002V2Strategy()
    r_btc = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_eth = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(40)]
    r_alt = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(39)] + [-0.07]

    allowed_risk_usd = 250.0

    should_exec, snapshot, diag = strat.generate_signal(
        symbol="SIZING_TEST",
        timestamp_ns=1700000000_000000000,
        r_alt_series=r_alt,
        r_btc_series=r_btc,
        r_eth_series=r_eth,
        btc_returns_1m_5m_15m=(0.0, 0.0, 0.0),
        btc_vol_5m_ratio=1.0,
        current_price=50.0,
        pre_shock_origin=55.0,
        pre_shock_vwap=54.5,
        delta_5s=500.0,
        bid_depth_0_5pct=60000.0,
        pre_shock_median_depth=100000.0,
        recent_1s_lows=[48.0, 47.5, 48.5],
        allowed_risk_usd=allowed_risk_usd,
    )

    assert should_exec is True
    assert diag["sizing_multiplier"] <= 1.0  # Capped at <= 1.0
    assert diag["allowed_risk_usd"] == allowed_risk_usd
    expected_qty = (allowed_risk_usd / diag["risk_distance"]) * diag["sizing_multiplier"]
    assert math.isclose(diag["position_quantity"], expected_qty)
    assert diag["notional_usd"] == expected_qty * 50.0
    assert snapshot.stop_price == diag["stop_loss"]
    assert snapshot.risk_distance == diag["risk_distance"]
