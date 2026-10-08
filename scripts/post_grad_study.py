"""Memecoins AFTER graduation (PumpSwap/Raydium AMM), where fees are ~0.3% per side instead of 1.25% on the pump.fun curve.

    uv run --with duckdb python scripts/post_grad_study.py fetch   --data data/raw --days 5     # ~1 h per 900 tokens, resumable
    uv run --with duckdb python scripts/post_grad_study.py analyze --cost 0.005

fetch: every graduation recorded in pumpfun_completes (all of them, no selection by outcome) that is at least 5 h old.
  GeckoTerminal (free, ~30 calls/min): token -> pools (the AMM pool with the most liquidity) -> 240 one-minute candles
  (USD price and volume) starting when the pool opened. Cached per mint in data/research/postgrad/.
analyze: at minute K after the pool opened (K = 3, 10, 30) decide ONLY with what is known by then (return since the
  pool's first price, drawdown from the high so far, volume so far) and buy at that candle's close; exit at the first 1-min
  candle that crosses take-profit or stop (stop assumed first if both), else after 120 min. Cost per side --cost
  (0.5% = 0.25% AMM fee + 0.25% slippage on a small order). Decisions and exits use closing prices only (see simulate). Groups:
    todos | dump (cayó >= 30% desde el máximo) | momentum (subió >= 50% desde el primer precio) | con volumen alto (>= mediana)
  Reports mean net per trade, % that hit TP, halves, best/worst day, and a sensitivity to 2x the cost.
"""
import argparse
import json
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
BASE = ROOT / "data" / "research" / "postgrad"
G = "https://api.geckoterminal.com/api/v2/networks/solana"
AMM = ("pumpswap", "raydium", "raydium-clmm", "raydium-cp")
_last = [0.0]


def call(path, params=None, gap=2.2, tries=6):
    q = "?" + "&".join(f"{k}={v}" for k, v in (params or {}).items()) if params else ""
    for i in range(tries):
        wait = gap - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(G + path + q, headers={"Accept": "application/json", "User-Agent": "quant-os"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(30 * (i + 1) if e.code == 429 else 3 + 3 * i)
        except Exception:
            time.sleep(3 + 3 * i)
    return None


def graduates(data: Path, days: float):
    import duckdb
    from recordings_summary import is_valid_parquet
    d = data / "pumpfun" / "table=pumpfun_completes"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)]
    if not files:
        raise SystemExit("No hay pumpfun_completes en --data")
    now = time.time()
    rows = duckdb.connect().execute(
        "SELECT mint, MIN(ts_received_utc_ns)/1e9 AS t FROM read_parquet([" + ",".join(f"'{p}'" for p in files) +
        f"], union_by_name=true) GROUP BY 1 HAVING MIN(ts_received_utc_ns)/1e9 BETWEEN {now - days * 86400} AND {now - 5 * 3600} "
        "ORDER BY t DESC").fetchall()
    return rows


