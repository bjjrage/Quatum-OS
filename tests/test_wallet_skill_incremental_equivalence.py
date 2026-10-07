"""Snapshot + incremental catch-up must end in the same wallet state as a full historical rebuild."""
import random

import pyarrow as pa
import pyarrow.parquet as pq

from src.paper.pump_wallet_skill_v1 import WalletSkillPaper

T0 = 1_791_000_000


def _trades(n, seed=3, start=T0):
    r = random.Random(seed)
    rows, vs = [], {}
    for i in range(n):
        m = f"M{r.randrange(40)}"
        vs[m] = vs.get(m, 30_000_000_000) * (1 + r.uniform(-0.05, 0.08))
        rows.append({"slot": i, "ts_chain_s": start + i * 30, "mint": m, "user": f"W{r.randrange(25)}",
                     "is_buy": r.random() < 0.6, "virtual_sol_reserves": int(vs[m]),
                     "virtual_token_reserves": 1_000_000_000_000_000, "signature": f"s{i}",
                     "sol_amount": 1, "token_amount": 1})
    return rows


def _write(base, rows, name):
    d = base / "pumpfun" / "table=pumpfun_trades"
    d.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), d / f"{name}.parquet")


def _state(p):
    return (p.skill.to_dict()["stats"], sorted(map(tuple, p.skill.to_dict()["pending"])), p.buyers)


def test_snapshot_plus_catchup_equals_full_rebuild(tmp_path, monkeypatch):
    import src.paper.pump_wallet_skill_v1 as mod
    monkeypatch.setattr(mod.time, "time", lambda: T0 + 5000 * 30 + 10)        # "now" just after the last trade
    rows = _trades(5000)
    raw = tmp_path / "raw"
    _write(raw, rows[:3000], "a")

    first = WalletSkillPaper(root=tmp_path / "paperA")
    first.bootstrap(raw)                                    # no snapshot: full history
    first.save(T0 + 3000 * 30, snapshot=True)

    _write(raw, rows[3000:], "b")                            # more history arrives while it was down
    resumed = WalletSkillPaper(root=tmp_path / "paperA")    # restores the snapshot
    assert resumed.snapshot_cutoff is not None
    n_inc = resumed.bootstrap(raw)                           # only after the cutoff (+ overlap)
    assert n_inc < 2100

    full = WalletSkillPaper(root=tmp_path / "paperB")
    assert full.bootstrap(raw) == 5000
    assert _state(resumed) == _state(full)
