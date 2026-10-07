"""Follow the money on Hyperliquid: do the wallets that won in the first half keep winning, and can their trades be copied?

    uv run python scripts/hl_wallet_follow.py fetch   --n 400 --days 60     # slow (about an hour), resumable
    uv run python scripts/hl_wallet_follow.py analyze --days 60

Universe (chosen WITHOUT looking at PnL, so winners are not pre-selected): leaderboard accounts with account value >= $100k
and monthly volume / account value between 1x and 30x (position traders, not high-frequency bots), random sample of --n.
Data: every public fill (userFillsByTime, the API only keeps the 10,000 most recent per account) and 5-minute candles.
analyze:
  1) Persistence: split the period in two halves. Net PnL (closed PnL - fees) / account value in each half; rank correlation
     across accounts and the H2 result of the top decile of H1 vs random deciles (null distribution of 500 draws).
  2) Copy test: the H2 opens of the top-decile accounts (>= $2,000 notional) are copied D minutes later at the 5 min candle
     open, held 1/4/24 h, cost 0.13% round trip. Compared with copying random deciles. t-stat over accounts.
"""
import argparse
import json
import math
import random
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
HL = "https://api.hyperliquid.xyz/info"
LB = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
BASE = ROOT / "data" / "research" / "hl"
COST = 0.0013
_budget = {"t": time.time(), "used": 0.0}


