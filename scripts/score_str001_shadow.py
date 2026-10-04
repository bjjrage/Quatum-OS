"""Settle the STR-001 shadow log against resolved Polymarket outcomes and print the verdict.

    uv run python scripts/score_str001_shadow.py --dir data/shadow
"""
import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.shadow.str001_shadow import ShadowConfig, score_shadow_log  # noqa: E402


def _outcome(market: dict):
    """1 if YES resolved true, 0 if false, None while unresolved."""
    if not market.get("closed"):
        return None
    try:
        prices = [float(x) for x in json.loads(market.get("outcomePrices") or "[]")]
    except ValueError:
        return None
    if len(prices) == 2 and max(prices) >= 0.99:
        return 1 if prices[0] >= 0.99 else 0
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/shadow")
    a = ap.parse_args()
    records = []
    for f in sorted(Path(a.dir).glob("str001_shadow_*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            records.extend(json.loads(line) for line in fh if line.strip())
    ids = sorted({r["market_id"] for r in records if r.get("status") == "PRICED"})
    outcomes = {}
    with httpx.Client() as client:
        for mid in ids:
            r = client.get(f"https://gamma-api.polymarket.com/markets/{mid}", timeout=15.0)
            if r.status_code == 200:
                o = _outcome(r.json())
                if o is not None:
                    outcomes[mid] = o
    print(f"priced markets: {len(ids)}  resolved: {len(outcomes)}")
    print(json.dumps(score_shadow_log(records, outcomes, ShadowConfig()), indent=2))


if __name__ == "__main__":
    main()
