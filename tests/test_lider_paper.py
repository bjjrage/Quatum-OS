import asyncio
from datetime import datetime, timezone

from src.paper import lider_paper as lp

DAY = 86400_000
NOW = int(datetime(2026, 10, 6, 0, 30, tzinfo=timezone.utc).timestamp() * 1000)


def klines(closes, qv=1000.0, last_qv=None, now_ms=NOW):
    """Velas diarias completas que terminan antes de now_ms."""
    n = len(closes)
    out = []
    for i, c in enumerate(closes):
        close_t = (now_ms // DAY) * DAY - (n - 1 - i) * DAY - 1
        v = last_qv if (last_qv and i >= n - 3) else qv
        out.append([close_t - DAY + 1, c, c, c, c, 1, close_t, v])
    return out


def test_kline_stats_leader_and_laggard():
    lead = klines([10.0] * 37 + [10, 12, 14.0], last_qv=5000.0)
    s = lp.kline_stats(lead, NOW)
    assert abs(s["r3"] - 0.4) < 1e-9 and s["vs"] > 4
    flat = lp.kline_stats(klines([10.0] * 40), NOW)
    assert abs(flat["r3"]) < 1e-9 and abs(flat["vs"] - 1) < 1e-9
    assert lp.kline_stats(klines([10.0] * 10), NOW) is None


def test_kline_stats_ignores_incomplete_candle():
    kl = klines([10.0] * 40)
    kl[-1][6] = NOW + 1000                      # vela de hoy sin cerrar
    s = lp.kline_stats(kl, NOW)
    assert s is not None
    assert s["r3"] == 0.0
    assert abs(s["vs"] - 1.0) < 1e-9
    assert lp.kline_stats(kl[:34], NOW) is None


def test_find_events():
    stats = {
        "FETUSDT": {"r3": 0.5, "vs": 3.0, "qv30": 100, "close": 1},
        "RENDERUSDT": {"r3": 0.0, "vs": 1.0, "qv30": 90, "close": 1},
        "TAOUSDT": {"r3": -0.05, "vs": 1.0, "qv30": 80, "close": 1},
        "WLDUSDT": {"r3": 0.20, "vs": 1.0, "qv30": 70, "close": 1},   # subió: ya no es rezagada
        "ARKMUSDT": {"r3": 0.02, "vs": 1.0, "qv30": 60, "close": 1},
        "BTCUSDT": {"r3": 0.01, "vs": 1.0, "qv30": 1000, "close": 1},
    }
    from src.research.niches import sector_map
    ev = lp.find_events(stats, sector_map(stats))
    assert len(ev) == 1 and ev[0]["segmento"] == "ia"
    assert ev[0]["lideres"][0]["symbol"] == "FETUSDT"
    assert [l["symbol"] for l in ev[0]["rezagadas"]] == ["RENDERUSDT", "TAOUSDT", "ARKMUSDT"]


def test_find_events_needs_volume_and_members():
    stats = {s: {"r3": 0.5 if s == "FETUSDT" else 0.0, "vs": 1.0, "qv30": 1, "close": 1}
             for s in ["FETUSDT", "RENDERUSDT", "TAOUSDT", "WLDUSDT"]}
    from src.research.niches import sector_map
    assert lp.find_events(stats, sector_map(stats)) == []           # sin salto de volumen
    stats["FETUSDT"]["vs"] = 3.0
    del stats["WLDUSDT"]
    assert lp.find_events(stats, sector_map(stats)) == []           # menos de 4 miembros


def test_x_ok():
    assert lp.x_ok({"x": {"x_status": "X_POSITIVE", "posts_found": 7, "narrative_link": True}})
    assert not lp.x_ok({"x": {"x_status": "X_POSITIVE", "posts_found": 4, "narrative_link": True}})
    assert not lp.x_ok({"x": {"x_status": "X_POSITIVE", "posts_found": 9, "narrative_link": False}})
    assert not lp.x_ok({"x": {"x_status": "API_ERROR", "posts_found": 9, "narrative_link": True}})
    assert not lp.x_ok({"x": None}) and not lp.x_ok({})


def test_lotbook_long_and_short(tmp_path):
    b = lp.LotBook(tmp_path / "a")
    long_ = b.open_lot("e1", "AAAUSDT", 1000, 1, 10.0, NOW)
    short = b.open_lot("e1", "BBBUSDT", 1000, -1, 20.0, NOW)
    assert b.s["posiciones"]["AAAUSDT"] > 0 > b.s["posiciones"]["BBBUSDT"]
    assert abs(b.equity({"AAAUSDT": 10.0, "BBBUSDT": 20.0}) - 10000) < 5          # solo costos
    r1 = b.close_lot(long_, 11.0, NOW + 7 * DAY, 0.02)
    r2 = b.close_lot(short, 18.0, NOW + 7 * DAY, 0.02)
    assert r1["ret_neto"] < 0.10 and r1["ret_neto"] > 0.09
    assert abs(r1["exceso_vs_mercado"] - 0.08) < 1e-9
    assert r2["ret_neto"] > 0.09 and abs(r2["exceso_vs_mercado"] - (-1 * (-0.10 - 0.02))) < 1e-9
    assert b.s["posiciones"] == {} and b.s["lotes"] == []
    b2 = lp.LotBook(tmp_path / "a")                                                # persiste
    assert len(b2.s["cerrados"]) == 2


def _prices(symbols, v=10.0):
    return {s: v for s in symbols}


def test_process_end_to_end_with_injected_x(tmp_path):
    names = ["FET", "RENDER", "TAO", "WLD", "ARKM", "BTC", "ETH", "SOL", "DOGE", "ARB"]
    syms = [n + "USDT" for n in names]
    data = {}
    for n in syms:
        if n == "FETUSDT":
            data[n] = klines([10.0] * 37 + [10, 12, 14.0], last_qv=5000.0)
        elif n in ("WLDUSDT",):
            data[n] = klines([10.0] * 37 + [10, 11.5, 12.0])
        else:
            data[n] = klines([10.0] * 40)

    async def get(path, **kw):
        if "klines" in path:
            return data[kw["symbol"]]
        return [{"symbol": s, "price": "10"} for s in syms]

    async def ask(ev, lag, day):
        if lag["symbol"] in ("RENDERUSDT", "TAOUSDT"):
            return {"posts_found": 12, "narrative_link": True}
        return {"posts_found": 1, "narrative_link": False}

    lider = lp.LiderPaper(tmp_path, api_key=None)
    assert lider.check_due(NOW)
    made = asyncio.run(lider.process(None, get, syms, NOW, ask=ask))
    assert len(made) == 1
    ev = made[0]
    assert ev["abrio"]["lider_x"] == ["RENDERUSDT", "TAOUSDT"]
    assert set(ev["abrio"]["lider_sin_x"]) == {"RENDERUSDT", "TAOUSDT", "ARKMUSDT"}
    assert len(ev["abrio"]["lider_azar"]) == 3
    assert not set(ev["abrio"]["lider_azar"]) & {"FETUSDT", "RENDERUSDT", "TAOUSDT", "ARKMUSDT", "WLDUSDT"}
    assert ev["abrio"]["lider_corto"] == ["FETUSDT"]
    assert not lider.check_due(NOW)                                     # ya procesado hoy
    # segundo intento al día siguiente: cooldown de 7 días
    again = asyncio.run(lider.process(None, get, syms, NOW + DAY, ask=ask))
    assert again == []
    # salida a los 7 días con precios +10% en rezagadas
    px = {s: 10.0 for s in syms}
    px["RENDERUSDT"] = 11.0
    assert lider.exits(px, NOW + 6 * DAY) == 0
    n = lider.exits(px, NOW + 7 * DAY + 1)
    assert n == 2 + 3 + 3 + 1
    cl = lider.books["lider_x"].s["cerrados"]
    assert len(cl) == 2 and max(c["ret_bruto"] for c in cl) > 0.099
    # reinicio: el estado se recarga
    lider2 = lp.LiderPaper(tmp_path, api_key=None)
    assert lider2.ev["segmento_ultimo"]["ia"] and len(lider2.ev["eventos"]) == 1


def test_no_x_key_means_no_filter_trades(tmp_path):
    lider = lp.LiderPaper(tmp_path, api_key=None)
    ev = {"id": "x", "lideres": [{"symbol": "AUSDT", "r3": .5, "vs": 3}],
          "rezagadas": [{"symbol": "BUSDT", "r3": 0, "vs": 1, "x": None}], "segmento": "ia"}
    r = asyncio.run(lider._ask_x(None, ev, ev["rezagadas"][0], "2026-10-06"))
    assert r["x_status"] == "NO_KEY"
    done = lider.open_event(ev, {"AUSDT": 1.0, "BUSDT": 1.0, "CUSDT": 1.0}, {"CUSDT": {}}, NOW)
    assert done["lider_x"] == [] and done["lider_sin_x"] == ["BUSDT"]


def test_x_budget(tmp_path):
    lider = lp.LiderPaper(tmp_path, api_key="k", daily_x_usd=1.0)
    lider.x_ledger.seed_legacy("2026-10-06", "leader_paper_legacy", 1.2)
    assert not lider._x_budget_ok("2026-10-06") and lider._x_budget_ok("2026-10-07")


def test_daily_checkpoint_retries_after_failure_and_deduplicates_completion(tmp_path):
    lider = lp.LiderPaper(tmp_path, api_key=None, events_file=tmp_path / "events.json")
    calls = {"n": 0}

    async def get(path, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("temporary network error")
        if "klines" in path:
            return klines([10.0] * 40)
        return [{"symbol": "AAAUSDT", "price": "10"}]

    try:
        asyncio.run(lider.process(None, get, ["AAAUSDT"], NOW))
    except RuntimeError:
        pass
    else:
        raise AssertionError("transient data failure should leave a retryable checkpoint")
    day = datetime.fromtimestamp(NOW / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    assert lider.ev["checkpoints"][day]["status"] == "FAILED_RETRYABLE"
    assert lider.check_due(NOW)

    asyncio.run(lider.process(None, get, ["AAAUSDT"], NOW))
    assert lider.ev["checkpoints"][day]["status"] == "COMPLETED"
    assert lider.ev["ultimo_chequeo_dia"] == day
    completed_calls = calls["n"]
    assert asyncio.run(lider.process(None, get, ["AAAUSDT"], NOW)) == []
    assert calls["n"] == completed_calls
    restarted = lp.LiderPaper(tmp_path, api_key=None, events_file=tmp_path / "events.json")
    assert restarted.ev["checkpoints"][day]["status"] == "COMPLETED"
