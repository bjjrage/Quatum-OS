"""Follow the money on Binance futures: do the big accounts' positions predict the next days, against retail?

    uv run python scripts/smart_money_positioning.py --days 365

Data (public, data.binance.vision, one zip per symbol and day / month):
  metrics (5 min): open interest, top traders' long/short ratio by POSITION size (the big accounts' money),
                   long/short ratio of ALL accounts by count (retail headcount), taker buy/sell volume ratio
  klines 1d:       daily close
Daily features per coin (last value of the day unless noted), all known at the close of day d:
  smart_minus_retail  3-day change of log(top-trader position ratio) minus 3-day change of log(all-account ratio):
                      big money getting longer while the crowd gets shorter (or the reverse)
  smart_level         log(top position ratio) minus its 30-day mean
  crowd_level         log(all-account ratio) minus its 30-day mean (contrarian: crowd too long -> short)
  oi_vs_price         3-day OI change minus 3-day price change (positions piling up without price following)
  taker               mean taker buy/sell ratio of the day, minus its 30-day mean
Each feature: every day, long the top 20% / short the bottom 20% of coins (equal weight, market neutral),
hold 1 day and 3 days (overlapping, 1/3 of the book rebalanced daily). Cost 0.05% per side on the turnover.
Reported: mean daily return, annualised, t-stat, hit rate, and the two halves of the period separately.
"""
import argparse
import csv
import io
import math
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://data.binance.vision/data/futures/um"
SYMBOLS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX", "LINK", "DOT", "LTC", "BCH", "TRX", "NEAR", "APT",
           "ARB", "OP", "SUI", "ATOM", "FIL", "ETC", "UNI", "AAVE", "INJ", "TIA", "SEI", "WLD", "1000PEPE", "WIF", "ORDI",
           "JUP", "FET", "ENA", "ONDO", "TAO", "HBAR", "XLM", "CRV", "LDO", "STX", "1000SHIB", "1000BONK", "PENDLE",
           "RUNE", "ALGO", "ICP", "SAND", "GALA", "APE", "DYDX"]
COST = 0.0005


def fetch(url, cache: Path):
    if cache.exists():
        return cache.read_bytes() or None
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                b = r.read()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(b)
            return b
        except urllib.error.HTTPError as e:
            if e.code == 404:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_bytes(b"")
                return None
            time.sleep(1 + i)
        except Exception:
            time.sleep(1 + i)
    return None


def rows_of(zbytes):
    if not zbytes:
        return []
    with zipfile.ZipFile(io.BytesIO(zbytes)) as z:
        txt = z.read(z.namelist()[0]).decode()
    return list(csv.reader(io.StringIO(txt)))


