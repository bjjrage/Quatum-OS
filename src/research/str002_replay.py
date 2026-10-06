"""STR-002 replay: impulse -> first stall -> long entry -> trailing exit, over RECORDED Binance data.

Point-in-time and bar-based (1-minute). Every decision at bar t uses only information up to the
close of bar t; entries fill at the last recorded ask of bar t (+ slippage). Exits are evaluated
conservatively: inside a bar the stop is assumed to hit before any favourable move.

This is an EXPLORATORY research tool. Comparing several configurations on the same data is multiple
testing: a winner here is a candidate to validate out of sample, never evidence of edge by itself.

The variants are deliberately parameters (nothing hidden in code):
  z_enter          how big the idiosyncratic impulse must be (in sigmas of pre-shock residuals)
  btc_block_sigma  block entries when BTC fell more than this many sigmas over the impulse window
  signals          which "first stall" signs count: green | delta | higher_low
  max_wait_min     give up if no stall sign appears within this many bars
  cooldown_min     pause per symbol after a shock is resolved
  trail_pct, init_stop_pct, max_hold_min   exit
"""
from __future__ import annotations

import math
from array import array
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

NaN = float('nan')


BTC, ETH = "BTCUSDT", "ETHUSDT"


@dataclass(frozen=True)
class ReplayConfig:
    name: str = "A_actual"
    z_enter: float = 3.0
    impulse_min: int = 5
    fit_min: int = 240
    refit_every: int = 15
    btc_block_sigma: float = 1.0
    signals: Tuple[str, ...] = ("delta", "higher_low")
    max_wait_min: int = 5
    cooldown_min: int = 10
    trail_pct: float = 0.004
    init_stop_pct: float = 0.006
    max_hold_min: int = 30
    fee_bps: float = 4.0
    slip_bps: float = 2.0
    min_price_move_pct: float = 0.0   # extra guard: impulse must also be at least this big in raw % terms
    # exit model: "trail" (trailing stop only) | "fixed" (target + stop) | "btc_adaptive"
    exit_mode: str = "trail"
    tp_pct: float = 0.006             # target for "fixed" and the base target of "btc_adaptive"
    btc_up_sigma: float = 1.0         # btc_adaptive: BTC up >= this -> drop the target, trail the stop
    btc_down_sigma: float = 1.0       # btc_adaptive: BTC down <= -this -> tighten stop to tight_trail_pct
    tight_trail_pct: float = 0.0015
    min_hold_min: int = 2             # target/trailing exits not before this; the hard stop always applies
    bar_min: int = 1                  # candle size in minutes. With bar_min > 1, every *_min field counts BARS.
    tp_fraction: float = 0.5          # half_trail: share of the position sold at tp_pct (the rest trails)


EXIT_LABELS = {"fixed": "salida fija", "trail": "trailing", "btc_adaptive": "adaptativa BTC",
               "half_trail": "mitad al objetivo + resto con trailing"}

VARIANTS: Dict[str, ReplayConfig] = {
    "A_actual": ReplayConfig(name="A_actual", z_enter=3.0, btc_block_sigma=1.0, signals=("delta", "higher_low")),
    "B_marcelo": ReplayConfig(name="B_marcelo", z_enter=2.0, btc_block_sigma=3.0, signals=("green", "delta")),
    "C_intermedia": ReplayConfig(name="C_intermedia", z_enter=2.5, btc_block_sigma=2.0, signals=("delta", "higher_low")),
    # Marcelo's own timeframe: 5-minute candles. Lengths in bars: impulse = 1 candle (5 min), history = 48 candles
    # (4 h), wait for the stall up to 3 candles (15 min), pause 2 candles, hold max 6 candles (30 min), min 1 candle.
    "D_marcelo_5m": ReplayConfig(name="D_marcelo_5m", bar_min=5, z_enter=2.0, btc_block_sigma=3.0,
                                 signals=("green", "delta"), impulse_min=1, fit_min=48, refit_every=3,
                                 max_wait_min=3, cooldown_min=2, max_hold_min=6, min_hold_min=1),
}

# Which variants get a random-entry benchmark (same exit, same number of entries, random moments).
BASELINE_FOR = ("B_marcelo", "D_marcelo_5m")


def exit_variants(base: ReplayConfig) -> List[ReplayConfig]:
    """Same entries, only the exit changes (isolates the value of the exit rule)."""
    return [replace(base, name=f"{base.name}__{m}", exit_mode=m) for m in ("fixed", "trail", "btc_adaptive")]


@dataclass
class Bars:
    """Aligned 1-minute bars for one symbol (all arrays share the same minute index)."""
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    buy: List[float]
    sell: List[float]
    ask: List[float]
    bid: List[float]
    gap: Optional[List[bool]] = None   # True where there is no usable data (outside the symbol's range / recorder down)


@dataclass
class Panel:
    minutes: List[int]                       # epoch minutes
    bars: Dict[str, Bars] = field(default_factory=dict)


