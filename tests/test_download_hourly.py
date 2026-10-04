import pyarrow.parquet as pq

from src.data.binance_history import download_hourly, hourly_path

H = 3_600_000


class Resp:
    def __init__(self, code, data):
        self.status_code, self._d = code, data

    def json(self):
        return self._d

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeClient:
    def __init__(self, n_hours, first_ms):
        self.n, self.first, self.calls = n_hours, first_ms, 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        if params["symbol"] == "NOPEUSDT":
            return Resp(400, {"code": -1121})
        t = max(params["startTime"], self.first)
        rows = []
        while len(rows) < params["limit"] and t < self.first + self.n * H:
            rows.append([t, "1", "2", "0.5", "1.5", "10", t + H - 1, "15", 7, "6", "9", "0"])
            t += H
        return Resp(200, rows)


def test_paginates_and_writes_closed_candles(tmp_path):
    first = 1_000 * H
    now = first + 4000 * H + H // 2              # last candle still open -> dropped
    c = FakeClient(4001, first)
    prog = download_hourly(c, tmp_path, ["AAAUSDT", "NOPEUSDT"], days=400, now_ms=now)
    assert prog.downloaded == 1 and prog.missing == 1 and prog.failed == 0
    t = pq.read_table(hourly_path(tmp_path, "AAAUSDT"))
    assert t.num_rows == 4000 and c.calls >= 3
    assert t.column("taker_buy_volume").to_pylist()[0] == 6.0
