"""Unit tests for Strategy Factory, STR-001 Relative Value, and STR-002 Event Study."""
import math
import pytest

from src.strategies.factory import EvidenceAdmissionGate, SignalDirection
from src.strategies.str001_empirical import STR001RelativeValueAlpha
from src.strategies.str002_event_study import STR002EventStudyAlpha, MoveClassification, BboQuote
from src.backtest.metrics import BacktestPerformanceReport
from src.research.events import PriceImpulseEvent, ShockDirection


def test_evidence_admission_gate_pass_and_fail() -> None:
    """Admission gate promotes strategies only when all empirical hurdles are met."""
    gate = EvidenceAdmissionGate(
        min_sharpe=1.2,
        max_drawdown_pct=15.0,
        min_profit_factor=1.3,
        min_trades=30,
        require_fdr_significance=True,
    )

    # Passing report
    good_report = BacktestPerformanceReport(
        initial_equity=100_000.0,
        final_equity=125_000.0,
        total_net_pnl=25_000.0,
        total_return_pct=25.0,
        annualized_sharpe=1.85,
        annualized_sortino=2.40,
        max_drawdown_pct=8.5,
        calmar_ratio=2.94,
        win_rate=0.58,
        profit_factor=1.75,
        expectancy_per_trade=250.0,
        total_trades=100,
        winning_trades=58,
        losing_trades=42,
        total_fees_paid=450.0,
        turnover=500_000.0,
    )
    passed, reasons = gate.evaluate(good_report, is_fdr_significant=True)
    assert passed is True
    assert len(reasons) == 0

    # Failing report: Low Sharpe, High Drawdown, FDR failed
    bad_report = good_report.model_copy(update={"annualized_sharpe": 0.8, "max_drawdown_pct": 22.0})
    passed_bad, reasons_bad = gate.evaluate(bad_report, is_fdr_significant=False)
    assert passed_bad is False
    assert len(reasons_bad) == 3


def test_str001_empirical_relative_value_signal() -> None:
    """STR-001 generates signal when Polymarket diverges from Deribit Breeden-Litzenberger probability."""
    alpha = STR001RelativeValueAlpha(
        min_edge_bps=200.0,
        poly_fee_bps=50.0,
        deribit_fee_bps=30.0,
        slippage_buffer_bps=20.0,
    )

    # Polymarket price = 0.65
    # ATM Deribit Call (F=60000, K=60000, T=0.1, sigma=0.50, skew=0) -> P_RN approx 0.49
    # Divergence approx +0.16 (+1600 bps) -> Significantly overpriced Polymarket contract
    data_large_spread = {
        "polymarket_mid_price": 0.65,
        "deribit_forward_price": 60000.0,
        "strike_price": 60000.0,
        "time_to_expiry_years": 0.1,
        "implied_volatility": 0.50,
        "dsigma_dK": 0.0,
    }

    sig = alpha.generate_signal(data_large_spread, current_ts_ns=1_000_000_000)
    assert sig is not None
    assert sig.direction == SignalDirection.SHORT  # Sell overpriced Polymarket
    assert sig.expected_edge_bps > 1000.0
    assert sig.confidence > 0.0

    # Small divergence within fee hurdle -> No trade
    data_tight_spread = {
        "polymarket_mid_price": 0.47,
        "deribit_forward_price": 60000.0,
        "strike_price": 60000.0,
        "time_to_expiry_years": 0.1,
        "implied_volatility": 0.50,
        "dsigma_dK": 0.0,
    }
    sig_tight = alpha.generate_signal(data_tight_spread, current_ts_ns=1_000_000_000)
    assert sig_tight is None


def test_str002_event_study_trajectory_and_signal() -> None:
    """STR-002 evaluates all 14 dimensions and trades only on Forced moves."""
    alpha = STR002EventStudyAlpha(min_z_score=2.5, min_retracement_target_pct=0.35, fee_and_slippage_bps=8.0)

    # Shock: Price expands up from 60,000 to 62,000 with liquidations
    forced_event = PriceImpulseEvent(
        event_id="impulse_1",
        symbol="BTCUSDT",
        venue="binance_perp",
        ts_start_ns=1_000_000_000_000_000,
        ts_peak_ns=1_000_001_000_000_000,
        start_price=60000.0,
        peak_price=62000.0,
        impulse_return=0.033,
        prior_volatility=0.008,
        z_score=4.12,
        direction=ShockDirection.EXPANSION_UP,
        has_forced_liquidations=True,
        forced_liquidation_volume=2_500_000.0,
    )

    # Causal path: BBO series with timestamps; entry at ASK after latency
    t0 = forced_event.ts_peak_ns
    bbo = [BboQuote(t0 + 1_000_000_000 * k, bid=b, ask=b + 1.0) for k, b in
           [(1, 61900.0), (61, 61600.0), (121, 61300.0), (181, 61000.0)]]
    obs = alpha.analyze_event_trajectory(forced_event, bbo)
    assert obs.classification == MoveClassification.FORCED_LIQUIDITY_MOVE
    assert obs.entry.entry_price_source == "NONE"  # SHORT hypothesis: no executable fills modeled
    assert obs.execution_side == "SHORT_RESEARCH_ONLY"
    assert obs.horizon_results == {}
    assert obs.post_hoc_diagnostics.label == "POST_HOC_DIAGNOSTIC"

    # SHORT after EXPANSION_UP is research-only: no executable Signal
    sig = alpha.generate_signal({"impulse_event": forced_event, "is_fundamental_news": False}, current_ts_ns=100)
    assert sig is None
    assert alpha.research_candidates and alpha.research_candidates[0]["is_executable"] is False

    # Informative Move (news / hack): No retracement obligation -> STRICTLY NO SIGNAL
    sig_info = alpha.generate_signal({"impulse_event": forced_event, "is_fundamental_news": True}, current_ts_ns=100)
    assert sig_info is None
