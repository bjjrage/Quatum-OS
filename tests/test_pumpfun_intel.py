import random

from src.research.pumpfun_intel import (co_buy_groups, run_intel, skill_persistence, smart_money_signal,
                                        wallet_profiles, wallet_token_pnl)


def synth(n_tokens=400, seed=1, skilled_edge=True):
    """Tokens con curva: los 'hábiles' compran temprano en tokens que suben; el grupo G compra junto."""
    rnd = random.Random(seed)
    trades, slot = [], 0
    skilled = [f"S{i}" for i in range(8)]
    group = [f"G{i}" for i in range(4)]
    for k in range(n_tokens):
        m = f"M{k}"
        t0 = k * 60
        good = rnd.random() < 0.3
        px = 1e-8
        for step in range(60):
            slot += 1
            ts = t0 + step * 5
            px *= (1.06 if good else 0.97) * rnd.uniform(0.97, 1.03)
            if step in (1, 2) and good and skilled_edge:
                u = rnd.choice(skilled)
            elif step == 3 and k % 5 == 0:
                for g in group:
                    trades.append((ts, slot, m, g, True, 0.5, 0.5 / px, px))
                continue
            else:
                u = f"R{rnd.randrange(3000)}"
            buy = rnd.random() < 0.6
            trades.append((ts, slot, m, u, buy, 0.2, 0.2 / px, px))
        for u in skilled:                                   # venden al final
            trades.append((t0 + 299, slot, m, u, False, 0.0, 0.0, px))
    trades.sort(key=lambda r: (r[1], r[0]))
    return trades


def test_profiles_and_pnl():
    tr = synth()
    prof = wallet_profiles(wallet_token_pnl(tr))
    assert prof["S0"]["tokens"] >= 3 and prof["S0"]["pnl_sol"] > 0


def test_groups_found():
    g = co_buy_groups(synth())
    assert g["grupos"] >= 1
    assert any({"G0", "G1", "G2", "G3"} <= set(mem) for mem in g["miembros"].values())


def test_skill_persists_when_planted_and_signal_beats_control():
    tr = synth(n_tokens=600)
    split = tr[0][0] + (tr[-1][0] - tr[0][0]) // 2
    p = skill_persistence(tr, split)
    assert p["status"] == "OK"
    s = smart_money_signal(tr, split, k_wallets=1, horizons=(120,))
    assert s["status"] == "OK"
    h = s["por_horizonte_s"]["120"]
    assert h["comparaciones"] >= 10 and h["diferencia_media"] > 0


def test_run_intel_without_data(tmp_path):
    assert run_intel(tmp_path)["status"] == "POCOS_DATOS"
