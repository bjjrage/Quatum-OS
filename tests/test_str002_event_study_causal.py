"""Hardening 02C: causal STR-002 event study execution model tests."""
import math

import pytest

from src.research.events import PriceImpulseEvent, ShockDirection
from src.strategies.factory import Signal, SignalDirection
from src.strategies.str002_event_study import (
    STR002EventStudyAlpha,
    BboQuote,
    EventProvenance,
    STATUS_EXECUTED,
    STATUS_STOPPED,
    STATUS_HORIZON_NOT_AVAILABLE,
    STATUS_MISSING_ASK,
    STATUS_MISSING_BID,
    STATUS_RESEARCH_ONLY_SHORT,
)
from src.strategies.str002_v2 import TwoFactorResidualEstimator, Str002V2Strategy

T0 = 1_000_000_000_000_000
NS = 1_000_000_000


def ts(sec: float) -> int:
    return T0 + int(sec * NS)


def q(sec, bid, ask, bd=None, ad=None):
    return BboQuote(timestamp_ns=ts(sec), bid=bid, ask=ask, bid_depth=bd, ask_depth=ad)


def down_event(**kw):
    base = dict(
        event_id="ev1", symbol="ETHUSDT", venue="binance_perp",
        ts_start_ns=T0 - 5 * NS, ts_peak_ns=T0, start_price=100.0, peak_price=90.0,
        impulse_return=-0.10, prior_volatility=0.01, z_score=-4.5,
        direction=ShockDirection.EXPANSION_DOWN, has_forced_liquidations=True,
        forced_liquidation_volume=5_000_000.0,
    )
    base.update(kw)
    return PriceImpulseEvent(**base)


def up_event():
    return down_event(
        event_id="evUp", start_price=90.0, peak_price=100.0, impulse_return=0.111,
        z_score=4.5, direction=ShockDirection.EXPANSION_UP,
    )


def base_series(decoy=True):
    s = []
    if decoy:
        s.append(q(0.1, 80.0, 80.5))  # BEFORE executable entry time (latency 250ms)
    s += [
        q(1.0, 90.5, 91.0),
        q(61, 92.0, 92.1), q(181, 93.0, 93.1), q(301, 94.0, 94.1),
        q(901, 95.0, 95.1), q(1801, 96.0, 96.1),
    ]
    return s


def alpha(**kw):
    return STR002EventStudyAlpha(**kw)


BID_AT = {"1m": 92.0, "3m": 93.0, "5m": 94.0, "15m": 95.0, "30m": 96.0}
SECS = {"1m": 61, "3m": 181, "5m": 301, "15m": 901, "30m": 1801}


@pytest.mark.parametrize("h", ["1m", "3m", "5m", "15m", "30m"])
def test_fixed_horizon_timestamp_based(h):
    obs = alpha().analyze_event_trajectory(down_event(), base_series())
    r = obs.horizon_results[h]
    assert r.status == STATUS_EXECUTED
    assert r.target_timestamp_ns == ts(1.0) + int({"1m": 60, "3m": 180, "5m": 300, "15m": 900, "30m": 1800}[h] * NS)
    assert r.exit_timestamp_ns == ts(SECS[h])
    assert r.exit_bid == BID_AT[h]
    assert r.gross_return_bps == pytest.approx((BID_AT[h] / 91.0 - 1.0) * 1e4)


def test_irregular_sampling_uses_first_quote_at_or_after_target():
    s = [q(1.0, 90.5, 91.0), q(59, 99.0, 99.1), q(75, 92.5, 92.6), q(200, 93.0, 93.1)]
    obs = alpha().analyze_event_trajectory(down_event(), s)
    r = obs.horizon_results["1m"]
    assert r.exit_timestamp_ns == ts(75) and r.exit_bid == 92.5  # not the earlier 59s row
    assert r.target_timestamp_ns == ts(61)


def test_missing_30m_does_not_use_last_row():
    s = [x for x in base_series() if x.timestamp_ns <= ts(901)]
    obs = alpha().analyze_event_trajectory(down_event(), s)
    r = obs.horizon_results["30m"]
    assert r.status == STATUS_HORIZON_NOT_AVAILABLE
    assert r.exit_bid is None and r.net_return_bps is None
    assert obs.horizon_results["15m"].status == STATUS_EXECUTED


def test_entry_after_decision_and_latency():
    obs = alpha().analyze_event_trajectory(
        down_event(), base_series(), signal_timestamp_ns=ts(3.0), decision_timestamp_ns=ts(5.0)
    )
    assert obs.event_timestamp_ns <= obs.signal_timestamp_ns <= obs.decision_timestamp_ns
    assert obs.entry_timestamp_ns >= obs.decision_timestamp_ns + int(250 * 1_000_000)