def post(body, weight, tries=6):
    """HL allows 1200 weight/min per IP: stay under 1000."""
    for i in range(tries):
        now = time.time()
        if now - _budget["t"] >= 60:
            _budget.update(t=now, used=0.0)
        if _budget["used"] + weight > 1000:
            time.sleep(max(0.5, 60 - (now - _budget["t"])))
            _budget.update(t=time.time(), used=0.0)
        _budget["used"] += weight
        try:
            req = urllib.request.Request(HL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            time.sleep(20 * (i + 1) if e.code == 429 else 3 + 3 * i)
        except Exception:
            time.sleep(3 + 3 * i)
    return None


def universe(n, seed=5):
    rows = json.loads(urllib.request.urlopen(LB, timeout=90).read())["leaderboardRows"]
    out = []
    for r in rows:
        w = dict(r["windowPerformances"])
        av, vm = float(r["accountValue"]), float(w["month"]["vlm"])
        if av >= 1e5 and 1 <= vm / av <= 30:
            out.append({"addr": r["ethAddress"], "av": av})
    random.Random(seed).shuffle(out)
    return out[:n]


def fetch_fills(addr, t0_ms):
    out, t = [], t0_ms
    while True:
        page = post({"type": "userFillsByTime", "user": addr, "startTime": int(t)}, 20 + 100)
        if not page:
            break
        out += page
        if len(page) < 2000:
            break
        t = page[-1]["time"] + 1
    return out


def cmd_fetch(a):
    (BASE / "fills").mkdir(parents=True, exist_ok=True)
    uni = universe(a.n)
    (BASE / "universe.json").write_text(json.dumps(uni))
    t0 = int((time.time() - a.days * 86400) * 1000)
    done = 0
    for i, u in enumerate(uni):
        f = BASE / "fills" / f"{u['addr']}.jsonl"
        if f.exists():
            done += 1
            continue
        fills = fetch_fills(u["addr"], t0)
        with f.open("w", encoding="utf-8") as fh:
            for x in fills:
                fh.write(json.dumps({"t": x["time"] // 1000, "c": x["coin"], "px": float(x["px"]), "sz": float(x["sz"]),
                                     "d": x.get("dir", ""), "pnl": float(x.get("closedPnl") or 0),
                                     "fee": float(x.get("fee") or 0)}) + "\n")
        if i % 20 == 0:
            print(f"  {i}/{len(uni)} cuentas ({len(fills)} fills la última)", flush=True)
    print(f"Listo: {len(uni)} cuentas en {BASE / 'fills'}")


def candles(coin, t0, t1):
    f = BASE / f"candles5m_{coin.replace('/', '_')}.json"
    if f.exists():
        d = json.loads(f.read_text())
        if d and d[0][0] <= t0 + 3600 and d[-1][0] >= t1 - 3600:
            return d
    out, t = {}, int(t0)
    while t < t1:
        rows = post({"type": "candleSnapshot", "req": {"coin": coin, "interval": "5m", "startTime": t * 1000,
                                                       "endTime": int(t1 * 1000)}}, 20 + 250)
        if not rows:
            break
        for r in rows:
            out[int(r["t"]) // 1000] = (float(r["o"]), float(r["c"]))
        if len(rows) < 5000:
            break
        t = rows[-1]["t"] // 1000 + 300
    d = [[k, *v] for k, v in sorted(out.items())]
    f.write_text(json.dumps(d))
    return d


def tstat(x):
    n = len(x)
    if n < 3:
        return float("nan")
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return m / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def spearman(a, b):
    def rk(x):
        o = sorted(range(len(x)), key=lambda i: x[i])
        r = [0] * len(x)
        for k, i in enumerate(o):
            r[i] = k
        return r
    ra, rb = rk(a), rk(b)
    n = len(a)
    return 1 - 6 * sum((ra[i] - rb[i]) ** 2 for i in range(n)) / (n * (n * n - 1)) if n > 2 else float("nan")


def cmd_analyze(a):
    uni = {u["addr"]: u["av"] for u in json.loads((BASE / "universe.json").read_text())}
    now = time.time()
    t_lo, cut = now - a.days * 86400, now - a.days * 43200
    acc = {}
    for addr, av in uni.items():
        f = BASE / "fills" / f"{addr}.jsonl"
        if not f.exists():
            continue
        fills = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]
        h1 = [x for x in fills if t_lo <= x["t"] < cut]
        h2 = [x for x in fills if x["t"] >= cut]
        c1 = sum(1 for x in h1 if x["d"].startswith("Close") or ">" in x["d"])
        c2 = sum(1 for x in h2 if x["d"].startswith("Close") or ">" in x["d"])
        if fills and min(x["t"] for x in fills) <= t_lo + 5 * 86400 and c1 >= 20 and c2 >= 20:
            acc[addr] = {"av": av, "h1": sum(x["pnl"] - x["fee"] for x in h1) / av,
                         "h2": sum(x["pnl"] - x["fee"] for x in h2) / av, "fills": fills}
    names = list(acc)
    out = ["# Seguir la plata en Hyperliquid: ¿persisten los ganadores y se pueden copiar?", "",
           f"Universo: {len(uni)} cuentas de posiciones elegidas al azar sin mirar ganancia; con historial que cubre las dos mitades "
           f"({a.days // 2} días cada una) y ≥ 20 cierres en cada una: {len(names)}.", ""]
    if len(names) < 30:
        out.append("Pocas cuentas elegibles todavía.")
        (ROOT / "docs" / "hl_wallet_follow.md").write_text("\n".join(out), encoding="utf-8")
        print("\n".join(out))
        return
    h1 = [acc[n]["h1"] for n in names]
    h2 = [acc[n]["h2"] for n in names]
    k = max(5, len(names) // 10)
    ranked = sorted(names, key=lambda n: -acc[n]["h1"])
    top, bottom = ranked[:k], ranked[-k:]
    rnd = random.Random(1)
    null = sorted(sum(acc[n]["h2"] for n in rnd.sample(names, k)) / k for _ in range(500))
    top_h2 = sum(acc[n]["h2"] for n in top) / k
    out += ["## 1. Persistencia: ¿el que ganó en la 1ª mitad gana en la 2ª?", "",
            f"- Correlación de rangos del resultado (neto / valor de la cuenta) entre mitades: **{spearman(h1, h2):+.2f}** "
            "(0 = suerte pura).", "",
            "| grupo (elegido en la 1ª mitad) | cuentas | resultado en la 2ª mitad (medio, sobre valor de cuenta) |", "|---|---|---|",
            f"| mejores {k} | {k} | **{top_h2 * 100:+.2f}%** |",
            f"| peores {k} | {k} | {sum(acc[n]['h2'] for n in bottom) / k * 100:+.2f}% |",
            f"| {k} al azar (mediana de 500 sorteos) | {k} | {null[250] * 100:+.2f}% (rango 5–95%: {null[25] * 100:+.2f}% a {null[475] * 100:+.2f}%) |",
            f"| todas | {len(names)} | {sum(h2) / len(h2) * 100:+.2f}% |", "",
            f"Los mejores de la 1ª mitad quedan por encima del {sum(1 for v in null if v < top_h2) / 5:.0f}% de los sorteos al azar.", ""]
    # copy test
    coins_needed = {x["c"] for n in top for x in acc[n]["fills"] if x["t"] >= cut and x["d"].startswith("Open")}
    cand = {}
    for c in sorted(coins_needed):
        if c.startswith("@") or ":" in c:
            continue
        d = candles(c, t_lo, now)
        if len(d) > 100:
            cand[c] = d
    import bisect

    def copy_ret(fills, delay_s, hold_s):
        res = []
        for x in fills:
            if x["t"] < cut or not x["d"].startswith("Open") or x["px"] * x["sz"] < 2000 or x["c"] not in cand:
                continue
            d = cand[x["c"]]
            ts = [r[0] for r in d]
            i = bisect.bisect_left(ts, x["t"] + delay_s)
            j = bisect.bisect_left(ts, x["t"] + delay_s + hold_s)
            if i >= len(d) or j >= len(d) or ts[i] - x["t"] > delay_s + 900:
                continue
            side = 1 if x["d"].endswith("Long") else -1
            res.append(side * (d[j][1] / d[i][1] - 1) - COST)
        return res

    out += ["## 2. Copiar: las aperturas de los mejores de la 1ª mitad, copiadas D minutos después, en la 2ª mitad", "",
            "| atraso | tenencia | operaciones copiadas | resultado medio por operación | t (por cuenta) | aciertos | "
            "al azar: mediana de 100 grupos |", "|---|---|---|---|---|---|---|"]
    for dm in (5, 15, 60):
        for hh, hn in ((3600, "1 h"), (4 * 3600, "4 h"), (24 * 3600, "24 h")):
            per_acc, allr = [], []
            for n in top:
                r = copy_ret(acc[n]["fills"], dm * 60, hh)
                if len(r) >= 3:
                    per_acc.append(sum(r) / len(r))
                allr += r
            if not allr:
                continue
            rr = random.Random(2)
            nulls = []
            for _ in range(100):
                rs = []
                for n in rr.sample(names, k):
                    rs += copy_ret(acc[n]["fills"], dm * 60, hh)
                if rs:
                    nulls.append(sum(rs) / len(rs))
            nulls.sort()
            out.append(f"| {dm} min | {hn} | {len(allr):,} | {sum(allr) / len(allr) * 100:+.3f}% | {tstat(per_acc):.1f} ({len(per_acc)}) | "
                       f"{sum(v > 0 for v in allr) / len(allr) * 100:.0f}% | {nulls[len(nulls) // 2] * 100:+.3f}% |")
    out += ["", "Coste 0,13% ida y vuelta. Para que valga: positivo con t > 2 y claramente por encima del grupo al azar. "
            "Probé 9 combinaciones; una positiva suelta puede ser azar."]
    (ROOT / "docs" / "hl_wallet_follow.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "analyze"])
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--days", type=int, default=60)
    a = ap.parse_args()
    (cmd_fetch if a.cmd == "fetch" else cmd_analyze)(a)


if __name__ == "__main__":
    main()
