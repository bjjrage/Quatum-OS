"""Reproducible, research-only Binance tests for a HyroTrader two-step account.

No broker, strategy registry or capital allocation is modified. Positions are
fixed quantities between explicit close/reopen events. Missing prices fail
closed. Historical results are exploratory: this dataset was researched before.
"""
from __future__ import annotations

import hashlib
import json
import math
from array import array
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist, median
from typing import Callable

DAY_MS = 86_400_000
HOUR_MS = 3_600_000
MAJORS = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT",
          "DOGEUSDT", "LINKUSDT", "AVAXUSDT", "LTCUSDT"}
NAN = float("nan")


def iso(day: int) -> str:
    return datetime.fromtimestamp(day * 86400, timezone.utc).date().isoformat()


@dataclass(frozen=True)
class Candidate:
    family: str
    lookback: int
    rebalance: int
    universe: str = "liquid20"
    fraction: float = 0.2

    @property
    def id(self) -> str:
        return f"{self.family}_{self.lookback}d_r{self.rebalance}_{self.universe}"


@dataclass
class Panel:
    day0: int
    n: int
    daily: dict[str, dict[str, list]]
    hourly: dict[str, dict[str, array]]
    hour0: int
    funding: dict[str, dict[int, list[tuple[int, float, float]]]]
    audit: dict
    eligibility_cache: dict = field(default_factory=dict)


