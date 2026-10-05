from src.paper.flujo_paper import PaperBook, book_metrics, taker_score, target_weights


def _k(day, vol, tb):
    o = day * 86400_000
    return [o, "1", "1", "1", "1", str(vol), o + 86400_000 - 1, "0", 0, str(tb), "0", "0"]


def test_taker_score_uses_only_completed_days():
    kl = [_k(d, 100, 60) for d in range(15)] + [_k(15, 100, 0)]      # el día 15 está en curso
    now = 15 * 86400_000 + 1000
    assert abs(taker_score(kl, now) - 0.6) < 1e-12
    assert taker_score(kl[:5], now) is None                          # pocos días


def test_target_weights_long_top_short_bottom():
    sc = {f"S{i}": i / 100 for i in range(20)}
    w = target_weights(sc)
    assert w["S19"] > 0 and w["S0"] < 0 and len(w) == 8
    assert abs(sum(abs(v) for v in w.values()) - 1.0) < 1e-12 and abs(sum(w.values())) < 1e-12


def test_book_metrics():
    d = {"bids": [["99.9", "10"], ["99.0", "100"]], "asks": [["100.1", "5"], ["102", "100"]]}
    m = book_metrics(d)
    assert abs(m["mid"] - 100.0) < 1e-9 and m["bid_usd_05"] == 999.0 and m["ask_usd_05"] == 500.5
    assert m["imbalance_05"] > 0


def test_paper_book_rebalance_costs_funding_and_persistence(tmp_path):
    b = PaperBook(tmp_path, capital=10_000)
    px = {"A": 100.0, "B": 50.0}
    b.rebalance({"A": 0.5, "B": -0.5}, px, 1)
    assert b.s["posiciones"]["A"] > 0 and b.s["posiciones"]["B"] < 0
    eq0 = b.equity(px)
    assert 9_990 < eq0 < 10_000                       # pagó comisión + deslizamiento
    b.equity({"A": 110.0, "B": 50.0})
    assert b.equity({"A": 110.0, "B": 50.0}) > eq0    # el largo sube: gana
    assert b.equity({"A": 100.0, "B": 55.0}) < eq0    # el corto sube: pierde
    paid = b.apply_funding("B", 0.001, 50.0)          # corto con funding positivo: cobra
    assert paid < 0
    b.save()
    b2 = PaperBook(tmp_path)                          # se reinicia y no pierde nada
    assert b2.s["posiciones"] == b.s["posiciones"] and abs(b2.s["cash"] - b.s["cash"]) < 1e-9


def test_entry_prices_tracked_and_backfilled(tmp_path):
    from src.paper.flujo_paper import SLIP
    b = PaperBook(tmp_path, capital=10_000)
    px = {"A": 100.0, "B": 50.0}
    b.rebalance({"A": 0.5, "B": -0.5}, px, 1)
    e = b.entry_prices()
    assert abs(e["A"] - 100 * (1 + SLIP)) < 1e-9 and abs(e["B"] - 50 * (1 - SLIP)) < 1e-9
    b.s.pop("entradas")                                # estado viejo sin entradas: se reconstruye igual
    e2 = b.entry_prices()
    assert abs(e2["A"] - e["A"]) < 1e-6 and abs(e2["B"] - e["B"]) < 1e-6


