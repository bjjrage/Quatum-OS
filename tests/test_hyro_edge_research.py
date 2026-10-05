import math
from array import array
from unittest.mock import patch

import pytest

from src.research.hyro_edge import Candidate, Panel, backtest, hourly_trace, phase, weights


def panel(n=200):
    daily, hourly, funding = {}, {}, {}
    for j, s in enumerate(("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT")):
        daily[s] = {"c": [100 + d * (j + 1) * .1 for d in range(n)],
                    "qv": [20_000_000.] * n, "vol": [100.] * n,
                    "taker": [40. + j * 3] * n, "flow": [-.2 + j * .06] * n,
                    "fund": [0.] * n}
        hourly[s] = {k: array("d", [100.] * (n * 24)) for k in ("o", "h", "l", "c")}
        funding[s] = {}
    return Panel(0, n, daily, hourly, 0, funding, {})


def test_both_entry_and_actual_exit_notional_pay_costs():
    p = panel()
    with patch("src.research.hyro_edge.weights", return_value={"BTCUSDT": 1.}):
        r = backtest(p, Candidate("trend", 28, 1), start=150, stop=152)
    assert r[0].pnl == pytest.approx(-.00075)
    assert r[1].pnl == pytest.approx(-.0015)
    assert r[1].closed[0]["net"] == pytest.approx(-.0015)


def test_positions_keep_fixed_quantity_between_rebalances():
    p = panel()
    h = 151 * 24 + 1
    p.hourly["BTCUSDT"]["o"][h + 24] = 110
    p.hourly["BTCUSDT"]["o"][h + 48] = 121
    with patch("src.research.hyro_edge.weights", return_value={"BTCUSDT": 1.}):
        r = backtest(p, Candidate("trend", 28, 7), side_cost_bps=0, start=150, stop=152)
    assert [a.pnl for a in r] == pytest.approx([.10, .11])


def test_funding_is_paid_on_marked_notional():
    p = panel()
    h = 151 * 24 + 8
    p.funding["BTCUSDT"][h] = [(h * 3_600_000, .001, 110)]
    with patch("src.research.hyro_edge.weights", return_value={"BTCUSDT": 1.}):
        r = backtest(p, Candidate("trend", 28, 7), side_cost_bps=0, start=150, stop=151)
    assert r[0].pnl == pytest.approx(-.0011)


def test_future_prices_flow_volume_cannot_change_past_signal():
    p = panel()
    cfg = Candidate("flow_residual", 7, 7, "majors")
    old = weights(p, 150, cfg)
    for ds in p.daily.values():
        for k, x in ds.items():
            x[151:] = [999999.] * (len(x) - 151)
    p.eligibility_cache.clear()
    assert weights(p, 150, cfg) == old


def test_missing_execution_prices_fail_closed():
    p = panel()
    p.hourly["BTCUSDT"]["o"][151 * 24 + 1] = math.nan
    with patch("src.research.hyro_edge.weights", return_value={"BTCUSDT": 1.}):
        with pytest.raises(ValueError, match="Missing"):
            backtest(p, Candidate("trend", 28, 1), start=150, stop=151)


def test_adverse_unrealized_loss_is_checked_before_a_profitable_close():
    trace = [{"hour": 24, "equity": 1.1, "open_equity": 1., "worst": .94, "best": 1.1,
              "realized": .1, "max_realized_loss": 0, "gross_upper": 1., "closes": []}]
    assert phase(trace, scale=1)["status"] == "BREACH_BOUND"


def test_profit_cap_and_valid_days_use_actual_scaled_trade_notional():
    trace = [{"hour": (d + 1) * 24, "equity": 1 + .03 * (d + 1),
              "open_equity": 1 + .03 * d, "worst": 1 + .03 * d,
              "best": 1 + .03 * (d + 1), "realized": .03, "max_realized_loss": 0.,
              "gross_upper": .5, "closes": [{"entry_notional": .06, "move": .02}]}
             for d in range(5)]
    full = phase(trace, target=.05, scale=1.)
    half = phase(trace, target=.05, scale=.5)
    assert full["status"] == "NUMERICAL_PASS" and full["days"] == 5
    assert full["credited_pct"] == pytest.approx(10.)  # 2% per day credited; losses uncapped.
    assert half["status"] == "UNFINISHED" and half["valid_days"] == 0


def test_hourly_trace_agrees_with_daily_cash_accounting_on_flat_prices():
    p = panel()
    cfg = Candidate("trend", 28, 1)
    with patch("src.research.hyro_edge.weights", return_value={"BTCUSDT": 1.}):
        daily = backtest(p, cfg, start=150, stop=152)
        trace = hourly_trace(p, cfg, 150, 152)
    assert trace[-1]["equity"] - 1 == pytest.approx(sum(r.pnl for r in daily))


def minutes_fixture():
    from src.research.hyro_minute import Minutes
    first = 151 * 1440 + 60
    return Minutes(first, first + 2880, {"BTCUSDT":
        {k: array("d", [100.] * 2880) for k in ("o", "h", "l", "c")}})


def test_minute_portfolio_cash_reconciles_after_final_liquidation():
    from src.research.hyro_minute import run
    p, m = panel(), minutes_fixture()
    with patch("src.research.hyro_minute.weights", return_value={"BTCUSDT": 1.}):
        r = run(p, m, Candidate("flow", 7, 7), 150, 152)
    assert sum(d["pnl"] for d in r["daily"]) == pytest.approx(-.00075)
    assert r["trades"][-1]["minute"] == m.last - 1


def test_minute_stop_takes_opening_gap_and_all_costs():
    from src.research.hyro_minute import run
    p, m = panel(), minutes_fixture()
    m.data["BTCUSDT"]["l"][5] = 89.
    m.data["BTCUSDT"]["o"][5] = 90.
    with patch("src.research.hyro_minute.weights", return_value={"BTCUSDT": 1.}):
        r = run(p, m, Candidate("flow", 7, 7), 150, 152, leg_stop=.08)
    assert r["leg_stop_count"] == 1
    assert r["trades"][0]["gross_move"] == pytest.approx(.10)
    assert r["trades"][0]["net"] == pytest.approx(-.05 - .000375 - .0003375)
    assert len(r["trades"]) == 1


def test_minute_daily_circuit_liquidates_at_adverse_prices_without_reentry():
    from src.research.hyro_minute import run
    p, m = panel(), minutes_fixture()
    m.data["BTCUSDT"]["l"][5] = 96.
    with patch("src.research.hyro_minute.weights", return_value={"BTCUSDT": 1.}):
        r = run(p, m, Candidate("flow", 7, 7), 150, 152, daily_stop=.015)
    assert r["daily_circuit_count"] == 1
    assert r["trades"][0]["gross_move"] == pytest.approx(.04)
    assert len(r["trades"]) == 1


def test_hourly_restart_preserves_the_frozen_weekly_calendar():
    p = panel()
    with patch("src.research.hyro_edge.weights", return_value={"BTCUSDT": 1.}):
        trace = hourly_trace(p, Candidate("flow", 7, 7), 151, 161)
    assert [r["hour"] // 24 - 1 for r in trace if r["block_start"]] == [151, 157]