def load_panel(root: Path, cutoff_ms: int) -> Panel:
    import duckdb
    con = duckdb.connect(config={"threads": 2})
    hourly: dict = {}
    daily: dict = {}
    funding: dict = {}
    audit: dict = {"cutoff_exclusive_utc": datetime.fromtimestamp(cutoff_ms / 1000, timezone.utc).isoformat(),
                   "symbols": [], "ohlc_invalid": 0, "duplicate_hours": 0}
    files = sorted((root / "klines_1h").glob("symbol=*/*.parquet"))
    btc_file = next(p for p in files if p.parent.name == "symbol=BTCUSDT")
    lo, hi = con.execute("SELECT min(open_time_ms),max(open_time_ms) FROM read_parquet(?) "
                         "WHERE open_time_ms < ?", [btc_file.as_posix(), cutoff_ms]).fetchone()
    hour0, hour1 = lo // HOUR_MS, hi // HOUR_MS
    day0, day1 = hour0 // 24 + 1, hour1 // 24
    n = day1 - day0 + 1
    fingerprint = hashlib.sha256()
    for p in files:
        sym = p.parent.name.split("=", 1)[1]
        fingerprint.update(p.name.encode())
        fingerprint.update(hashlib.sha256(p.read_bytes()).digest())
        rows = con.execute("SELECT open_time_ms,open,high,low,close,volume,quote_volume,taker_buy_volume "
                           "FROM read_parquet(?) WHERE open_time_ms < ? ORDER BY 1",
                           [p.as_posix(), cutoff_ms]).fetchall()
        if not rows:
            continue
        h = {k: array("d", [NAN]) * (hour1 - hour0 + 1) for k in ("o", "h", "l", "c")}
        ds = {k: [NAN] * n for k in ("c", "qv", "flow", "vol", "taker", "fund")}
        sums: dict = {}
        seen: set = set()
        for ts, op, high, low, close, vol, qv, tb in rows:
            if ts in seen:
                audit["duplicate_hours"] += 1
                raise ValueError(f"Duplicate hourly data: {sym} {ts}")
            seen.add(ts)
            if not (0 < low <= min(op, close) <= max(op, close) <= high
                    and vol >= 0 and 0 <= tb <= vol * 1.00001 and ts % HOUR_MS == 0):
                audit["ohlc_invalid"] += 1
                raise ValueError(f"Invalid hourly data: {sym} {ts}")
            ix = ts // HOUR_MS - hour0
            if 0 <= ix < len(h["o"]):
                for k, val in zip(("o", "h", "l", "c"), (op, high, low, close)):
                    h[k][ix] = val
            d = ts // DAY_MS - day0
            if 0 <= d < n:
                a = sums.setdefault(d, [0, 0.0, 0.0, 0.0, close])
                a[0] += 1
                a[1] += qv
                a[2] += vol
                a[3] += tb
                a[4] = close
        for d, (count, qv, vol, tb, close) in sums.items():
            if count == 24 and vol > 0:
                ds["c"][d], ds["qv"][d] = close, qv
                ds["vol"][d], ds["taker"][d] = vol, tb
                ds["flow"][d] = 2 * tb / vol - 1
        fp = root / "funding" / f"symbol={sym}" / "funding.parquet"
        if not fp.exists():
            raise ValueError(f"Funding file missing: {sym}")
        fingerprint.update(hashlib.sha256(fp.read_bytes()).digest())
        fr = con.execute("SELECT funding_time_ms,funding_rate,mark_price FROM read_parquet(?) "
                         "WHERE funding_time_ms < ? ORDER BY 1", [fp.as_posix(), cutoff_ms]).fetchall()
        fd: dict = {}
        fsums: dict = {}
        for ts, rate, mark in fr:
            if not math.isfinite(rate):
                raise ValueError(f"Nonfinite funding rate: {sym} {ts}")
            fd.setdefault(ts // HOUR_MS, []).append((ts, rate, mark))
            d = ts // DAY_MS - day0
            fsums[d] = fsums.get(d, 0.0) + rate
        for d, rate in fsums.items():
            if 0 <= d < n:
                ds["fund"][d] = rate
        hourly[sym], daily[sym], funding[sym] = h, ds, fd
        audit["symbols"].append({"symbol": sym, "hours": len(rows), "first_utc":
                                  datetime.fromtimestamp(rows[0][0] / 1000, timezone.utc).isoformat(),
                                  "last_utc": datetime.fromtimestamp(rows[-1][0] / 1000, timezone.utc).isoformat(),
                                  "internal_missing_hours": (rows[-1][0] - rows[0][0]) // HOUR_MS + 1 - len(rows),
                                  "funding_events": len(fr), "funding_marks_approximated":
                                  sum(not math.isfinite(mark) or mark <= 0 for _, _, mark in fr),
                                  "funding_days_without_event": sum(math.isfinite(ds["c"][d]) and
                                      not math.isfinite(ds["fund"][d]) for d in range(n)),
                                  "bytes_hourly": p.stat().st_size})
    audit["sha256_hourly_and_funding_files"] = fingerprint.hexdigest()
    con.close()
    return Panel(day0, n, daily, hourly, hour0, funding, audit)


def mean_window(x: list, d: int, length: int) -> float:
    if d < length - 1:
        return NAN
    v = x[d - length + 1:d + 1]
    return sum(v) / length if all(math.isfinite(a) for a in v) else NAN


def ret(x: list, d: int, length: int) -> float:
    return x[d] / x[d - length] - 1 if d >= length and x[d - length] > 0 else NAN


def volatility(x: list, d: int, length: int = 28) -> float:
    if d < length:
        return NAN
    v = [ret(x, j, 1) for j in range(d - length + 1, d + 1)]
    if not all(math.isfinite(a) for a in v):
        return NAN
    m = sum(v) / length
    return math.sqrt(sum((a - m) ** 2 for a in v) / (length - 1))


def eligible(p: Panel, d: int, universe: str) -> list[str]:
    key = (d, universe)
    if key in p.eligibility_cache:
        return p.eligibility_cache[key]
    scores = []
    for s, ds in p.daily.items():
        if d < 90 or not all(math.isfinite(a) for a in ds["c"][d - 90:d + 1]):
            continue
        qv = mean_window(ds["qv"], d, 28)
        if qv >= 5_000_000 and (universe != "majors" or s in MAJORS):
            scores.append((qv, s))
    scores.sort(reverse=True)
    result = [s for _, s in scores[:20 if universe == "liquid20" else len(scores)]]
    p.eligibility_cache[key] = result
    return result


def ranked(scores: list[tuple[float, str]], fraction: float, long_high: bool = True) -> dict[str, float]:
    scores = sorted((v, s) for v, s in scores if math.isfinite(v))
    if len(scores) < 6:
        return {}
    k = max(1, int(len(scores) * fraction))
    low, high = scores[:k], scores[-k:]
    longs, shorts = (high, low) if long_high else (low, high)
    return {**{s: 0.5 / k for _, s in longs}, **{s: -0.5 / k for _, s in shorts}}


def weights(p: Panel, d: int, cfg: Candidate) -> dict[str, float]:
    syms = eligible(p, d, cfg.universe)
    scores = []
    L = cfg.lookback
    if cfg.family in ("trend", "breakout"):
        w = {}
        for s in syms:
            x = p.daily[s]["c"]
            signal = ret(x, d, L)
            if cfg.family == "breakout":
                prev = x[d - L:d]
                signal = 1 if x[d] > max(prev) else -1 if x[d] < min(prev) else 0
            vol = volatility(x, d)
            if signal and math.isfinite(signal) and vol > 0:
                w[s] = math.copysign(1 / vol, signal)
        total = sum(abs(v) for v in w.values())
        return {s: v / total for s, v in w.items()} if total else {}
    for s in syms:
        ds = p.daily[s]
        if cfg.family in ("flow", "flow_residual", "flow_acceleration"):
            # Volume-weighted imbalance, rather than an unweighted average of ratios.
            tb = sum(ds["taker"][d - L + 1:d + 1])
            volume = sum(ds["vol"][d - L + 1:d + 1])
            score = 2 * tb / volume - 1 if volume > 0 else NAN
            if cfg.family == "flow_acceleration":
                score -= mean_window(ds["flow"], d, 28)
        elif cfg.family == "momentum":
            score = ret(ds["c"], d - 1, L)
        elif cfg.family in ("reversal", "quiet_reversal"):
            score = -ret(ds["c"], d, L)
            if cfg.family == "quiet_reversal":
                recent = mean_window(ds["qv"], d, L)
                trend = mean_window(ds["qv"], d, 28)
                if not (recent < trend):
                    continue
        elif cfg.family == "funding":
            score = -mean_window(ds["fund"], d, L)
        else:
            raise ValueError(cfg.family)
        scores.append((score, s))
    if cfg.family == "flow_residual":
        # Cross-sectional OLS of flow on contemporaneous past return; use its residual.
        pairs = [(ret(p.daily[s]["c"], d, L), v, s) for v, s in scores if math.isfinite(v)]
        pairs = [v for v in pairs if math.isfinite(v[0])]
        if len(pairs) >= 6:
            mx, my = sum(x for x, _, _ in pairs) / len(pairs), sum(y for _, y, _ in pairs) / len(pairs)
            den = sum((x - mx) ** 2 for x, _, _ in pairs)
            beta = sum((x - mx) * (y - my) for x, y, _ in pairs) / den if den else 0
            scores = [(y - my - beta * (x - mx), s) for x, y, s in pairs]
    return ranked(scores, cfg.fraction)


def candidates() -> list[Candidate]:
    out = []
    for universe in ("liquid20", "majors"):
        for fam, horizons, rebs in (
            ("flow", (7, 14), (3, 7)), ("flow_residual", (7, 14), (3, 7)),
            ("flow_acceleration", (7,), (3, 7)), ("momentum", (14, 28), (7,)),
            ("trend", (28, 56), (1,)), ("breakout", (20, 55), (1,)),
            ("reversal", (1, 3), (1,)), ("quiet_reversal", (1, 3), (1,)),
            ("funding", (7,), (7,))):
            out.extend(Candidate(fam, L, reb, universe) for L in horizons for reb in rebs)
    return out


def price(p: Panel, s: str, hour: int, column: str = "o") -> float:
    i = hour - p.hour0
    a = p.hourly[s][column]
    if not 0 <= i < len(a) or not a[i] > 0:
        raise ValueError(f"Missing {column} price: {s}, hour {hour}")
    return a[i]


def funding_cost(p: Panel, s: str, q: float, start_hour: int, end_hour: int) -> float:
    total = 0.0
    for h in range(start_hour, end_hour):
        for ts, rate, mark in p.funding[s].get(h, []):
            if start_hour * HOUR_MS <= ts < end_hour * HOUR_MS:
                total += q * (mark if math.isfinite(mark) and mark > 0 else price(p, s, h)) * rate
    return total


@dataclass
class DayResult:
    signal_day: int
    pnl: float
    fee_notional: float
    funding: float
    gross: float
    close_pnl: float = 0.0
    closed: list = field(default_factory=list)
    weights: dict = field(default_factory=dict)
    block_start: bool = False


def backtest(p: Panel, cfg: Candidate, side_cost_bps: float = 7.5, start: int = 150,
             stop: int | None = None) -> list[DayResult]:
    """Fixed initial-capital sizing; full close/reopen every rebalance, no free rebalancing.

    Signal uses a full UTC day's observations. Execution is the next day's
    01:00 open (one-hour delay); PnL intervals are 01:00 to next 01:00.
    Fee/slippage is charged on both actual notionals, funding on marked notional.
    """
    stop = min(stop if stop is not None else p.n - 2, p.n - 2)
    lots: dict = {}
    out = []
    cost = side_cost_bps / 10000
    for d in range(start, stop):
        h = (p.day0 + d + 1) * 24 + 1
        block_start = (d - start) % cfg.rebalance == 0
        new = weights(p, d, cfg) if block_start else {}
        fees = close_pnl = 0.0
        closed = []
        if block_start:
            for s, (q, entry, accumulated_fund, entry_fee) in lots.items():
                px = price(p, s, h)
                exit_fee = abs(q * px) * cost
                realized = q * (px - entry) - accumulated_fund - entry_fee - exit_fee
                closed.append({"symbol": s, "entry_notional": abs(q * entry),
                               "gross_move": abs(px / entry - 1), "net": realized})
                close_pnl += q * (px - entry) - exit_fee
                fees += abs(q * px)
            lots = {}
            for s, w in new.items():
                px = price(p, s, h)
                q = w / px
                lots[s] = (q, px, 0.0, abs(w) * cost)
                fees += abs(w)
        gross = fund = 0.0
        for s, (q, entry, accumulated_fund, entry_fee) in list(lots.items()):
            gross += q * (price(p, s, h + 24) - price(p, s, h))
            fc = funding_cost(p, s, q, h, h + 24)
            fund += fc
            lots[s] = (q, entry, accumulated_fund + fc, entry_fee)
        # Opening/closing costs and funding are realized on the actual day of payment.
        close_pnl -= sum(abs(w) * cost for w in new.values()) + fund
        out.append(DayResult(d, gross - fund - fees * cost, fees, fund, gross,
                             close_pnl, closed, new, block_start))
    return out


def statistics(values: list[float], turnover: list[float] | None = None) -> dict:
    n = len(values)
    if n < 10:
        return {"days": n}
    mu = sum(values) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in values) / (n - 1))
    # Newey-West HAC standard error with seven daily lags.
    lr_var = sum((x - mu) ** 2 for x in values) / n
    for lag in range(1, min(7, n - 1) + 1):
        cov = sum((values[t] - mu) * (values[t - lag] - mu) for t in range(lag, n)) / n
        lr_var += 2 * (1 - lag / 8) * cov
    se = math.sqrt(max(lr_var, 1e-20) / n)
    t = mu / se
    eq = peak = 0.0
    dd = 0.0
    for x in values:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return {"days": n, "net_return_pct_initial": sum(values) * 100,
            "annual_mean_pct_initial": mu * 365 * 100,
            "sharpe": mu / sd * math.sqrt(365) if sd else 0,
            "hac_t_7lag": t, "one_sided_normal_p": 1 - NormalDist().cdf(t),
            "mean_ci95_pct_day": [(mu - 1.96 * se) * 100, (mu + 1.96 * se) * 100],
            "max_drawdown_pct_initial": dd * 100, "worst_interval_pct": min(values) * 100,
            "annual_vol_pct_initial": sd * math.sqrt(365) * 100,
            "turnover_daily": sum(turnover) / n if turnover else 0}


