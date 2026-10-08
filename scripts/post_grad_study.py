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


class ApiError(RuntimeError):
    """Rate limit / network failure: NOT the same as 'this token has no pool' (404), so it must not be cached as empty."""


def call(path, params=None, gap=2.6, tries=5):
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
    raise ApiError(path)


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


DEX = "https://api.dexscreener.com/tokens/v1/solana/"
_gap = [4.0]                      # adaptive pause between GeckoTerminal calls (its real limit is well below the advertised 30/min)


def pools_by_dexscreener(mints):
    """Best AMM pool per mint, 30 mints per DexScreener call (its limit is ~300/min): saves half of the GeckoTerminal calls."""
    out = {}
    for i in range(0, len(mints), 30):
        chunk = mints[i:i + 30]
        for k in range(4):
            try:
                req = urllib.request.Request(DEX + ",".join(chunk), headers={"User-Agent": "quant-os", "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    pairs = json.loads(r.read())
                break
            except Exception:
                pairs = None
                time.sleep(3 + 3 * k)
        if pairs is None:
            raise ApiError("dexscreener")
        for x in pairs:
            m = (x.get("baseToken") or {}).get("address")
            if m in chunk and x.get("dexId") in AMM:
                liq = float((x.get("liquidity") or {}).get("usd") or 0)
                if m not in out or liq > out[m][1]:
                    out[m] = (x["pairAddress"], liq)
        time.sleep(0.3)
    return {m: v[0] for m, v in out.items()}


def candles_for(pool, t):
    """One GeckoTerminal call; the pause adapts: slower after a 429, slowly faster after successes."""
    for i in range(6):
        wait = _gap[0] - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(f"{G}/pools/{pool}/ohlcv/minute?aggregate=1&limit=1000&before_timestamp={int(t + 4 * 3600)}",
                                         headers={"Accept": "application/json", "User-Agent": "quant-os"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            _gap[0] = max(3.5, _gap[0] * 0.97)
            return sorted(((d.get("data") or {}).get("attributes") or {}).get("ohlcv_list") or [])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            _gap[0] = min(20.0, _gap[0] * 1.5)
            time.sleep(10 if e.code == 429 else 3 + 3 * i)
        except Exception:
            time.sleep(3 + 3 * i)
    raise ApiError(pool)


def cmd_fetch(a):
    BASE.mkdir(parents=True, exist_ok=True)
    if a.retry_empty:                    # entries cached as empty by an older version that mistook rate limits for 'no pool'
        n_del = 0
        for f in BASE.glob("*.json"):
            try:
                if not json.loads(f.read_text()).get("candles"):
                    f.unlink()
                    n_del += 1
            except ValueError:
                f.unlink()
        print(f"--retry-empty: {n_del} entradas sin velas borradas para reintentarlas.", flush=True)
    todo = [(m, t) for m, t in graduates(a.data, a.days) if not (BASE / f"{m}.json").exists()]
    if a.max_tokens:
        todo = todo[:a.max_tokens]
    print(f"{len(todo):,} graduados por consultar (~{len(todo) * 4 / 3600:.1f} h a ~15 por minuto; el ritmo real lo marca "
          f"GeckoTerminal). Más nuevos primero: un corte parcial sirve.", flush=True)
    n = ok = fails = 0
    for i in range(0, len(todo), 30):
        chunk = todo[i:i + 30]
        try:
            pools = pools_by_dexscreener([m for m, _ in chunk])
        except ApiError:
            print("  DexScreener no respondió; reintento en 60 s", flush=True)
            time.sleep(60)
            continue
        for m, t in chunk:
            out = {"mint": m, "grad_t": t, "pool": pools.get(m), "candles": []}
            if out["pool"]:
                try:
                    out["candles"] = candles_for(out["pool"], t)
                except ApiError:
                    fails += 1
                    print(f"  fallo de la API en {m[:8]}… (no se guarda; se reintenta en la próxima corrida). Fallos: {fails}", flush=True)
                    time.sleep(60)
                    continue
                ok += bool(out["candles"])
            (BASE / f"{m}.json").write_text(json.dumps(out))
            n += 1
            if n % 25 == 0:
                print(f"  {n:,}/{len(todo):,} consultados, {ok} con velas, {fails} fallos, pausa actual {_gap[0]:.1f} s", flush=True)
    print(f"Listo: {n:,} consultados, {ok} con velas, {fails} fallos (relanzar para reintentarlos).")


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


def curve_features(data: Path, mints):
    """What happened on the bonding curve, per graduated mint, using ONLY events before the graduation:
    minutes to graduate, distinct buyers, SOL bought, share of the bought supply still held by the early wallets (those that
    bought in the first 5 min), creator's earlier graduations, and whether a paid push / Telegram call came before it."""
    import duckdb
    import pandas as pd
    from recordings_summary import is_valid_parquet

    def src(venue, table):
        d = data / venue / f"table={table}"
        fs = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
        return "read_parquet([" + ",".join(f"'{x}'" for x in fs) + "], union_by_name=true)" if fs else None
    trs, crs, cps = src("pumpfun", "pumpfun_trades"), src("pumpfun", "pumpfun_creates"), src("pumpfun", "pumpfun_completes")
    if not (trs and crs and cps):
        return {}
    con = duckdb.connect()
    con.execute("PRAGMA temp_directory='.duckdb_tmp'")
    con.register("want", pd.DataFrame({"mint": list(mints)}))
    con.execute(f"""CREATE TABLE g AS SELECT mint, MIN(ts_received_utc_ns)/1e9 AS gt FROM {cps}
        WHERE mint IN (SELECT mint FROM want) GROUP BY 1""")
    con.execute(f"""CREATE TABLE b AS SELECT mint, MIN(ts_received_utc_ns)/1e9 AS born, arg_min(creator, ts_received_utc_ns) AS creator
        FROM {crs} WHERE mint IN (SELECT mint FROM want) GROUP BY 1""")
    con.execute(f"""CREATE TABLE tf AS SELECT DISTINCT t.signature, t.mint, t.ts_received_utc_ns/1e9 AS ts, t."user" AS u, t.is_buy,
        t.sol_amount::DOUBLE/1e9 AS sol, t.token_amount::DOUBLE AS tok
        FROM {trs} t JOIN g USING (mint) WHERE t.ts_received_utc_ns/1e9 <= g.gt""")
    con.execute("""CREATE TABLE f1 AS SELECT tf.mint, COUNT(DISTINCT u) FILTER (WHERE is_buy) AS buyers_curve,
        SUM(sol) FILTER (WHERE is_buy) AS sol_curve FROM tf GROUP BY 1""")
    con.execute("""CREATE TABLE early AS SELECT DISTINCT tf.mint, tf.u FROM tf JOIN b USING (mint)
        WHERE tf.is_buy AND tf.ts <= b.born + 300""")
    con.execute("""CREATE TABLE pos AS SELECT mint, u, SUM(CASE WHEN is_buy THEN tok ELSE -tok END) AS net FROM tf GROUP BY 1, 2""")
    con.execute("""CREATE TABLE f2 AS SELECT pos.mint, SUM(GREATEST(net, 0)) FILTER (WHERE (pos.mint, pos.u) IN
        (SELECT mint, u FROM early)) / NULLIF(SUM(GREATEST(net, 0)), 0) AS early_share FROM pos GROUP BY 1""")
    # earlier graduations of the same creator (graduated before this token was born: nothing from the future)
    con.execute(f"""CREATE TABLE cg AS SELECT c.creator, MIN(cp.ts_received_utc_ns)/1e9 AS gt FROM {crs} c JOIN {cps} cp USING (mint)
        GROUP BY c.creator, c.mint""")
    con.execute("""CREATE TABLE f3 AS SELECT b.mint, COUNT(cg.gt) AS creator_prior_grads FROM b LEFT JOIN cg
        ON cg.creator = b.creator AND cg.gt < b.born GROUP BY 1""")
    push = []
    for tbl, col in (("token_boosts", "token_address"), ("token_profiles", "token_address")):
        sp = src("dexscreener", tbl)
        if sp:
            push.append(f"SELECT {col} AS mint, ts_polled_utc_ns/1e9 AS t FROM {sp}")
    orders = ROOT / "data" / "research" / "dex_orders.jsonl"
    if orders.exists():
        rows = []
        for ln in orders.read_text(encoding="utf-8").splitlines():
            try:
                j = json.loads(ln)
            except ValueError:
                continue
            for o in j.get("orders") or []:
                if o.get("paymentTimestamp"):
                    rows.append((j["mint"], o["paymentTimestamp"] / 1000.0))
        if rows:
            con.register("ordf", pd.DataFrame(rows, columns=["mint", "t"]))
            push.append("SELECT mint, t FROM ordf")
    con.execute("CREATE TABLE f4 AS SELECT g.mint, " + ("COUNT(p.t) > 0" if push else "FALSE") + " AS push_before FROM g " +
                (f"LEFT JOIN ({' UNION ALL '.join(push)}) p ON p.mint = g.mint AND p.t < g.gt " if push else "") + "GROUP BY 1")
    calls = src("telegram", "calls")
    con.execute("CREATE TABLE f5 AS SELECT g.mint, " + ("COUNT(c.ts_received_utc_ns) > 0" if calls else "FALSE") + " AS call_before FROM g " +
                (f"LEFT JOIN {calls} c ON c.token_address = g.mint AND c.ts_received_utc_ns/1e9 < g.gt " if calls else "") + "GROUP BY 1")
    df = con.execute("""SELECT g.mint, (g.gt - b.born) / 60 AS min_to_grad, f1.buyers_curve, f1.sol_curve, f2.early_share,
        f3.creator_prior_grads, f4.push_before, f5.call_before FROM g JOIN b USING (mint) LEFT JOIN f1 USING (mint)
        LEFT JOIN f2 USING (mint) LEFT JOIN f3 USING (mint) LEFT JOIN f4 USING (mint) LEFT JOIN f5 USING (mint)""").df()
    return {r.mint: r for r in df.itertuples()}


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
    feats = {}
    if a.data and a.data.exists():
        try:
            feats = curve_features(a.data, [m for m, _, _ in toks])
        except Exception as e:                                   # keep the candle-only study working
            out.append(f"(No pude calcular los datos de la curva: {type(e).__name__}: {str(e)[:120]})")
    fv = lambda m, k: getattr(feats.get(m), k, None) if feats else None   # noqa: E731
    mtg = sorted(v for m, _, _ in toks if (v := fv(m, "min_to_grad")) is not None)
    bcv = sorted(v for m, _, _ in toks if (v := fv(m, "buyers_curve")) is not None)
    q_fast = mtg[len(mtg) // 2] if mtg else None
    q_buy = bcv[len(bcv) // 2] if bcv else None
    if feats:
        out += [f"Datos de la curva cruzados por token (solo eventos antes de graduarse): {len(feats):,}. "
                f"Mediana: {q_fast:.0f} min hasta graduarse, {q_buy:.0f} compradores distintos.", ""]
    rules = [(1.3, 0.85), (1.5, 0.8), (2.0, 0.7)]
    for K in (3, 10, 30):
        rows = []
        for m, t, c in toks:
            if len(c) <= K + 5:
                continue
            p0, hi = c[0][4], max(x[4] for x in c[:K + 1])
            px = c[K][4]
            vol = sum(x[5] for x in c[:K + 1])
            rows.append({"m": m, "t": t, "i": K, "c": c, "ret": px / p0 - 1, "dd": px / hi - 1, "vol": vol,
                         "fast": (fv(m, "min_to_grad") or 1e9) <= (q_fast or -1), "buyers": fv(m, "buyers_curve") or 0,
                         "early": fv(m, "early_share"), "cprior": fv(m, "creator_prior_grads") or 0,
                         "push": bool(fv(m, "push_before")), "call": bool(fv(m, "call_before"))})
        medv = sorted(r["vol"] for r in rows)[len(rows) // 2]
        groups = [("todos", rows), ("dump: cayó ≥ 30% desde el máximo", [r for r in rows if r["dd"] <= -0.30]),
                  ("momentum: subió ≥ 50% desde el primer precio", [r for r in rows if r["ret"] >= 0.50]),
                  ("volumen ≥ mediana", [r for r in rows if r["vol"] >= medv]),
                  ("dump y volumen ≥ mediana", [r for r in rows if r["dd"] <= -0.30 and r["vol"] >= medv])]
        if feats:
            med_early = sorted(r["early"] for r in rows if r["early"] is not None)
            med_early = med_early[len(med_early) // 2] if med_early else None
            groups += [("curva: se graduó rápido (≤ mediana)", [r for r in rows if r["fast"]]),
                       ("curva: se graduó lento", [r for r in rows if not r["fast"]]),
                       ("curva: compradores ≥ mediana", [r for r in rows if r["buyers"] >= q_buy]),
                       ("curva: tempranas aún tienen ≥ mediana", [r for r in rows if med_early is not None and
                                                                    r["early"] is not None and r["early"] >= med_early]),
                       ("curva: tempranas ya vendieron", [r for r in rows if med_early is not None and
                                                           r["early"] is not None and r["early"] < med_early]),
                       ("creador con graduados previos", [r for r in rows if r["cprior"] >= 1]),
                       ("con push pago antes de graduarse", [r for r in rows if r["push"]]),
                       ("con call de Telegram antes", [r for r in rows if r["call"]]),
                       ("rápido y compradores ≥ mediana", [r for r in rows if r["fast"] and r["buyers"] >= q_buy]),
                       ("rápido, compradores ≥ mediana y dump", [r for r in rows if r["fast"] and r["buyers"] >= q_buy and r["dd"] <= -0.30])]
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
    out += [f"Probé 3 minutos de entrada × {len(groups)} grupos × 3 reglas = {3 * len(groups) * 3} combinaciones: alguna positiva puede ser azar. "
            "Sirve solo si es positiva en las dos mitades, sobrevive al costo ×2 y no depende de un solo día."]
    Path(ROOT / "docs" / "post_grad_study.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "analyze"])
    ap.add_argument("--data", type=Path, default=ROOT / "data" / "raw")
    ap.add_argument("--days", type=float, default=5)
    ap.add_argument("--cost", type=float, default=0.005)
    ap.add_argument("--max-tokens", type=int, default=0, help="fetch: only the N most recent graduates")
    ap.add_argument("--retry-empty", action="store_true", help="fetch: re-query entries saved without candles")
    ap.add_argument("--min-tokens", type=int, default=50)
    ap.add_argument("--min-group", type=int, default=30)
    a = ap.parse_args()
    (cmd_fetch if a.cmd == "fetch" else cmd_analyze)(a)


if __name__ == "__main__":
    main()