def test_timeline_violation_rejected():
    with pytest.raises(ValueError):
        alpha().analyze_event_trajectory(down_event(), base_series(), signal_timestamp_ns=ts(-1))
    with pytest.raises(ValueError):
        alpha().analyze_event_trajectory(
            down_event(), base_series(), signal_timestamp_ns=ts(5), decision_timestamp_ns=ts(2)
        )


def test_modeled_latency_enforced():
    s = [q(0.1, 80.0, 80.5), q(1.0, 90.5, 91.0), q(2.5, 91.0, 91.5)] + base_series(False)[1:]
    obs = alpha(execution_latency_ms=2000.0).analyze_event_trajectory(down_event(), s)
    assert obs.entry_timestamp_ns == ts(2.5)
    assert obs.entry.entry_ask == 91.5


def test_invalid_latency_rejected():
    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            alpha(execution_latency_ms=bad)


def test_long_entry_uses_ask():
    obs = alpha().analyze_event_trajectory(down_event(), base_series())
    assert obs.entry.entry_ask == 91.0 and obs.entry.entry_price_source == "ASK"
    assert obs.entry.entry_ask != down_event().peak_price  # never the event peak


def test_long_exit_uses_bid():
    obs = alpha().analyze_event_trajectory(down_event(), base_series())
    r = obs.horizon_results["1m"]
    assert r.exit_price_source == "BID" and r.exit_bid == 92.0
    assert r.gross_return_bps == pytest.approx((92.0 / 91.0 - 1) * 1e4)  # not ask 92.1


def test_missing_ask_fails_closed():
    s = [q(1.0, 90.5, None)] + base_series(False)[1:]
    obs = alpha().analyze_event_trajectory(down_event(), s)
    assert obs.entry.status == STATUS_MISSING_ASK
    for r in obs.horizon_results.values():
        assert r.status == STATUS_MISSING_ASK
        assert r.net_return_bps is None and r.gross_return_bps is None


def test_missing_bid_marks_horizon_unavailable():
    s = base_series()
    s[4] = q(301, None, 94.1)
    obs = alpha().analyze_event_trajectory(down_event(), s)
    r = obs.horizon_results["5m"]
    assert r.status == STATUS_MISSING_BID and r.net_return_bps is None and r.exit_bid is None
    assert obs.horizon_results["3m"].status == STATUS_EXECUTED


def test_stop_evaluated_chronologically():
    s = [q(1.0, 90.5, 91.0), q(30, 89.9, 90.0), q(61, 99.0, 99.1), q(181, 99.0, 99.1)]
    obs = alpha().analyze_event_trajectory(down_event(), s)
    assert obs.stop_price == pytest.approx(90.0)
    for h in ("1m", "3m"):
        r = obs.horizon_results[h]
        assert r.status == STATUS_STOPPED and r.exit_timestamp_ns == ts(30)
        assert r.net_return_bps < 0  # later rebound NOT credited


def test_gap_through_stop_uses_conservative_bid():
    s = [q(1.0, 90.5, 91.0), q(10, 85.0, 85.5), q(61, 99.0, 99.1)]
    obs = alpha().analyze_event_trajectory(down_event(), s)
    r = obs.horizon_results["1m"]
    assert r.status == STATUS_STOPPED
    assert r.exit_bid == 85.0 and r.exit_bid < obs.stop_price  # not the theoretical 90.0
    assert obs.stop_fill_model == "BID_AT_TRIGGER_QUOTE_CONSERVATIVE"


def _results(obs):
    return {h: (r.status, r.exit_bid, r.net_return_bps) for h, r in obs.horizon_results.items()}


def test_mfe_is_diagnostic_only():
    a = alpha().analyze_event_trajectory(down_event(), base_series())
    spike = sorted(base_series() + [q(100, 200.0, 200.1)], key=lambda x: x.timestamp_ns)
    b = alpha().analyze_event_trajectory(down_event(), spike)
    assert b.post_hoc_diagnostics.mfe > a.post_hoc_diagnostics.mfe
    assert a.post_hoc_diagnostics.label == "POST_HOC_DIAGNOSTIC"
    assert _results(a) == _results(b)


