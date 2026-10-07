import math
import random
from array import array

from src.research.recorder_studies import model_prob, study_poly_leads_core


def _setup(lead_s):
    random.seed(1)
    n, s0 = 12000, 1_000_000
    px = [100000.0]
    for _ in range(n - 1):
        px.append(px[-1] * math.exp(random.gauss(0, 0.0002)))
    b, a = array("d", [p - 0.5 for p in px]), array("d", [p + 0.5 for p in px])
    q = {"BTCUSDT": (b, a)}
    mk, quotes = [], {}
    for k in range(6):
        st = s0 + 2000 + k * 1500
        en = st + 900
        tok = f"T{k}"
        mk.append({"up_token": tok, "asset": "BTCUSDT", "start_s": st, "end_s": en, "minutes": 15})
        qt = {}
        for t in range(st, en, 5):
            ref = t + lead_s if t + lead_s < en else t
            p = model_prob(b, a, s0, st, ref, en)
            if p == p:
                qt[t] = (max(0.01, p - 0.01), min(0.99, p + 0.01))
        quotes[tok] = qt
    return mk, quotes, s0, q


def test_detects_polymarket_that_knows_the_future():
    r = study_poly_leads_core(*_setup(20))
    assert r["por_horizonte"]["15"]["t_cambio"] > 3


def test_no_lead_means_no_signal():
    r = study_poly_leads_core(*_setup(0))
    assert abs(r["por_horizonte"]["15"]["t_cambio"]) < 2.7
