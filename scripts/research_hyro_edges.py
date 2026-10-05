"""Run the read-only market-data research; write artifacts to data/research/hyro_2026_10_04."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.research.hyro_edge import (backtest, candidates, evaluate, hourly_trace, iso, load_panel,
                                    phase, segments, statistics, write_json)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/research/hyro_2026_10_04")
    parser.add_argument("--skip-replay", action="store_true")
    args = parser.parse_args()
    out = Path(args.output)
    cfgs = candidates()
    cutoff = int(datetime(2026, 10, 4, tzinfo=timezone.utc).timestamp() * 1000)
    protocol = {"account_initial_usdt": 10000, "mode": "TWO_STEP_RESEARCH_ONLY",
                "data_cutoff_exclusive_utc": "2026-10-04T00:00:00Z",
                "strategies": [asdict(c) for c in cfgs], "new_trials": len(cfgs),
                "prior_trials_lower_bound": 210,
                "cost_per_side_bps": 7.5, "stress_per_side_bps": 12.5,
                "train": "2022-03 to 2023-12", "validation": "2024",
                "test_reused": "2025-2026; NOT a virgin holdout",
                "purge": "full holding period plus two days before split",
                "selection_rule": "maximize min(train Sharpe, 2024 Sharpe), no 2025+ ranking",
                "claims": "No strategy can be called proven or live eligible on this run",
                "hypotheses": {"flow": "persistent demand by informed or constrained takers",
                    "flow_residual": "flow unexplained by recent price changes predicts delayed adjustment",
                    "flow_acceleration": "new demand differs from the asset's usual imbalance",
                    "momentum": "slow information diffusion and investor herding",
                    "trend": "risk-adjusted persistent directional positioning",
                    "breakout": "large moves continue after crossing past range",
                    "reversal": "temporary liquidity demand creates price overshoot",
                    "quiet_reversal": "reversal conditioned on reduced recent trading activity",
                    "funding": "crowded leveraged positions pay a carry premium"},
                "falsification": "negative net returns, unstable adjacent parameters, or cross-venue failure",
                "rule_sources": [
                    "https://www.hyrotrader.com/trading-rules/",
                    "https://www.hyrotrader.com/faq/rules/how-is-the-5-daily-drawdown-calculated/",
                    "https://www.hyrotrader.com/faq/evaluation-process/minimum-trading-days/",
                    "https://www.hyrotrader.com/faq/rules/what-are-the-risk-management-conditions-at-hyrotrader/",
                    "https://www.hyrotrader.com/faq/rules/are-there-any-other-rules-for-a-funded-account/"],
                "rule_conflict": "FAQ says static daily; September blog says trailing daily and 6% total in both. Run 10% static and 6% trailing sensitivity; dashboard contract needed before execution.",
                "execution_limitations": ["Binance prices/funding, Bybit-style assumed taker fees",
                    "no Bybit prices/funding, point-in-time market caps or full delisted universe",
                    "hourly OHLC adverse bounds are conservative, not synchronized tick marks",
                    "no fill capacity verification, no live capital, no registry promotion"]}
    protocol["sha256"] = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    write_json(out / "protocol.json", protocol)
    print(f"Protocol frozen: {len(cfgs)} candidates; loading hourly+funding data", flush=True)
    p = load_panel(Path("data/historical/binance_um"), cutoff)
    write_json(out / "dataset_audit.json", p.audit)
    results, row_map = [], {}
    for i, cfg in enumerate(cfgs):
        result, rows = evaluate(p, cfg)
        results.append(result)
        row_map[cfg.id] = rows
        print(f"{i+1}/{len(cfgs)} {cfg.id}: train={result['train'].get('sharpe',0):.2f}, "
              f"2024={result['validation'].get('sharpe',0):.2f}", flush=True)
    results.sort(key=lambda r: -r["selection_score"])
    write_json(out / "screen.json", {"protocol_sha256": protocol["sha256"], "rows": results})
    lo, hi = segments(p)["test_reused"]
    detailed = []
    # Frozen selection: top three by training/validation score, one per family, plus the original flow candidate.
    selected = []
    for r in results:
        if r["config"]["family"] not in {a["config"]["family"] for a in selected}:
            selected.append(r)
        if len(selected) == 3:
            break
    original = next(r for r in results if r["id"] == "flow_7d_r7_liquid20")
    if original not in selected:
        selected.append(original)
    for result in selected:
        cfg = next(c for c in cfgs if c.id == result["id"])
        rows = row_map[cfg.id]
        stress = [r for r in rows if lo <= r.signal_day < hi]
        result["stress_test"] = statistics([r.pnl - r.fee_notional * .0005 for r in stress])
        result["by_year"] = {}
        for year in range(2022, 2027):
            subset = [r for r in rows if iso(p.day0 + r.signal_day + 1).startswith(str(year))]
            result["by_year"][str(year)] = statistics([r.pnl for r in subset])
        result["scale_half_test"] = statistics([r.pnl * .5 for r in stress])
        write_json(out / f"{cfg.id}_daily.json", {"rows": [asdict(r) for r in rows]})
        if not args.skip_replay:
            replay = {}
            # Monthly starts on the frozen weekly calendar; cases overlap and are not independent.
            for scale in (.5, 1.0):
                cases = {"faq_static10": [], "strict_trailing6": []}
                first_start = 150 + ((lo - 150 + 6) // 7) * 7
                for start in range(first_start, hi - 360 + 1, 28):
                    trace = hourly_trace(p, cfg, start, start + 360)
                    for name, total, trailing in (("faq_static10", .10, False), ("strict_trailing6", .06, True)):
                        first = phase(trace, scale=scale, total_limit=total, trailing_daily=trailing)
                        second = {"status": "NOT_REACHED"}
                        if first["status"] == "NUMERICAL_PASS":
                            # Verification begins after the qualifying UTC day; no reused PnL or open positions.
                            first_day = trace[0]["hour"] // 24
                            next_signal = first_day + first["days"] - p.day0 - 1
                            next_signal = 150 + ((next_signal - 150 + 6) // 7) * 7
                            second_trace = hourly_trace(p, cfg, next_signal, start + 360)
                            second = phase(second_trace, target=.05, scale=scale, total_limit=total, trailing_daily=trailing)
                        cases[name].append({"start_signal": iso(p.day0 + start), "challenge": first,
                                            "verification": second,
                                            "two_phase_numeric_pass": second["status"] == "NUMERICAL_PASS"})
                replay[str(scale)] = cases
            result["conditional_historical_replay"] = replay
        detailed.append(result)
        print(f"Detailed replay finished: {cfg.id}", flush=True)
    write_json(out / "final.json", {"protocol": protocol, "audit": p.audit,
        "selected_without_test_ranking": detailed,
        "statistical_gates_passed": sum(r["train_validation_gate"] for r in results),
        "proven_strategies": 0, "note": "Replay counts are overlapping historical cases, not a forecast pass probability."})
    print("Artifacts saved to " + str(out.resolve()), flush=True)


if __name__ == "__main__":
    main()
