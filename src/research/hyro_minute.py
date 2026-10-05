"""One-minute execution/risk stress for the frozen weekly flow candidates.

Research only. Conservative stop fills: stop or opening gap, plus all costs;
account circuit breakers liquidate at adverse minute prices, never ideal stops.
"""
from __future__ import annotations

import math
from array import array
from dataclasses import dataclass
from pathlib import Path

from src.research.hyro_edge import Candidate, HOUR_MS, Panel, iso, statistics, weights


@dataclass
class Minutes:
    first: int
    last: int
    data: dict


def load_minutes(root: Path, syms: list[str], first: int, last: int) -> Minutes:
    import duckdb
    con = duckdb.connect(config={"threads": 2})
    con.execute("SET enable_progress_bar=false")
    data = {}
    for j, s in enumerate(syms):
        files = [p.as_posix() for p in (root / f"symbol={s}").glob("*.parquet")]
        rows = con.execute("SELECT open_time_ms//60000,open,high,low,close FROM read_parquet(?) "
                           "WHERE open_time_ms>=? AND open_time_ms<? ORDER BY 1",
                           [files, first * 60000, last * 60000]).fetchall()
        cols = {k: array("d", [math.nan]) * (last - first) for k in ("o", "h", "l", "c")}
        seen = set()
        for t, op, high, low, close in rows:
            if t in seen:
                raise ValueError(f"Duplicate minute: {s} {t}")
            seen.add(t)
            for key, value in zip(("o", "h", "l", "c"), (op, high, low, close)):
                cols[key][t - first] = value
        data[s] = cols
        print(f"Loaded minutes {j+1}/{len(syms)} {s}", flush=True)
    con.close()
    return Minutes(first, last, data)


def minute_price(m: Minutes, s: str, t: int, key: str = "o") -> float:
    a = m.data[s][key][t - m.first]
    if not a > 0:
        raise ValueError(f"Missing minute {s} {t} {key}")
    return a


def run(p: Panel, m: Minutes, cfg: Candidate, start: int, stop: int,
        scale: float = .5, leg_stop: float | None = None,
        daily_stop: float | None = None, side_cost_bps: float = 7.5) -> dict:
    lots = {}
    cash = 1.0
    cost = side_cost_bps / 10000
    daily, trades, traces = [], [], []
    day_realized = 0.0
    qualified = False
    current_day = None
    day_start = previous_eq = 1.0
    leg_stops = circuit_stops = 0
    fee_total = fund_total = 0.0
    funding_at = {}
    for s in m.data:
        for events in p.funding[s].values():
            for ts, rate, markpx in events:
                if m.first <= ts // 60000 < m.last:
                    funding_at.setdefault(ts // 60000, []).append((s, rate, markpx))

    def close(s: str, px: float, t: int, why: str) -> None:
        nonlocal cash, day_realized, qualified, fee_total
        q, entry, paid, entryfee = lots.pop(s)
        fee = abs(q * px) * cost
        gross = q * (px - entry)
        cash += gross - fee
        day_realized += gross - fee
        fee_total += fee
        net = gross - paid - entryfee - fee
        qualified |= abs(q * entry) >= .05 and abs(px / entry - 1) >= .01
        trades.append({"symbol": s, "minute": t, "entry_notional": abs(q * entry),
                       "gross_move": abs(px / entry - 1), "net": net, "reason": why})

    def mark(t: int, key: str = "c") -> float:
        return cash + sum(q * (minute_price(m, s, t, key) - px) for s, (q, px, _, _) in lots.items())

    for d in range(start, min(stop, p.n - 2)):
        first = (p.day0 + d + 1) * 1440 + 60
        rebalance = (d - start) % cfg.rebalance == 0
        for t in range(first, first + 1440):
            utc_day = t // 1440
            if utc_day != current_day:
                if current_day is not None:
                    eq = mark(t, "o")
                    daily.append({"day": current_day, "pnl": eq - previous_eq,
                                  "realized": day_realized, "qualified": qualified})
                    previous_eq = eq
                current_day = utc_day
                day_start = mark(t, "o")
                day_realized, qualified = 0.0, False
            if t == first and rebalance:
                for s in list(lots):
                    close(s, minute_price(m, s, t), t, "REBALANCE")
                for s, weight in weights(p, d, cfg).items():
                    w = weight * scale
                    px = minute_price(m, s, t)
                    fee = abs(w) * cost
                    cash -= fee
                    day_realized -= fee
                    fee_total += fee
                    lots[s] = (w / px, px, 0.0, fee)
            for s, rate, markpx in funding_at.get(t, []):
                if s in lots:
                    q, entry, paid, entryfee = lots[s]
                    fc = q * (markpx if math.isfinite(markpx) and markpx > 0 else minute_price(m, s, t)) * rate
                    cash -= fc
                    day_realized -= fc
                    fund_total += fc
                    lots[s] = (q, entry, paid + fc, entryfee)
            if leg_stop is not None:
                for s, (q, entry, _, _) in list(lots.items()):
                    threshold = entry * (1 - leg_stop if q > 0 else 1 + leg_stop)
                    if q > 0 and minute_price(m, s, t, "l") <= threshold:
                        close(s, min(threshold, minute_price(m, s, t)), t, "LEG_STOP")
                        leg_stops += 1
                    elif q < 0 and minute_price(m, s, t, "h") >= threshold:
                        close(s, max(threshold, minute_price(m, s, t)), t, "LEG_STOP")
                        leg_stops += 1
            worst = cash + sum(q * (minute_price(m, s, t, "l" if q > 0 else "h") - entry)
                               for s, (q, entry, _, _) in lots.items())
            gross = sum(abs(q) * minute_price(m, s, t, "h") for s, (q, _, _, _) in lots.items())
            if lots and daily_stop is not None and worst <= day_start - daily_stop:
                for s, (q, _, _, _) in list(lots.items()):
                    close(s, minute_price(m, s, t, "l" if q > 0 else "h"), t, "DAILY_CIRCUIT")
                circuit_stops += 1
            if t % 60 == 59 or (trades and trades[-1]["minute"] == t):
                eq = mark(t)
                traces.append({"minute": t, "equity": eq, "worst": min(worst, eq),
                               "day_start": day_start, "gross_upper": gross})
    last = (p.day0 + min(stop, p.n - 2) + 1) * 1440 + 60 - 1
    for s in list(lots):
        close(s, minute_price(m, s, last, "c"), last, "END_OF_SAMPLE")
    daily.append({"day": current_day, "pnl": cash - previous_eq,
                  "realized": day_realized, "qualified": qualified})
    # Aggregation reconciles exactly with the final cash balance after all positions close.
    if abs(sum(r["pnl"] for r in daily) - (cash - 1)) > 1e-8:
        raise AssertionError("Cash/equity reconciliation failed")
    return {"id": cfg.id, "scale": scale, "leg_stop": leg_stop, "daily_stop": daily_stop,
            "statistics": statistics([r["pnl"] for r in daily]), "trades": trades,
            "daily": daily, "hourly_checkpoints": traces, "leg_stop_count": leg_stops,
            "daily_circuit_count": circuit_stops, "fees_pct_initial": fee_total * 100,
            "funding_paid_pct_initial": fund_total * 100,
            "realized_trade_max_loss_pct": max([-t["net"] * 100 for t in trades] + [0])}
