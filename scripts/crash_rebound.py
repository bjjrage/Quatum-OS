"""Forced-selling crashes (liquidation cascades / whale dumps) on Binance perps: does buying the rebound pay?

    uv run python scripts/crash_rebound.py --days 365

Data: 5-minute klines of USDT perps from data.binance.vision (monthly + daily files), 30 liquid coins.
Crash event: the 3-bar (15 min) return is <= -X (X = 3%, 5%, 8%) AND the volume of those 3 bars is >= 3x the median
3-bar volume of the previous 24 h (the forced-selling footprint). One event per coin per 4 h.
Entries (all after the crash, nothing from the future):
  knife      buy at the open of the next bar
  green      buy at the close of the first bar that closes green and above the previous bar's high (rebound confirmed),
             within 1 h of the crash
  retrace25  buy when price has recovered 25% of the drop (at that level), within 1 h
Exit: take profit at 50% retrace of the drop (measured from the crash low), stop at the crash low minus 0.5%
(or the low made after the crash, whichever is lower), or time stop after 4 h. If TP and SL are hit in the same bar
the stop is assumed first. Costs 0.05% fee per side + 0.05% slippage per side.
Results per $1 of position (leverage only multiplies them). t-stat over days (crashes cluster: one bad day hits all coins).
"""
import argparse
import io
import math
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://data.binance.vision/data/futures/um"
COINS = ["BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX", "LINK", "DOT", "LTC", "BCH", "NEAR", "APT", "ARB",
         "OP", "SUI", "ATOM", "FIL", "UNI", "AAVE", "INJ", "TIA", "WLD", "1000PEPE", "WIF", "ENA", "ONDO", "TAO", "1000BONK"]
COST = 2 * (0.0005 + 0.0005)


def fetch(url, cache: Path):
    if cache.exists():
        return cache.read_bytes() or None
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
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


