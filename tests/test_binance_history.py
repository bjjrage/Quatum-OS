import hashlib
import io
import zipfile
from datetime import date

import pytest

from src.data import binance_history as bh

HEADER = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"


def _csv(start_ms, n, px=100.0, header=True):
    lines = [HEADER] if header else []
    for i in range(n):
        t = start_ms + i * 60000
        p = px * (1 + 0.0001 * (i % 7 - 3))
        lines.append(f"{t},{p},{p*1.001},{p*0.999},{p},10.0,{t+59999},1000.0,50,6.0,600.0,0")
    return "\n".join(lines) + "\n"


def _zip(name, text):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, text)
    return buf.getvalue()


class Resp:
    def __init__(self, status, content=b"", text="", js=None):
        self.status_code, self.content, self.text, self._js = status, content, text, js

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._js


class FakeClient:
    def __init__(self, files, bad_checksum=()):
        self.files, self.bad, self.calls = files, set(bad_checksum), []

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if url.endswith(".CHECKSUM"):
            z = self.files.get(url[:-9])
            if z is None:
                return Resp(404)
            h = "0" * 64 if url[:-9] in self.bad else hashlib.sha256(z).hexdigest()
            return Resp(200, text=f"{h}  file.zip\n")
        z = self.files.get(url)
        return Resp(200, content=z) if z is not None else Resp(404)


def test_parse_csv_with_and_without_header():
    for header in (True, False):
        t = bh.parse_kline_csv(_csv(0, 5, header=header), "BTCUSDT")
        assert t.num_rows == 5 and t.column("taker_buy_volume")[0].as_py() == 6.0


def test_plan_covers_full_months_and_current_month_days():
    plan = bh.plan_files(["BTCUSDT"], 2, today=date(2026, 10, 4))
    periods = [p["period"] for p in plan]
    assert periods == ["2026-08", "2026-09", "2026-10-01", "2026-10-02", "2026-10-03"]


def test_download_verifies_checksum_skips_missing_and_resumes(tmp_path):
    plan = bh.plan_files(["BTCUSDT", "NEWUSDT"], 1, today=date(2026, 10, 2))
    files = {}
    for p in plan:
        if p["symbol"] == "NEWUSDT" and p["kind"] == "monthly":
            continue                                        # listed after that month: 404 upstream
        files[p["url"]] = _zip("x.csv", _csv(0, 3))
    bad = [p["url"] for p in plan if p["symbol"] == "BTCUSDT" and p["kind"] == "daily"]
    c = FakeClient(files, bad_checksum=bad)
    prog = bh.download_klines(c, tmp_path, ["BTCUSDT", "NEWUSDT"], months=1, today=date(2026, 10, 2))
    assert prog.missing == 1 and prog.failed == 1 and prog.downloaded == 2
    assert not bh.kline_path(tmp_path, "BTCUSDT", "2026-10-01").exists()     # bad checksum never written
    c2 = FakeClient(files)
    prog2 = bh.download_klines(c2, tmp_path, ["BTCUSDT", "NEWUSDT"], months=1, today=date(2026, 10, 2))
    assert prog2.skipped == 2 and prog2.downloaded == 1                        # resumes, retries the failed one


def test_daily_files_removed_once_month_is_complete(tmp_path):
    d = tmp_path / "klines_1m" / "symbol=BTCUSDT"
    d.mkdir(parents=True)
    for name in ("BTCUSDT-2026-09.parquet", "BTCUSDT-2026-09-15.parquet", "BTCUSDT-2026-10-01.parquet"):
        (d / name).write_bytes(b"x")
    bh.download_klines(FakeClient({}), tmp_path, ["BTCUSDT"], months=0, today=date(2026, 10, 1))
    assert not (d / "BTCUSDT-2026-09-15.parquet").exists() and (d / "BTCUSDT-2026-10-01.parquet").exists()


def test_funding_pagination(tmp_path):
    class FC:
        def __init__(self):
            self.n = 0

        def get(self, url, params=None, timeout=None):
            self.n += 1
            start = params["startTime"]
            if self.n == 1:
                return Resp(200, js=[{"fundingTime": start + i, "fundingRate": "0.0001", "markPrice": "1"} for i in range(1000)])
            return Resp(200, js=[{"fundingTime": start + 5, "fundingRate": "-0.0002", "markPrice": ""}])
    counts = bh.download_funding(FC(), tmp_path, ["BTCUSDT"], months=1, now_ms=10**12)
    assert counts["BTCUSDT"] == 1001


def test_history_feeds_the_replay_end_to_end(tmp_path):
    import pyarrow.parquet as pq
    from src.research.str002_replay import VARIANTS, historical_range, load_panel_historical, run_replay
    for sym, px in (("BTCUSDT", 100.0), ("ETHUSDT", 50.0), ("ALTUSDT", 10.0)):
        out = bh.kline_path(tmp_path, sym, "2026-09")
        out.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(bh.parse_kline_csv(_csv(1_790_000_000_000, 400, px), sym), out)
    rng = historical_range(tmp_path)
    p = load_panel_historical(tmp_path, ["BTCUSDT", "ETHUSDT", "ALTUSDT"], start_ns=rng[0], end_ns=rng[1])
    assert len(p.minutes) == 400 and p.bars["ALTUSDT"].buy[5] == 6.0 and p.bars["ALTUSDT"].sell[5] == 4.0
    res = run_replay(p, list(VARIANTS.values()))
    assert set(res["variants"]) == set(VARIANTS)


def test_history_api(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from apps.api.main import app
    from apps.api.services import history_runner as hr
    monkeypatch.setattr(hr, "HIST_ROOT", tmp_path)
    c = TestClient(app)
    assert c.get("/api/history/status").json()["symbols_on_disk"] == 0
    assert TestClient(app, client=("203.0.113.9", 1)).post("/api/history/download").status_code == 403
