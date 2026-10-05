import math
import random

import pyarrow as pa
import pyarrow.parquet as pq

from src.data.binance_history import KLINE_SCHEMA, hourly_path
from src.research.portfolio_lab import (BTC, COST_PER_TURNOVER, Daily, backtest, build_strategies, load_daily,
                                        run_portfolio_lab, s_tsmom)


def grid(n=900, k=30, seed=1, trend=0.0):
    rnd = random.Random(seed)
    g = Daily(days=list(range(n)))
    for j in range(k):
        s = BTC if j == 0 else f"S{j}USDT"
        p, prev, xs = 100.0, 0.0, []
        for _ in range(n):
            r = rnd.gauss(0, 0.03) + trend * prev
            prev = r
            p *= 1 + r
            xs.append(p)
        g.sig[s], g.px[s] = xs, xs
        g.taker[s] = [0.5 + rnd.gauss(0, 0.02) for _ in range(n)]
        g.fund[s] = [0.0001] * n
    return g


def test_random_market_nothing_passes():
    res = run_portfolio_lab(grid())
    assert res["n_estrategias"] == len(build_strategies()) and res["pasan"] == []


def test_planted_trend_is_found():
    g = grid(n=1200, trend=0.25, seed=2)
    res = run_portfolio_lab(g, [s for s in build_strategies() if s[0] == "tendencia_por_activo"])
    best = res["todas"][0]
    assert best["entrenamiento"]["t_stat"] > 3


def test_costs_and_funding_charged():
    g = Daily(days=list(range(200)))
    g.sig[BTC] = g.px[BTC] = [100.0] * 200
    g.fund[BTC] = [0.001] * 200
    g.taker[BTC] = [0.5] * 200
    rows = backtest(g, lambda gg, d: {BTC: 1.0})
    assert abs(rows[0][1] - (-COST_PER_TURNOVER - 0.001)) < 1e-12   # first day: buy cost + funding paid
    assert abs(rows[1][1] - (-0.001)) < 1e-12                         # then only funding


def test_no_lookahead():
    g = grid(n=400)
    f = s_tsmom(14, False, True)
    before = f(g, 300)
    for s in g.sig:
        for i in range(301, 400):
            g.sig[s][i] *= 2
    assert f(g, 300) == before


def test_load_daily_from_hourly_files(tmp_path):
    H = 3_600_000
    for sym in (BTC, "AAAUSDT"):
        cols = {n: [] for n in KLINE_SCHEMA.names}
        for h in range(24 * 200):
            for n_, v in zip(KLINE_SCHEMA.names, [h * H, 1.0, 1.0, 1.0, 100.0 + h, 10.0, 15.0, 1, 6.0, sym]):
                cols[n_].append(v)
        p = hourly_path(tmp_path, sym)
        p.parent.mkdir(parents=True)
        pq.write_table(pa.table(cols, schema=KLINE_SCHEMA), p)
    g = load_daily(tmp_path)
    i = 5
    dd = g.days[i]
    assert g.sig[BTC][i] == 100.0 + dd * 24 + 23 and g.px[BTC][i] == 100.0 + (dd + 1) * 24
    assert abs(g.taker[BTC][i] - 0.6) < 1e-12


def _with_qvol(g, seed=3):
    rnd = random.Random(seed)
    for s in g.px:
        base = rnd.uniform(1e6, 1e8)
        g.qvol[s] = [base * rnd.uniform(0.5, 1.5) for _ in g.days]
    return g


def test_v2_runs_and_buffer_cuts_turnover():
    from src.research.portfolio_lab import s_xs_buf, sc_taker, s_xs, taker_v2
    g = _with_qvol(grid(n=700))
    plain = backtest(g, s_xs(sc_taker(7), 8, True), 1)
    buf = backtest(g, s_xs_buf(sc_taker(7), 8, True), 1)
    assert sum(t for _, _, t in buf) < sum(t for _, _, t in plain)
    res = run_portfolio_lab(g, taker_v2())
    assert res["n_estrategias"] == 5 and all(r["entrenamiento"].get("dias", 0) > 100 for r in res["todas"])


def test_voltarget_scales_and_caps():
    from src.research.portfolio_lab import s_voltarget
    g = _with_qvol(grid(n=300))
    base = lambda gg, d: {BTC: 1.0}
    w = s_voltarget(base, target_annual=0.15, cap=2.0)(g, 200)
    # synthetic daily vol 3% -> ~57% annual -> scale ~0.26
    assert 0.1 < w[BTC] < 0.5
    w2 = s_voltarget(base, target_annual=10.0, cap=2.0)(g, 200)
    assert w2[BTC] == 2.0
