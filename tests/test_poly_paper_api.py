import json

from fastapi.testclient import TestClient


def test_poly_paper_endpoint_reads_events(tmp_path, monkeypatch):
    import src.paper.poly_updown_paper as m
    monkeypatch.setattr(m, "OUT_DIR", tmp_path)
    ev = [{"ts": 1000, "kind": "signal", "slug": "btc-updown-5m-1"},
          {"ts": 1002, "kind": "fill", "slug": "btc-updown-5m-1", "side": "up", "price": 0.4, "usd": 20, "shares": 50,
           "minutes": 5, "asset": "BTCUSDT", "edge": 0.08, "t": 1002},
          {"ts": 1300, "kind": "settle", "slug": "btc-updown-5m-1", "pnl": 29.0},
          {"ts": 1400, "kind": "resolve", "slug": "btc-updown-5m-1", "pnl_official": 29.0}]
    (tmp_path / "events.jsonl").write_text("\n".join(json.dumps(e) for e in ev) + "\nnot json\n", encoding="utf-8")
    (tmp_path / "state.json").write_text(json.dumps({"config": {"threshold": 0.05}, "abiertas": []}), encoding="utf-8")
    from apps.api.main import app
    d = TestClient(app).get("/api/research/poly_paper").json()
    assert d["llenadas"] == 1 and d["resueltas"] == 1 and d["pnl_oficial_usd"] == 29.0 and d["corriendo"] is True
    assert d["ultimas"][0]["pnl_oficial"] == 29.0 and d["criterio"]["cumple"] is False and d["config"]["threshold"] == 0.05
