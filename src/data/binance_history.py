"""Historical Binance USD-M futures data (public, free) -> local Parquet.

Source: https://data.binance.vision (official Binance public data dumps).
  monthly: /data/futures/um/monthly/klines/{SYM}/1m/{SYM}-1m-{YYYY-MM}.zip
  daily:   /data/futures/um/daily/klines/{SYM}/1m/{SYM}-1m-{YYYY-MM-DD}.zip
  each zip has a sibling .CHECKSUM (sha256) that is verified before anything is written.
Funding history: GET https://fapi.binance.com/fapi/v1/fundingRate (paginated, 1000 rows per call).

Stored apart from the live recorder data (different provenance):
  data/historical/binance_um/klines_1m/symbol=SYM/SYM-YYYY-MM.parquet        (full months)
  data/historical/binance_um/klines_1m/symbol=SYM/SYM-YYYY-MM-DD.parquet     (days of the current month)
  data/historical/binance_um/funding/symbol=SYM/funding.parquet

Resumable: files already on disk are skipped. A partial current month is refreshed on every run.
"""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import pyarrow as pa
import pyarrow.parquet as pq

BASE_URL = "https://data.binance.vision/data/futures/um"
FAPI = "https://fapi.binance.com"

KLINE_SCHEMA = pa.schema([
    ("open_time_ms", pa.int64()), ("open", pa.float64()), ("high", pa.float64()), ("low", pa.float64()),
    ("close", pa.float64()), ("volume", pa.float64()), ("quote_volume", pa.float64()), ("count", pa.int64()),
    ("taker_buy_volume", pa.float64()), ("symbol", pa.string()),
])
FUNDING_SCHEMA = pa.schema([("funding_time_ms", pa.int64()), ("funding_rate", pa.float64()),
                            ("mark_price", pa.float64()), ("symbol", pa.string())])


class ChecksumMismatch(Exception):
    pass


@dataclass
class Progress:
    total: int = 0
    done: int = 0
    downloaded: int = 0
    skipped: int = 0
    missing: int = 0            # file does not exist upstream (symbol listed later, etc.)
    failed: int = 0
    current: str = ""
    errors: List[str] = field(default_factory=list)


def parse_kline_csv(text: str, symbol: str) -> pa.Table:
    """Binance kline CSV (with or without header row) -> Arrow table."""
    rows = list(csv.reader(io.StringIO(text)))
    if rows and rows[0] and not rows[0][0].strip().lstrip("-").isdigit():
        rows = rows[1:]                                          # header present
    cols: Dict[str, list] = {n: [] for n in KLINE_SCHEMA.names}
    for r in rows:
        if len(r) < 11 or not r[0].strip():
            continue
        cols["open_time_ms"].append(int(r[0])); cols["open"].append(float(r[1])); cols["high"].append(float(r[2]))
        cols["low"].append(float(r[3])); cols["close"].append(float(r[4])); cols["volume"].append(float(r[5]))
        cols["quote_volume"].append(float(r[7])); cols["count"].append(int(float(r[8])))
        cols["taker_buy_volume"].append(float(r[9])); cols["symbol"].append(symbol)
    return pa.table(cols, schema=KLINE_SCHEMA)


def verify_and_extract(zip_bytes: bytes, checksum_text: Optional[str]) -> str:
    if checksum_text:
        expected = checksum_text.strip().split()[0].lower()
        got = hashlib.sha256(zip_bytes).hexdigest()
        if got != expected:
            raise ChecksumMismatch(f"sha256 {got} != {expected}")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".csv"))
        return zf.read(name).decode("utf-8")


def plan_files(symbols: Sequence[str], months: int, today: Optional[date] = None) -> List[Dict[str, str]]:
    """Full months for the last `months` months + daily files for the current month up to yesterday."""
    today = today or datetime.now(timezone.utc).date()
    first_this_month = today.replace(day=1)
    plan: List[Dict[str, str]] = []
    ym = []
    y, m = first_this_month.year, first_this_month.month
    for _ in range(months):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        ym.append(f"{y:04d}-{m:02d}")
    ym.reverse()
    days = []
    d = first_this_month
    while d < today:                                             # yesterday is the last complete day
        days.append(d.isoformat())
        d += timedelta(days=1)
    for sym in symbols:
        for p in ym:
            plan.append({"symbol": sym, "kind": "monthly", "period": p,
                         "url": f"{BASE_URL}/monthly/klines/{sym}/1m/{sym}-1m-{p}.zip"})
        for p in days:
            plan.append({"symbol": sym, "kind": "daily", "period": p,
                         "url": f"{BASE_URL}/daily/klines/{sym}/1m/{sym}-1m-{p}.zip"})
    return plan