def test_all_strategies_weights_and_due_rule():
    from src.paper.flujo_paper import compute_all_weights, is_due
    now = 40 * 86400_000 + 5 * 60_000
    kl, fund = {}, {}
    for i in range(20):
        sym = "BTCUSDT" if i == 0 else f"S{i}USDT"
        rows, px = [], 100.0
        for d in range(40):
            px *= 1 + (0.01 if d % 2 else -0.01) * (1 + i / 10)          # volatilidad distinta por cripto
            o = d * 86400_000
            rows.append([o, "1", "1", "1", str(px), "100", o + 86400_000 - 1, "0", 0, str(40 + i), "0", "0"])
        kl[sym] = rows
        fund[sym] = [{"fundingTime": now - k * 8 * 3600_000, "fundingRate": str(0.0001 * i)} for k in range(1, 22)]
    w = compute_all_weights(kl, fund, now)
    assert w["flujo_v1"]["S19USDT"] > 0                      # más compra agresiva -> comprado
    assert w["carry_funding"]["S19USDT"] < 0                 # funding más alto -> vendido
    assert w["baja_vol"]["S19USDT"] < 0 and w["baja_vol"]["S1USDT"] > 0
    assert abs(sum(abs(v) for v in w["combinada"].values()) - 1) < 1e-9
    assert set(w["btc_tendencia"]) <= {"BTCUSDT"}
    assert is_due(0, now, 7)
    assert not is_due(now - 86400_000, now, 7) and is_due(now - 7 * 86400_000, now, 7)
    assert not is_due(now - 7 * 86400_000, now + 3 * 3600_000, 7)        # fuera de la ventana 00:05-00:59


# ---------------------------------------------------------------- examen en paper
from src.paper.flujo_paper import EXAMS, exam_step, exam_view

DAY = 86400_000
T0 = 1_791_000_000_000 - (1_791_000_000_000 % DAY) + 3600_000      # 01:00 UTC de algún día


def _exam_book(tmp_path):
    b = PaperBook(tmp_path / "examen_2x", capital=10_000, leverage=2.0)
    exam_step(b, EXAMS["examen_2x"], {}, T0)                       # crea el examen
    b.rebalance({"AAA": 0.5, "BBB": -0.5}, {"AAA": 100.0, "BBB": 100.0}, T0, fee=0, slip=0)
    return b


def test_exam_burns_on_daily_loss(tmp_path):
    b = _exam_book(tmp_path)
    assert exam_step(b, EXAMS["examen_2x"], {"AAA": 100.0, "BBB": 100.0}, T0 + 60_000) is None
    # 2x: largo 10k en AAA; AAA -4.5% => -450 USD > 4% de 10k
    assert exam_step(b, EXAMS["examen_2x"], {"AAA": 95.5, "BBB": 100.0}, T0 + 120_000) == "QUEMO"
    assert b.s["posiciones"] == {} and b.s["examen"]["estado"] == "QUEMO"
    # mismo día no reinicia; al día siguiente 00:05 sí
    assert exam_step(b, EXAMS["examen_2x"], {}, T0 + 3600_000) is None
    assert exam_step(b, EXAMS["examen_2x"], {}, T0 - 3600_000 + DAY + 300_000) == "REINICIO"
    assert b.s["examen"]["intento"] == 2 and b.s["cash"] == 10_000 and b.s["ultimo_rebalanceo_ms"] == 0
    assert b.s["examen"]["historial"][0]["estado"] == "QUEMO"


def test_exam_passes_after_min_days_and_best_day_rule(tmp_path):
    b = _exam_book(tmp_path)
    r = EXAMS["examen_2x"]
    px = 100.0
    ev = None
    for d in range(10):                                            # +2,5%/día en AAA => +250 USD/día
        px *= 1.025
        ev = exam_step(b, r, {"AAA": px, "BBB": 100.0}, T0 + d * DAY + 60_000)
        if ev:
            break
    assert ev == "PASO"
    assert len(b.s["examen"]["dias_operados"]) >= 5
    v = exam_view(b, None)
    assert v["estado"] == "PASO" and v["intento"] == 1


def test_exam_view_margins(tmp_path):
    b = _exam_book(tmp_path)
    exam_step(b, EXAMS["examen_2x"], {"AAA": 99.0, "BBB": 100.0}, T0 + 60_000)
    v = exam_view(b, b.equity({"AAA": 99.0, "BBB": 100.0}))
    assert round(v["pnl_hoy_usd"]) == -100 and round(v["margen_hoy_usd"]) == 300
    assert round(v["margen_total_usd"]) == 500 and round(v["falta_para_pasar_usd"]) == 1100
