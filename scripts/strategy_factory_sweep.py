#!/usr/bin/env python3
"""Strategy Factory Sweep 01.

A fixed, pre-declared hypothesis sweep over public Binance USD-M 1h/funding data
plus lagged public macro series from FRED. This is DISCOVERY only: no candidate
is promoted by this script. All signals use data available at or before t and
outcomes start after t.

Outputs:
  strategy_results.json
  trades.csv
  data_manifest.json
  summary.md

Guardrails:
- fixed hypotheses/thresholds before seeing results
- 70/30 chronological train/holdout split
- 12 bps round-trip cost on every trade/basket
- minimum holdout sample
- Bonferroni correction across reported hypotheses
- no strategy registry/lifecycle mutation
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import random
import statistics
import time
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

START_MONTH = "2025-04"
END_MONTH = "2026-09"
COST_RT = 0.0012  # 4 bps fee + 2 bps slippage per side
MIN_HOLDOUT = 30

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "AVAXUSDT", "NEARUSDT",
    "SUIUSDT", "ARBUSDT", "OPUSDT", "RENDERUSDT", "FETUSDT", "WIFUSDT",
    "1000PEPEUSDT", "SEIUSDT", "JTOUSDT", "WLDUSDT", "ARKMUSDT",
    "AXSUSDT", "ONDOUSDT", "AAVEUSDT",
]

SEGMENTS = {
    "l1": ["ETHUSDT", "SOLUSDT", "AVAXUSDT", "NEARUSDT", "SUIUSDT", "SEIUSDT"],
    "l2": ["ARBUSDT", "OPUSDT"],
    "ai": ["RENDERUSDT", "FETUSDT", "WLDUSDT", "ARKMUSDT"],
    "memes": ["DOGEUSDT", "WIFUSDT", "1000PEPEUSDT"],
    "defi": ["JTOUSDT", "AAVEUSDT"],
    "rwa": ["ONDOUSDT"],
    "gaming": ["AXSUSDT"],
}

LEAD_TARGETS = {
    "btc": [s for s in SYMBOLS if s != "BTCUSDT"],
    "eth_l2": ["ARBUSDT", "OPUSDT", "AAVEUSDT"],
    "sol_beta": ["WIFUSDT", "1000PEPEUSDT", "JTOUSDT"],
}

FRED = {
    "nasdaq": "NASDAQCOM",
    "yield2y": "DGS2",
    "vix": "VIXCLS",
    "usd": "DTWEXBGS",
}


@dataclass(frozen=True)
class Bar:
    ts: int
    close: float
    volume: float
    quote_volume: float
    taker_buy_base: float


@dataclass(frozen=True)
class Trade:
    strategy: str
    ts: int
    symbol: str
    side: int
    hold_h: int
    gross: float
    net: float
    meta: Dict[str, object]


class Series:
    def __init__(self, times: Sequence[int], rows: Dict[int, Bar]):
        self.times = times
        self.close: List[Optional[float]] = []
        self.vol: List[float] = []
        self.qv: List[float] = []
        self.tb: List[float] = []
        for ts in times:
            b = rows.get(ts)
            self.close.append(b.close if b else None)
            self.vol.append(b.volume if b else 0.0)
            self.qv.append(b.quote_volume if b else 0.0)
            self.tb.append(b.taker_buy_base if b else 0.0)

        self.p_qv = [0.0]
        self.p_vol = [0.0]
        self.p_tb = [0.0]
        self.logret: List[Optional[float]] = [None] * len(times)
        self.p_r = [0.0]
        self.p_r2 = [0.0]
        self.p_rc = [0]
        for i in range(len(times)):
            self.p_qv.append(self.p_qv[-1] + self.qv[i])
            self.p_vol.append(self.p_vol[-1] + self.vol[i])
            self.p_tb.append(self.p_tb[-1] + self.tb[i])
            r = None
            if i > 0 and self.close[i] and self.close[i - 1] and self.close[i] > 0 and self.close[i - 1] > 0:
                r = math.log(self.close[i] / self.close[i - 1])
            self.logret[i] = r
            self.p_r.append(self.p_r[-1] + (r or 0.0))
            self.p_r2.append(self.p_r2[-1] + (r * r if r is not None else 0.0))
            self.p_rc.append(self.p_rc[-1] + (1 if r is not None else 0))

    def px(self, i: int) -> Optional[float]:
        return self.close[i] if 0 <= i < len(self.close) else None

    def ret(self, i: int, h: int) -> Optional[float]:
        if i - h < 0:
            return None
        a, b = self.px(i - h), self.px(i)
        return (b / a - 1.0) if a and b and a > 0 else None

    @staticmethod
    def _psum(p: Sequence[float], i: int, h: int) -> float:
        j = max(0, i + 1 - h)
        return p[i + 1] - p[j]

    def taker_ratio(self, i: int, h: int) -> Optional[float]:
        v = self._psum(self.p_vol, i, h)
        return self._psum(self.p_tb, i, h) / v if v > 0 else None

    def qv_ratio(self, i: int, recent: int, base: int) -> Optional[float]:
        if i + 1 < recent + base:
            return None
        r0 = i + 1 - recent
        b0 = r0 - base
        r = (self.p_qv[i + 1] - self.p_qv[r0]) / recent
        b = (self.p_qv[r0] - self.p_qv[b0]) / base
        return r / b if b > 0 else None

    def sigma(self, i: int, h: int = 168) -> Optional[float]:
        if i + 1 < h:
            return None
        a = i + 1 - h
        n = self.p_rc[i + 1] - self.p_rc[a]
        if n < int(h * 0.8) or n < 2:
            return None
        s = self.p_r[i + 1] - self.p_r[a]
        s2 = self.p_r2[i + 1] - self.p_r2[a]
        mu = s / n
        var = max((s2 - n * mu * mu) / (n - 1), 0.0)
        return math.sqrt(var)

    def zret(self, i: int, h: int) -> Optional[float]:
        r, sig = self.ret(i, h), self.sigma(i, 168)
        if r is None or not sig or sig <= 0:
            return None
        return r / (sig * math.sqrt(h))


def month_range(start: str, end: str) -> List[str]:
    y, m = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def fetch(url: str, retries: int = 3) -> Optional[bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": "QuantOS-Research/1.0"})
    for k in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if k + 1 == retries:
                raise
        except Exception:
            if k + 1 == retries:
                raise
        time.sleep(0.5 * (k + 1))
    return None


def norm_ts(v: int) -> int:
    # Binance archives can use ms or us depending on era/data family.
    while v > 10**14:
        v //= 1000
    return v


def load_klines(symbol: str, months: Sequence[str], manifest: Dict[str, object]) -> Dict[int, Bar]:
    out: Dict[int, Bar] = {}
    ok = miss = 0
    for ym in months:
        fn = f"{symbol}-1h-{ym}.zip"
        url = f"https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/1h/{fn}"
        raw = fetch(url)
        if raw is None:
            miss += 1
            continue
        ok += 1
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = z.namelist()[0]
            text = io.TextIOWrapper(z.open(name), encoding="utf-8")
            for row in csv.reader(text):
                if not row or not row[0].lstrip("-").isdigit():
                    continue
                try:
                    ts = norm_ts(int(row[0]))
                    out[ts] = Bar(
                        ts=ts,
                        close=float(row[4]),
                        volume=float(row[5]),
                        quote_volume=float(row[7]),
                        taker_buy_base=float(row[9]),
                    )
                except (ValueError, IndexError):
                    continue
    manifest.setdefault("binance", {})[symbol] = {
        "months_ok": ok,
        "months_missing": miss,
        "rows": len(out),
        "first_ts": min(out) if out else None,
        "last_ts": max(out) if out else None,
    }
    return out


def load_funding(symbol: str, months: Sequence[str], manifest: Dict[str, object]) -> Dict[int, float]:
    out: Dict[int, float] = {}
    ok = 0
    for ym in months:
        fn = f"{symbol}-fundingRate-{ym}.zip"
        url = f"https://data.binance.vision/data/futures/um/monthly/fundingRate/{symbol}/{fn}"
        raw = fetch(url)
        if raw is None:
            continue
        ok += 1
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = z.namelist()[0]
            rows = list(csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8")))
        if not rows:
            continue
        header = [x.strip().lower() for x in rows[0]]
        has_header = not rows[0][0].lstrip("-").isdigit()
        data = rows[1:] if has_header else rows
        for row in data:
            try:
                if has_header:
                    i_ts = header.index("calc_time") if "calc_time" in header else 0
                    if "last_funding_rate" in header:
                        i_rate = header.index("last_funding_rate")
                    elif "fundingrate" in header:
                        i_rate = header.index("fundingrate")
                    else:
                        i_rate = len(row) - 1
                else:
                    i_ts, i_rate = 0, len(row) - 1
                ts = norm_ts(int(float(row[i_ts])))
                out[ts] = float(row[i_rate])
            except (ValueError, IndexError):
                continue
    manifest.setdefault("funding", {})[symbol] = {"months_ok": ok, "rows": len(out)}
    return out


def fetch_fred(series_id: str, start: date, end: date) -> List[Tuple[date, float]]:
    url = (
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        f"&cosd={start.isoformat()}&coed={end.isoformat()}"
    )
    raw = fetch(url)
    if raw is None:
        return []
    text = raw.decode("utf-8-sig", errors="replace")
    out = []
    for row in csv.reader(io.StringIO(text)):
        if not row or row[0].lower() in ("date", "observation_date"):
            continue
        try:
            out.append((date.fromisoformat(row[0]), float(row[1])))
        except (ValueError, IndexError):
            continue
    return out


class Macro:
    def __init__(self, data: Dict[str, List[Tuple[date, float]]]):
        self.data = {k: sorted(v) for k, v in data.items()}

    def _last_n(self, name: str, d: date, n: int = 6) -> List[float]:
        xs = [v for dd, v in self.data.get(name, []) if dd <= d]
        return xs[-n:]

    def state(self, d: date) -> Optional[str]:
        # Critical anti-lookahead rule: caller supplies previous calendar day.
        vals = {}
        for name in ("nasdaq", "yield2y", "vix", "usd"):
            x = self._last_n(name, d, 6)
            if len(x) < 2:
                return None
            vals[name] = x[-1] - x[0]
        good = sum([
            vals["nasdaq"] > 0,
            vals["yield2y"] < 0,
            vals["vix"] < 0,
            vals["usd"] < 0,
        ])
        bad = sum([
            vals["nasdaq"] < 0,
            vals["yield2y"] > 0,
            vals["vix"] > 0,
            vals["usd"] > 0,
        ])
        if good >= 3:
            return "RISK_ON"
        if bad >= 3:
            return "RISK_OFF"
        return "MIXED"


def normal_p_two_sided(t: float) -> float:
    return max(0.0, min(1.0, 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(t) / math.sqrt(2.0))))))


def summarize(xs: Sequence[float]) -> Dict[str, Optional[float]]:
    if not xs:
        return {"n": 0, "mean": None, "median": None, "win_rate": None, "t": None, "p": None, "ci95_lo": None, "ci95_hi": None}
    n = len(xs)
    mu = statistics.fmean(xs)
    med = statistics.median(xs)
    wr = sum(x > 0 for x in xs) / n
    if n > 1:
        sd = statistics.stdev(xs)
        se = sd / math.sqrt(n) if sd > 0 else 0.0
        t = mu / se if se > 0 else None
        p = normal_p_two_sided(t) if t is not None else None
        lo, hi = mu - 1.96 * se, mu + 1.96 * se
    else:
        t = p = lo = hi = None
    return {"n": n, "mean": mu, "median": med, "win_rate": wr, "t": t, "p": p, "ci95_lo": lo, "ci95_hi": hi}


def future_return(s: Series, i: int, hold_h: int, side: int) -> Optional[Tuple[float, float]]:
    a, b = s.px(i), s.px(i + hold_h)
    if not a or not b:
        return None
    gross = side * (b / a - 1.0)
    return gross, gross - COST_RT


def run_sweep(series: Dict[str, Series], funding: Dict[str, Dict[int, float]], macro: Macro, times: Sequence[int]) -> List[Trade]:
    trades: List[Trade] = []
    last: Dict[Tuple[str, str], int] = {}
    funding_grid: Dict[str, List[Optional[float]]] = {}
    for sym, f in funding.items():
        vals: List[Optional[float]] = [None] * len(times)
        latest = None
        for i, ts in enumerate(times):
            if ts in f:
                latest = f[ts]
            vals[i] = latest
        funding_grid[sym] = vals

    def emit(name: str, sym: str, side: int, i: int, hold: int, meta: Dict[str, object], gap: Optional[int] = None):
        if sym not in series or i + hold >= len(times):
            return
        key = (name, sym)
        min_gap = gap if gap is not None else hold
        if key in last and i - last[key] < min_gap:
            return
        fr = future_return(series[sym], i, hold, side)
        if fr is None:
            return
        last[key] = i
        trades.append(Trade(name, times[i], sym, side, hold, fr[0], fr[1], meta))

    def emit_basket(name: str, syms: Sequence[str], side: int, i: int, hold: int, meta: Dict[str, object], gap: int):
        valid = []
        for sym in syms:
            if sym in series:
                fr = future_return(series[sym], i, hold, side)
                if fr is not None:
                    valid.append((sym, fr))
        if len(valid) < 2:
            return
        key = (name, "BASKET")
        if key in last and i - last[key] < gap:
            return
        last[key] = i
        gross = statistics.fmean(x[1][0] for x in valid)
        net = statistics.fmean(x[1][1] for x in valid)
        trades.append(Trade(name, times[i], "|".join(x[0] for x in valid), side, hold, gross, net, meta))

    def emit_pair(name: str, long_sym: str, short_sym: str, i: int, hold: int, meta: Dict[str, object], gap: int):
        if long_sym not in series or short_sym not in series:
            return
        a = future_return(series[long_sym], i, hold, 1)
        b = future_return(series[short_sym], i, hold, -1)
        if a is None or b is None:
            return
        key = (name, long_sym + "|" + short_sym)
        if key in last and i - last[key] < gap:
            return
        last[key] = i
        trades.append(Trade(name, times[i], f"{long_sym}|{short_sym}", 0, hold,
                            0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1]), meta))

    start_i = 24 * 14
    btc = series.get("BTCUSDT")
    if btc is None:
        return trades

    for i in range(start_i, len(times) - 25):
        dt = datetime.fromtimestamp(times[i] / 1000, tz=timezone.utc)
        macro_state = macro.state(dt.date() - timedelta(days=1))

        # A) Flow / absorption: aggressive flow that fails to move price versus flow continuation.
        for sym, s in series.items():
            z4 = s.zret(i, 4)
            tr4 = s.taker_ratio(i, 4)
            vr = s.qv_ratio(i, 4, 96)
            if z4 is None or tr4 is None or vr is None:
                continue
            if vr >= 1.5 and abs(z4) <= 0.50:
                if tr4 >= 0.60:
                    emit("OB_PROXY_BUY_ABSORPTION_SHORT_4H", sym, -1, i, 4, {"z4": z4, "taker4": tr4, "qv_ratio": vr}, 4)
                elif tr4 <= 0.40:
                    emit("OB_PROXY_SELL_ABSORPTION_LONG_4H", sym, 1, i, 4, {"z4": z4, "taker4": tr4, "qv_ratio": vr}, 4)
            if vr >= 1.3 and abs(z4) >= 1.5:
                if z4 > 0 and tr4 >= 0.56:
                    emit("FLOW_PRICE_CONTINUATION_LONG_4H", sym, 1, i, 4, {"z4": z4, "taker4": tr4, "qv_ratio": vr}, 4)
                elif z4 < 0 and tr4 <= 0.44:
                    emit("FLOW_PRICE_CONTINUATION_SHORT_4H", sym, -1, i, 4, {"z4": z4, "taker4": tr4, "qv_ratio": vr}, 4)
            if abs(z4) >= 2.5 and vr >= 1.5:
                tr_prev = s.taker_ratio(i - 4, 12)
                if tr_prev is not None:
                    if z4 > 0 and tr4 <= tr_prev - 0.05:
                        emit("IMPULSE_FLOW_EXHAUSTION_SHORT_12H", sym, -1, i, 12, {"z4": z4, "taker4": tr4, "prev": tr_prev}, 12)
                    elif z4 < 0 and tr4 >= tr_prev + 0.05:
                        emit("IMPULSE_FLOW_EXHAUSTION_LONG_12H", sym, 1, i, 12, {"z4": z4, "taker4": tr4, "prev": tr_prev}, 12)

        # B) Major -> lagging asset propagation, conditional on fresh target flow.
        for label, leader, targets in [
            ("BTC", "BTCUSDT", LEAD_TARGETS["btc"]),
            ("ETH", "ETHUSDT", LEAD_TARGETS["eth_l2"]),
            ("SOL", "SOLUSDT", LEAD_TARGETS["sol_beta"]),
        ]:
            if leader not in series:
                continue
            ls = series[leader]
            zl = ls.zret(i, 4)
            lvr = ls.qv_ratio(i, 4, 96)
            if zl is None or lvr is None or abs(zl) < 2.0 or lvr < 1.2:
                continue
            side = 1 if zl > 0 else -1
            for sym in targets:
                s = series.get(sym)
                if s is None:
                    continue
                zt = s.zret(i, 4)
                tr2 = s.taker_ratio(i, 2)
                vr2 = s.qv_ratio(i, 2, 48)
                if zt is None or tr2 is None or vr2 is None:
                    continue
                lag_ok = abs(zt) <= 0.75
                flow_ok = (side > 0 and tr2 >= 0.53) or (side < 0 and tr2 <= 0.47)
                if lag_ok and flow_ok and vr2 >= 1.1:
                    emit(f"{label}_LEAD_LAG_FLOW_CONFIRM_4H", sym, side, i, 4,
                         {"leader_z4": zl, "target_z4": zt, "taker2": tr2, "qv_ratio2": vr2}, 4)
                    if macro_state == ("RISK_ON" if side > 0 else "RISK_OFF"):
                        emit(f"{label}_LEAD_LAG_MACRO_CONFIRM_4H", sym, side, i, 4,
                             {"leader_z4": zl, "target_z4": zt, "macro": macro_state}, 4)

        # C) Segment breadth and rotation. Sample every 6h to reduce duplicate overlapping events.
        if dt.hour % 6 == 0:
            for seg, members0 in SEGMENTS.items():
                members = [s for s in members0 if s in series and series[s].ret(i, 6) is not None]
                if len(members) < 3:
                    continue
                r6 = {s: series[s].ret(i, 6) for s in members}
                r24 = {s: series[s].ret(i, 24) for s in members}
                pos = sum((r6[s] or 0) > 0 for s in members) / len(members)
                med6 = statistics.median(r6[s] for s in members if r6[s] is not None)
                if pos >= 0.75 and med6 >= 0.01:
                    selected = [s for s in members if (series[s].taker_ratio(i, 6) or 0.5) >= 0.52]
                    emit_basket("SEGMENT_BREADTH_CONTINUATION_LONG_12H", selected, 1, i, 12,
                                {"segment": seg, "breadth": pos, "median6": med6}, 12)
                elif pos <= 0.25 and med6 <= -0.01:
                    selected = [s for s in members if (series[s].taker_ratio(i, 6) or 0.5) <= 0.48]
                    emit_basket("SEGMENT_BREADTH_CONTINUATION_SHORT_12H", selected, -1, i, 12,
                                {"segment": seg, "breadth": pos, "median6": med6}, 12)

                ranked = sorted((r24[s], s) for s in members if r24[s] is not None)
                if len(ranked) >= 3:
                    loser_r, loser = ranked[0]
                    winner_r, winner = ranked[-1]
                    if winner_r - loser_r >= 0.12:
                        emit_pair("SEGMENT_PAIR_MEAN_REVERSION_24H", loser, winner, i, 24,
                                  {"segment": seg, "spread24": winner_r - loser_r}, 24)
                        emit_pair("SEGMENT_PAIR_MOMENTUM_24H", winner, loser, i, 24,
                                  {"segment": seg, "spread24": winner_r - loser_r}, 24)

                # Conditioned leader -> laggard rotation (NOT the rejected pure price-only rule).
                r72 = {s: series[s].ret(i, 72) for s in members}
                leaders = [s for s in members if r72[s] is not None and r72[s] >= 0.15 and
                           (series[s].qv_ratio(i, 72, 168) or 0) >= 1.5]
                if leaders:
                    leader = max(leaders, key=lambda s: r72[s] or -9)
                    for lag in members:
                        if lag == leader or r72[lag] is None or not (-0.05 <= r72[lag] <= 0.05):
                            continue
                        lag6 = series[lag].ret(i, 6)
                        tr6 = series[lag].taker_ratio(i, 6)
                        tr_prev = series[lag].taker_ratio(i - 6, 24)
                        vr6 = series[lag].qv_ratio(i, 6, 72)
                        if lag6 is not None and lag6 >= 0.005 and tr6 is not None and tr_prev is not None and                                 tr6 >= tr_prev + 0.03 and (vr6 or 0) >= 1.2:
                            emit("LEADER_LAGGARD_ROTATION_FLOW_24H", lag, 1, i, 24,
                                 {"segment": seg, "leader": leader, "leader72": r72[leader], "lag72": r72[lag],
                                  "lag6": lag6, "taker_delta": tr6 - tr_prev, "qv_ratio6": vr6}, 24)

                    # Post-explosion leader short, only with explicit exhaustion confirmation.
                    l6 = series[leader].ret(i, 6)
                    tr6 = series[leader].taker_ratio(i, 6)
                    trprev = series[leader].taker_ratio(i - 6, 24)
                    if l6 is not None and l6 <= 0 and tr6 is not None and trprev is not None and tr6 <= trprev - 0.03:
                        emit("POST_EXPLOSION_LEADER_EXHAUSTION_SHORT_24H", leader, -1, i, 24,
                             {"segment": seg, "leader72": r72[leader], "ret6": l6, "taker_delta": tr6 - trprev}, 24)

        # D) Funding crowding / squeeze hypotheses, using the most recent PREVIOUS-hour-known funding.
        if i > 0:
            for sym, grid in funding_grid.items():
                if sym not in series:
                    continue
                rate = grid[i - 1]
                r24 = series[sym].ret(i, 24)
                if rate is None or r24 is None:
                    continue
                if rate >= 0.0005 and r24 >= 0.02:
                    emit("FUNDING_CROWDED_LONG_CONTRARIAN_SHORT_8H", sym, -1, i, 8,
                         {"funding": rate, "ret24": r24}, 8)
                elif rate <= -0.0005 and r24 <= -0.02:
                    emit("FUNDING_CROWDED_SHORT_CONTRARIAN_LONG_8H", sym, 1, i, 8,
                         {"funding": rate, "ret24": r24}, 8)
                if 0 <= rate <= 0.00025 and r24 >= 0.03:
                    emit("FUNDING_HEALTHY_TREND_LONG_8H", sym, 1, i, 8, {"funding": rate, "ret24": r24}, 8)
                elif -0.00025 <= rate <= 0 and r24 <= -0.03:
                    emit("FUNDING_HEALTHY_TREND_SHORT_8H", sym, -1, i, 8, {"funding": rate, "ret24": r24}, 8)

        # E) Macro-regime hypotheses. Macro values are lagged by one calendar day above.
        br24 = btc.ret(i, 24)
        if br24 is not None:
            if macro_state == "RISK_ON" and br24 >= 0.02:
                emit("MACRO_RISK_ON_BTC_MOMENTUM_24H", "BTCUSDT", 1, i, 24,
                     {"macro": macro_state, "btc24": br24}, 24)
            if macro_state == "RISK_OFF" and br24 <= -0.02:
                emit("MACRO_RISK_OFF_BTC_MOMENTUM_24H", "BTCUSDT", -1, i, 24,
                     {"macro": macro_state, "btc24": br24}, 24)
            if macro_state == "RISK_ON" and br24 <= -0.03:
                emit("MACRO_RISK_ON_BUY_BTC_DIP_24H", "BTCUSDT", 1, i, 24,
                     {"macro": macro_state, "btc24": br24}, 24)
            if macro_state == "RISK_OFF" and br24 >= 0.03:
                emit("MACRO_RISK_OFF_FADE_BTC_RALLY_24H", "BTCUSDT", -1, i, 24,
                     {"macro": macro_state, "btc24": br24}, 24)

        # F) Weekend -> Sunday/CME reopen style repricing proxy.
        if dt.weekday() == 6 and dt.hour == 20:
            r48 = btc.ret(i, 48)
            if r48 is not None and abs(r48) >= 0.03:
                side = 1 if r48 > 0 else -1
                emit("SUNDAY_REOPEN_WEEKEND_MOMENTUM_4H", "BTCUSDT", side, i, 4, {"weekend48": r48}, 168)
                emit("SUNDAY_REOPEN_WEEKEND_FADE_4H", "BTCUSDT", -side, i, 4, {"weekend48": r48}, 168)

    return trades


def aggregate(trades: Sequence[Trade], split_ts: int) -> List[Dict[str, object]]:
    grouped: Dict[str, List[Trade]] = defaultdict(list)
    for t in trades:
        grouped[t.strategy].append(t)
    names = sorted(grouped)
    alpha = 0.05 / max(len(names), 1)
    out = []
    for name in names:
        ts = grouped[name]
        train = [t.net for t in ts if t.ts < split_ts]
        hold = [t.net for t in ts if t.ts >= split_ts]
        a, b = summarize(train), summarize(hold)
        if b["n"] < MIN_HOLDOUT:
            status = "INSUFFICIENT_HOLDOUT"
        elif (a["mean"] or 0) <= 0 or (b["mean"] or 0) <= 0:
            status = "REJECT"
        elif b["p"] is not None and b["p"] <= alpha and (b["mean"] or 0) >= 0.0005:
            status = "SURVIVES_FIRST_GATE"
        else:
            status = "WATCH"
        out.append({
            "strategy": name,
            "status": status,
            "train": a,
            "holdout": b,
            "bonferroni_alpha": alpha,
            "cost_round_trip": COST_RT,
            "first_event": min((t.ts for t in ts), default=None),
            "last_event": max((t.ts for t in ts), default=None),
        })
    out.sort(key=lambda r: (
        0 if r["status"] == "SURVIVES_FIRST_GATE" else
        1 if r["status"] == "WATCH" else
        2 if r["status"] == "INSUFFICIENT_HOLDOUT" else 3,
        -(r["holdout"]["mean"] or -99),
    ))
    return out


def iso(ts: Optional[int]) -> Optional[str]:
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat() if ts else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/strategy_sweep_01")
    ap.add_argument("--start-month", default=START_MONTH)
    ap.add_argument("--end-month", default=END_MONTH)
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest: Dict[str, object] = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "start_month": args.start_month,
        "end_month": args.end_month,
        "symbols_requested": SYMBOLS,
        "cost_round_trip": COST_RT,
        "purpose": "DISCOVERY_ONLY",
    }
    months = month_range(args.start_month, args.end_month)

    print(f"Downloading {len(months)} months for {len(SYMBOLS)} symbols...")
    raw = {}
    fund = {}
    for k, sym in enumerate(SYMBOLS, 1):
        print(f"[{k}/{len(SYMBOLS)}] {sym}", flush=True)
        rows = load_klines(sym, months, manifest)
        if len(rows) >= 24 * 60:
            raw[sym] = rows
            fund[sym] = load_funding(sym, months, manifest)

    if "BTCUSDT" not in raw:
        raise RuntimeError("BTCUSDT historical data unavailable")

    times = sorted(raw["BTCUSDT"])
    aligned = {sym: Series(times, rows) for sym, rows in raw.items()}
    manifest["symbols_loaded"] = sorted(aligned)
    manifest["grid_rows"] = len(times)
    manifest["grid_first"] = iso(times[0])
    manifest["grid_last"] = iso(times[-1])

    start_d = datetime.fromtimestamp(times[0] / 1000, tz=timezone.utc).date() - timedelta(days=30)
    end_d = datetime.fromtimestamp(times[-1] / 1000, tz=timezone.utc).date()
    macro_data = {}
    for name, sid in FRED.items():
        try:
            macro_data[name] = fetch_fred(sid, start_d, end_d)
        except Exception as e:
            print(f"FRED {sid} failed: {type(e).__name__}: {e}")
            macro_data[name] = []
    manifest["fred"] = {k: {"series": FRED[k], "rows": len(v)} for k, v in macro_data.items()}
    macro = Macro(macro_data)

    split_ts = times[int(len(times) * 0.70)]
    manifest["train_holdout_split"] = iso(split_ts)
    trades = run_sweep(aligned, fund, macro, times)
    results = aggregate(trades, split_ts)

    with (outdir / "trades.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["strategy", "ts_utc", "symbol", "side", "hold_h", "gross", "net", "meta_json"])
        for t in trades:
            w.writerow([t.strategy, iso(t.ts), t.symbol, t.side, t.hold_h, t.gross, t.net,
                        json.dumps(t.meta, sort_keys=True)])

    payload = {
        "meta": {
            "purpose": "DISCOVERY_ONLY",
            "live_capital_authorized": 0,
            "cost_round_trip": COST_RT,
            "split_ts": split_ts,
            "split_utc": iso(split_ts),
            "hypotheses_reported": len(results),
            "events_total": len(trades),
            "notes": [
                "SURVIVES_FIRST_GATE is not strategy validation or permission to paper/live trade.",
                "Pure price-only leader->laggard is intentionally absent; only flow-conditioned rotation is tested.",
                "Macro inputs are lagged by one calendar day to avoid same-day publication/close look-ahead.",
                "Microstructure/liquidation hypotheses requiring local recorder Parquet are deferred to Sweep 02.",
            ],
        },
        "results": results,
    }
    (outdir / "strategy_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (outdir / "data_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Strategy Factory — Sweep 01",
        "",
        "**DISCOVERY ONLY. No registry promotion. Live capital remains USD 0.**",
        "",
        f"Data: {iso(times[0])} → {iso(times[-1])}; split: {iso(split_ts)}; events: {len(trades)}.",
        f"Cost charged: {COST_RT*100:.3f}% round trip. Bonferroni correction across {len(results)} reported hypotheses.",
        "",
        "| Status | Strategy | N holdout | Mean net | Win rate | p |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in results:
        h = r["holdout"]
        lines.append(
            f"| {r['status']} | {r['strategy']} | {h['n']} | "
            f"{(h['mean']*100 if h['mean'] is not None else float('nan')):.3f}% | "
            f"{(h['win_rate']*100 if h['win_rate'] is not None else float('nan')):.1f}% | "
            f"{(h['p'] if h['p'] is not None else float('nan')):.4g} |"
        )
    (outdir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\nTop results:")
    for r in results[:12]:
        h = r["holdout"]
        print(f"{r['status']:24s} {r['strategy']:50s} n={h['n']:4d} mean={(h['mean'] or 0)*100:+.3f}% p={h['p']}")
    print(f"Artifacts written to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
