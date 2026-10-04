import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from src.data.binance_history import KLINE_SCHEMA
from src.research.pyr_like import analysis_symbols, evaluate, profile_symbols, split_groups
from src.research.str002_replay import Bars, ReplayConfig, simulate_exit, Panel


def _bars(o, h, l, c):
    n = len(c)
    nan = [float("nan")] * n
    return Bars(list(o), list(h), list(l), list(c), [0.0] * n, [0.0] * n, nan, nan, [False] * n)


def test_half_trail_blends_two_legs():
    cfg = ReplayConfig(exit_mode="half_trail", tp_pct=0.01, tp_fraction=0.5, trail_pct=0.005, init_stop_pct=0.01,
                       max_hold_min=10, min_hold_min=1, fee_bps=0, slip_bps=0)
    # entry at 100; bar1 reaches +1% (sells half at 101); bar2 runs to 104; bar3 falls to the trailing stop
    o = [100, 100, 101, 104, 103]
    h = [100, 101.2, 104, 104, 103]
    l = [100, 100, 101, 103.3, 102]
    c = [100, 101, 104, 103.5, 102.5]
    tr = simulate_exit(_bars(o, h, l, c), 0, cfg)
    assert tr["exit_reason"].startswith("MITAD+")
    # first half +1%; second half exits at the trailing stop 104*(1-0.005)=103.48
    assert abs(tr["gross_pct"] - (0.5 * 1.0 + 0.5 * 3.48)) < 0.05


def test_half_trail_stop_before_target_is_plain_loss():
    cfg = ReplayConfig(exit_mode="half_trail", tp_pct=0.01, init_stop_pct=0.005, max_hold_min=5, min_hold_min=1,
                       fee_bps=0, slip_bps=0)
    tr = simulate_exit(_bars([100, 100, 99], [100, 100.2, 99], [100, 99.0, 98.5], [100, 99.2, 98.8]), 0, cfg)
    assert tr["exit_reason"] == "HARD_STOP" and tr["gross_pct"] < 0


def _write(root: Path, sym: str, closes):
    rows = {n: [] for n in KLINE_SCHEMA.names}
    for i, c in enumerate(closes):
        for n, v in zip(KLINE_SCHEMA.names, [i * 60_000, c, c, c, c, 1.0, 1.0, 1, 0.5, sym]):
            rows[n].append(v)
    d = root / "klines_1m" / f"symbol={sym}"
    d.mkdir(parents=True)
    pq.write_table(pa.table(rows, schema=KLINE_SCHEMA), d / f"{sym}-2026-01.parquet")


def test_profile_ranks_by_volatility(tmp_path):
    n = 60 * 24 * 25
    calm = [100 + 0.01 * ((i // 5) % 2) for i in range(n)]
    wild = [100 * (1.03 if (i // 5) % 2 else 1.0) for i in range(n)]
    _write(tmp_path, "CALMUSDT", calm); _write(tmp_path, "WILDUSDT", wild); _write(tmp_path, "MIDUSDT", [100 + 0.2 * ((i // 5) % 2) for i in range(n)])
    prof = profile_symbols(tmp_path, ["CALMUSDT", "WILDUSDT", "MIDUSDT"], 0, n * 60_000 * 1_000_000)
    assert [p["symbol"] for p in prof] and max(prof, key=lambda p: p["sigma5_pct"])["symbol"] == "WILDUSDT"
    g = split_groups(prof)
    assert "WILDUSDT" in g["parecidas_a_PYR"] and "CALMUSDT" in g["tranquilas"]


def test_analysis_symbols_adds_candidates_without_duplicates():
    s = analysis_symbols(["BTCUSDT", "GALAUSDT"])
    assert s.count("GALAUSDT") == 1 and "PYRUSDT" in s
