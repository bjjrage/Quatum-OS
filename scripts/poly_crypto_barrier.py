"""Polymarket crypto price markets ("Will Bitcoin reach $150k in February?", "Bitcoin above $100k on Dec 20?") priced
against a volatility model built from Binance. Slow (days), so speed does not matter.

    uv run python scripts/poly_crypto_barrier.py

For every resolved market with an explicit $ strike we take the daily Yes price history (clob prices-history) and, on each
day, compute a fair value from Binance daily data known BEFORE that moment (close of the previous UTC day):
  touch ("reach/hit/dip to/fall to"):  P = 2 * (1 - Phi(|ln(K/S)| / (sigma*sqrt(T))))  (zero drift, GBM), 0 if the barrier
        was already touched in the window (the market is then resolved: those days are skipped)
  terminal ("above/below X on <date>"): P = Phi(+-ln(S/K) / (sigma*sqrt(T)))
sigma = std of daily log returns over the previous 30 days * sqrt(365).
1) Calibration of the market alone: Yes price bucket (first sample of each market in that bucket) vs how often it resolved Yes.
2) Model vs market: first day in each market where |market - model| >= delta -> buy the cheap side, hold to resolution.
   Cost: 1.5 cents per share of slippage (spread) on entry; these long-dated markets carry no taker fee.
   t-stats over clusters (same asset and same end date: strikes of one month move together).
"""
import argparse
import gzip
import io
import json
import math
import re
import sys
import time
import urllib.request
import zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from poly_trades_edge import get

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GAMMA = "https://gamma-api.polymarket.com/markets"
HIST = "https://clob.polymarket.com/prices-history"
ASSETS = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH", "solana": "SOL", "sol": "SOL", "xrp": "XRP",
          "dogecoin": "DOGE"}
MONTHS = {m: i + 1 for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                          "september", "october", "november", "december"])}
SLIP = 0.015


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def money(s):
    m = re.search(r"\$\s?([\d,]+(?:\.\d+)?)\s?([kKmM]?)", s)
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    return v * {"k": 1e3, "m": 1e6}.get(m.group(2).lower(), 1)


def parse(q, start_d: date, end_d: date):
    """-> dict(asset, K, kind, w0, w1) or None."""
    ql = q.lower()
    asset = next((v for k, v in ASSETS.items() if re.search(rf"\b{k}\b", ql)), None)
    K = money(q)
    if not asset or not K:
        return None
    touch = re.search(r"\b(reach|hit|dip to|fall to|drop to|touch)\b", ql)
    term = re.search(r"\b(above|below|over|under)\b", ql) and re.search(r"\bon\b", ql)
    if not touch and not term:
        return None
    kind = "touch" if touch else "terminal"
    w1 = end_d
    w0 = start_d
    mm = re.search(r"\bin (" + "|".join(MONTHS) + r")\b", ql)
    yy = re.search(r"\bin (20\d\d)\b", ql)
    if kind == "touch" and mm:
        mo = MONTHS[mm.group(1)]
        yr = end_d.year if mo <= end_d.month or end_d.month == 1 else end_d.year - 1
        if end_d.month == 1 and mo == 12:
            yr = end_d.year - 1
        w0 = date(yr, mo, 1)
    elif kind == "touch" and yy:
        w0 = date(int(yy.group(1)), 1, 1)
    return {"asset": asset, "K": K, "kind": kind, "below": bool(re.search(r"\b(below|under|dip to|fall to|drop to)\b", ql)),
            "w0": w0, "w1": w1}


def spot_daily(asset, cache: Path):
    out = {}
    sym = f"{asset}USDT"
    today = date.today()
    months, d = [], date(2023, 11, 1)
    while d <= today:
        months.append(d.strftime("%Y-%m"))
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    for m in months:
        f = cache / f"{sym}-{m}.zip"
        if not f.exists():
            url = f"https://data.binance.vision/data/spot/monthly/klines/{sym}/1d/{sym}-1d-{m}.zip"
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_bytes(r.read())
            except Exception:
                if m != today.strftime("%Y-%m"):
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_bytes(b"")
                continue
        b = f.read_bytes()
        if not b:
            continue
        with zipfile.ZipFile(io.BytesIO(b)) as z:
            for ln in z.read(z.namelist()[0]).decode().splitlines():
                p = ln.split(",")
                try:
                    t = int(p[0])
                    t = t // 1000000 if t > 1e14 else t // 1000
                    out[datetime.fromtimestamp(t, timezone.utc).date()] = (float(p[2]), float(p[3]), float(p[4]))
                except (ValueError, IndexError):
                    continue
    # current month from daily files
    for k in range(40, 0, -1):
        dd = today - timedelta(days=k)
        if dd in out:
            continue
        url = f"https://data.binance.vision/data/spot/daily/klines/{sym}/1d/{sym}-1d-{dd}.zip"
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                b = r.read()
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                p = z.read(z.namelist()[0]).decode().splitlines()[0].split(",")
                out[dd] = (float(p[2]), float(p[3]), float(p[4]))
        except Exception:
            continue
    return out


