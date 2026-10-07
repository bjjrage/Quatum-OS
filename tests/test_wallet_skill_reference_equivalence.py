"""Deterministic production-vs-reference wallet maturity replay."""

from collections import defaultdict

from src.paper.pump_wallet_skill_v1 import EVAL_HORIZON_S, WalletSkillBook


def test_synthetic_replay_matches_independent_full_scan_reference():
    # 5,000 ordered observations, with repeated wallet/token marks and both
    # winning and losing windows. The oracle deliberately scans its full pending
    # map; the production book is compared after every identical input event.
    events = []
    for i in range(5_000):
        mint_index = i // 50
        user_index = i % 50
        events.append((f"W{user_index}", f"M{mint_index}", True,
                       1.0 if user_index == 0 else (2.1 if user_index < 4 else 0.9),
                       1_000.0 + i * 10.0))

    production = WalletSkillBook()
    reference_stats = defaultdict(lambda: {"matured": 0, "wins": 0})
    reference_pending = {}

    def reference_mature(now):
        due = [key for key, obs in reference_pending.items() if obs["matures_at"] <= now]
        for key in due:
            obs = reference_pending.pop(key)
            row = reference_stats[key[0]]
            row["matured"] += 1
            row["wins"] += int(obs["peak_multiple"] >= 2.0)

    for wallet, mint, is_buy, price, now in events:
        production.on_trade(wallet, mint, is_buy, price, now)
        reference_mature(now)
        for (pending_wallet, pending_mint), obs in reference_pending.items():
            if pending_mint == mint:
                obs["peak_multiple"] = max(obs["peak_multiple"], price / obs["entry_price"])
        key = (wallet, mint)
        if is_buy and price > 0 and key not in reference_pending:
            reference_pending[key] = {
                "entry_ts": now,
                "entry_price": price,
                "matures_at": now + EVAL_HORIZON_S,
                "peak_multiple": 1.0,
            }

    final_time = events[-1][-1] + EVAL_HORIZON_S
    production.mature(final_time)
    reference_mature(final_time)
    assert production.pending == reference_pending
    assert production.stats == dict(reference_stats)
    assert {w: production.is_good(w) for w in reference_stats} == {
        w: row["matured"] >= 5 and row["wins"] / row["matured"] >= 0.35
        for w, row in reference_stats.items()
    }