def load_symbol(sym, days, cache):
    s = f"{sym}USDT"
    today = date.today()
    metrics = {}
    for k in range(days + 35, 0, -1):
        d = today - timedelta(days=k)
        rs = rows_of(fetch(f"{BASE}/daily/metrics/{s}/{s}-metrics-{d}.zip", cache / "metrics" / s / f"{d}.zip"))
        last, takers = None, []
        for r in rs:
            if not r or r[0] == "create_time":
                continue
            try:
                oi, top_pos, all_acc, taker = float(r[2]), float(r[5]), float(r[6]), float(r[7])
            except (ValueError, IndexError):
                continue
            last = (oi, top_pos, all_acc)
            takers.append(taker)
        if last and takers:
            metrics[d] = (*last, sum(takers) / len(takers))
    closes = {}
    months = sorted({(today - timedelta(days=k)).strftime("%Y-%m") for k in range(days + 35, 0, -1)})
    for m in months:
        for r in rows_of(fetch(f"{BASE}/monthly/klines/{s}/1d/{s}-1d-{m}.zip", cache / "klines" / s / f"{m}.zip")):
            try:
                closes[date.fromtimestamp(int(r[0]) / 1000)] = float(r[4])
            except (ValueError, IndexError):
                continue
    # current month is not in the monthly files yet: daily files
    for k in range(40, 0, -1):
        d = today - timedelta(days=k)
        if d in closes:
            continue
        for r in rows_of(fetch(f"{BASE}/daily/klines/{s}/1d/{s}-1d-{d}.zip", cache / "klines_d" / s / f"{d}.zip")):
            try:
                closes[date.fromtimestamp(int(r[0]) / 1000)] = float(r[4])
            except (ValueError, IndexError):
                continue
    return sym, metrics, closes


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
    ap.add_argument("--cache", type=Path, default=Path("data/research/binance_vision"))
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/smart_money_positioning.md"))
    a = ap.parse_args()
    with ThreadPoolExecutor(16) as ex:
        data = {s: (m, c) for s, m, c in ex.map(lambda s: load_symbol(s, a.days, a.cache), SYMBOLS)}
    data = {s: v for s, v in data.items() if len(v[0]) > 60 and len(v[1]) > 60}
    print(f"{len(data)} monedas con datos", flush=True)
    days = sorted({d for m, _ in data.values() for d in m})
    feats = defaultdict(dict)      # feats[name][(sym, d)] = value
    ret = {}                       # ret[(sym, d)] = close(d+1)/close(d) - 1
    for s, (m, c) in data.items():
        ds = sorted(d for d in m if d in c)
        for i, d in enumerate(ds):
            nxt = d + timedelta(days=1)
            if nxt in c:
                ret[(s, d)] = c[nxt] / c[d] - 1
            if i < 30:
                continue
            win = ds[i - 30:i]
            lt = math.log(m[d][1]); la = math.log(m[d][2])
            d3 = ds[i - 3]
            feats["smart_minus_retail"][(s, d)] = (lt - math.log(m[d3][1])) - (la - math.log(m[d3][2]))
            feats["smart_level"][(s, d)] = lt - sum(math.log(m[x][1]) for x in win) / 30
            feats["crowd_level (contrario)"][(s, d)] = -(la - sum(math.log(m[x][2]) for x in win) / 30)
            feats["oi_vs_price"][(s, d)] = math.log(m[d][0] / m[d3][0]) - math.log(c[d] / c[d3])
            feats["taker"][(s, d)] = m[d][3] - sum(m[x][3] for x in win) / 30
    out = ["# Follow the money: posiciones de las cuentas grandes en futuros de Binance", "",
           f"{len(data)} monedas, {days[0]} a {days[-1]}. Largo 20% más alto / corto 20% más bajo de cada señal, "
           f"neutral al mercado, costo {COST:.2%} por lado sobre lo que se rota.", "",
           "| señal | tenencia | días | retorno diario medio | anualizado | t | aciertos | 1ª mitad (t) | 2ª mitad (t) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for name, f in feats.items():
        by_day = defaultdict(list)
        for (s, d), v in f.items():
            by_day[d].append((v, s))
        legs = {}
        for d, lst in by_day.items():
            if len(lst) < 10:
                continue
            lst.sort()
            k = max(2, len(lst) // 5)
            legs[d] = ({s for _, s in lst[-k:]}, {s for _, s in lst[:k]})
        for hold in (1, 3):
            series, prev = [], None
            ds = sorted(legs)
            for i, d in enumerate(ds):
                books = [legs[ds[j]] for j in range(max(0, i - hold + 1), i + 1)]
                r_day, n_b = 0.0, 0
                for lo, sh in books:
                    rl = [ret[(s, d)] for s in lo if (s, d) in ret]
                    rs = [ret[(s, d)] for s in sh if (s, d) in ret]
                    if rl and rs:
                        r_day += (sum(rl) / len(rl) - sum(rs) / len(rs)) / 2
                        n_b += 1
                if not n_b:
                    continue
                r_day /= n_b
                lo, sh = legs[d]
                if prev:
                    turn = (len(lo ^ prev[0]) / max(1, len(lo)) + len(sh ^ prev[1]) / max(1, len(sh))) / 2
                    r_day -= COST * 2 * turn / hold
                prev = (lo, sh)
                series.append((d, r_day))
            if len(series) < 30:
                continue
            x = [r for _, r in series]
            h = len(x) // 2
            mu = sum(x) / len(x)
            out.append(f"| {name} | {hold} d | {len(x)} | {mu * 100:+.3f}% | {mu * 365 * 100:+.0f}% | {tstat(x):.1f} | "
                       f"{sum(v > 0 for v in x) / len(x) * 100:.0f}% | {sum(x[:h]) / h * 100:+.3f}% ({tstat(x[:h]):.1f}) | "
                       f"{sum(x[h:]) / (len(x) - h) * 100:+.3f}% ({tstat(x[h:]):.1f}) |")
    out += ["", "Para que valga: t > 2 en total y el mismo signo con t razonable en las dos mitades. "
            "Probé 5 señales × 2 tenencias = 10 variantes: alguna puede dar t ≈ 2 por azar."]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
