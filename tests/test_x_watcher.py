import asyncio
import json

from src.collectors.x_watcher import (TokenActivity, XWatcher, estimate_cost, parse_json_answer, response_text)


class _Sink:
    def __init__(self):
        self.rows = []

    async def append(self, venue, table, row):
        self.rows.append((venue, table, row))


class _Resp:
    def __init__(self, status, payload):
        self.status, self._p = status, payload

    async def json(self, content_type=None):
        return self._p

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _Http:
    def __init__(self, payload, status=200):
        self.payload, self.status, self.bodies = payload, status, []

    def post(self, url, json=None, headers=None, timeout=None):
        self.bodies.append((json, headers))
        return _Resp(self.status, self.payload)


def _activity():
    a = TokenActivity()
    a.on_create({"mint": "MINT1", "symbol": "PEPEL", "name": "Pepe Lindo"}, 1000.0)
    for i in range(30):
        a.on_trade({"mint": "MINT1", "user": f"W{i}", "sol_amount": 300_000_000, "is_buy": True}, 1000.0 + i)
    a.on_trade({"mint": "MINT2", "user": "X", "sol_amount": 10**9, "is_buy": True}, 1000.0)
    return a


def test_candidates_need_many_buyers_and_net_flow():
    a = _activity()
    assert a.candidates(1040.0, min_buyers=25, min_net_sol=5) == ["MINT1"]    # 30 compradores, 9 SOL netos
    assert a.candidates(1040.0) == []                         # filtro por defecto más exigente (50 / 10 SOL)
    a.on_trade({"mint": "MINT3", "user": "Z", "sol_amount": 10**9, "is_buy": True}, 1000.0)
    assert "MINT3" not in a.candidates(1040.0, min_buyers=1, min_net_sol=0)   # no lo vimos nacer
    a.asked.add("MINT1")
    assert a.candidates(1040.0, min_buyers=25, min_net_sol=5) == []          # una sola consulta por token
    a.asked.clear()
    assert a.candidates(1000.0 + 4000, min_buyers=25, min_net_sol=5) == []   # ventana de 5 min vencida


def test_ask_stores_row_and_tracks_cost_without_leaking_key():
    answer = {"posts_found": 7, "earliest_post_utc": "2026-10-05T01:00:00Z",
              "accounts": [{"handle": "@a", "followers": 120000}, {"handle": "@b", "followers": 300}],
              "has_large_account": True, "coordinated_shilling": False, "summary": "x"}
    payload = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "ok " + json.dumps(answer)}]}],
               "usage": {"input_tokens": 1000, "output_tokens": 200,
                         "server_side_tool_usage_details": {"x_posts_fetched": 20, "x_users_fetched": 10}}}
    sink, http = _Sink(), _Http(payload)
    xw = XWatcher(sink, _activity(), "xai-SECRET", daily_usd=5.0, http=http)
    row = asyncio.run(xw.ask("MINT1", 1040.0))
    assert row["posts_found"] == 7 and row["max_followers"] == 120000 and row["has_large_account"]
    assert abs(row["cost_usd"] - (20 * 0.005 + 10 * 0.01 + 0.002 + 0.002)) < 1e-9
    assert sink.rows[0][1] == "x_mentions" and "SECRET" not in json.dumps(sink.rows[0][2])
    body, headers = http.bodies[0]
    assert body["tools"] == [{"type": "x_search"}] and "MINT1" in body["input"][0]["content"]
    assert body["max_tool_calls"] == 1


def test_budget_blocks_after_limit_and_paces_per_hour():
    xw = XWatcher(_Sink(), _activity(), "k", daily_usd=0.1)
    xw.spent_today = 0.2
    assert not xw._budget_ok()
    xw2 = XWatcher(_Sink(), _activity(), "k", daily_usd=24.0)
    assert xw2._budget_ok()
    xw2.spent_today = xw2.spent_hour = 5.0        # gastó en una hora mucho más que 1/24 del día
    assert not xw2._budget_ok()


def test_parsing_helpers():
    assert parse_json_answer('bla {"posts_found": 2} bla')["posts_found"] == 2
    assert parse_json_answer("nada") == {}
    assert response_text({"output_text": "hola"}) == "hola"
    assert estimate_cost({}) == 0.0
    assert abs(estimate_cost({"usage": {"cost_in_usd_ticks": 1485123000}}) - 0.1485123) < 1e-12