def segments(p: Panel) -> dict[str, tuple[int, int]]:
    toix = lambda d: int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp() // 86400) - p.day0
    return {"train": (150, toix("2024-01-01")),
            "validation": (toix("2024-01-01"), toix("2025-01-01")),
            "test_reused": (toix("2025-01-01"), p.n - 2)}


def evaluate(p: Panel, cfg: Candidate, prior_trials: int = 210) -> tuple[dict, list[DayResult]]:
    rows = backtest(p, cfg)
    parts = segments(p)
    result = {"id": cfg.id, "config": asdict(cfg)}
    for name, (lo, hi) in parts.items():
        # Purge the full maximum holding span before each boundary.
        end = hi - cfg.rebalance - 2 if name != "test_reused" else hi
        subset = [r for r in rows if lo <= r.signal_day < end]
        result[name] = statistics([r.pnl for r in subset], [r.fee_notional for r in subset])
    count = prior_trials + len(candidates())
    result["train_bonferroni_p"] = min(1, result["train"].get("one_sided_normal_p", 1) * count)
    result["train_validation_gate"] = bool(result["train_bonferroni_p"] < .05
        and result["validation"].get("sharpe", 0) > .5
        and result["validation"].get("net_return_pct_initial", 0) > 0)
    # Ranking is deliberately independent of the last segment.
    result["selection_score"] = min(result["train"].get("sharpe", -99),
                                     result["validation"].get("sharpe", -99))
    result["status"] = "EXPLORATORY_REQUIRES_NEW_DATA_AND_PAPER"
    return result, rows


