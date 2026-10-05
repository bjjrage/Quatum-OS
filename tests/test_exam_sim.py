import random

from src.research.exam_sim import RULES, run_phase, simulate


def test_phase_rules_are_model_only():
    it = iter([0.03] * 10)
    assert run_phase(it, RULES["HyroTrader_1F"][0], 1.0, 100) == ("TARGET_REACHED_MODEL_ONLY", 5)
    assert run_phase(iter([-0.05]), RULES["HyroTrader_1F"][0], 1.0, 100)[0] == "RISK_LIMIT_REACHED_MODEL_ONLY"
    assert run_phase(iter([0.09, 0.001] + [0.0] * 60), RULES["HyroTrader_1F"][0], 1.0, 50)[0] == "HORIZON_END_MODEL_ONLY"


def test_more_edge_improves_model_only_target_projection():
    rnd = random.Random(1)
    good = [rnd.gauss(0.002, 0.01) for _ in range(800)]
    zero = [x - 0.002 for x in good]
    a = simulate(good, RULES["HyroTrader_2F"], 1.0, n=400)
    b = simulate(zero, RULES["HyroTrader_2F"], 1.0, n=400)
    assert a["target_hit_pct_model_only"] > b["target_hit_pct_model_only"]
    assert a["rules_status"] == "RULES_UNVERIFIED"
    assert "target_hit_pct" not in a
    assert "pasa_pct" not in a
