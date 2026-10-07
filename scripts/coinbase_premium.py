"""Coinbase premium: does US money (Coinbase BTC-USD paying more than Binance BTC-USDT) lead the BTC price?

    uv run python scripts/coinbase_premium.py --days 365

Coinbase is where US institutions, ETFs' brokers and US retail buy; Binance is offshore. When Coinbase trades above
Binance, US money is the one buying. Hourly closes: Coinbase public candles, Binance spot BTCUSDT 1h klines from
data.binance.vision. premium = Coinbase/Binance - 1 (USDT ~ USD; its slow drift is removed by the 7-day z-score).
Signal at hour h = z-score of the premium vs the previous 7 days (and its 6 h change). Outcome = BTC return over the
next 1, 4, 24 h (Binance close to close, starting at h, so nothing from the future). Reported by quintile of the signal,
plus a simple rule: long when z > 1, short when z < -1, held 24 h, with the two halves of the period.
"""
import argparse
import io
import json
import math
import sys
import time
import urllib.request
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_json(url):
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "quant-os"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1 + 2 * i)
    return []


def coinbase_hours(t0, t1):
    out, t = {}, t0
    while t < t1:
        end = min(t + 300 * 3600, t1)
        s = datetime.fromtimestamp(t, timezone.utc).isoformat()
        e = datetime.fromtimestamp(end, timezone.utc).isoformat()
        for c in get_json(f"https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600&start={s}&end={e}"):
            out[int(c[0])] = float(c[4])
        t = end
        time.sleep(0.15)
    return out


def binance_hours(days, cache: Path):
    out = {}
    today = date.today()
    months = sorted({(today - timedelta(days=k)).strftime("%Y-%m") for k in range(days + 10, 0, -1)})
    urls = [(f"https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1h/BTCUSDT-1h-{m}.zip", f"m{m}") for m in months]
    urls += [(f"https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1h/BTCUSDT-1h-{today - timedelta(days=k)}.zip",
              f"d{today - timedelta(days=k)}") for k in range(35, 0, -1)]
    for url, name in urls:
        f = cache / f"{name}.zip"
        if not f.exists():
            try:
                with urllib.request.urlopen(url, timeout=30) as r:
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_bytes(r.read())
            except Exception:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_bytes(b"")
        b = f.read_bytes()
        if not b:
            continue
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            for ln in z.read(z.namelist()[0]).decode().splitlines():
                p = ln.split(",")
                try:
                    ts = int(p[0])
                    ts = ts // 1000000 if ts > 1e14 else ts // 1000      # 2025+ spot files use microseconds
                    out[ts] = float(p[4])
                except (ValueError, IndexError):
                    continue
    return out


def tstat(x):
    n = len(x)
    if n < 3:
        return float("nan")
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return m / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--cache", type=Path, default=Path("data/research/binance_vision/spot_btc_1h"))
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/coinbase_premium.md"))
    a = ap.parse_args()
    now = int(time.time()) // 3600 * 3600
    t0 = now - a.days * 86400
    cb = coinbase_hours(t0 - 8 * 86400, now)
    bn = binance_hours(a.days + 8, a.cache)
    hours = sorted(h for h in cb if h in bn)
    prem = {h: cb[h] / bn[h] - 1 for h in hours}
    print(f"horas con ambos precios: {len(hours)}", flush=True)
    rows = []
    for i, h in enumerate(hours):
        if h < t0:
            continue
        past = [prem[x] for x in hours[max(0, i - 168):i]]
        if len(past) < 150:
            continue
        mu = sum(past) / len(past)
        sd = math.sqrt(sum((v - mu) ** 2 for v in past) / (len(past) - 1)) or 1e-9
        z = (prem[h] - mu) / sd
        r = {}
        for k in (1, 4, 24):
            if h + k * 3600 in bn:
                r[k] = bn[h + k * 3600] / bn[h] - 1
        if 24 in r:
            rows.append((h, z, prem[h], r))
    out = ["# Prima de Coinbase (dinero de EE.UU.) vs precio futuro de BTC", "",
           f"{len(rows):,} horas, {datetime.fromtimestamp(rows[0][0], timezone.utc):%Y-%m-%d} a "
           f"{datetime.fromtimestamp(rows[-1][0], timezone.utc):%Y-%m-%d}. Prima media {sum(p for _, _, p, _ in rows) / len(rows) * 100:+.3f}%.",
           "", "## Retorno de BTC después, por quintil de la prima (z-score vs 7 días)", "",
           "| quintil | z medio | +1 h | +4 h | +24 h | n |", "|---|---|---|---|---|---|"]
    srt = sorted(rows, key=lambda r: r[1])
    q = len(srt) // 5
    for i in range(5):
        part = srt[i * q:(i + 1) * q if i < 4 else len(srt)]
        out.append(f"| {i + 1} {'(más baja)' if i == 0 else '(más alta)' if i == 4 else ''} | "
                   f"{sum(r[1] for r in part) / len(part):+.2f} | "
                   + " | ".join(f"{sum(r[3][k] for r in part if k in r[3]) / len(part) * 100:+.3f}%" for k in (1, 4, 24))
                   + f" | {len(part)} |")
    out += ["", "## Regla: largo si z > 1, corto si z < -1, mantener 24 h (sin superponer), costo 0,05% por lado", "",
            "| tramo | operaciones | retorno medio | t | aciertos |", "|---|---|---|---|---|"]
    trades, busy = [], 0
    for h, z, _, r in rows:
        if h < busy or abs(z) <= 1:
            continue
        s = 1 if z > 1 else -1
        trades.append((h, s * r[24] - 0.001))
        busy = h + 24 * 3600
    for name, part in (("todo", trades), ("1ª mitad", trades[:len(trades) // 2]), ("2ª mitad", trades[len(trades) // 2:])):
        x = [v for _, v in part]
        if x:
            out.append(f"| {name} | {len(x)} | {sum(x) / len(x) * 100:+.2f}% | {tstat(x):.1f} | {sum(v > 0 for v in x) / len(x) * 100:.0f}% |")
    for side, name in ((1, "solo largos (z > 1)"), (-1, "solo cortos (z < -1)")):
        x = [v for (h, v), (hh, z, _, r) in zip(trades, [next(rr for rr in rows if rr[0] == h) for h, _ in trades])
             if (z > 1) == (side == 1)]
        if x:
            out.append(f"| {name} | {len(x)} | {sum(x) / len(x) * 100:+.2f}% | {tstat(x):.1f} | {sum(v > 0 for v in x) / len(x) * 100:.0f}% |")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