# --------------------------------------------------------------------------- data loading
def load_panel(base_data_path: Path, symbols: Sequence[str], start_ns: Optional[int] = None,
               end_ns: Optional[int] = None, venue: str = "binance_perp") -> Panel:
    """Build a 1-minute panel from the recorded lakehouse (trade_ticks + bbo_ticks), DuckDB, read-only."""
    import duckdb
    from src.research.recorder_studies import is_complete_parquet
    base = Path(base_data_path)
    tfiles = [p.as_posix() for p in base.glob(f"{venue}/table=trade_ticks/**/*.parquet") if is_complete_parquet(p)]
    bfiles = [p.as_posix() for p in base.glob(f"{venue}/table=bbo_ticks/**/*.parquet") if is_complete_parquet(p)]
    if not tfiles:
        raise FileNotFoundError(f"No trade_ticks recorded under {base}/{venue}")
    syms = ",".join(f"'{s}'" for s in symbols)
    tw = f"symbol IN ({syms})"
    if start_ns is not None:
        tw += f" AND ts_received_utc_ns >= {int(start_ns)}"
    if end_ns is not None:
        tw += f" AND ts_received_utc_ns <= {int(end_ns)}"
    con = duckdb.connect()
    rows = con.execute(f"""
        SELECT symbol, CAST(floor(ts_received_utc_ns / 60000000000.0) AS BIGINT) AS m,
               arg_min(price, ts_received_utc_ns), max(price), min(price), arg_max(price, ts_received_utc_ns),
               sum(CASE WHEN upper(side) = 'BUY' THEN size ELSE 0 END),
               sum(CASE WHEN upper(side) = 'SELL' THEN size ELSE 0 END)
        FROM read_parquet({tfiles!r}, union_by_name=true) WHERE {tw} GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchall()
    quotes: Dict[Tuple[str, int], Tuple[float, float]] = {}
    if bfiles:
        for sym, m, bid, ask in con.execute(f"""
            SELECT symbol, CAST(floor(ts_received_utc_ns / 60000000000.0) AS BIGINT) AS m,
                   arg_max(bid_price, ts_received_utc_ns), arg_max(ask_price, ts_received_utc_ns)
            FROM read_parquet({bfiles!r}, union_by_name=true) WHERE {tw} GROUP BY 1, 2
        """).fetchall():
            quotes[(sym, int(m))] = (float(bid), float(ask))
    return panel_from_rows(rows, quotes, symbols)


def load_panel_historical(hist_root: Path, symbols: Sequence[str], start_ns: Optional[int] = None,
                          end_ns: Optional[int] = None) -> Panel:
    """1-minute panel from downloaded Binance klines (data/historical/binance_um). No bid/ask: entries fill
    at the candle close + slippage. Buy/sell split comes from the taker-buy volume of each candle.

    Built symbol by symbol from columnar reads so months of data stay within a few hundred MB of RAM."""
    import duckdb
    root = Path(hist_root)
    con = duckdb.connect()

    def files(sym: str) -> List[str]:
        return [p.as_posix() for p in root.glob(f"klines_1m/symbol={sym}/*.parquet")]

    t_where = ""
    if start_ns is not None:
        t_where += f" AND open_time_ms >= {int(start_ns // 1_000_000)}"
    if end_ns is not None:
        t_where += f" AND open_time_ms <= {int(end_ns // 1_000_000)}"
    ranges = {}
    for sym in (BTC, ETH):
        f = files(sym)
        if not f:
            raise FileNotFoundError(f"Falta el historial de {sym}: es necesario como referencia.")
        lo, hi = con.execute(f"SELECT min(open_time_ms // 60000), max(open_time_ms // 60000) "
                             f"FROM read_parquet({f!r}) WHERE TRUE {t_where}").fetchone()
        if lo is None:
            raise ValueError(f"No hay datos de {sym} en el período pedido.")
        ranges[sym] = (int(lo), int(hi))
    lo = max(r[0] for r in ranges.values())
    hi = min(r[1] for r in ranges.values())
    if hi - lo < 10:
        raise ValueError("Not enough overlapping minutes between BTC and ETH")
    n = hi - lo + 1
    panel = Panel(minutes=list(range(lo, hi + 1)))
    btc_down = None
    for sym in [BTC, ETH] + [s_ for s_ in symbols if s_ not in (BTC, ETH)]:
        f = files(sym)
        if not f:
            continue
        tbl = con.execute(f"""
            SELECT CAST(open_time_ms // 60000 AS BIGINT) AS m, open, high, low, close, taker_buy_volume,
                   greatest(volume - taker_buy_volume, 0) AS sv
            FROM read_parquet({f!r}) WHERE open_time_ms // 60000 BETWEEN {lo} AND {hi} {t_where} ORDER BY m
        """).fetch_arrow_table()
        if tbl.num_rows == 0:
            continue
        o = array("d", [NaN]) * n; h = array("d", [NaN]) * n; l = array("d", [NaN]) * n; c = array("d", [NaN]) * n
        bv = array("d", [0.0]) * n; sv = array("d", [0.0]) * n
        have = bytearray(n)
        cols = [tbl.column(i).to_pylist() for i in range(7)]
        for m, oo, hh, ll, cc, bb, ss in zip(*cols):
            i = m - lo
            o[i], h[i], l[i], c[i], bv[i], sv[i] = oo, hh, ll, cc, bb, ss
            have[i] = 1
        del cols, tbl
        first = have.find(1)
        last_i = have.rfind(1)
        last = c[first]
        for i in range(n):                     # flat bars where no candle exists (marked by `gap` when unusable)
            if not have[i]:
                o[i] = h[i] = l[i] = c[i] = last
            else:
                last = c[i]
        if sym == BTC:
            btc_down = [not x for x in have]   # no BTC candle = exchange/data outage: unusable for everyone
        gap = [i < first or i > last_i or (btc_down[i] if btc_down is not None else False) for i in range(n)]
        nanarr = array("d", [NaN]) * n
        panel.bars[sym] = Bars(o, h, l, c, bv, sv, nanarr, nanarr, gap)
    return panel


def historical_range(hist_root: Path) -> Optional[Tuple[int, int]]:
    """(first, last) open time in ns of the downloaded BTC history, or None."""
    import duckdb
    files = [p.as_posix() for p in Path(hist_root).glob(f"klines_1m/symbol={BTC}/*.parquet")]
    if not files:
        return None
    lo, hi = duckdb.connect().execute(
        f"SELECT min(open_time_ms), max(open_time_ms) FROM read_parquet({files!r})").fetchone()
    return (int(lo) * 1_000_000, int(hi) * 1_000_000) if lo is not None else None


def panel_from_rows(rows: Sequence[Tuple], quotes: Dict[Tuple[str, int], Tuple[float, float]],
                    symbols: Sequence[str]) -> Panel:
    by_sym: Dict[str, Dict[int, Tuple]] = {}
    for sym, m, o, h, l, c, bv, sv in rows:
        by_sym.setdefault(sym, {})[int(m)] = (float(o), float(h), float(l), float(c), float(bv), float(sv))
    if BTC not in by_sym or ETH not in by_sym:
        raise ValueError("BTCUSDT and ETHUSDT are required as the systemic factors")
    # The time axis is the BTC/ETH overlap (not the intersection of every symbol: a symbol added
    # recently must not shrink the whole history). Per-symbol coverage is tracked with `gap`.
    lo = max(min(by_sym[BTC]), min(by_sym[ETH]))
    hi = min(max(by_sym[BTC]), max(by_sym[ETH]))
    if hi - lo < 10:
        raise ValueError("Not enough overlapping minutes between BTC and ETH")
    minutes = list(range(lo, hi + 1))
    n = len(minutes)
    panel = Panel(minutes=minutes)
    for sym in symbols:
        d = by_sym.get(sym)
        if not d:
            continue
        # compact float arrays: months of minutes x dozens of symbols must fit in memory
        o = array("d", [NaN]) * n; h = array("d", [NaN]) * n; l = array("d", [NaN]) * n; c = array("d", [NaN]) * n
        bv = array("d", [0.0]) * n; sv = array("d", [0.0]) * n; ask = array("d", [NaN]) * n; bid = array("d", [NaN]) * n
        for i, m in enumerate(minutes):
            r = d.get(m)
            if r is not None:
                o[i], h[i], l[i], c[i], bv[i], sv[i] = r
            q = quotes.get((sym, m))
            if q is not None:
                bid[i], ask[i] = q
        first = next((i for i in range(n) if not math.isnan(c[i])), None)
        if first is None:
            continue
        lastidx = max(i for i in range(n) if not math.isnan(c[i]))
        gap = [i < first or i > lastidx for i in range(n)]
        last = c[first]
        for i in range(n):  # forward-fill minutes without trades as flat bars (marked by `gap` when unusable)
            if math.isnan(c[i]):
                o[i] = h[i] = l[i] = c[i] = last
            else:
                last = c[i]
        panel.bars[sym] = Bars(o, h, l, c, bv, sv, ask, bid, gap)
    # A minute with no BTC trade means the recorder was down: unusable for every symbol.
    btc = by_sym[BTC]
    down = [m not in btc for m in minutes]
    for b in panel.bars.values():
        b.gap = [g or dn for g, dn in zip(b.gap or [False] * n, down)]
    return panel


def resample_panel(panel: Panel, k: int) -> Panel:
    """Aggregate 1-minute bars into k-minute candles (a candle is unusable if any of its minutes is)."""
    if k <= 1:
        return panel
    n = len(panel.minutes)
    starts = [i for i in range(n) if panel.minutes[i] % k == 0 and i + k <= n]
    out = Panel(minutes=[panel.minutes[i] for i in starts])
    for sym, b in panel.bars.items():
        o, h, l, c, bv, sv, ask, bid, gap = [], [], [], [], [], [], [], [], []
        for i in starts:
            j = i + k
            o.append(b.o[i]); h.append(max(b.h[i:j])); l.append(min(b.l[i:j])); c.append(b.c[j - 1])
            bv.append(sum(b.buy[i:j])); sv.append(sum(b.sell[i:j]))
            ask.append(b.ask[j - 1]); bid.append(b.bid[j - 1])
            gap.append(any(b.gap[i:j]) if b.gap is not None else False)
        out.bars[sym] = Bars(o, h, l, c, bv, sv, ask, bid, gap)
    return out


def data_coverage(panel: Panel) -> Dict[str, Any]:
    """How much continuous, usable history there is (the model needs fit_min + impulse_min minutes in a row)."""
    g = panel.bars[BTC].gap or [False] * len(panel.minutes)
    usable = sum(1 for x in g if not x)
    longest = cur = 0
    for x in g:
        cur = 0 if x else cur + 1
        longest = max(longest, cur)
    return {"total_minutes": len(g), "usable_minutes": usable, "recorder_down_minutes": len(g) - usable,
            "longest_continuous_hours": longest / 60.0}


# --------------------------------------------------------------------------- statistics (pure python)
def _log_ret(c: Sequence[float]) -> List[float]:
    return [0.0] + [math.log(c[i] / c[i - 1]) for i in range(1, len(c))]


def _std(x: Sequence[float], ddof: int = 0) -> float:
    n = len(x)
    if n - ddof <= 0:
        return 0.0
    m = sum(x) / n
    return math.sqrt(sum((v - m) ** 2 for v in x) / (n - ddof))


def _ols(X: List[List[float]], y: List[float]) -> List[float]:
    """Least squares by normal equations + Gauss-Jordan (k <= 3 regressors, tiny ridge for stability)."""
    k = len(X[0])
    A = [[0.0] * (k + 1) for _ in range(k)]
    for row, yy in zip(X, y):
        for i in range(k):
            ri = row[i]
            for j in range(k):
                A[i][j] += ri * row[j]
            A[i][k] += ri * yy
    for i in range(k):
        A[i][i] += 1e-12
    for i in range(k):
        piv = max(range(i, k), key=lambda r: abs(A[r][i]))
        A[i], A[piv] = A[piv], A[i]
        d = A[i][i] or 1e-18
        for j in range(i, k + 1):
            A[i][j] /= d
        for r in range(k):
            if r != i:
                f = A[r][i]
                if f:
                    for j in range(i, k + 1):
                        A[r][j] -= f * A[i][j]
    return [A[i][k] for i in range(k)]


def _residual_z_reference(alt_c: Sequence[float], btc_c: Sequence[float], eth_c: Sequence[float],
               cfg: ReplayConfig, gap: Optional[Sequence[bool]] = None) -> List[float]:
    """z-score of the cumulative idiosyncratic return over the last `impulse_min` bars.

    Coefficients are fitted on a window that ENDS before the impulse window starts (frozen parameters).
    Regressors: BTC return, and ETH return orthogonalised against BTC.
    """
    n = len(alt_c)
    ra, rb, re_ = _log_ret(alt_c), _log_ret(btc_c), _log_ret(eth_c)
    k, w = cfg.impulse_min, cfg.fit_min
    z = [0.0] * n
    start = w + k
    res = [0.0] * n
    sig = [1e-9] * n
    coef = None
    for t in range(start, n):
        if coef is None or (t - start) % cfg.refit_every == 0:
            a, b = t - k - w, t - k
            xb, xe, y = rb[a:b], re_[a:b], ra[a:b]
            d = _ols([[1.0, v] for v in xb], xe)
            eta = [e - (d[0] + d[1] * v) for e, v in zip(xe, xb)]
            beta = _ols([[1.0, v, g] for v, g in zip(xb, eta)], y)
            resid = [yy - (beta[0] + beta[1] * v + beta[2] * g) for yy, v, g in zip(y, xb, eta)]
            s = _std(resid, ddof=3)
            coef = (d, beta, s if s > 1e-9 else 1e-9)
        d, beta, s = coef
        eta_t = re_[t] - (d[0] + d[1] * rb[t])
        res[t] = ra[t] - (beta[0] + beta[1] * rb[t] + beta[2] * eta_t)
        sig[t] = s
    csum = [0.0] * n
    acc = 0.0
    for i in range(n):
        acc += res[i]
        csum[i] = acc
    gp = [0] * (n + 1)
    for i in range(n):
        gp[i + 1] = gp[i] + (1 if gap is not None and gap[i] else 0)
    for t in range(start, n):
        if gp[t + 1] - gp[t - k - w] > 0:   # any missing data in fit + impulse window: no signal
            z[t] = 0.0
            continue
        z[t] = (csum[t] - csum[t - k]) / (sig[t] * math.sqrt(k))
    return z


def _btc_blocked_reference(btc_c: Sequence[float], cfg: ReplayConfig) -> List[bool]:
    """True where BTC fell >= btc_block_sigma sigmas over the impulse window (sigma from trailing history)."""
    n, k, w = len(btc_c), cfg.impulse_min, cfg.fit_min
    lr = [0.0] * n
    for t in range(k, n):
        lr[t] = math.log(btc_c[t] / btc_c[t - k])
    out = [False] * n
    for t in range(w + k, n):
        sigma = _std(lr[t - w:t]) or 1e-9
        out[t] = lr[t] <= -cfg.btc_block_sigma * sigma
    return out


def _btc_move_sigmas_reference(btc_c: Sequence[float], cfg: ReplayConfig) -> List[float]:
    """BTC log-return over the impulse window, in sigmas of its trailing distribution (0 before warm-up)."""
    n, k, w = len(btc_c), cfg.impulse_min, cfg.fit_min
    lr = [0.0] * n
    for t in range(k, n):
        lr[t] = math.log(btc_c[t] / btc_c[t - k])
    out = [0.0] * n
    for t in range(w + k, n):
        sigma = _std(lr[t - w:t]) or 1e-9
        out[t] = lr[t] / sigma
    return out


# --------------------------------------------------------------------------- fast (O(1) per bar) versions
# Mathematically identical to the reference versions above (tests compare them). Needed for months of data.
def _prefix(xs: Sequence[float]) -> List[float]:
    out = [0.0] * (len(xs) + 1)
    acc = 0.0
    for i, v in enumerate(xs):
        acc += v
        out[i + 1] = acc
    return out


def _solve3(A: List[List[float]], bvec: List[float]) -> List[float]:
    M = [row[:] + [bv] for row, bv in zip(A, bvec)]
    for i in range(3):
        M[i][i] += 1e-12
    for i in range(3):
        piv = max(range(i, 3), key=lambda r: abs(M[r][i]))
        M[i], M[piv] = M[piv], M[i]
        d = M[i][i] or 1e-18
        for j in range(i, 4):
            M[i][j] /= d
        for r in range(3):
            if r != i and M[r][i]:
                f = M[r][i]
                for j in range(i, 4):
                    M[r][j] -= f * M[i][j]
    return [M[0][3], M[1][3], M[2][3]]


def residual_z(alt_c: Sequence[float], btc_c: Sequence[float], eth_c: Sequence[float],
               cfg: ReplayConfig, gap: Optional[Sequence[bool]] = None) -> List[float]:
    """z-score of the cumulative idiosyncratic return over the last `impulse_min` bars.

    Coefficients are fitted on a window that ENDS before the impulse window starts (frozen parameters).
    Regressing on [1, BTC, ETH-orthogonalised-to-BTC] spans the same space as [1, BTC, ETH], so the fitted
    residuals are the same; rolling sums make each refit O(1).
    """
    n = len(alt_c)
    ra, rb, re_ = _log_ret(alt_c), _log_ret(btc_c), _log_ret(eth_c)
    k, w = cfg.impulse_min, cfg.fit_min
    z = [0.0] * n
    start = w + k
    if n <= start:
        return z
    Pb, Pe, Py = _prefix(rb), _prefix(re_), _prefix(ra)
    Pbb = _prefix([v * v for v in rb]); Pee = _prefix([v * v for v in re_]); Pbe = _prefix([a * b for a, b in zip(rb, re_)])
    Pyb = _prefix([a * b for a, b in zip(ra, rb)]); Pye = _prefix([a * b for a, b in zip(ra, re_)])
    Pyy = _prefix([v * v for v in ra])
    res = [0.0] * n
    sig = [1e-9] * n
    beta, s = None, 1e-9
    for t in range(start, n):
        if beta is None or (t - start) % cfg.refit_every == 0:
            a, b = t - k - w, t - k
            Sb, Se, Sy = Pb[b] - Pb[a], Pe[b] - Pe[a], Py[b] - Py[a]
            Sbb, See, Sbe = Pbb[b] - Pbb[a], Pee[b] - Pee[a], Pbe[b] - Pbe[a]
            Syb, Sye, Syy = Pyb[b] - Pyb[a], Pye[b] - Pye[a], Pyy[b] - Pyy[a]
            beta = _solve3([[float(w), Sb, Se], [Sb, Sbb, Sbe], [Se, Sbe, See]], [Sy, Syb, Sye])
            rss = Syy - (beta[0] * Sy + beta[1] * Syb + beta[2] * Sye)
            s = math.sqrt(max(rss, 0.0) / (w - 3)) if w > 3 else 1e-9
            s = s if s > 1e-9 else 1e-9
        res[t] = ra[t] - (beta[0] + beta[1] * rb[t] + beta[2] * re_[t])
        sig[t] = s
    csum = _prefix(res)
    gp = _prefix([1.0 if (gap is not None and gap[i]) else 0.0 for i in range(n)])
    sk = math.sqrt(k)
    for t in range(start, n):
        if gp[t + 1] - gp[t - k - w] > 0:   # any missing data in fit + impulse window: no signal
            continue
        z[t] = (csum[t + 1] - csum[t + 1 - k]) / (sig[t] * sk)
    return z


def _btc_window_sigmas(btc_c: Sequence[float], cfg: ReplayConfig) -> Tuple[List[float], List[float]]:
    n, k, w = len(btc_c), cfg.impulse_min, cfg.fit_min
    lr = [0.0] * n
    for t in range(k, n):
        lr[t] = math.log(btc_c[t] / btc_c[t - k])
    P, P2 = _prefix(lr), _prefix([v * v for v in lr])
    sig = [0.0] * n
    for t in range(w + k, n):
        m = (P[t] - P[t - w]) / w
        var = (P2[t] - P2[t - w]) / w - m * m
        sig[t] = math.sqrt(var) if var > 0 else 0.0
    return lr, sig


def btc_blocked(btc_c: Sequence[float], cfg: ReplayConfig) -> List[bool]:
    """True where BTC fell >= btc_block_sigma sigmas over the impulse window (sigma from trailing history)."""
    lr, sig = _btc_window_sigmas(btc_c, cfg)
    n, start = len(btc_c), cfg.fit_min + cfg.impulse_min
    return [t >= start and lr[t] <= -cfg.btc_block_sigma * (sig[t] or 1e-9) for t in range(n)]


def btc_move_sigmas(btc_c: Sequence[float], cfg: ReplayConfig) -> List[float]:
    """BTC log-return over the impulse window, in sigmas of its trailing distribution (0 before warm-up)."""
    lr, sig = _btc_window_sigmas(btc_c, cfg)
    n, start = len(btc_c), cfg.fit_min + cfg.impulse_min
    return [lr[t] / (sig[t] or 1e-9) if t >= start else 0.0 for t in range(n)]



# --------------------------------------------------------------------------- simulation
def _stall(b: Bars, t: int, shock_t: int, bottom: float, signals: Sequence[str]) -> Optional[str]:
    if "green" in signals and b.c[t] > b.o[t]:
        return "green"
    if "delta" in signals and b.buy[t] > b.sell[t]:
        return "delta"
    if "higher_low" in signals and t > shock_t and b.l[t] > bottom:
        return "higher_low"
    return None


def simulate_exit(b: Bars, entry_t: int, cfg: ReplayConfig, btc_sig: Optional[Sequence[float]] = None
                  ) -> Optional[Dict[str, Any]]:
    """Enter long at the ask of bar entry_t and manage the exit. Shared by the strategy and the random benchmark."""
    n = len(b.c)
    slip = cfg.slip_bps / 1e4
    cost = 2.0 * cfg.fee_bps / 1e4
    raw = b.ask[entry_t] if not math.isnan(b.ask[entry_t]) else b.c[entry_t]
    entry = float(raw) * (1.0 + slip)
    hard_stop = entry * (1.0 - cfg.init_stop_pct)
    hw, stop = entry, hard_stop
    target = entry * (1.0 + cfg.tp_pct) if cfg.exit_mode in ("fixed", "btc_adaptive") else None
    trailing = cfg.exit_mode == "trail"
    half = cfg.exit_mode == "half_trail"
    half_target = entry * (1.0 + cfg.tp_pct) if half else None
    leg1 = None                                   # half_trail: price at which the first part was sold
    exit_px, exit_t, reason = None, None, "MAX_HOLD"
    btc_up_seen = False
    for u in range(entry_t + 1, min(n, entry_t + 1 + cfg.max_hold_min)):
        if b.gap is not None and b.gap[u]:          # data stops mid-trade: close at last known price
            exit_px, exit_t, reason = b.c[u - 1] * (1.0 - slip), u - 1, "DATA_GAP"
            break
        held = u - entry_t
        active_stop = stop if held >= cfg.min_hold_min else hard_stop
        if b.l[u] <= active_stop:                 # conservative: stop first inside the bar
            exit_px, exit_t = min(active_stop, b.o[u]) * (1.0 - slip), u
            reason = "HARD_STOP" if active_stop <= hard_stop + 1e-12 else "TRAIL_STOP"
            break
        if target is not None and held >= cfg.min_hold_min and b.h[u] >= target:
            exit_px, exit_t, reason = max(target, b.o[u]) * (1.0 - slip), u, "TARGET"
            break
        if half and leg1 is None and held >= cfg.min_hold_min and b.h[u] >= half_target:
            leg1 = max(half_target, b.o[u]) * (1.0 - slip)   # sell the first part at the target
            stop = max(stop, entry)                           # the rest can no longer lose: stop at break-even
            trailing = True
        hw = max(hw, b.h[u])
        if cfg.exit_mode == "btc_adaptive" and btc_sig is not None:
            bs = btc_sig[u]                        # known at the close of bar u
            if bs >= cfg.btc_up_sigma:
                btc_up_seen = True
                target, trailing = None, True      # BTC tailwind: let it run, trail the stop
            elif bs <= -cfg.btc_down_sigma:
                stop = max(stop, b.c[u] * (1.0 - cfg.tight_trail_pct))   # BTC turning: tighten
        if trailing:
            stop = max(stop, hw * (1.0 - cfg.trail_pct))
        exit_px, exit_t = b.c[u] * (1.0 - slip), u
    if exit_px is None:
        return None
    gross = exit_px / entry - 1.0
    if leg1 is not None:                          # blend: tp_fraction sold at the target, the rest at the exit
        gross = cfg.tp_fraction * (leg1 / entry - 1.0) + (1.0 - cfg.tp_fraction) * gross
        reason = "MITAD+" + reason
    return {"entry": entry, "exit": float(exit_px), "hold_min": int(exit_t - entry_t) * cfg.bar_min,
            "gross_pct": gross * 100.0, "net_pct": (gross - cost) * 100.0, "exit_reason": reason,
            "stop_pct": cfg.init_stop_pct * 100.0,
            "btc_tailwind": bool(cfg.exit_mode == "btc_adaptive" and btc_up_seen), "_exit_t": exit_t}


def simulate_symbol(sym: str, panel: Panel, z: Sequence[float], blocked: Sequence[bool],
                    cfg: ReplayConfig, btc_sig: Optional[Sequence[float]] = None) -> List[Dict[str, Any]]:
    b = panel.bars[sym]
    n = len(z)
    trades: List[Dict[str, Any]] = []
    t = cfg.fit_min + cfg.impulse_min
    while t < n:
        if z[t] <= -cfg.z_enter and not blocked[t]:
            if cfg.min_price_move_pct > 0 and b.c[t] / b.c[max(0, t - cfg.impulse_min)] - 1.0 > -cfg.min_price_move_pct:
                t += 1
                continue
            shock_t, bottom, entry_t, why = t, b.l[t], None, None
            for u in range(t, min(n, t + cfg.max_wait_min)):
                if blocked[u]:
                    break
                sign = _stall(b, u, shock_t, bottom, cfg.signals)
                if sign is not None:
                    entry_t, why = u, sign
                    break
                bottom = min(bottom, b.l[u])
            if entry_t is None:
                t += cfg.cooldown_min
                continue
            tr = simulate_exit(b, entry_t, cfg, btc_sig)
            if tr is None:
                t = entry_t + 1
                continue
            exit_t = tr.pop("_exit_t")
            trades.append({"symbol": sym, "minute": int(panel.minutes[entry_t]), "signal": why,
                           "z": float(z[shock_t]), **tr})
            t = exit_t + cfg.cooldown_min
        else:
            t += 1
    return trades


def summarize(trades: List[Dict[str, Any]], span_days: float) -> Dict[str, Any]:
    n = len(trades)
    if n == 0:
        return {"n_trades": 0, "trades_per_day": 0.0, "note": "no entries"}
    net = [t["net_pct"] for t in trades]
    wins = [x for x in net if x > 0]
    losses = [x for x in net if x <= 0]
    cum, peak, dd = 0.0, 0.0, 0.0
    for t in sorted(trades, key=lambda t: t["minute"]):
        cum += t["net_pct"]
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    mean = sum(net) / n
    sd = _std(net, ddof=1) if n > 1 else 0.0
    srt = sorted(net)
    median = srt[n // 2] if n % 2 else 0.5 * (srt[n // 2 - 1] + srt[n // 2])
    by_sym: Dict[str, List[float]] = {}
    for t in trades:
        by_sym.setdefault(t["symbol"], []).append(t["net_pct"])
    out = {
        "n_trades": n, "trades_per_day": n / max(span_days, 1e-9), "win_rate": len(wins) / n,
        "mean_net_pct": mean, "median_net_pct": median, "sum_net_pct": sum(net),
        "mean_gross_pct": sum(t.get("gross_pct", t["net_pct"]) for t in trades) / n,
        "avg_win_pct": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss_pct": sum(losses) / len(losses) if losses else 0.0,
        "profit_factor": (sum(wins) / -sum(losses)) if sum(losses) < 0 else float("inf"),
        "max_drawdown_pct_points": dd,
        "naive_t_stat": mean / (sd / math.sqrt(n)) if n > 1 and sd > 0 else float("nan"),
        "exit_reasons": {r: sum(1 for t in trades if t["exit_reason"] == r) for r in {t["exit_reason"] for t in trades}},
        "signals": {x: sum(1 for t in trades if t["signal"] == x) for x in {t["signal"] for t in trades}},
        "top_symbols": sorted(((s, len(v), sum(v)) for s, v in by_sym.items()), key=lambda x: -x[1])[:8],
    }
    out["share_hold_under_2min"] = sum(1 for t in trades if t.get("hold_min", 99) < 2) / n
    if n < 30:
        out["warning"] = "Fewer than 30 trades: too few to conclude anything."
    return out


def _run_cfg(panel: Panel, cfg: ReplayConfig, alts: Sequence[str], zc: Dict, btc_sig: Sequence[float]
             ) -> List[Dict[str, Any]]:
    blocked = btc_blocked(panel.bars[BTC].c, cfg)
    trades: List[Dict[str, Any]] = []
    for s in alts:
        key = (s, cfg.impulse_min, cfg.fit_min, cfg.refit_every)
        if key not in zc:
            zc[key] = residual_z(panel.bars[s].c, panel.bars[BTC].c, panel.bars[ETH].c, cfg, panel.bars[s].gap)
        trades += simulate_symbol(s, panel, zc[key], blocked, cfg, btc_sig)
    return trades


def random_baseline(panel: Panel, cfg: ReplayConfig, alts: Sequence[str], n_entries: int,
                    strategy_mean_net_pct: Optional[float], runs: int = 200, seed: int = 12345,
                    btc_sig: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    """Same exit, same number of entries, but entering at RANDOM moments (only where data is valid).

    If the strategy is not clearly better than this, its entry signal adds nothing.
    """
    import random
    if n_entries <= 0:
        return {"status": "SIN_DATOS", "reason": "La estrategia no tuvo operaciones."}
    start = cfg.fit_min + cfg.impulse_min
    usable = [s_ for s_ in alts if len(panel.bars[s_].c) - 2 > start]
    if not usable:
        return {"status": "SIN_DATOS", "reason": "No hay momentos válidos para comparar."}
    rnd = random.Random(seed)

    def draw():
        for _ in range(1000):                       # rejection sampling: skip moments without valid data
            sym = usable[rnd.randrange(len(usable))]
            b = panel.bars[sym]
            t = rnd.randrange(start, len(b.c) - 2)
            g = b.gap
            if g is None or (not g[t] and not g[t + 1]):
                return sym, t
        return None

    # Cap the work on long histories: 500 random entries per run is plenty to know the random mean; with fewer
    # entries than the strategy, the random range is wider, so the test only gets harder (conservative).
    n_draw = min(n_entries, 500)
    means = []
    for _ in range(runs):
        vals = []
        for _ in range(n_draw):
            pick = draw()
            if pick is None:
                continue
            sym, t = pick
            tr = simulate_exit(panel.bars[sym], t, cfg, btc_sig)
            if tr is not None:
                vals.append(tr["net_pct"])
        if vals:
            means.append(sum(vals) / len(vals))
    means.sort()
    if not means:
        return {"status": "SIN_DATOS", "reason": "No se pudo simular."}
    q = lambda f: means[min(len(means) - 1, max(0, int(f * (len(means) - 1))))]
    out = {"status": "OK", "runs": len(means), "n_entries": n_entries, "n_entries_sampled": n_draw,
           "random_median_net_pct": q(0.5), "random_p5_net_pct": q(0.05), "random_p95_net_pct": q(0.95),
           "strategy_mean_net_pct": strategy_mean_net_pct}
    if strategy_mean_net_pct is not None:
        out["share_random_worse"] = sum(1 for m in means if m < strategy_mean_net_pct) / len(means)
        sh = out["share_random_worse"]
        out["verdict"] = ("MEJOR_QUE_AZAR" if sh >= 0.95 else "PEOR_QUE_AZAR" if sh <= 0.05 else "IGUAL_QUE_AZAR")
    return out


def _run_cfg(panel: Panel, cfg: ReplayConfig, alts: Sequence[str], zc: Dict, btc_sig: Sequence[float]
             ) -> List[Dict[str, Any]]:
    blocked = btc_blocked(panel.bars[BTC].c, cfg)
    trades: List[Dict[str, Any]] = []
    for s in alts:
        key = (s, cfg.bar_min, cfg.impulse_min, cfg.fit_min, cfg.refit_every)
        if key not in zc:
            zc[key] = residual_z(panel.bars[s].c, panel.bars[BTC].c, panel.bars[ETH].c, cfg, panel.bars[s].gap)
        trades += simulate_symbol(s, panel, zc[key], blocked, cfg, btc_sig)
    return trades


def run_replay(panel: Panel, cfgs: Sequence[ReplayConfig], alts: Optional[Sequence[str]] = None,
               exit_base: Optional[str] = "B_marcelo", risk_per_trade: float = 0.0075,
               baseline_for: Sequence[str] = BASELINE_FOR, baseline_runs: int = 200) -> Dict[str, Any]:
    alts = [s for s in (alts or list(panel.bars)) if s not in (BTC, ETH) and s in panel.bars]
    cov = data_coverage(panel)
    span_days = cov["usable_minutes"] / 1440.0
    out: Dict[str, Any] = {"span_days": span_days, "n_alts": len(alts), "variants": {}, "exit_comparison": {},
                           "baseline": {}, "coverage": cov,
                           "needed_continuous_hours": (cfgs[0].fit_min + cfgs[0].impulse_min) * cfgs[0].bar_min / 60.0 if cfgs else 4.1,
                           "risk_per_trade_pct": risk_per_trade * 100.0,
                           "caveat": "Exploratory, in-sample, several variants compared on the same data."}
    zc: Dict[Tuple, List[float]] = {}
    panels: Dict[int, Panel] = {}
    sigs: Dict[int, List[float]] = {}

    def ctx(cfg: ReplayConfig):
        if cfg.bar_min not in panels:
            panels[cfg.bar_min] = resample_panel(panel, cfg.bar_min)
            sigs[cfg.bar_min] = btc_move_sigmas(panels[cfg.bar_min].bars[BTC].c, cfg)
        return panels[cfg.bar_min], sigs[cfg.bar_min]

    by_name = {c.name: c for c in cfgs}
    for cfg in cfgs:
        pn, sg = ctx(cfg)
        trades = _run_cfg(pn, cfg, alts, zc, sg)
        summ = summarize(trades, span_days)
        out["variants"][cfg.name] = {"config": {**cfg.__dict__, "signals": list(cfg.signals)},
                                     "summary": summ,
                                     "prop_check": prop_checks(trades, pn, risk_per_trade), "trades": trades}
        if cfg.name in baseline_for:
            out["baseline"][cfg.name] = random_baseline(pn, cfg, alts, summ.get("n_trades", 0),
                                                        summ.get("mean_net_pct"), runs=baseline_runs, btc_sig=sg)
    if exit_base and exit_base in by_name:
        for cfg in exit_variants(by_name[exit_base]):
            pn, sg = ctx(cfg)
            trades = _run_cfg(pn, cfg, alts, zc, sg)
            out["exit_comparison"][cfg.exit_mode] = {
                "label": EXIT_LABELS[cfg.exit_mode], "config": {**cfg.__dict__, "signals": list(cfg.signals)},
                "summary": summarize(trades, span_days),
                "prop_check": prop_checks(trades, pn, risk_per_trade), "trades": trades}
    return out


# --------------------------------------------------------------------------- prop-firm exam check
PROP_RULES: Dict[str, Dict[str, Any]] = {
    # Sources (verify before paying, rules change): hyrotrader.com/blog/hyrotrader-vs-breakout,
    # mubite.com/en/challengeRules. Floating (open) losses are NOT simulated: closed trades only.
    "HyroTrader_1F": {"label": "HyroTrader 1 fase", "daily": 0.04, "max": 0.06, "targets": [0.10],
                      "consistency": 0.40, "min_days": 5},
    "HyroTrader_2F": {"label": "HyroTrader 2 fases", "daily": 0.05, "max": 0.10, "targets": [0.10, 0.05],
                      "consistency": 0.40, "min_days": 5},
    "Mubite_2F": {"label": "Mubite 2 fases", "daily": 0.05, "max": 0.08, "targets": [0.10, 0.05],
                  "consistency": None, "min_days": 13, "max_risk_per_trade": 0.03},
}


def _account_returns(trades: List[Dict[str, Any]], risk_per_trade: float) -> List[Tuple[int, float]]:
    """(exit_minute, account return) per trade. Size so that hitting the initial stop loses risk_per_trade."""
    out = []
    for t in trades:
        stop = max(t.get("stop_pct", 0.6), 1e-6) / 100.0
        lev = risk_per_trade / stop
        out.append((t["minute"] + t["hold_min"], lev * t["net_pct"] / 100.0))
    return sorted(out)


def prop_check(trades: List[Dict[str, Any]], rules: Dict[str, Any], risk_per_trade: float) -> Dict[str, Any]:
    if rules.get("max_risk_per_trade") is not None and risk_per_trade > rules["max_risk_per_trade"]:
        return {"status": "FAIL_RULES", "reason": "Riesgo por operación mayor al permitido."}
    rets = _account_returns(trades, risk_per_trade)
    if not rets:
        return {"status": "SIN_DATOS", "reason": "No hubo operaciones."}
    phases = list(rules["targets"])
    start_bal, bal = 1.0, 1.0
    phase, days_in_phase, day, day_start = 0, set(), None, 1.0
    day_pnl: Dict[int, float] = {}
    worst_day = 0.0
    for minute, r in rets:
        d = minute // 1440
        if d != day:
            day, day_start = d, bal
        bal *= (1.0 + r)
        days_in_phase.add(d)
        day_pnl[d] = bal - day_start
        dd_day = (bal - day_start) / start_bal
        worst_day = min(worst_day, dd_day)
        if dd_day <= -rules["daily"]:
            return {"status": "FAIL_DAILY", "phase": phase + 1, "reason": f"Superó la pérdida diaria de {rules['daily']*100:.0f}%.",
                    "worst_day_pct": worst_day * 100}
        if (bal - start_bal) / start_bal <= -rules["max"]:
            return {"status": "FAIL_MAX", "phase": phase + 1, "reason": f"Superó la pérdida total de {rules['max']*100:.0f}%.",
                    "worst_day_pct": worst_day * 100}
        target = phases[phase]
        if (bal - start_bal) / start_bal >= target:
            cons = rules.get("consistency")
            best = max(day_pnl.values()) / start_bal if day_pnl else 0.0
            if cons is not None and best > cons * target:
                continue  # target reached but one day is too large: must keep trading (not a fail)
            if len(days_in_phase) < rules["min_days"]:
                continue  # needs more trading days
            phase += 1
            if phase == len(phases):
                return {"status": "PASA", "reason": "Llegó al objetivo sin romper límites.",
                        "worst_day_pct": worst_day * 100}
            start_bal, bal, days_in_phase, day_pnl, day = 1.0, 1.0, set(), {}, None
    target = phases[phase]
    return {"status": "AUN_NO", "phase": phase + 1,
            "progress_pct": (bal - start_bal) / start_bal * 100, "target_pct": target * 100,
            "worst_day_pct": worst_day * 100,
            "reason": "No rompió límites, pero todavía no llegó al objetivo con estos datos."}


def prop_checks(trades: List[Dict[str, Any]], panel: Panel, risk_per_trade: float) -> Dict[str, Any]:
    return {k: {"label": r["label"], **prop_check(trades, r, risk_per_trade)} for k, r in PROP_RULES.items()}


def shock_counts(panel: Panel, z_levels: Sequence[float] = (2.0, 2.5, 3.0),
                 btc_sigmas: Sequence[float] = (1.0, 2.0, 3.0, 99.0), cfg: ReplayConfig = ReplayConfig()
                 ) -> Dict[str, Any]:
    """How many impulses per day would be detected at each threshold / BTC filter (before stall + exits)."""
    alts = [s for s in panel.bars if s not in (BTC, ETH)]
    days = max(data_coverage(panel)["usable_minutes"] / 1440.0, 1e-9) if BTC in panel.bars else 1e-9
    zs = {s: residual_z(panel.bars[s].c, panel.bars[BTC].c, panel.bars[ETH].c, cfg, panel.bars[s].gap) for s in alts}
    table: Dict[str, Dict[str, float]] = {}
    for bs in btc_sigmas:
        blocked = btc_blocked(panel.bars[BTC].c, replace(cfg, btc_block_sigma=bs))
        for zl in z_levels:
            cnt = 0
            for s in alts:
                z, t = zs[s], cfg.fit_min + cfg.impulse_min
                while t < len(z):
                    if z[t] <= -zl and not blocked[t]:
                        cnt += 1
                        t += cfg.cooldown_min
                    else:
                        t += 1
            table.setdefault(f"btc_block_{bs:g}_sigma", {})[f"z_{zl:g}"] = cnt / days
    return {"span_days": days, "n_alts": len(alts), "impulses_per_day": table}
