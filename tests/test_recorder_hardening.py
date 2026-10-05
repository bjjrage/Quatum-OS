import asyncio
import importlib.util
import json
from pathlib import Path

from src.collectors.binance_recorder import BinanceRecorder
from src.collectors.polymarket_recorder import PolymarketRecorder

ROOT = Path(__file__).resolve().parents[1]


def _load_run_recorder():
    spec = importlib.util.spec_from_file_location("run_recorder", ROOT / "scripts" / "run_recorder.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_supervisor_restart_rules():
    rr = _load_run_recorder()
    assert rr.should_restart(1, False, 0)            # se cayó -> reiniciar
    assert not rr.should_restart(0, False, 0)        # salió bien (apagado pedido) -> no
    assert not rr.should_restart(1, True, 0)         # pidieron apagarlo -> no
    assert not rr.should_restart(1, False, 12)       # bucle de caídas -> no


def test_rest_fallback_rows_match_bbo_schema():
    data = [{"symbol": "BTCUSDT", "bidPrice": "60000.1", "bidQty": "2", "askPrice": "60000.2", "askQty": "1", "time": 1700000000000},
            {"symbol": "DOGEUSDT", "bidPrice": "0.1", "bidQty": "5", "askPrice": "0.1001", "askQty": "5", "time": 1700000000000},
            {"symbol": "ETHUSDT", "bidPrice": "0", "bidQty": "1", "askPrice": "1", "askQty": "1", "time": 1}]
    rows = BinanceRecorder.rest_book_rows(data, {"BTCUSDT", "ETHUSDT"}, 1700000000500000000, 1)
    assert len(rows) == 1 and rows[0]["symbol"] == "BTCUSDT"
    r = rows[0]
    assert r["ts_exchange_ns"] == 1700000000000 * 1_000_000 and r["bid_price"] < r["ask_price"]
    assert set(r) == {"ts_exchange_ns", "ts_received_utc_ns", "ts_received_mono_ns", "observed_event_age_ns", "venue",
                      "symbol", "bid_price", "bid_size", "ask_price", "ask_size", "spread"}


class _Resp:
    def __init__(self, status, payload):
        self.status, self._p = status, payload

    async def json(self):
        return self._p

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _Session:
    def __init__(self, known):
        self.known, self.calls = known, []

    def get(self, url, params=None, timeout=None):
        slug = (params or {}).get("slug")
        self.calls.append(slug)
        if slug in self.known:
            return _Resp(200, [self.known[slug]])
        return _Resp(200, [])


class _Sink:
    def __init__(self):
        self.rows = []

    async def append(self, venue, table, row):
        self.rows.append((table, row))


def test_fast_updown_discovery_finds_short_markets():
    t = 1_791_000_000 - 1_791_000_000 % 900
    slug = f"btc-updown-15m-{t}"
    item = {"id": "m1", "conditionId": "c1", "question": "Bitcoin Up or Down - October 4, 3:15PM-3:30PM ET",
            "endDate": "2026-10-04T19:30:00Z", "clobTokenIds": json.dumps(["UP1", "DN1"]),
            "outcomes": json.dumps(["Up", "Down"]), "active": True, "closed": False}
    rec = PolymarketRecorder.__new__(PolymarketRecorder)
    rec.sink = _Sink()
    rec.active_asset_ids, rec._subscribed_asset_ids = set(), set()
    rec.market_metadata_cache, rec._fast_tokens, rec._fast_seen_slugs = {}, {}, set()
    rec._ws = None
    rec._session = _Session({slug: item})
    n = asyncio.run(rec._fast_updown_once(now_s=t + 10))
    assert n == 2 and {"UP1", "DN1"} <= rec.active_asset_ids
    assert rec._fast_tokens["UP1"] == t + 900
    assert any(tb == "polymarket_metadata_history" for tb, _ in rec.sink.rows)
    assert len(rec._session.calls) == 3 * 2 * 3            # 3 criptos x (5m,15m) x 3 ventanas
    rec._session.calls.clear()
    asyncio.run(rec._fast_updown_once(now_s=t + 10))       # el slug ya visto no se vuelve a pedir
    assert slug not in rec._session.calls