def hourly_trace(p: Panel, cfg: Candidate, start: int, stop: int, side_cost_bps: float = 7.5) -> list[dict]:
    """Equity and adverse OHLC bounds; simultaneous leg extremes are conservative.

    Trace is independently restarted with no existing positions. UTC midnight,
    realized trade days, funding and actual close fees are explicitly represented.
    """
    lot: dict = {}
    balance = 1.0
    out = []
    cost = side_cost_bps / 10000
    for d in range(start, min(stop, p.n - 2)):
        first = (p.day0 + d + 1) * 24 + 1
        rebal = d == start or (d - 150) % cfg.rebalance == 0
        for h in range(first, first + 24):
            realized, qualified, max_loss = 0.0, False, 0.0
            closes = []
            entry = h == first and rebal
            if entry:
                for s, (q, px, paid, entryfee) in lot.items():
                    exitpx = price(p, s, h)
                    exitfee = abs(q * exitpx) * cost
                    balance += q * (exitpx - px) - exitfee
                    realized += q * (exitpx - px) - exitfee
                    trade_net = q * (exitpx - px) - paid - entryfee - exitfee
                    max_loss = max(max_loss, -trade_net)
                    qualified |= abs(q * px) >= .05 and abs(exitpx / px - 1) >= .01
                    closes.append({"entry_notional": abs(q * px), "move": abs(exitpx / px - 1),
                                   "net": trade_net})
                lot = {}
                for s, w in weights(p, d, cfg).items():
                    px = price(p, s, h)
                    fee = abs(w) * cost
                    balance -= fee
                    realized -= fee
                    lot[s] = (w / px, px, 0.0, fee)
            open_equity = balance + sum(q * (price(p, s, h) - px) for s, (q, px, _, _) in lot.items())
            for s, (q, px, paid, entryfee) in list(lot.items()):
                fc = funding_cost(p, s, q, h, h + 1)
                balance -= fc
                realized -= fc
                lot[s] = (q, px, paid + fc, entryfee)
            eq = balance
            worst = best = balance
            gross = 0.0
            for s, (q, px, _, _) in lot.items():
                eq += q * (price(p, s, h, "c") - px)
                low, high = price(p, s, h, "l"), price(p, s, h, "h")
                worst += q * ((low if q > 0 else high) - px)
                best += q * ((high if q > 0 else low) - px)
                gross += abs(q) * high
            # No assumed fills at an ideal stop. Bounds include paid fees/funding.
            out.append({"hour": h, "equity": eq, "open_equity": open_equity, "worst": worst,
                        "best": best, "realized": realized, "qualified_close": qualified,
                        "max_realized_loss": max_loss, "gross_upper": gross,
                        "closes": closes,
                        "block_start": entry})
    return out


