import random

from src.paper.pump_paper import ACCOUNTS, FEE, PUMP_FEE_MODEL, GroupGraph, PumpAccount, PumpPaper, buy_tokens, sell_sol
from src.research.niches import NicheHeat, meme_keys, sector_map

VS0, VT0 = 30 * 10**9, 1_073_000_000 * 10**6          # reservas iniciales típicas de pump.fun



def test_pump_fee_assumption_is_versioned_and_marked_unverified():
    assert FEE == 0.0125  # current paper assumption remains unchanged
    assert PUMP_FEE_MODEL["status"] == "ECONOMICS_UNVERIFIED"
    assert PUMP_FEE_MODEL["version"] == "PUMPFUN_FEE_SCHEDULE_2026-05"
    assert PUMP_FEE_MODEL["source_url"].startswith("https://pump.fun/")

def test_curve_round_trip_loses_only_fees():
    tok = buy_tokens(1.0, VS0, VT0)
    back = sell_sol(tok, VS0 + int(1.0 * 0.9875 * 1e9), VT0 - int(tok))
    assert 0.97 < back < 0.976                          # ~1,25% por lado


def _ev(mint, user, buy, sol, slot, vs, vt, tok=1e12):
    return {"mint": mint, "user": user, "is_buy": buy, "sol_amount": int(sol * 1e9), "token_amount": int(tok),
            "slot": slot, "virtual_sol_reserves": vs, "virtual_token_reserves": vt}


def test_group_graph_links_only_repeated_coordinated_wallets():
    g = GroupGraph()
    for i, m in enumerate(["m1", "m2", "m3"]):
        g.on_buy(m, "A", 100 * i)
        g.on_buy(m, "B", 100 * i + 1)
        g.on_buy(m, "C", 100 * i + 50)                  # C compra lo mismo pero lejos en el tiempo
    assert g.is_member("A") and "B" in g.linked("A")
    assert not g.is_member("C")


def test_group_graph_ignores_bots_that_buy_everything():
    g = GroupGraph()
    for i in range(200):                                # el bot compra 200 tokens
        g.on_buy(f"x{i}", "BOT", 1000 + 10 * i)
    for i, m in enumerate(["m1", "m2", "m3"]):
        g.on_buy(m, "BOT", 100 * i)
        g.on_buy(m, "D", 100 * i + 1)
    assert not g.is_member("BOT")


def _paper(tmp_path):
    p = PumpPaper(root=tmp_path, rnd=random.Random(0))
    # historia: A y B compran juntos 3 tokens viejos -> grupo
    for i, m in enumerate(["o1", "o2", "o3"]):
        p.groups.on_buy(m, "A", 10 * i)
        p.groups.on_buy(m, "B", 10 * i + 1)
    return p


def test_group_signal_enters_and_exits_when_group_sells(tmp_path):
    p = _paper(tmp_path)
    now = 1_000_000.0
    p.on_create({"mint": "NEW", "creator": "DEV", "user": "DEV", "symbol": "CAT", "name": "cat coin"}, now)
    p.on_create({"mint": "OTHER", "creator": "DEV2", "user": "DEV2", "symbol": "ZZ", "name": "zz"}, now)
    vs, vt = VS0, VT0
    p.on_trade(_ev("OTHER", "R", True, 0.5, 5, vs, vt), now + 5)
    p.on_trade(_ev("NEW", "A", True, 1.0, 10, vs + 10**9, vt - 3 * 10**13, tok=3e13), now + 10)
    p.on_trade(_ev("NEW", "B", True, 1.0, 11, vs + 2 * 10**9, vt - 6 * 10**13, tok=3e13), now + 11)
    assert "NEW" in p.signaled
    assert "NEW" in p.accounts["grupo"].pending_buy and "NEW" in p.accounts["grupo_aguantar"].pending_buy
    assert "OTHER" in p.accounts["azar"].pending_buy                # control: otro token joven al mismo tiempo
    assert list(p.x_queue) == ["NEW"]
    # la operación siguiente llena la compra (llegamos tarde)
    p.on_trade(_ev("NEW", "Z", True, 0.5, 12, vs + 25 * 10**8, vt - 7 * 10**13), now + 12)
    assert "NEW" in p.accounts["grupo"].s["posiciones"]
    # el grupo vende la mitad de lo que tenía -> marcar venta, se llena en la siguiente
    p.on_trade(_ev("NEW", "A", False, 1.2, 20, vs + 15 * 10**8, vt - 4 * 10**13, tok=3e13), now + 20)
    assert "NEW" in p.accounts["grupo"].pending_sell
    assert "NEW" not in p.accounts["grupo_aguantar"].pending_sell       # la de salida fija no vende por eso
    p.on_trade(_ev("NEW", "Q", False, 0.1, 21, vs + 14 * 10**8, vt - 38 * 10**12), now + 21)
    assert "NEW" not in p.accounts["grupo"].s["posiciones"]
    assert p.accounts["grupo"].s["n_cerradas"] == 1


