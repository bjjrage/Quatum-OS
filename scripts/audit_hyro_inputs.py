"""Full minute/hour/funding integrity crosscheck; never modify vendor history."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    root = Path("data/historical/binance_um")
    con = duckdb.connect(config={"threads": 2})
    con.execute("SET enable_progress_bar=false")
    minute = [p.as_posix() for p in (root / "klines_1m").rglob("*.parquet")]
    hourly = [p.as_posix() for p in (root / "klines_1h").rglob("*.parquet")]
    funding = [p.as_posix() for p in (root / "funding").rglob("*.parquet")]
    rows, dup, bad = con.execute("SELECT count(*),count(*)-count(DISTINCT (symbol,open_time_ms)),"
        "count(*) FILTER(WHERE low<=0 OR low>least(open,close) OR high<greatest(open,close) "
        "OR taker_buy_volume>volume*1.00001 OR open_time_ms%60000<>0) FROM read_parquet(?)", [minute]).fetchone()
    con.execute("CREATE TEMP TABLE agg AS SELECT symbol,open_time_ms//3600000*3600000 t,count(*) n,"
        "arg_min(open,open_time_ms) o,max(high) h,min(low) l,arg_max(close,open_time_ms) c,"
        "arg_min(volume,open_time_ms) first_volume,sum(volume) volume "
        "FROM read_parquet(?) GROUP BY 1,2", [minute])
    con.execute("CREATE TEMP TABLE diffs AS SELECT a.*, b.open hourly_open,b.close hourly_close,"
        "greatest(abs(a.o/b.open-1),abs(a.c/b.close-1),abs(a.h/b.high-1),abs(a.l/b.low-1)) difference "
        "FROM agg a JOIN read_parquet(?) b ON a.symbol=b.symbol AND a.t=b.open_time_ms WHERE a.n=60", [hourly])
    matched, mismatch, emptyfirst, maxdiff = con.execute("SELECT count(*),count(*) FILTER(WHERE difference>1e-7),"
        "count(*) FILTER(WHERE difference>1e-7 AND first_volume=0),max(difference) FROM diffs").fetchone()
    top = con.execute("SELECT symbol,t,o,hourly_open,c,hourly_close,first_volume,difference FROM diffs "
                      "ORDER BY difference DESC LIMIT 12").fetchall()
    dupfund, badmarks = con.execute("SELECT count(*)-count(DISTINCT(symbol,funding_time_ms)),"
        "count(*) FILTER(WHERE mark_price<=0 OR NOT isfinite(mark_price)) FROM read_parquet(?)", [funding]).fetchone()
    maxgap = con.execute("SELECT max(gap)/3600000 FROM (SELECT funding_time_ms-lag(funding_time_ms) "
        "OVER (PARTITION BY symbol ORDER BY funding_time_ms) gap FROM read_parquet(?))", [funding]).fetchone()[0]
    result = {"minute_rows": rows, "duplicate_minutes": dup, "invalid_ohlc": bad,
              "matched_complete_hours": matched, "mismatched_hours_relative_tolerance_1e7": mismatch,
              "mismatches_with_zero_volume_first_minute": emptyfirst,
              "max_relative_price_difference_pct": maxdiff * 100, "largest_discrepancies": top,
              "funding_duplicate_events": dupfund, "funding_nonpositive_marks": badmarks,
              "funding_max_gap_hours": maxgap,
              "interpretation": "Zero-trade minutes can carry previous prices; hourly opens can be the first trade. Differences are retained and disclosed, not silently repaired. Nonpositive funding marks use contemporaneous hourly price as an explicit approximation."}
    dest = Path("data/research/hyro_2026_10_04/minute_crosscheck.json")
    dest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "largest_discrepancies"}, indent=2))
    if dup or bad or dupfund:
        raise ValueError("Input integrity checks failed")


if __name__ == "__main__":
    main()