def klines(coin, days, cache):
    s = f"{coin}USDT"
    today = date.today()
    bars = {}
    files = []
    for m in sorted({(today - timedelta(days=k)).strftime("%Y-%m") for k in range(days, 0, -1)}):
        if m != today.strftime("%Y-%m"):
            files.append((f"{BASE}/monthly/klines/{s}/5m/{s}-5m-{m}.zip", cache / s / f"m{m}.zip"))
    for k in range(today.day + 1, 0, -1):
        d = today - timedelta(days=k)
        if d.strftime("%Y-%m") == today.strftime("%Y-%m"):
            files.append((f"{BASE}/daily/klines/{s}/5m/{s}-5m-{d}.zip", cache / s / f"d{d}.zip"))
    for url, c in files:
        b = fetch(url, c)
        if not b:
            continue
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            for ln in z.read(z.namelist()[0]).decode().splitlines():
                p = ln.split(",")
                try:
                    bars[int(p[0]) // 1000] = (float(p[1]), float(p[2]), float(p[3]), float(p[4]), float(p[5]))
                except (ValueError, IndexError):
                    continue
    ts = sorted(bars)
    return coin, ts, [bars[t] for t in ts]


def simulate(ts, b, i_crash, low, drop_from, entry_mode):
    """Returns (entry_time, pnl) or None. b[i] = (o, h, l, c, v)."""
    n = len(b)
    rng = drop_from - low
    entry, j0 = None, None
    if entry_mode == "knife":
        if i_crash + 1 < n:
            entry, j0 = b[i_crash + 1][0], i_crash + 1
    else:
        for j in range(i_crash + 1, min(n, i_crash + 13)):
            o, h, l, c, v = b[j]
            low = min(low, l)
            if entry_mode == "green" and c > o and c > b[j - 1][1]:
                entry, j0 = c, j + 1
                break
            if entry_mode == "retrace25" and h >= low + 0.25 * (drop_from - low):
                entry, j0 = max(o, low + 0.25 * (drop_from - low)), j
                break
    if entry is None or j0 is None or j0 >= n:
        return None
    tp = low + 0.5 * rng
    if tp <= entry * 1.002:
        tp = entry * 1.002 + 0.25 * rng
    sl = low * 0.995
    for j in range(j0, min(n, j0 + 48)):
        o, h, l, c, v = b[j]
        if l <= sl:
            return ts[j0], sl / entry - 1 - COST
        if h >= tp:
            return ts[j0], tp / entry - 1 - COST
    j = min(n, j0 + 48) - 1
    return ts[j0], b[j][3] / entry - 1 - COST


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
    ap.add_argument("--cache", type=Path, default=Path("data/research/binance_vision/klines5m"))
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/crash_rebound.md"))
    a = ap.parse_args()
    with ThreadPoolExecutor(10) as ex:
        data = list(ex.map(lambda c: klines(c, a.days, a.cache), COINS))
    data = [d for d in data if len(d[1]) > 1000]
    print(f"{len(data)} monedas con velas de 5 min", flush=True)
    res = defaultdict(list)       # (X, mode) -> [(coin, entry_ts, pnl)]
    events = defaultdict(int)
    for coin, ts, b in data:
        vol3 = [sum(b[k][4] for k in range(i - 2, i + 1)) if i >= 2 else 0 for i in range(len(b))]
        for X in (0.03, 0.05, 0.08):
            last = -1e18
            for i in range(290, len(b) - 1):
                if ts[i] - last < 4 * 3600 or ts[i] - ts[i - 3] != 900:
                    continue
                drop_from = b[i - 3][3]
                if b[i][3] / drop_from - 1 > -X:
                    continue
                med = sorted(vol3[i - 288:i - 3])[len(vol3[i - 288:i - 3]) // 2] or 1e-9
                if vol3[i] < 3 * med:
                    continue
                low = min(b[k][2] for k in range(i - 2, i + 1))
                events[X] += 1
                last = ts[i]
                for mode in ("knife", "green", "retrace25"):
                    r = simulate(ts, b, i, low, drop_from, mode)
                    if r:
                        res[(X, mode)].append((coin, r[0], r[1]))
    t0 = min(ts[0] for _, ts, _ in data)
    t1 = max(ts[-1] for _, ts, _ in data)
    mid = (t0 + t1) / 2
    out = ["# Caídas forzadas (cascadas de liquidación / ventas de ballena): ¿paga comprar el rebote?", "",
           f"{len(data)} monedas, velas de 5 min, {datetime.fromtimestamp(t0, timezone.utc):%Y-%m-%d} a "
           f"{datetime.fromtimestamp(t1, timezone.utc):%Y-%m-%d}. Costos {COST:.2%} ida y vuelta. "
           "Resultado por cada US$ 1 de posición (el apalancamiento solo lo multiplica).", "",
           "| caída en 15 min | entrada | eventos | operaciones | resultado medio | t (por día) | aciertos | "
           "mejor / peor | 1ª mitad | 2ª mitad |", "|---|---|---|---|---|---|---|---|---|---|"]
    for X in (0.03, 0.05, 0.08):
        for mode, name in (("knife", "al toque (cuchillo)"), ("green", "rebote confirmado (vela verde)"),
                           ("retrace25", "recuperó 25%")):
            tr = res[(X, mode)]
            if not tr:
                out.append(f"| ≥ {X:.0%} | {name} | {events[X]} | 0 | | | | | | |")
                continue
            per_day = defaultdict(float)
            for _, t, p in tr:
                per_day[int(t // 86400)] += p
            x = [p for _, _, p in tr]
            h1 = [p for _, t, p in tr if t < mid]
            h2 = [p for _, t, p in tr if t >= mid]
            out.append(f"| ≥ {X:.0%} | {name} | {events[X]} | {len(x)} | {sum(x) / len(x) * 100:+.2f}% | "
                       f"{tstat(list(per_day.values())):.1f} | {sum(v > 0 for v in x) / len(x) * 100:.0f}% | "
                       f"{max(x) * 100:+.1f}% / {min(x) * 100:+.1f}% | "
                       f"{(sum(h1) / len(h1) * 100) if h1 else float('nan'):+.2f}% ({len(h1)}) | "
                       f"{(sum(h2) / len(h2) * 100) if h2 else float('nan'):+.2f}% ({len(h2)}) |")
    out += ["", "Salida: toma de ganancia al 50% de recuperación de la caída, stop debajo del mínimo, o 4 h. "
            "Para que valga: resultado medio > 0 con t > 2 y positivo en las dos mitades."]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
