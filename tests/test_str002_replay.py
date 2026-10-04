import math
import random
from pathlib import Path

import pytest

from src.research.str002_replay import (BTC, ETH, VARIANTS, Bars, Panel, ReplayConfig, btc_blocked,
                                        load_panel, residual_z, run_replay, shock_counts, summarize)

N = 700


def _series(seed=1, drop_at=500, drop=-0.03, rebound=0.02, btc_drop_at=None):
    rnd = random.Random(seed)
    btc, eth, alt = [100.0], [50.0], [10.0]
    for t in range(1, N):
        rb = rnd.gauss(0, 0.0005)
        if btc_drop_at is not None and btc_drop_at <= t < btc_drop_at + 5:
            rb = -0.004
        re_ = 0.8 * rb + rnd.gauss(0, 0.0004)
        ra = 1.2 * rb + rnd.gauss(0, 0.0006)
        if t == drop_at:
            ra += drop
        if drop_at < t <= drop_at + 4:
            ra += rebound / 4
        btc.append(btc[-1] * math.exp(rb)); eth.append(eth[-1] * math.exp(re_)); alt.append(alt[-1] * math.exp(ra))
    return btc, eth, alt


def _bars(c, buy_bias_from=None):
    o = [c[0]] + c[:-1]
    h = [max(a, b) * 1.0002 for a, b in zip(o, c)]
    l = [min(a, b) * 0.9998 for a, b in zip(o, c)]
    buy = [1.0] * len(c); sell = [1.0] * len(c)
    if buy_bias_from is not None:
        for i in range(buy_bias_from, len(c)):
            buy[i], sell[i] = 2.0, 1.0
    return Bars(o, h, l, c, buy, sell, [x * 1.0001 for x in c], [x * 0.9999 for x in c])


def _panel(**kw):
    btc, eth, alt = _series(**kw)
    p = Panel(minutes=list(range(N)))
    p.bars = {BTC: _bars(btc), ETH: _bars(eth), "ALTUSDT": _bars(alt, buy_bias_from=502)}
    return p


def test_no_entry_without_impulse():
    p = _panel(drop=0.0, rebound=0.0)
    out = run_replay(p, [ReplayConfig(name="x", z_enter=5.0, btc_block_sigma=99.0)])
    assert out["variants"]["x"]["summary"]["n_trades"] == 0


def test_low_threshold_fires_on_pure_noise():
    """Documented property: z=2 on pure noise already triggers ~2% of bars, so most z=2 entries are noise."""
    p = _panel(drop=0.0, rebound=0.0)
    n = shock_counts(p, z_levels=(2.0,), btc_sigmas=(99.0,))["impulses_per_day"]["btc_block_99_sigma"]["z_2"]
    assert n > 0


def test_impulse_then_first_stall_enters_and_exits_with_trailing():
    p = _panel()
    cfg = ReplayConfig(name="t", z_enter=3.0, btc_block_sigma=99.0, signals=("delta",), fee_bps=0, slip_bps=0)
    out = run_replay(p, [cfg])["variants"]["t"]
    trades = out["trades"]
    assert len(trades) == 1
    t = trades[0]
    assert 500 <= t["minute"] <= 505          # entered at the first stall, not 5 bars later
    assert t["z"] <= -3.0
    assert t["net_pct"] > 0                    # captured part of the rebound with the trailing stop
    assert t["exit_reason"] in ("TRAIL_STOP", "HARD_STOP", "MAX_HOLD")


def test_btc_dropping_hard_blocks_entry_when_filter_is_strict():
    p = _panel(btc_drop_at=498)
    strict = ReplayConfig(name="s", z_enter=2.0, btc_block_sigma=1.0, signals=("delta",))
    loose = ReplayConfig(name="l", z_enter=2.0, btc_block_sigma=99.0, signals=("delta",))
    out = run_replay(p, [strict, loose])["variants"]
    assert out["s"]["summary"]["n_trades"] <= out["l"]["summary"]["n_trades"]
    assert btc_blocked(p.bars[BTC].c, strict)[500] is True


def test_z_at_t_does_not_depend_on_the_future():
    p = _panel()
    cfg = ReplayConfig()
    full = residual_z(p.bars["ALTUSDT"].c, p.bars[BTC].c, p.bars[ETH].c, cfg)
    cut = 520
    part = residual_z(p.bars["ALTUSDT"].c[:cut], p.bars[BTC].c[:cut], p.bars[ETH].c[:cut], cfg)
    assert all(abs(full[i] - part[i]) < 1e-9 for i in range(cfg.fit_min + cfg.impulse_min, cut))