def cmd_fetch(a):
    BASE.mkdir(parents=True, exist_ok=True)
    todo = [(m, t) for m, t in graduates(a.data, a.days) if not (BASE / f"{m}.json").exists()]
    print(f"{len(todo):,} graduados por consultar (~{len(todo) * 2 * 2.2 / 3600:.1f} h).", flush=True)
    n = ok = 0
    for m, t in todo:
        out = {"mint": m, "grad_t": t, "pool": None, "candles": []}
        d = call(f"/tokens/{m}/pools", {"page": 1})
        pools = [p for p in ((d or {}).get("data") or []) if p["relationships"]["dex"]["data"]["id"] in AMM]
        if pools:
            p = max(pools, key=lambda p: float(p["attributes"].get("reserve_in_usd") or 0))
            out["pool"] = p["attributes"]["address"]
            o = call(f"/pools/{out['pool']}/ohlcv/minute", {"aggregate": 1, "limit": 1000,
                                                              "before_timestamp": int(t + 4 * 3600)})
            l = (((o or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
            out["candles"] = sorted(l)             # [ts, o, h, l, c, v]
            ok += bool(out["candles"])
        (BASE / f"{m}.json").write_text(json.dumps(out))
        n += 1
        if n % 50 == 0:
            print(f"  {n:,}/{len(todo):,} consultados, {ok} con velas", flush=True)
    print(f"Listo: {n:,} consultados, {ok} con velas.")


def fill_minutes(c):
    """GeckoTerminal leaves out the minutes without trades: rebuild a candle for EVERY minute (flat at the last close, zero
    volume) so that 'minute K' and 'hold 120 candles' really mean minutes. Capped at 4 h from the first trade."""
    if not c:
        return []
    c = sorted(c)
    t0, out, j, last = int(c[0][0]) // 60 * 60, [], 0, c[0][4]
    for k in range(240):
        t = t0 + 60 * k
        if j < len(c) and int(c[j][0]) // 60 * 60 == t:
            out.append(list(c[j]))
            last = c[j][4]
            j += 1
        else:
            out.append([t, last, last, last, last, 0.0])
        if j >= len(c) and t > c[-1][0]:
            break
    return out


def simulate(c, i, tp, sl, cost, hold=120):
    """c: candles sorted [ts,o,h,l,c,v]; enter at the close of candle i. Decisions use CLOSES only: one-minute wicks in thin
    pools are often garbage ticks (a 900x spike with a flat close) and would invent take-profits that never existed."""
    entry = c[i][4]
    for j in range(i + 1, min(len(c), i + 1 + hold)):
        px = c[j][4]
        if px <= entry * sl:
            return px / entry * (1 - cost) / (1 + cost) - 1, False
        if px >= entry * tp:
            return px / entry * (1 - cost) / (1 + cost) - 1, True
    j = min(len(c) - 1, i + hold)
    return c[j][4] / entry * (1 - cost) / (1 + cost) - 1, False


def tstat(x):
    import math
    n = len(x)
    if n < 3:
        return float("nan")
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return m / (sd / math.sqrt(n)) if sd > 0 else float("nan")


def cmd_analyze(a):
    toks = []
    for f in BASE.glob("*.json"):
        d = json.loads(f.read_text())
        c = fill_minutes([x for x in d["candles"] if x[4] > 0])
        if len(c) >= 40:
            toks.append((d["mint"], d["grad_t"], c))
    out = ["# Memecoins después de graduarse (AMM): ¿hay una regla que pague con comisiones bajas?", "",
           f"{len(toks):,} graduados con velas de 1 minuto (de {len(list(BASE.glob('*.json'))):,} consultados). "
           f"Costo {a.cost * 100:.2f}% por lado (mitad comisión del AMM, mitad deslizamiento). Se decide solo con lo conocido "
           "hasta el minuto K y se compra al cierre de esa vela.", ""]
    if len(toks) < a.min_tokens:
        out.append("Pocos todavía: dejar que termine el fetch.")
        Path(ROOT / "docs" / "post_grad_study.md").write_text("\n".join(out), encoding="utf-8")
        print("\n".join(out))
        return
    cut = sorted(t for _, t, _ in toks)[len(toks) // 2]
    rules = [(1.3, 0.85), (1.5, 0.8), (2.0, 0.7)]
    for K in (3, 10, 30):
        rows = []
        for m, t, c in toks:
            if len(c) <= K + 5:
                continue
            p0, hi = c[0][4], max(x[4] for x in c[:K + 1])
            px = c[K][4]
            vol = sum(x[5] for x in c[:K + 1])
            rows.append({"m": m, "t": t, "i": K, "c": c, "ret": px / p0 - 1, "dd": px / hi - 1, "vol": vol})
        medv = sorted(r["vol"] for r in rows)[len(rows) // 2]
        groups = [("todos", rows), ("dump: cayó ≥ 30% desde el máximo", [r for r in rows if r["dd"] <= -0.30]),
                  ("momentum: subió ≥ 50% desde el primer precio", [r for r in rows if r["ret"] >= 0.50]),
                  ("volumen ≥ mediana", [r for r in rows if r["vol"] >= medv]),
                  ("dump y volumen ≥ mediana", [r for r in rows if r["dd"] <= -0.30 and r["vol"] >= medv])]
        out += [f"## Entrada al minuto {K} después de abrir el pool", "",
                "| grupo | " + " | ".join(f"TP +{int((tp - 1) * 100)}% / SL -{int((1 - sl) * 100)}%" for tp, sl in rules) + " |",
                "|---|" + "---|" * len(rules)]
        for name, g in groups:
            cells = []
            for tp, sl in rules:
                if len(g) < a.min_group:
                    cells.append("(pocos)")
                    continue
                res = [simulate(r["c"], r["i"], tp, sl, a.cost)[0] for r in g]
                m_ = sum(res) / len(res) * 100
                cells.append(f"**{m_:+.2f}%** ({len(g)})" if m_ > 0 else f"{m_:+.2f}% ({len(g)})")
            out.append(f"| {name} | " + " | ".join(cells) + " |")
        out.append("")
        # positives: halves, days, double cost
        pos = []
        for name, g in groups:
            for tp, sl in rules:
                if len(g) >= a.min_group:
                    res = [simulate(r["c"], r["i"], tp, sl, a.cost)[0] for r in g]
                    if sum(res) / len(res) > 0:
                        pos.append((name, tp, sl, g, res))
        if pos:
            out += ["| positivas | regla | n | medio | 1ª mitad | 2ª mitad | acierta TP | mejor / peor día | con costo ×2 | t |",
                    "|---|---|---|---|---|---|---|---|---|---|"]
            for name, tp, sl, g, res in pos:
                h1 = [x for x, r in zip(res, g) if r["t"] < cut]
                h2 = [x for x, r in zip(res, g) if r["t"] >= cut]
                day = defaultdict(list)
                for x, r in zip(res, g):
                    day[int(r["t"] // 86400)].append(x)
                dm = [sum(v) / len(v) * 100 for v in day.values()]
                hit = sum(simulate(r["c"], r["i"], tp, sl, a.cost)[1] for r in g) / len(g) * 100
                res2 = [simulate(r["c"], r["i"], tp, sl, a.cost * 2)[0] for r in g]
                out.append(f"| {name} | +{int((tp - 1) * 100)}% / -{int((1 - sl) * 100)}% | {len(g)} | {sum(res) / len(res) * 100:+.2f}% | "
                           f"{sum(h1) / max(len(h1), 1) * 100:+.2f}% | {sum(h2) / max(len(h2), 1) * 100:+.2f}% | {hit:.0f}% | "
                           f"{max(dm):+.1f}% / {min(dm):+.1f}% | {sum(res2) / len(res2) * 100:+.2f}% | {tstat(res):.1f} |")
            out.append("")
    out += ["Probé 3 minutos de entrada × 5 grupos × 3 reglas = 45 combinaciones: alguna positiva puede ser azar. "
            "Sirve solo si es positiva en las dos mitades, sobrevive al costo ×2 y no depende de un solo día."]
    Path(ROOT / "docs" / "post_grad_study.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "analyze"])
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--days", type=float, default=5)
    ap.add_argument("--cost", type=float, default=0.005)
    ap.add_argument("--min-tokens", type=int, default=50)
    ap.add_argument("--min-group", type=int, default=30)
    a = ap.parse_args()
    (cmd_fetch if a.cmd == "fetch" else cmd_analyze)(a)


if __name__ == "__main__":
    main()
