import random

from src.research.exam_sim import RULES, run_phase, simulate


def test_phase_rules():
    it = iter([0.03] * 10)
    assert run_phase(it, RULES["HyroTrader_1F"][0], 1.0, 100) == ("PASA", 5)        # mínimo 5 días
    assert run_phase(iter([-0.05]), RULES["HyroTrader_1F"][0], 1.0, 100)[0] == "QUEMA"   # pérdida diaria
    assert run_phase(iter([0.09, 0.001, 0.001, 0.001, 0.001, 0.001] + [0.0] * 60), RULES["HyroTrader_1F"][0], 1.0, 50)[0] == "TIEMPO"  # regla 40%


def test_more_edge_passes_more():
    rnd = random.Random(1)
    good = [rnd.gauss(0.002, 0.01) for _ in range(800)]
    zero = [x - 0.002 for x in good]
    a = simulate(good, RULES["HyroTrader_2F"], 1.0, n=400)
    b = simulate(zero, RULES["HyroTrader_2F"], 1.0, n=400)
    assert a["pasa_pct"] > b["pasa_pct"]