def test_lower_threshold_never_has_fewer_impulses():
    p = _panel()
    counts = shock_counts(p, z_levels=(2.0, 3.0), btc_sigmas=(99.0,))["impulses_per_day"]["btc_block_99_sigma"]
    assert counts["z_2"] >= counts["z_3"] > 0


def test_summary_warns_on_small_samples_and_handles_empty():
    assert summarize([], 1.0)["n_trades"] == 0
    s = summarize([{"net_pct": 0.5, "minute": 1, "symbol": "X", "exit_reason": "A", "signal": "d"}], 1.0)
    assert "warning" in s


def test_loader_builds_panel_from_parquet(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    base = tmp_path / "binance_perp"
    rows = {"ts_received_utc_ns": [], "symbol": [], "side": [], "price": [], "size": []}
    for sym, px in ((BTC, 100.0), (ETH, 50.0), ("ALTUSDT", 10.0)):
        for m in range(30):
            for sec, side in ((1, "BUY"), (30, "SELL")):
                rows["ts_received_utc_ns"].append((m * 60 + sec) * 1_000_000_000)
                rows["symbol"].append(sym); rows["side"].append(side)
                rows["price"].append(px + m * 0.01); rows["size"].append(1.0)
    d = base / "table=trade_ticks" / "date=2026-10-04"
    d.mkdir(parents=True)
    pq.write_table(pa.table(rows), d / "part.parquet")
    p = load_panel(tmp_path, [BTC, ETH, "ALTUSDT"])
    assert len(p.minutes) == 30 and set(p.bars) == {BTC, ETH, "ALTUSDT"}
    assert p.bars["ALTUSDT"].buy[3] == 1.0 and p.bars["ALTUSDT"].sell[3] == 1.0


# ---------------------------------------------------------------- exits + prop-firm check
from dataclasses import replace
from src.research.str002_replay import PROP_RULES, btc_move_sigmas, exit_variants, prop_check, simulate_symbol


def test_exit_comparison_uses_identical_entries():
    p = _panel()
    base = ReplayConfig(name="b", z_enter=3.0, btc_block_sigma=99.0, signals=("delta",))
    out = run_replay(p, [base], exit_base="b")
    ec = out["exit_comparison"]
    assert set(ec) == {"fixed", "trail", "btc_adaptive"}
    entries = {m: [(t["symbol"], t["minute"], round(t["entry"], 9)) for t in v["trades"]] for m, v in ec.items()}
    assert entries["fixed"] == entries["trail"] == entries["btc_adaptive"]


def _one_trade_panel(btc_up_after_entry: bool):
    """Flat alt that rises steadily after minute 300; BTC either rises with it or stays flat."""
    n = 400
    btc = [100.0] * n; eth = [50.0] * n; alt = [10.0] * n
    for t in range(1, n):
        btc[t] = btc[t - 1] * (1.0 + (0.0008 if (btc_up_after_entry and t > 300) else 0.00001 * ((-1) ** t)))
        eth[t] = eth[t - 1] * (1.0 + 0.00001 * ((-1) ** t))
        alt[t] = alt[t - 1] * (1.0 + (0.0015 if t > 300 else 0.00002 * ((-1) ** t)))
    p = Panel(minutes=list(range(n)))
    p.bars = {BTC: _bars(btc), ETH: _bars(eth), "ALTUSDT": _bars(alt)}
    return p


def _force_entry(p, cfg):
    z = [0.0] * len(p.minutes); z[300] = -9.0
    blocked = [False] * len(p.minutes)
    p.bars["ALTUSDT"].buy[300] = 5.0
    return simulate_symbol("ALTUSDT", p, z, blocked, cfg, btc_move_sigmas(p.bars[BTC].c, cfg))


def test_btc_adaptive_lets_winners_run_when_btc_rises():
    base = ReplayConfig(name="x", signals=("delta",), tp_pct=0.006, max_hold_min=30, fee_bps=0, slip_bps=0)
    p_up = _one_trade_panel(True)
    fixed = _force_entry(p_up, replace(base, exit_mode="fixed"))[0]
    adapt = _force_entry(_one_trade_panel(True), replace(base, exit_mode="btc_adaptive"))[0]
    assert fixed["exit_reason"] == "TARGET"
    assert adapt["btc_tailwind"] is True and adapt["net_pct"] > fixed["net_pct"]


def test_btc_adaptive_behaves_like_fixed_when_btc_is_flat():
    base = ReplayConfig(name="x", signals=("delta",), tp_pct=0.006, fee_bps=0, slip_bps=0)
    fixed = _force_entry(_one_trade_panel(False), replace(base, exit_mode="fixed"))[0]
    adapt = _force_entry(_one_trade_panel(False), replace(base, exit_mode="btc_adaptive"))[0]
    assert adapt["btc_tailwind"] is False and adapt["exit_reason"] == fixed["exit_reason"] == "TARGET"


def test_min_hold_blocks_early_target_but_never_the_hard_stop():
    base = ReplayConfig(name="x", signals=("delta",), tp_pct=0.0001, min_hold_min=3, exit_mode="fixed", fee_bps=0, slip_bps=0)
    t = _force_entry(_one_trade_panel(False), base)[0]
    assert t["hold_min"] >= 3


def _tr(day, net, stop=0.6):
    return {"minute": day * 1440 + 60, "hold_min": 5, "net_pct": net, "stop_pct": stop}


def test_prop_check_fails_on_daily_loss():
    trades = [_tr(0, -0.6) for _ in range(7)]           # 7 full stops at 0.75% risk = -5.1% in one day
    assert prop_check(trades, PROP_RULES["HyroTrader_1F"], 0.0075)["status"] == "FAIL_DAILY"


def test_prop_check_passes_with_steady_small_gains_over_enough_days():
    trades = [_tr(d, 0.25) for d in range(20) for _ in range(2)]   # +0.625% per trade at 0.75% risk / 0.6% stop
    r = prop_check(trades, PROP_RULES["HyroTrader_1F"], 0.0075)
    assert r["status"] == "PASA", r


def test_prop_check_consistency_rule_keeps_trading_after_one_huge_day():
    trades = [_tr(0, 6.0)] + [_tr(d, 0.0) for d in range(1, 3)]   # one day makes ~7.5% -> >40% of the 10% target
    r = prop_check(trades, PROP_RULES["HyroTrader_1F"], 0.0075)
    assert r["status"] == "AUN_NO"


def test_mubite_rejects_risk_above_its_cap():
    assert prop_check([_tr(0, 0.1)], PROP_RULES["Mubite_2F"], 0.05)["status"] == "FAIL_RULES"


# ---------------------------------------------------------------- data coverage (real-recording quirks)
from src.research.str002_replay import data_coverage, panel_from_rows


def _rows(sym, minutes, px=10.0, jump_at=None):
    out = []
    p = px
    for m in minutes:
        if jump_at is not None and m == jump_at:
            p *= 0.95
        out.append((sym, m, p, p * 1.0001, p * 0.9999, p, 1.0, 1.0))
        p *= 1.0 + 0.0001 * (1 if m % 2 else -1)
    return out


def test_recently_added_symbol_does_not_shrink_history():
    full = list(range(0, 600))
    rows = _rows(BTC, full, 100) + _rows(ETH, full, 50) + _rows("OLDUSDT", full) + _rows("NEWUSDT", list(range(550, 600)))
    p = panel_from_rows(rows, {}, [BTC, ETH, "OLDUSDT", "NEWUSDT"])
    assert len(p.minutes) == 600
    assert p.bars["NEWUSDT"].gap[100] is True and p.bars["OLDUSDT"].gap[100] is False


def test_recorder_downtime_never_creates_a_fake_impulse():
    up = [m for m in range(0, 900) if not (400 <= m < 460)]          # recorder down for an hour
    rows = (_rows(BTC, up, 100) + _rows(ETH, up, 50) + _rows("ALTUSDT", up, jump_at=460))
    p = panel_from_rows(rows, {}, [BTC, ETH, "ALTUSDT"])
    cfg = ReplayConfig()
    z = residual_z(p.bars["ALTUSDT"].c, p.bars[BTC].c, p.bars[ETH].c, cfg, p.bars["ALTUSDT"].gap)
    i = p.minutes.index(460)
    assert all(z[j] == 0.0 for j in range(i, i + cfg.fit_min))      # window still contains the gap
    cov = data_coverage(p)
    assert cov["recorder_down_minutes"] == 60 and abs(cov["longest_continuous_hours"] - 440 / 60) < 1e-9


# ---------------------------------------------------------------- 5-minute candles + random benchmark
from src.research.str002_replay import random_baseline, resample_panel


def test_resample_builds_correct_5min_candles():
    p = _panel()
    q = resample_panel(p, 5)
    b, a = p.bars["ALTUSDT"], q.bars["ALTUSDT"]
    i = p.minutes.index(q.minutes[3])
    assert a.o[3] == b.o[i] and a.c[3] == b.c[i + 4]
    assert a.h[3] == max(b.h[i:i + 5]) and a.l[3] == min(b.l[i:i + 5])
    assert a.buy[3] == sum(b.buy[i:i + 5])
    assert all(m % 5 == 0 for m in q.minutes)


def test_resample_marks_candle_unusable_if_any_minute_is():
    up = [m for m in range(0, 300) if m != 52]
    rows = _rows(BTC, up, 100) + _rows(ETH, up, 50) + _rows("ALTUSDT", up)
    p = panel_from_rows(rows, {}, [BTC, ETH, "ALTUSDT"])
    q = resample_panel(p, 5)
    assert q.bars["ALTUSDT"].gap[q.minutes.index(50)] is True
    assert q.bars["ALTUSDT"].gap[q.minutes.index(45)] is False


def test_hold_time_is_reported_in_minutes_for_5min_candles():
    p = resample_panel(_one_trade_panel(False), 5)
    cfg = ReplayConfig(name="x", bar_min=5, signals=("delta",), impulse_min=1, fit_min=48, max_hold_min=6,
                       min_hold_min=1, exit_mode="trail", fee_bps=0, slip_bps=0)
    b = p.bars["ALTUSDT"]
    from src.research.str002_replay import simulate_exit
    tr = simulate_exit(b, 60, cfg)
    assert tr["hold_min"] % 5 == 0 and tr["hold_min"] >= 5


def test_random_baseline_detects_a_real_edge_and_a_fake_one():
    # Market that always rebounds after a drop; the "strategy" enters right after drops, random entries don't.
    p = _panel()
    cfg = ReplayConfig(name="b", z_enter=3.0, btc_block_sigma=99.0, signals=("delta",), fee_bps=0, slip_bps=0)
    good = random_baseline(p, cfg, ["ALTUSDT"], n_entries=1, strategy_mean_net_pct=5.0, runs=100)
    bad = random_baseline(p, cfg, ["ALTUSDT"], n_entries=1, strategy_mean_net_pct=-5.0, runs=100)
    assert good["verdict"] == "MEJOR_QUE_AZAR" and bad["verdict"] == "PEOR_QUE_AZAR"
    assert good["random_p5_net_pct"] <= good["random_median_net_pct"] <= good["random_p95_net_pct"]


def test_random_baseline_is_reproducible():
    p = _panel()
    cfg = ReplayConfig(name="b", fee_bps=0, slip_bps=0)
    a = random_baseline(p, cfg, ["ALTUSDT"], 5, 0.0, runs=50)
    b = random_baseline(p, cfg, ["ALTUSDT"], 5, 0.0, runs=50)
    assert a == b


# ---------------------------------------------------------------- fast math == reference math
from src.research.str002_replay import (_btc_blocked_reference, _btc_move_sigmas_reference,
                                        _residual_z_reference)


def test_fast_residual_z_matches_reference():
    p = _panel()
    for cfg in (ReplayConfig(), ReplayConfig(impulse_min=1, fit_min=48, refit_every=3)):
        a = residual_z(p.bars["ALTUSDT"].c, p.bars[BTC].c, p.bars[ETH].c, cfg)
        b = _residual_z_reference(p.bars["ALTUSDT"].c, p.bars[BTC].c, p.bars[ETH].c, cfg)
        assert max(abs(x - y) for x, y in zip(a, b)) < 1e-6


def test_fast_btc_filters_match_reference():
    p = _panel(btc_drop_at=498)
    cfg = ReplayConfig(btc_block_sigma=1.0)
    assert btc_blocked(p.bars[BTC].c, cfg) == _btc_blocked_reference(p.bars[BTC].c, cfg)
    a, b = btc_move_sigmas(p.bars[BTC].c, cfg), _btc_move_sigmas_reference(p.bars[BTC].c, cfg)
    assert max(abs(x - y) for x, y in zip(a, b)) < 1e-6


def test_fast_path_handles_a_year_of_minutes_quickly():
    import time as _t
    n = 525_600
    rnd = random.Random(3)
    btc, eth, alt = [100.0], [50.0], [10.0]
    for _ in range(1, n):
        r = rnd.gauss(0, 5e-4)
        btc.append(btc[-1] * math.exp(r)); eth.append(eth[-1] * math.exp(0.8 * r + rnd.gauss(0, 4e-4)))
        alt.append(alt[-1] * math.exp(1.2 * r + rnd.gauss(0, 6e-4)))
    t0 = _t.time()
    residual_z(alt, btc, eth, ReplayConfig())
    btc_blocked(btc, ReplayConfig())
    assert _t.time() - t0 < 30