def test_max_retracement_does_not_determine_net_return():
    a = alpha().analyze_event_trajectory(down_event(), base_series())
    spike = sorted(base_series() + [q(100, 200.0, 200.1)], key=lambda x: x.timestamp_ns)
    b = alpha().analyze_event_trajectory(down_event(), spike)
    assert a.post_hoc_diagnostics.max_retracement_ratio != b.post_hoc_diagnostics.max_retracement_ratio
    for h in a.horizon_results:
        assert a.horizon_results[h].net_return_bps == b.horizon_results[h].net_return_bps


def test_no_best_horizon_selection():
    obs = alpha().analyze_event_trajectory(down_event(), base_series())
    names = set(obs.__dataclass_fields__)
    assert not any("best" in n or "net_edge" in n for n in names)
    assert set(obs.horizon_results) == {"1m", "3m", "5m", "15m", "30m"}


def test_explicit_fees_applied():
    obs = alpha(entry_fee_bps=3.0, exit_fee_bps=5.0, slippage_bps=1.0).analyze_event_trajectory(
        down_event(), base_series())
    r = obs.horizon_results["1m"]
    assert (r.entry_fee_bps, r.exit_fee_bps) == (3.0, 5.0)
    assert r.total_cost_bps == 9.0
    assert r.cost_assumption_label == "MODEL_ASSUMPTION"


def test_explicit_slippage_applied():
    obs = alpha(slippage_bps=7.0).analyze_event_trajectory(down_event(), base_series())
    r = obs.horizon_results["1m"]
    assert r.slippage_bps == 7.0 and r.total_cost_bps == 2.0 + 2.0 + 7.0


def test_spread_reflected_by_executable_bbo_not_double_counted():
    tight = [q(1.0, 90.9, 91.0), q(61, 92.0, 92.01)]
    wide = [q(1.0, 90.9, 91.0), q(61, 91.0, 93.0)]  # same-ish mid at exit, wide spread
    a = alpha().analyze_event_trajectory(down_event(), tight).horizon_results["1m"]
    b = alpha().analyze_event_trajectory(down_event(), wide).horizon_results["1m"]
    assert b.gross_return_bps < a.gross_return_bps
    assert a.total_cost_bps == b.total_cost_bps  # spread not added to explicit costs
    assert b.exit_spread_component_bps > a.exit_spread_component_bps


def test_depth_missing_stays_unresolved():
    obs = alpha().analyze_event_trajectory(down_event(), base_series(), order_qty=100.0)
    assert obs.entry.capacity_status == "DEPTH_NOT_AVAILABLE"
    assert obs.entry.fill_ratio is None and obs.depth is None


@pytest.mark.parametrize("depth,expected", [(200.0, "FULL_FILL"), (70.0, "PARTIAL_FILL"), (30.0, "CAPACITY_LIMITED"), (0.0, "UNEXECUTABLE")])
def test_depth_limited_classification(depth, expected):
    s = [q(1.0, 90.5, 91.0, ad=depth), q(61, 92.0, 92.1)]
    obs = alpha().analyze_event_trajectory(down_event(), s, order_qty=100.0)
    assert obs.entry.capacity_status == expected
    assert obs.depth == depth


def test_future_mutation_does_not_alter_signal_or_entry():
    # Estimator/signal side: mutate data strictly after t
    n, t = 45, 39
    base = [0.0002 + 0.00005 * ((i % 3) - 1) for i in range(n)]
    alt = base[:t] + [-0.07] + base[t + 1:]
    est = TwoFactorResidualEstimator()
    fit1 = est.fit_pre_shock(alt[:t], base[:t], base[:t])
    e1, z1 = est.evaluate_shock_at_t(fit1, alt[t], base[t], base[t])
    alt_m = alt[: t + 1] + [9.9] * (n - t - 1)
    base_m = base[: t + 1] + [-5.0] * (n - t - 1)
    fit2 = est.fit_pre_shock(alt_m[:t], base_m[:t], base_m[:t])
    e2, z2 = est.evaluate_shock_at_t(fit2, alt_m[t], base_m[t], base_m[t])
    assert (fit1.beta_down, fit1.beta_up, fit1.gamma_eth, fit1.sigma_eps) == (
        fit2.beta_down, fit2.beta_up, fit2.gamma_eth, fit2.sigma_eps)
    assert (e1, z1) == (e2, z2)

    # Strategy decision at t unchanged (no future input possible; truncated series identical)
    def run():
        st = Str002V2Strategy()
        return st.generate_signal(
            symbol="FM", timestamp_ns=ts(0), r_alt_series=alt[: t + 1], r_btc_series=base[: t + 1],
            r_eth_series=base[: t + 1], btc_returns_1m_5m_15m=(0.0001,) * 3, btc_vol_5m_ratio=1.0,
            current_price=10.0, pre_shock_origin=11.0, pre_shock_vwap=10.9, delta_5s=500.0,
            bid_depth_0_5pct=60000.0, pre_shock_median_depth=100000.0, recent_1s_lows=[9.8, 9.7, 9.9],
            allowed_risk_usd=100.0)
    assert run()[2]["decision"] == run()[2]["decision"] == "EXECUTE_LONG"

    # Event study side: mutate quotes strictly after entry
    a = alpha().analyze_event_trajectory(down_event(), base_series())
    mutated = [x for x in base_series() if x.timestamp_ns <= a.entry_timestamp_ns] + [
        q(61, 50.0, 50.1), q(181, 150.0, 150.1), q(301, 10.0, 10.1)]
    b = alpha().analyze_event_trajectory(down_event(), mutated)
    for f in ("event_id", "signal_timestamp_ns", "decision_timestamp_ns", "entry_timestamp_ns", "execution_side"):
        assert getattr(a, f) == getattr(b, f)
    assert a.entry.entry_ask == b.entry.entry_ask
    assert a.post_hoc_diagnostics.mfe != b.post_hoc_diagnostics.mfe  # allowed to change