def test_no_signal_when_crowd_already_arrived(tmp_path):
    p = _paper(tmp_path)
    now = 2_000_000.0
    p.on_create({"mint": "LATE", "creator": "DEV", "user": "DEV", "symbol": "X", "name": "x"}, now)
    for i in range(45):
        p.on_trade(_ev("LATE", f"u{i}", True, 0.2, i, VS0, VT0), now + i)
    p.on_trade(_ev("LATE", "A", True, 1.0, 100, VS0, VT0), now + 100)
    p.on_trade(_ev("LATE", "B", True, 1.0, 101, VS0, VT0), now + 101)
    assert "LATE" not in p.signaled                     # llegó la gente: el detector de grupo no entra tarde


def test_account_stop_loss_and_time_exit(tmp_path):
    a = PumpAccount("t", ACCOUNTS["azar"], tmp_path)
    a.request_buy("M", 0.0)
    a.on_trade("M", VS0, VT0, 1.0)
    assert "M" in a.s["posiciones"]
    a.on_trade("M", VS0 // 3, VT0 * 3, 2.0)             # precio / 9 -> stop
    assert "M" in a.pending_sell
    a.on_trade("M", VS0 // 3, VT0 * 3, 3.0)
    assert a.s["n_cerradas"] == 1 and a.s["resultado_sol"] < -0.1
    a.request_buy("N", 10.0)
    a.tick(10.0 + 20, {"N": [VS0, VT0, 10.0]})          # sin operación siguiente: se llena por tiempo
    assert "N" in a.s["posiciones"]
    a.tick(10.0 + 20 + 7200, {"N": [VS0, VT0, 10.0]})   # 2 h sin llegar al 2x
    a.tick(10.0 + 20 + 7200 + 20, {"N": [VS0, VT0, 10.0]})
    assert "N" not in a.s["posiciones"]


def test_ladder_takes_half_at_2x_then_trails(tmp_path):
    a = PumpAccount("t", ACCOUNTS["grupo"], tmp_path)
    size = a.entry_size()
    assert abs(size - 0.5) < 1e-9                        # 5% de 10 SOL
    a.request_buy("M", 0.0)
    a.on_trade("M", VS0, VT0, 1.0)
    k = VS0 * VT0
    vs = int(VS0 * 1.6)                                  # precio x2,56 -> vale > 2x
    a.on_trade("M", vs, k // vs, 2.0)
    assert a.pending_sell["M"][2] == 0.5
    a.on_trade("M", vs, k // vs, 3.0)                    # se vende la mitad
    pos = a.s["posiciones"]["M"]
    assert pos["tomado"] and a.s["tomas_2x"] == 1 and pos["cobrado"] > pos["costo"]   # ya recuperó lo puesto
    vs2 = int(VS0 * 2.2)                                 # sigue subiendo: nuevo máximo
    a.on_trade("M", vs2, k // vs2, 4.0)
    assert "M" not in a.pending_sell
    vs3 = int(VS0 * 1.7)                                 # cae > 35% desde el máximo -> vende el resto
    a.on_trade("M", vs3, k // vs3, 5.0)
    a.on_trade("M", vs3, k // vs3, 6.0)
    assert "M" not in a.s["posiciones"]
    c = a.s["cerradas"][-1]
    assert c["tomo_2x"] and c["multiplo"] > 1.5


def test_hold10_does_not_take_at_2x(tmp_path):
    a = PumpAccount("t", ACCOUNTS["grupo_aguantar"], tmp_path)
    a.request_buy("M", 0.0)
    a.on_trade("M", VS0, VT0, 1.0)
    k = VS0 * VT0
    vs = int(VS0 * 1.6)
    a.on_trade("M", vs, k // vs, 2.0)
    assert "M" not in a.pending_sell


def test_compounding_size_grows_with_equity(tmp_path):
    a = PumpAccount("t", ACCOUNTS["nicho"], tmp_path)
    a.s["cash"] = 20.0
    assert abs(a.entry_size() - 1.0) < 1e-9


def test_meme_keys_and_niche_heat():
    assert "cat:gatos" in meme_keys("Kitty Meow", "KMEOW")
    assert "w:troll" in meme_keys("Troll Face", "TROLL")
    h = NicheHeat()
    base = 100_000.0
    for i in range(10):
        h.register(f"t{i}", "troll", "TRL")
    for k in range(60):                                  # 5 h tranquilas
        h.add_trade("t0", 0.5, base + k * 300)
    t = base + 60 * 300
    for i in range(10):                                  # de golpe 10 tokens del nicho con volumen
        h.add_trade(f"t{i}", 5.0, t + i)
    assert h.is_hot("w:troll", t + 20)
    assert "w:troll" in h.hot_keys_of("t3", t + 20)


def test_niche_signal_buys_young_token_in_hot_niche(tmp_path):
    p = PumpPaper(root=tmp_path, rnd=random.Random(0))
    now = 500_000.0
    for i in range(8):
        p.on_create({"mint": f"T{i}", "creator": "D", "user": "D", "symbol": "TRL", "name": "troll"}, now)
        p.on_trade(_ev(f"T{i}", f"u{i}", True, 5.0, i, VS0, VT0), now + i)
    assert any(f"T{i}" in p.accounts["nicho"].pending_buy for i in range(8))


def test_sector_map():
    m = sector_map(["FETUSDT", "DOGEUSDT", "ARBUSDT", "XYZUSDT"])
    assert m == {"FETUSDT": "ia", "DOGEUSDT": "memes", "ARBUSDT": "l2"}


def test_warmup_from_parquet(tmp_path):
    import time
    import pyarrow as pa
    import pyarrow.parquet as pq
    now = int(time.time())
    d = tmp_path / "raw" / "pumpfun" / "table=pumpfun_trades" / "x"
    d.mkdir(parents=True)
    rows = []
    for i, m in enumerate(["o1", "o2", "o3"]):
        for k, u in enumerate(["A", "B"]):
            rows.append({"signature": f"s{i}{k}", "slot": 100 * i + k, "ts_chain_s": now - 3600 + i, "mint": m,
                         "user": u, "is_buy": True, "sol_amount": 10**9, "token_amount": 10**12,
                         "virtual_sol_reserves": VS0, "virtual_token_reserves": VT0})
    rows.append(dict(rows[0]))                           # duplicado (reconexión): se descarta
    pq.write_table(pa.Table.from_pylist(rows), d / "part.parquet")
    c = tmp_path / "raw" / "pumpfun" / "table=pumpfun_creates" / "x"
    c.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist([{"mint": "o1", "creator": "D", "user": "D", "ts_chain_s": now - 3700,
                                          "symbol": "CAT", "name": "cat"}]), c / "part.parquet")
    p = PumpPaper(root=tmp_path / "paper")
    assert p.warmup(tmp_path / "raw") == 6
    assert p.groups.is_member("A") and p.warm
    assert p.meta["o1"]["symbol"] == "CAT"


def test_niche_strategies_run_on_synthetic_panel():
    import math
    import random as _r
    from src.research.portfolio_lab import Daily, backtest, niche_strategies
    syms = ["FETUSDT", "WLDUSDT", "DOGEUSDT", "1000PEPEUSDT", "ARBUSDT", "OPUSDT", "AXSUSDT", "SANDUSDT",
            "SOLUSDT", "AVAXUSDT", "BTCUSDT", "LINKUSDT", "PYTHUSDT"]
    n = 260
    rnd = _r.Random(1)
    g = Daily(days=list(range(n)))
    for s in syms:
        p, xs = 100.0, []
        for _ in range(n):
            p *= math.exp(rnd.gauss(0, 0.03))
            xs.append(p)
        g.sig[s], g.px[s] = xs, xs
        g.taker[s] = [0.5 + rnd.gauss(0, 0.01) for _ in range(n)]
        g.qvol[s] = [1e6 * (1 + rnd.random()) for _ in range(n)]
        g.fund[s] = [0.0] * n
    for _, desc, fn, reb in niche_strategies():
        rows = backtest(g, fn, reb)
        assert rows, desc
        assert any(t > 0 for _, _, t in rows), desc          # alguna vez arma cartera


# ---------------------------------------------------------------- billeteras con habilidad
def _feed_token(p, mint, buyers, t0, final_mult, vs=VS0, vt=VT0, slot0=1000):
    """Crea el token, hace compras de `buyers` y después lleva el precio a `final_mult` x el de la compra N°10."""
    p.on_create({"mint": mint, "creator": "DEV", "user": "DEV", "symbol": mint, "name": mint}, t0)
    for i, u in enumerate(buyers):
        p.on_trade(_ev(mint, u, True, 0.1, slot0 + i, vs, vt), t0 + 1 + i)
    return t0 + len(buyers) + 1


def test_skillbook_labels_only_after_two_hours_and_flags_good_wallets():
    from src.paper.pump_paper import SKILL, SkillBook
    sb = SkillBook()
    t = 1000.0
    for k in range(6):                                    # 6 tokens: W acierta en 3 (50%), las demás no
        m = f"T{k}"
        sb.on_trade(m, "DEV", True, 1.0, t, t)            # visto al nacer
        for i in range(SKILL["k_buyers"] - 1):                # la compra del creador es la N°1
            g = sb.on_trade(m, "W" if i == 0 else f"X{k}_{i}", True, 1.0, t + 1 + i, t)
        assert g == 0
        sb.on_trade(m, "Z", True, 2.5 if k < 3 else 0.4, t + 30, t)     # 2,5x o -60%
        assert sb.stats.get("W", [0, 0])[0] == 0           # todavía no se acredita
        t += 5
    sb.expire(t + 3 * 3600)
    assert sb.stats["W"] == [6, 3] and sb.is_good("W")
    assert sb.labelled == 6 and sb.hits == 3


def test_skillbook_ignores_tokens_seen_late():
    from src.paper.pump_paper import SkillBook
    sb = SkillBook()
    assert sb.on_trade("L", "A", True, 1.0, 5000.0, 1000.0) is None      # nació hace 4000 s
    assert "L" not in sb.track


def test_good_wallets_trigger_entry_and_control(tmp_path):
    from src.paper.pump_paper import SKILL
    p = PumpPaper(root=tmp_path, rnd=random.Random(0), legacy=False)
    assert "grupo" not in p.accounts and "billeteras" in p.accounts
    for w in ("G1", "G2"):
        p.skill.stats[w] = [10, 5]                         # 50% de aciertos en 10 tokens
    p.warm = True
    now = 2_000_000.0
    p.on_create({"mint": "OTHER", "creator": "D2", "user": "D2", "symbol": "ZZ", "name": "zz"}, now)
    p.on_trade(_ev("OTHER", "R", True, 0.5, 5, VS0, VT0), now + 1)
    buyers = ["G1", "G2"] + [f"U{i}" for i in range(SKILL["k_buyers"] - 2)]
    _feed_token(p, "NEW", buyers, now + 2, 1.0)
    assert "NEW" in p.accounts["billeteras"].pending_buy
    assert p.accounts["billeteras"].pending_buy["NEW"]["size"] == 0.5          # tamaño fijo
    assert "NEW" in p.accounts["billeteras_2x"].pending_buy                     # misma señal, salida completa al 2x
    assert p.accounts["billeteras_2x"].rules["take_frac"] == 1.0
    assert "OTHER" in p.accounts["billeteras_azar"].pending_buy


def test_one_good_wallet_is_not_enough(tmp_path):
    from src.paper.pump_paper import SKILL
    p = PumpPaper(root=tmp_path, rnd=random.Random(0), legacy=False)
    p.skill.stats["G1"] = [10, 5]
    p.warm = True
    now = 3_000_000.0
    _feed_token(p, "NEW", ["G1"] + [f"U{i}" for i in range(SKILL["k_buyers"] - 1)], now, 1.0)
    assert "NEW" not in p.accounts["billeteras"].pending_buy


def _write_trades(base, rows):
    import json
    import duckdb
    d = base / "pumpfun" / "table=pumpfun_trades"
    d.mkdir(parents=True, exist_ok=True)
    js = d / "rows.json"
    js.write_text(json.dumps(rows), encoding="utf-8")
    duckdb.connect().execute(f"COPY (SELECT * FROM read_json_auto('{js.as_posix()}')) TO '{(d / 'part-0.parquet').as_posix()}' (FORMAT PARQUET)")
    js.unlink()


def test_warmup_follows_positions_left_open_when_os_was_off(tmp_path):
    """Una posición abierta antes de apagar el OS se sigue con lo grabado después de su entrada (mismas reglas)."""
    import time
    root = tmp_path / "paper"
    t0 = time.time() - 3 * 3600
    p = PumpPaper(root=root, legacy=False)
    a = p.accounts["billeteras"]
    assert a.request_buy("MINTX", t0)
    a._fill_buy("MINTX", VS0, VT0, t0)
    a.save()
    rows = []
    for i, f in enumerate([0.9, 0.7, 0.5, 0.4, 0.3]):          # el precio cae: debe saltar el stop de -50%
        vs = int(VS0 * f ** 0.5)
        rows.append({"slot": 10 + i, "ts_chain_s": int(t0 + 60 * (i + 1)), "signature": f"s{i}", "mint": "MINTX",
                     "user": f"U{i}", "is_buy": False, "sol_amount": 10**8, "token_amount": 10**9,
                     "virtual_sol_reserves": vs, "virtual_token_reserves": int(VS0 * VT0 / vs)})
    _write_trades(tmp_path / "raw", rows)
    p2 = PumpPaper(root=root, legacy=False)
    assert "MINTX" in p2.accounts["billeteras"].s["posiciones"]
    p2.warmup(tmp_path / "raw", hours=48)
    s = p2.accounts["billeteras"].s
    assert "MINTX" not in s["posiciones"]
    assert s["n_cerradas"] == 1 and s["cerradas"][-1]["motivo"].startswith("stop")
    assert s["cerradas"][-1]["multiplo"] < 0.6

def test_warmup_ignores_rows_with_corrupt_chain_time(tmp_path):
    """Hay filas grabadas con ts_chain_s basura (años en el futuro); en Windows hacen fallar las fechas (OSError 22)."""
    import time
    root = tmp_path / "paper"
    t0 = time.time() - 3 * 3600
    p = PumpPaper(root=root, legacy=False)
    a = p.accounts["billeteras"]
    assert a.request_buy("MINTY", t0)
    a._fill_buy("MINTY", VS0, VT0, t0)
    a.save()
    rows = [{"slot": 11, "ts_chain_s": int(t0 + 60), "signature": "a", "mint": "MINTY", "user": "U1", "is_buy": True,
             "sol_amount": 10**8, "token_amount": 10**9, "virtual_sol_reserves": VS0, "virtual_token_reserves": VT0},
            {"slot": 12, "ts_chain_s": 10**12, "signature": "b", "mint": "MINTY", "user": "U2", "is_buy": False,
             "sol_amount": 10**8, "token_amount": 10**9, "virtual_sol_reserves": VS0 // 4, "virtual_token_reserves": VT0 * 4}]
    _write_trades(tmp_path / "raw", rows)
    p2 = PumpPaper(root=root, legacy=False)
    assert p2.warmup(tmp_path / "raw", hours=48) == 1
    assert p2._last_data_ts < time.time() + 600
