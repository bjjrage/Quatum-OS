from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")
from src.research.hyro_edge import Candidate, iso, load_panel, weights, write_json
from src.research.hyro_minute import load_minutes, run


def main():
    out = Path("data/research/hyro_2026_10_04")
    protocol = {"candidates": ["flow_7d_r7_liquid20", "flow_residual_7d_r7_liquid20"],
                "gross_initial": .5, "baseline": "no stop", "overlay": "8% price stop per leg; 1.5% initial-capital UTC-day circuit; no reopening until weekly rebalance",
                "period": "2026-04-05 execution to 2026-10-03 00:59 UTC",
                "schedule": "same fixed seven-day calendar as the screened model, signal Saturday, execution Sunday 01:00 UTC",
                "coverage_amendment": "Some selected symbols only have minute data from 2026-04-01. The October-start run failed on a missing first entry before producing results. An April-1 coverage anchor changed the weekly calendar; preserve that as sensitivity only, and align canonical replay with the frozen original calendar.",
                "new_tests": 4, "role": "risk falsification, no new selection, no claim of significance",
                "fill": "leg stop or opening gap plus costs; portfolio liquidation at adverse minute extremes",
                "cutoff": "exclude current UTC day"}
    protocol["sha256"] = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    write_json(out / "minute_protocol.json", protocol)
    cutoff = int(datetime(2026, 10, 4, tzinfo=timezone.utc).timestamp() * 1000)
    root = Path("data/historical/binance_um")
    p = load_panel(root, cutoff)
    write_json(out / "dataset_audit.json", p.audit)
    start = int(datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp() // 86400) - p.day0
    start = 150 + ((start - 150 + 6) // 7) * 7
    stop = p.n - 2
    cfgs = [Candidate(fam, 7, 7) for fam in ("flow", "flow_residual")]
    needed = set()
    for cfg in cfgs:
        for d in range(start, stop, 7):
            needed.update(weights(p, d, cfg))
    first = (p.day0 + start + 1) * 1440 + 60
    last = (p.day0 + stop + 1) * 1440 + 60
    m = load_minutes(root / "klines_1m", sorted(needed), first, last)
    result = []
    for cfg in cfgs:
        for protected in (False, True):
            label = cfg.id + ("_protected" if protected else "_baseline")
            print("Minute execution test: " + label, flush=True)
            r = run(p, m, cfg, start, stop, leg_stop=.08 if protected else None,
                    daily_stop=.015 if protected else None)
            write_json(out / (label + "_minute.json"), r)
            result.append({k: v for k, v in r.items() if k not in ("daily", "trades", "hourly_checkpoints")})
            print(label + " " + str(r["statistics"]), flush=True)
    write_json(out / "minute_summary.json", {"protocol": protocol, "results": result})


if __name__ == "__main__":
    main()