def kline_path(root: Path, symbol: str, period: str) -> Path:
    return root / "klines_1m" / f"symbol={symbol}" / f"{symbol}-{period}.parquet"


def download_klines(client, root: Path, symbols: Sequence[str], months: int = 12,
                    on_progress: Optional[Callable[[Progress], None]] = None,
                    today: Optional[date] = None) -> Progress:
    plan = plan_files(symbols, months, today)
    prog = Progress(total=len(plan))
    for item in plan:
        sym, period = item["symbol"], item["period"]
        out = kline_path(root, sym, period)
        prog.current = f"{sym} {period}"
        if out.exists():
            prog.skipped += 1
        else:
            try:
                r = client.get(item["url"], timeout=60.0)
                if r.status_code == 404:
                    prog.missing += 1
                else:
                    r.raise_for_status()
                    ck = client.get(item["url"] + ".CHECKSUM", timeout=30.0)
                    text = verify_and_extract(r.content, ck.text if ck.status_code == 200 else None)
                    table = parse_kline_csv(text, sym)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    tmp = out.with_suffix(".tmp")
                    pq.write_table(table, tmp)
                    tmp.replace(out)                            # atomic: never a half-written file
                    prog.downloaded += 1
            except Exception as ex:                             # one bad file must not stop the rest
                prog.failed += 1
                if len(prog.errors) < 20:
                    prog.errors.append(f"{sym} {period}: {type(ex).__name__}: {ex}")
        prog.done += 1
        if on_progress:
            on_progress(prog)
    # once a month is complete, its daily files are redundant: drop them
    for sym in symbols:
        d = root / "klines_1m" / f"symbol={sym}"
        if not d.exists():
            continue
        monthly = {p.stem[len(sym) + 1:] for p in d.glob(f"{sym}-????-??.parquet")}
        for p in d.glob(f"{sym}-????-??-??.parquet"):
            if p.stem[len(sym) + 1:len(sym) + 8] in monthly:
                p.unlink(missing_ok=True)
    return prog


def download_funding(client, root: Path, symbols: Sequence[str], months: int = 12,
                     now_ms: Optional[int] = None) -> Dict[str, int]:
    """Funding-rate history via the public REST API (paginated). Returns rows per symbol."""
    now_ms = now_ms or int(datetime.now(timezone.utc).timestamp() * 1000)
    start = now_ms - months * 31 * 86_400_000
    counts: Dict[str, int] = {}
    for sym in symbols:
        rows = {"funding_time_ms": [], "funding_rate": [], "mark_price": [], "symbol": []}
        t = start
        for _ in range(50):                                      # hard cap on pages
            r = client.get(f"{FAPI}/fapi/v1/fundingRate",
                           params={"symbol": sym, "startTime": t, "limit": 1000}, timeout=30.0)
            if r.status_code != 200:
                break
            batch = r.json()
            if not batch:
                break
            for x in batch:
                rows["funding_time_ms"].append(int(x["fundingTime"]))
                rows["funding_rate"].append(float(x["fundingRate"]))
                mp = x.get("markPrice")
                rows["mark_price"].append(float(mp) if mp not in (None, "") else float("nan"))
                rows["symbol"].append(sym)
            last = int(batch[-1]["fundingTime"])
            if len(batch) < 1000 or last <= t:
                break
            t = last + 1
        counts[sym] = len(rows["symbol"])
        if rows["symbol"]:
            out = root / "funding" / f"symbol={sym}" / "funding.parquet"
            out.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.table(rows, schema=FUNDING_SCHEMA), out)
    return counts


def inventory(root: Path) -> Dict[str, Dict[str, object]]:
    """What is on disk: per symbol, number of files and first/last period."""
    out: Dict[str, Dict[str, object]] = {}
    base = root / "klines_1m"
    if not base.exists():
        return out
    for d in sorted(base.glob("symbol=*")):
        sym = d.name.split("=", 1)[1]
        periods = sorted(p.stem[len(sym) + 1:] for p in d.glob("*.parquet"))
        if periods:
            out[sym] = {"files": len(periods), "first": periods[0], "last": periods[-1],
                        "funding": (root / "funding" / f"symbol={sym}" / "funding.parquet").exists()}
    return out