def tstat_cluster(items):
    g = defaultdict(list)
    for c, v in items:
        g[c].append(v)
    x = [sum(v) / len(v) for v in g.values()]
    n = len(x)
    if n < 3:
        return float("nan"), n
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return (m / (sd / math.sqrt(n)) if sd > 0 else float("nan")), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path("data/research/binance_vision/spot_1d"))
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/poly_crypto_barrier.md"))
    a = ap.parse_args()
    mk, seen = [], set()
    for ps in ({"order": "volumeNum", "ascending": "false"},
               {"order": "endDate", "ascending": "false", "volume_num_min": 5000},
               {"order": "endDate", "ascending": "true", "volume_num_min": 5000}):
        off = 0
        while off < 8000:
            try:
                page = get(GAMMA, {"closed": "true", "limit": 100, "offset": off, **ps})
            except Exception:
                break
            if not page:
                break
            for m in page:
                if m["conditionId"] in seen or "updown" in (m.get("slug") or "") or "up-or-down" in (m.get("slug") or ""):
                    continue
                try:
                    pr = [float(x) for x in json.loads(m["outcomePrices"])]
                    toks = json.loads(m["clobTokenIds"])
                    outs = [str(o).lower() for o in json.loads(m["outcomes"])]
                    s = datetime.fromisoformat(m["startDate"].replace("Z", "+00:00")).date()
                    e = datetime.fromisoformat((m.get("endDate") or m["closedTime"]).replace("Z", "+00:00")).date()
                except Exception:
                    continue
                if max(pr) < 0.99 or "yes" not in outs:
                    continue
                p = parse(m.get("question", ""), s, e)
                if not p:
                    continue
                seen.add(m["conditionId"])
                p.update(q=m["question"], tok=toks[outs.index("yes")], yes=pr[outs.index("yes")] >= 0.99, vol=float(m.get("volumeNum") or 0))
                mk.append(p)
            off += 100
    print(f"{len(mk)} mercados con strike parseado ({sum(1 for m in mk if m['kind'] == 'touch')} touch, "
          f"{sum(1 for m in mk if m['kind'] == 'terminal')} terminal)", flush=True)
    spots = {}
    for asset in {m["asset"] for m in mk}:
        spots[asset] = spot_daily(asset, a.cache)
        print(f"spot {asset}: {len(spots[asset])} días", flush=True)
    rows = []
    for i, m in enumerate(mk):
        sp = spots.get(m["asset"]) or {}
        try:
            h = get(HIST, {"market": m["tok"], "interval": "max", "fidelity": 1440}).get("history", [])
        except Exception:
            continue
        for pt in h:
            t = datetime.fromtimestamp(int(pt["t"]), timezone.utc)
            d = t.date()
            if not (m["w0"] <= d < m["w1"]):
                continue
            ref = d - timedelta(days=1)                   # last fully closed UTC day
            if ref not in sp:
                continue
            rets = []
            for k in range(30):
                x, y = sp.get(ref - timedelta(days=k)), sp.get(ref - timedelta(days=k + 1))
                if x and y:
                    rets.append(math.log(x[2] / y[2]))
            if len(rets) < 25:
                continue
            mu = sum(rets) / len(rets)
            sig = math.sqrt(sum((r - mu) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(365)
            S = sp[ref][2]
            T = max((datetime.combine(m["w1"], datetime.min.time(), timezone.utc) - t).total_seconds() / (365 * 86400), 1e-6)
            x = math.log(m["K"] / S)
            p_mkt = float(pt["p"])
            if m["kind"] == "touch":
                hi = max((sp[w][0] for w in (m["w0"] + timedelta(days=k) for k in range((ref - m["w0"]).days + 1)) if w in sp), default=0)
                lo = min((sp[w][1] for w in (m["w0"] + timedelta(days=k) for k in range((ref - m["w0"]).days + 1)) if w in sp), default=1e18)
                if (m["K"] > S and hi >= m["K"]) or (m["K"] < S and lo <= m["K"]):
                    continue                              # already touched: resolved, not a forecast
                p_mod = 2 * (1 - phi(abs(x) / (sig * math.sqrt(T))))
            else:
                p_mod = phi(-x / (sig * math.sqrt(T)))
                if m["below"]:
                    p_mod = 1 - p_mod
            rows.append({"m": m, "d": d, "p_mkt": p_mkt, "p_mod": min(max(p_mod, 0), 1), "left_d": T * 365})
        if i % 40 == 0:
            print(f"  {i}/{len(mk)}", flush=True)

    cl = lambda r: (r["m"]["asset"], r["m"]["w1"])   # noqa: E731
    out = ["# Mercados de precio cripto de Polymarket contra un modelo de volatilidad con Binance", "",
           f"{len(mk)} mercados resueltos con strike en dólares; {len(rows):,} observaciones diarias válidas. "
           "Cada día: precio del Sí de Polymarket contra el valor justo con Binance de ayer (σ de 30 días, sin deriva).", "",
           "## 1. Calibración del mercado solo: precio del Sí → cuántas veces resolvió Sí", "",
           "| precio del Sí | mercados | resolvió Sí | diferencia | t |", "|---|---|---|---|---|"]
    first = {}
    for r in sorted(rows, key=lambda r: r["d"]):
        b = min(int(r["p_mkt"] * 10), 9)
        first.setdefault((id(r["m"]), b), r)
    for b in range(10):
        sel = [r for (mid, bb), r in first.items() if bb == b]
        if len(sel) < 15:
            continue
        diffs = [(cl(r), (1.0 if r["m"]["yes"] else 0.0) - r["p_mkt"]) for r in sel]
        t, n = tstat_cluster(diffs)
        out.append(f"| {b / 10:.1f}–{(b + 1) / 10:.1f} | {len(sel)} | {sum(r['m']['yes'] for r in sel) / len(sel) * 100:.0f}% "
                   f"(esperado {sum(r['p_mkt'] for r in sel) / len(sel) * 100:.0f}%) | "
                   f"{sum(v for _, v in diffs) / len(diffs) * 100:+.1f} pts | {t:.1f} |")
    out += ["", f"## 2. Mercado contra modelo: primer día con diferencia ≥ δ, comprar el lado barato (costo {SLIP * 100:.1f} centavos)", "",
            "| δ | lado | mercados | resultado medio por acción | t (por grupo) | aciertos | 1ª mitad | 2ª mitad |",
            "|---|---|---|---|---|---|---|---|"]
    cut = sorted(r["d"] for r in rows)[len(rows) // 2] if rows else None
    for delta in (0.05, 0.10, 0.15, 0.25):
        for side, name in (("sell", "vender (mercado > modelo): comprar No"), ("buy", "comprar Sí (modelo > mercado)")):
            trades, got = [], set()
            for r in sorted(rows, key=lambda r: r["d"]):
                if id(r["m"]) in got:
                    continue
                gap = r["p_mkt"] - r["p_mod"]
                if side == "sell" and gap >= delta and r["p_mkt"] < 0.97:
                    got.add(id(r["m"]))
                    trades.append((r, (0.0 if r["m"]["yes"] else 1.0) - (1 - r["p_mkt"]) - SLIP))
                if side == "buy" and -gap >= delta and r["p_mkt"] > 0.03:
                    got.add(id(r["m"]))
                    trades.append((r, (1.0 if r["m"]["yes"] else 0.0) - r["p_mkt"] - SLIP))
            if len(trades) < 10:
                out.append(f"| {delta:.2f} | {name} | {len(trades)} | | | | | |")
                continue
            t, n = tstat_cluster([(cl(r), v) for r, v in trades])
            h1 = [v for r, v in trades if r["d"] < cut]
            h2 = [v for r, v in trades if r["d"] >= cut]
            out.append(f"| {delta:.2f} | {name} | {len(trades)} | {sum(v for _, v in trades) / len(trades) * 100:+.1f} pts | "
                       f"{t:.1f} ({n}) | {sum(v > 0 for _, v in trades) / len(trades) * 100:.0f}% | "
                       f"{(sum(h1) / len(h1) * 100) if h1 else float('nan'):+.1f} ({len(h1)}) | "
                       f"{(sum(h2) / len(h2) * 100) if h2 else float('nan'):+.1f} ({len(h2)}) |")
    out += ["", "Resultado por acción: 0 = apuesta justa. Un grupo = mismo activo y misma fecha de cierre (los strikes de un mes se mueven juntos). "
            "Para que valga: positivo con t > 2 y con el mismo signo en las dos mitades."]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    main()
