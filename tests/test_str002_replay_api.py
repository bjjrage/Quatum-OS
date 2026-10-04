import time
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.services import replay_runner as rr

c = TestClient(app)


def test_status_endpoint_available():
    assert c.get("/api/backtests/str002/status").json()["state"] in ("IDLE", "DONE", "RUNNING", "ERROR")


def test_non_local_cannot_start():
    assert TestClient(app, client=("203.0.113.9", 1)).post("/api/backtests/str002/run").status_code == 403


def test_run_end_to_end_on_small_recorded_data(tmp_path, monkeypatch):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from config.settings import settings
    now = time.time_ns()
    rows = {"ts_received_utc_ns": [], "symbol": [], "side": [], "price": [], "size": []}
    for sym, px in (("BTCUSDT", 100.0), ("ETHUSDT", 50.0), ("ALTUSDT", 10.0)):
        for m in range(60):
            rows["ts_received_utc_ns"].append(now - (60 - m) * 60 * 10**9 + 5 * 10**9)
            rows["symbol"].append(sym); rows["side"].append("BUY"); rows["price"].append(px); rows["size"].append(1.0)
    d = tmp_path / "raw" / "binance_perp" / "table=trade_ticks" / "date=x"
    d.mkdir(parents=True)
    pq.write_table(pa.table(rows), d / "p.parquet")
    monkeypatch.setattr(settings.storage, "base_data_path", tmp_path / "raw")
    monkeypatch.setattr(settings.binance, "initial_calibration_sample_v0", ["BTCUSDT", "ETHUSDT", "ALTUSDT"])
    monkeypatch.setattr(rr, "OUT", tmp_path / "out.json")
    assert c.post("/api/backtests/str002/run?days=1").json()["ok"] is True
    for _ in range(100):
        s = c.get("/api/backtests/str002/status").json()
        if s["state"] in ("DONE", "ERROR"):
            break
        time.sleep(0.1)
    assert s["state"] == "DONE", s
    assert set(s["result"]["variants"]) == {"A_actual", "B_marcelo", "C_intermedia", "D_marcelo_5m"}
    assert set(s["result"]["baseline"]) == {"B_marcelo", "D_marcelo_5m"}


def test_status_survives_nan_and_infinity_in_results():
    import json
    r = rr._slim({"variants": {"A": {"summary": {"profit_factor": float("inf"), "naive_t_stat": float("nan")}, "trades": [1]}},
                  "exit_comparison": {}})
    json.dumps(r, allow_nan=False)
    assert r["variants"]["A"]["summary"]["profit_factor"] is None and "trades" not in r["variants"]["A"]
