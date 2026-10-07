import pyarrow as pa

from src.collectors.funder_tracker import FunderTracker, find_funding
from src.common.types import SCHEMAS

C, M, X = "Creator1111111111111111111111111111111111111", "Mother111111111111111111111111111111111111111", "Other1111"


def tx(*ins, inner=(), err=None):
    return {"meta": {"err": err, "innerInstructions": [{"instructions": list(inner)}]},
            "transaction": {"message": {"instructions": list(ins)}}}


def sysix(kind, **info):
    return {"program": "system", "parsed": {"type": kind, "info": info}}


def test_find_funding_variants():
    assert find_funding(tx(sysix("transfer", source=M, destination=C, lamports=2_000_000_000)), C) == (M, 2_000_000_000)
    assert find_funding(tx(sysix("createAccount", source=M, newAccount=C, lamports=5)), C) == (M, 5)
    assert find_funding(tx(inner=[sysix("transfer", source=M, destination=C, lamports=7)]), C) == (M, 7)
    two = tx(sysix("transfer", source=X, destination=C, lamports=1), sysix("transfer", source=M, destination=C, lamports=9))
    assert find_funding(two, C) == (M, 9)                                   # biggest inflow wins
    assert find_funding(tx(sysix("transfer", source=C, destination=M, lamports=9)), C) is None   # outgoing
    assert find_funding(tx(sysix("transfer", source=M, destination=C, lamports=9), err={"x": 1}), C) is None
    assert find_funding(tx({"program": "spl-token", "parsed": {"type": "transfer", "info": {}}}), C) is None
    assert find_funding(None, C) is None


class Act:
    def __init__(self, buyers):
        self.buyers = buyers

    def stats(self, mint, now):
        return {"unique_buyers_5m": self.buyers.get(mint, 0)}


def test_select_only_tokens_with_traction():
    f = FunderTracker(None, Act({"hot": 30, "cold": 2}), min_buyers=15, check_after_s=180, give_up_after_s=900)
    f.on_create({"mint": "hot", "creator": C}, 0)
    f.on_create({"mint": "cold", "creator": "C2"}, 0)
    f.on_create({"mint": "nocreator"}, 0)
    assert f.select(100) == 0 and len(f.pending) == 2                       # too early
    assert f.select(200) == 1 and list(f.queue) == [("hot", C)] and "cold" in f.pending
    f.select(1000)
    assert not f.pending                                                    # cold token given up


class Resp:
    def __init__(self, payload):
        self.status, self.payload = 200, payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def json(self, content_type=None):
        return self.payload


class Http:
    def __init__(self):
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append(json["method"])
        if json["method"] == "getSignaturesForAddress":
            return Resp({"result": [{"signature": "new", "blockTime": 30}, {"signature": "mid", "blockTime": 20},
                                    {"signature": "old", "blockTime": 10}]})
        sig = json["params"][0]
        result = tx(sysix("transfer", source=M, destination=C, lamports=3)) if sig == "old" else tx()
        return Resp({"result": result})


async def test_resolve_reads_oldest_first_caches_and_matches_schema():
    http = Http()
    f = FunderTracker(None, Act({}), http=http, max_rpm=1000)
    row = await f.resolve("mint1", C)
    assert (row["funder"], row["lamports"], row["funding_signature"], row["funding_block_time"]) == (M, 3, "old", 10)
    assert http.calls == ["getSignaturesForAddress", "getTransaction"] and row["reached_oldest"] is True
    again = await f.resolve("mint2", C)
    assert again["funder"] == M and again["cached"] is True and len(http.calls) == 2      # no extra RPC
    assert pa.Table.from_pylist([row, again], schema=SCHEMAS["creator_funding"]).num_rows == 2
    assert set(row) == set(SCHEMAS["creator_funding"].names)


async def test_rate_limited_lookup_is_retried_and_error_type_is_counted(monkeypatch):
    import asyncio
    from src.collectors import funder_tracker as ft

    calls = {"n": 0}

    class LimitedThenOk(Http):
        def post(self, url, json=None, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                class R(Resp):
                    def __init__(self):
                        self.status, self.payload = 429, {}
                return R()
            return super().post(url, json=json, timeout=timeout)

    class Sink:
        rows = []

        async def append(self, v, t, r):
            Sink.rows.append(r)

    sleeps = []

    async def fake_sleep(s):
        sleeps.append(s)
        if len(sleeps) > 3:
            raise asyncio.CancelledError

    f = FunderTracker(Sink(), Act({}), rpc_url="https://mainnet.helius-rpc.com/?api-key=x", max_rpm=1000)
    f.queue.append(("mint1", C))
    monkeypatch.setattr(ft.asyncio, "sleep", fake_sleep)

    class Session:
        async def __aenter__(self):
            return LimitedThenOk()

        async def __aexit__(self, *a):
            return False

    import aiohttp
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: Session())
    await f.run()
    assert f.error_types == {"RPC 429": 1} and 15 in sleeps and f.using_helius
    assert Sink.rows and Sink.rows[0]["funder"] == M                       # retried and resolved
