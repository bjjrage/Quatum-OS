"""Frozen robustness checks; do not select a new model on these results."""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from src.research.hyro_edge import Candidate, backtest, iso, load_panel, segments, statistics, write_json


def bootstrap(values, block=7, repetitions=5000, seed=20261004):
    rnd = random.Random(seed)
    n = len(values)
    block_sums = [sum(values[i:i + block]) for i in range(n - block + 1)]
    sums = []
    for _ in range(repetitions):
        full, remainder = divmod(n, block)
        total = sum(rnd.choice(block_sums) for _ in range(full))
        ix = rnd.randrange(n - block + 1)
        total += sum(values[ix:ix + remainder])
        sums.append(total / n * 365 * 100)
    sums.sort()
    return {"block_days": block, "repetitions": repetitions, "seed": seed,
            "annual_mean_pct_initial_ci95": [sums[int(.025 * repetitions)], sums[int(.975 * repetitions)]],
            "note": "Unadjusted exploratory CI; blocks do not fix reused holdout or selection bias."}


def main():
    out = Path("data/research/hyro_2026_10_04")
    write_json(out / "robustness_protocol.json", {"week_offsets": list(range(7)),
        "families": ["flow", "flow_residual"], "lookback_and_rebalance_days": 7,
        "purpose": "falsification; do not choose the best weekday",
        "additional_offsets_vs_screen": 12, "bootstrap": "5000 seven-day moving blocks, fixed seed",
        "ensemble": "equal one-seventh allocation to all seven weekly entry calendars; do not pick a weekday",
        "selection_status": "exploratory; cumulative known trials lower bound now 274 including 42+8+12+2 new tests"})
    cutoff = int(datetime(2026, 10, 4, tzinfo=timezone.utc).timestamp() * 1000)
    p = load_panel(Path("data/historical/binance_um"), cutoff)
    lo, hi = segments(p)["test_reused"]
    results = []
    for fam in ("flow", "flow_residual"):
        cfg = Candidate(fam, 7, 7)
        offsets = []
        cohort_maps = []
        rows = None
        for offset in range(7):
            allrows = backtest(p, cfg, start=150 + offset)
            cohort_maps.append({r.signal_day: r for r in allrows})
            part = [r for r in allrows if lo <= r.signal_day < hi]
            offsets.append({"schedule_offset": offset, "statistics": statistics([r.pnl for r in part])})
            if offset == 0:
                rows = part
        values = [r.pnl for r in rows]
        top5 = set(sorted(range(len(values)), key=lambda i: -values[i])[:5])
        without = [v for i, v in enumerate(values) if i not in top5]
        # Estimate BTC beta in training only; apply it unchanged in the retrospective segment.
        btc = p.hourly["BTCUSDT"]["o"]
        pairs = []
        for r in backtest(p, cfg):
            h = (p.day0 + r.signal_day + 1) * 24 + 1 - p.hour0
            b = btc[h + 24] / btc[h] - 1
            pairs.append((r.signal_day, r.pnl, b))
        training = [v for v in pairs if v[0] < lo - 370]
        my = sum(y for _, y, _ in training) / len(training)
        mx = sum(x for _, _, x in training) / len(training)
        beta = sum((x - mx) * (y - my) for _, y, x in training) / sum((x - mx) ** 2 for _, _, x in training)
        alpha = [y - beta * b for d, y, b in pairs if lo <= d < hi]
        by_symbol = {}
        for r in rows:
            for t in r.closed:
                by_symbol[t["symbol"]] = by_symbol.get(t["symbol"], 0) + t["net"]
        results.append({"id": cfg.id, "schedule_sensitivity": offsets,
                        "bootstrap": bootstrap(values), "without_best_5_days": statistics(without),
                        "btc_beta_fitted_training": beta, "beta_adjusted_test": statistics(alpha),
                        "closed_trade_contribution_pct": sorted([(s, v * 100) for s, v in by_symbol.items()],
                                                                  key=lambda a: -a[1]),
                        "contribution_note": "Only trades closed during the period; opening inventory crossing the boundary is included, terminal open positions excluded."})
        common = sorted(set.intersection(*(set(c) for c in cohort_maps)))
        averaged = {d: sum(c[d].pnl for c in cohort_maps) / 7 for d in common}
        ensemble = {name: statistics([.5 * averaged[d] for d in common
                                     if a <= d < (b - 9 if name != "test_reused" else b)])
                    for name, (a, b) in segments(p).items()}
        results[-1]["seven_calendar_ensemble_gross_half"] = ensemble
        results[-1]["ensemble_limitations"] = (
            "Fixed subportfolio arithmetic with full close/reopen costs, no netting savings. "
            "Not replayed with minute stops or Hyro valid-day requirements; individual cohort closes "
            "can be below the 5%-of-initial qualifying-trade notional. An exploratory aggregation, not a validated second strategy.")
        print(cfg.id + " robustness completed", flush=True)
    write_json(out / "robustness.json", {"results": results})


if __name__ == "__main__":
    main()
