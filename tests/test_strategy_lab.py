import random
from array import array

from src.research.strategy_lab import (BTC, ETH, COST_ROUNDTRIP, Hourly, _sigma_1h, build_configs, fam_ts, run_lab_on)


def make_grid(n=24 * 200, k=24, seed=1, momentum=0.0):
    rnd = random.Random(seed)
    g = Hourly(n=n, h0=0)
    for j in range(k):
        s = BTC if j == 0 else ETH if j == 1 else f"S{j}USDT"
        c = [100.0]
        prev = 0.0
        for _ in range(n - 1):
            r = rnd.gauss(0, 0.01) + momentum * prev
            prev = r
            c.append(c[-1] * (1 + r))
        o = [c[0]] + c[:-1]
        g.o[s], g.c[s] = array("d", o), array("d", c)
    g.sig = {s: _sigma_1h(c) for s, c in g.c.items()}
    return g


def test_random_walk_nothing_passes():
    g = make_grid()
    cfgs = [c for c in build_configs() if c[0] in ("movimiento_fuerte", "ranking")]
    res = run_lab_on(g, cfgs)
    assert res["n_ideas"] == len(cfgs) and res["pasan"] == []


def test_planted_momentum_is_found_on_train_and_holdout():
    g = make_grid(n=24 * 300, momentum=0.35, seed=3)        # each hour's move partly repeats in the next hour
    cfgs = [c for c in build_configs() if c[0] == "movimiento_fuerte" and "seguir" in c[1] and "3 h" in c[1]]
    res = run_lab_on(g, cfgs)
    best = res["todas"][0]
    assert best["entrenamiento"]["t_stat"] > 3 and best["prueba_final"]["exceso_neto_pct"] != 0


def test_costs_are_charged():
    assert abs(COST_ROUNDTRIP - 0.0012) < 1e-12


def test_no_lookahead_signal_uses_only_past():
    g = make_grid(n=24 * 30)
    t1 = fam_ts(g, 3, 1.5, 6, "mom", False)
    # change the future of the series after hour 400: trades before 400 must be unchanged
    for s in g.c:
        for i in range(400, g.n):
            g.c[s][i] *= 1.5
    g.sig = {s: _sigma_1h(c) for s, c in g.c.items()}
    t2 = fam_ts(g, 3, 1.5, 6, "mom", False)
    assert [t for t in t1 if t[0] < 390] == [t for t in t2 if t[0] < 390]
