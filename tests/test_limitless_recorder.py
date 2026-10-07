import json

import pyarrow as pa

from src.collectors.limitless_recorder import API, LimitlessRecorder, book_row, expiration_s, is_short_crypto, market_row
from src.common.types import SCHEMAS

NOW = 1_791_400_000.0


def mk(slug, title, exp_s, **kw):
    return {"slug": slug, "id": 7, "title": title, "expirationTimestamp": int(exp_s * 1000), "status": "FUNDED",
            "tradeType": "clob", "marketType": "single", "categories": ["Crypto"], "tags": [], **kw}


def test_expiration_and_selection():
    assert expiration_s({"expirationTimestamp": 1_791_400_000_000}) == 1_791_400_000
    assert expiration_s({"expirationTimestamp": 1_791_400_000}) == 1_791_400_000
    assert is_short_crypto(mk("btc-above", "$BTC above $100,000 on Oct 7, 14:00 UTC?", NOW + 3600), NOW, 26)
    assert not is_short_crypto(mk("btc-later", "BTC above 100k?", NOW + 40 * 3600), NOW, 26)      # too far
    assert not is_short_crypto(mk("btc-past", "BTC above 100k?", NOW - 10), NOW, 26)              # expired
    assert not is_short_crypto(mk("election", "Who wins the election?", NOW + 3600, categories=["Politics"]), NOW, 26)


def test_rows_match_schemas_and_book_is_sorted():
    m = market_row(mk("eth-above", "ETH above 3000?", NOW + 600), 5)
    assert m["expiration_ms"] == int((NOW + 600) * 1000) and json.loads(m["raw_json"])["slug"] == "eth-above"
    b = book_row("eth-above", {"bids": [{"price": 0.40, "size": 10}, {"price": 0.45, "size": 3}],
                               "asks": [{"price": "0.60", "size": "2"}, {"price": 0.52, "size": 8}, {"price": 0.5, "size": 0}],
                               "adjustedMidpoint": 0.485, "lastTradePrice": "0.47", "tokenId": "123"}, 9)
    assert (b["best_bid"], b["bid_size"], b["best_ask"], b["ask_size"]) == (0.45, 3, 0.52, 8)   # unsorted + zero-size dropped
    assert b["adjusted_mid"] == 0.485 and b["last_trade"] == 0.47 and json.loads(b["asks_json"])[0] == [0.52, 8.0]
    assert book_row("x", {"bids": [], "asks": []}, 1) is None
    for table, row in (("limitless_markets", m), ("limitless_book", b)):
        assert pa.Table.from_pylist([row], schema=SCHEMAS[table]).num_rows == 1 and set(row) == set(SCHEMAS[table].names)


class Resp:
    def __init__(self, status, payload):
        self.status, self.payload = status, payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self, content_type=None):
        return self.payload


class Http:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        if url == API + "/markets/active":
            return Resp(200, {"data": self.pages[params["page"] - 1] if params["page"] <= len(self.pages) else [],
                              "totalMarketsCount": 99})
        if url.endswith("/orderbook"):
            return Resp(200, {"bids": [{"price": 0.4, "size": 5}], "asks": [{"price": 0.6, "size": 5}], "tokenId": "1"})
        return Resp(404, {})


class Sink:
    def __init__(self):
        self.rows = []

    async def append(self, venue, table, row):
        self.rows.append((venue, table, row))


async def test_discover_paginates_tracks_short_crypto_and_records_books():
    page1 = [mk(f"btc-{i}", "BTC above 100k?", NOW + 1800) for i in range(25)]
    page2 = [mk("sports", "Team A wins?", NOW + 1800, categories=["Sports"]), mk("eth-1", "ETH up?", NOW + 900)]
    sink = Sink()
    rec = LimitlessRecorder(sink, http=Http([page1, page2]), max_rps=1000)
    assert await rec.discover_once(NOW) == 27
    assert len(rec.tracked) == 26 and "sports" not in rec.tracked
    assert await rec.discover_once(NOW) == 0                     # already seen: no duplicate market rows
    assert await rec.books_once() == 26
    assert {t for _, t, _ in sink.rows} == {"limitless_markets", "limitless_book"}
    await rec.discover_once(NOW + 3600)                          # all expired -> stop tracking
    assert not rec.tracked
