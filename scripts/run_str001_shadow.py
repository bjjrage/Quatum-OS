"""Run the STR-001 shadow runner (no orders, no keys, public endpoints only).

    uv run python scripts/run_str001_shadow.py            # loop forever, JSONL in data/shadow/
    uv run python scripts/run_str001_shadow.py --once     # one cycle and print a summary

Score it later with:  uv run python scripts/score_str001_shadow.py
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.shadow.str001_shadow import ShadowConfig, ShadowRunner  # noqa: E402


def _settle_resolved(trader, client) -> None:
    """Cash-settle paper positions whose Polymarket market has resolved (YES=1 / NO=0)."""
    import json as _json
    for mid in list(trader.open):
        try:
            r = client.get(f"https://gamma-api.polymarket.com/markets/{mid}", timeout=15.0)
            if r.status_code != 200 or not r.json().get("closed"):
                continue
            prices = [float(x) for x in _json.loads(r.json().get("outcomePrices") or "[]")]
            if len(prices) == 2 and max(prices) >= 0.99:
                trader.settle(mid, 1 if prices[0] >= 0.99 else 0)
        except Exception:
            continue


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--cycle-s", type=float, default=30.0)
    ap.add_argument("--out-dir", default="data/shadow")
    ap.add_argument("--paper", action="store_true", help="also route decisions through router+PaperBroker (data/paper)")
    a = ap.parse_args()
    runner = ShadowRunner(out_dir=Path(a.out_dir), cfg=ShadowConfig(), cycle_s=a.cycle_s)
    trader = None
    if a.paper:
        from src.shadow.str001_paper import Str001PaperTrader
        trader = Str001PaperTrader()
        _orig = runner.run_cycle

        def _cycle(client):
            recs = _orig(client)
            for r in recs:
                trader.on_decision(r)
            _settle_resolved(trader, client)
            print("paper:", trader.summary())
            return recs
        runner.run_cycle = _cycle
    with httpx.Client(headers={"User-Agent": "quant-os-shadow/1.0"}) as client:
        if a.once:
            recs = runner.run_cycle(client)
            print(f"mapped markets: {len(runner.mapped)}  rejected: {len(runner.rejected)}")
            print("reject reasons:", dict(Counter(r.reason for r in runner.rejected)))
            print("evaluations:", dict(Counter((r['status'], r.get('reason', r['action'])) for r in recs)))
            return
        runner.run_forever(client)


if __name__ == "__main__":
    main()