def test_pre_entry_data_change_does_not_change_fill():
    a = alpha().analyze_event_trajectory(down_event(), base_series(decoy=True))
    s = base_series(decoy=False)
    s.insert(0, q(0.2, 1.0, 2.0))  # strictly before decision+latency
    b = alpha().analyze_event_trajectory(down_event(), s)
    assert a.entry.entry_ask == b.entry.entry_ask == 91.0
    assert a.entry_timestamp_ns == b.entry_timestamp_ns


def test_short_does_not_return_standard_signal():
    al = alpha()
    sig = al.generate_signal({"impulse_event": up_event(), "is_fundamental_news": False}, current_ts_ns=1)
    assert sig is None
    assert al.research_candidates[0]["is_executable"] is False
    # and LONG still works
    sig_long = al.generate_signal({"impulse_event": down_event(), "is_fundamental_news": False}, current_ts_ns=1)
    assert isinstance(sig_long, Signal) and sig_long.direction == SignalDirection.LONG
    obs = al.analyze_event_trajectory(up_event(), base_series())
    assert obs.entry.status == STATUS_RESEARCH_ONLY_SHORT and obs.horizon_results == {}


def test_provenance_populated():
    prov = EventProvenance(beta_down=1.4, beta_up=1.1, gamma_eth=0.3, residual=-0.06,
                           shock_z_score=-4.2, btc_state="FLAT", dataset_version_or_hash="h1", git_sha="abc123")
    obs = alpha().analyze_event_trajectory(down_event(), base_series(), provenance=prov,
                                           funding_rate=0.0001, market_regime="CHOP")
    assert obs.provenance.strategy_id == "STR-002" and obs.provenance.git_sha == "abc123"
    assert obs.provenance.beta_down == 1.4 and obs.provenance.btc_state == "FLAT"
    assert (obs.event_id, obs.symbol, obs.venue) == ("ev1", "ETHUSDT", "binance_perp")
    assert obs.funding_rate == 0.0001 and obs.market_regime == "CHOP"
    assert obs.stop_price is not None and obs.risk_distance is not None


def test_unavailable_provenance_remains_unknown():
    obs = alpha().analyze_event_trajectory(down_event(), [q(1.0, None, 91.0), q(61, 92.0, 92.1)])
    p = obs.provenance
    assert p.beta_down is None and p.residual is None and p.git_sha == "UNKNOWN"
    assert p.dataset_version_or_hash == "UNKNOWN" and p.btc_state == "UNKNOWN"
    assert obs.market_regime == "UNKNOWN" and obs.liquidity_tier == "UNKNOWN"
    assert obs.funding_rate is None and obs.open_interest_delta is None
    assert obs.spread_bps is None and obs.depth is None  # nothing fabricated


def test_net_return_formula_reconciles_exactly():
    a = alpha(entry_fee_bps=1.5, exit_fee_bps=2.5, slippage_bps=3.25)
    obs = a.analyze_event_trajectory(down_event(), base_series())
    for r in obs.horizon_results.values():
        gross = (r.exit_bid / obs.entry.entry_ask - 1.0) * 1e4
        assert r.gross_return_bps == gross
        assert r.total_cost_bps == 1.5 + 2.5 + 3.25
        assert r.net_return_bps == gross - r.total_cost_bps
        assert math.isclose(r.net_return_bps, gross - 7.25, rel_tol=0, abs_tol=1e-12)