def phase(trace: list[dict], target: float = .10, daily_limit: float = .05,
          total_limit: float = .10, scale: float = .5, trailing_daily: bool = False,
          min_valid_days: int = 5) -> dict:
    """Conditional historical rule replay, not a probability of passing Hyro review."""
    if not trace:
        return {"status": "NO_DATA"}
    last_day = None
    day_start = 1.0
    day_peak = 1.0
    credited = day_realized = 0.0
    valid_days = set()
    first_day = trace[0]["hour"] // 24
    max_dd = 0.0
    peak = 1.0
    for r in trace:
        day = r["hour"] // 24
        if day != last_day:
            if last_day is not None:
                credited += min(day_realized, .4 * target)
            day_realized = 0.0
            day_start = 1 + scale * (r["open_equity"] - 1)
            # On opening hour, day-start includes no entry cost yet.
            if last_day is None:
                day_start = 1.0
            day_peak = day_start
            last_day = day
        worst, eq, best = (1 + scale * (r[k] - 1) for k in ("worst", "equity", "best"))
        floor = (day_peak if trailing_daily else day_start) - daily_limit
        peak = max(peak, best)
        max_dd = max(max_dd, peak - worst)
        if worst <= 1 - total_limit or worst <= floor:
            return {"status": "BREACH_BOUND", "days": day - first_day + 1,
                    "reason": "TOTAL" if worst <= 1 - total_limit else "DAILY",
                    "max_dd_pct_initial": max_dd * 100}
        if scale * r["max_realized_loss"] > .03:
            return {"status": "BREACH_TRADE", "days": day - first_day + 1}
        if scale * r["gross_upper"] > 2:
            return {"status": "BREACH_NOTIONAL_BOUND", "days": day - first_day + 1}
        if any(scale * t["entry_notional"] >= .05 and t["move"] >= .01 for t in r.get("closes", [])):
            valid_days.add(day)
        day_realized += scale * r["realized"]
        day_peak = max(day_peak, best)
        progress = credited + min(day_realized, .4 * target)
        if progress >= target and len(valid_days) >= min_valid_days:
            return {"status": "NUMERICAL_PASS", "days": day - first_day + 1,
                    "valid_days": len(valid_days), "credited_pct": progress * 100,
                    "max_dd_pct_initial": max_dd * 100}
    return {"status": "UNFINISHED", "days": trace[-1]["hour"] // 24 - first_day + 1,
            "valid_days": len(valid_days), "credited_pct":
            (credited + min(day_realized, .4 * target)) * 100}


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
