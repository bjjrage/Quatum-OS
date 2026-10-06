"""Screen the recordings for tradable edges and write a compact Markdown report.

Usage (from repo root):
    uv run --with pandas --with numpy python scripts/edge_scan.py "<ruta>/data/raw" -o docs/edge_scan_report.md

Studies (all calibrated on the first half of the data, judged on the second half, net of costs):
  A. Binance perp short-horizon: signed trade flow and top-of-book imbalance vs forward mid return.
  B. Binance perp forced liquidations: fade vs follow by liquidation size.
  C. Pump.fun: first-60s features (buyers, SOL bought) vs forward price and graduation.

Truncated parquet files are skipped. Entry is assumed 1 s after the signal (latency).
Read the numbers skeptically: ~4 days of data, overlapping samples, no queue/impact model.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from recordings_summary import is_valid_parquet

OFI_WINDOWS = (5, 30)
HORIZONS = (10, 30, 60, 300)
LIQ_HORIZONS = (10, 30, 60, 300, 900)
PUMP_HORIZONS = (60, 300, 900)
TOP_Q = 0.9


def src(root: Path, venue: str, table: str):
    d = root / venue / f"table={table}"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
    if not files:
        return None
    return "read_parquet([" + ",".join(f"'{p}'" for p in files) + "], union_by_name=true)"


def utc(sec: float) -> str:
    return datetime.fromtimestamp(sec, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


# ---------- Study A: flow / imbalance ----------

def build_symbol_frame(b: pd.DataFrame, tb: pd.DataFrame) -> pd.DataFrame:
    idx = np.arange(int(b.sec.min()), int(b.sec.max()) + 1)
    mid = pd.Series(b.mid.values, index=b.sec.values).reindex(idx)
    sp = pd.Series(b.spread_bps.values, index=b.sec.values).reindex(idx)
    imb = pd.Series(b.imb.values, index=b.sec.values).reindex(idx)
    t = tb.set_index("sec").reindex(idx).fillna(0.0)
    out = pd.DataFrame({"sec": idx})
    for w in OFI_WINDOWS:
        v = t.v.rolling(w).sum().replace(0, np.nan)
        out[f"ofi_{w}"] = (t.sv.rolling(w).sum() / v).values
        out[f"imb_{w}"] = imb.rolling(w, min_periods=1).mean().values
    entry = mid.shift(-1)
    for h in HORIZONS:
        out[f"fwd_{h}"] = ((mid.shift(-(1 + h)) / entry - 1) * 1e4).values
    out["sp"] = sp.shift(-1).values
    out.loc[mid.isna().values, :] = np.nan
    out["sec"] = idx
    return out.dropna(subset=["sec"])


def pct_from_is(d: pd.DataFrame, sig: str, cut: float) -> pd.Series:
    out = pd.Series(np.nan, index=d.index)
    for _, g in d.groupby("symbol"):
        ref = np.sort(g.loc[g.sec < cut, sig].values)
        if len(ref) < 1000:
            continue
        out.loc[g.index] = np.searchsorted(ref, g[sig].values, side="right") / len(ref)
    return out


def tstat_by_hour(sec: pd.Series, pnl: pd.Series) -> float:
    blocks = pnl.groupby((sec // 3600).values).mean()
    if len(blocks) < 3 or blocks.std() == 0:
        return float("nan")
    return float(blocks.mean() / (blocks.std() / np.sqrt(len(blocks))))


def eval_flow(df: pd.DataFrame, sig: str, h: int, fee_bps: float) -> dict | None:
    d = df[["sec", "symbol", sig, f"fwd_{h}", "sp"]].dropna().reset_index(drop=True)
    if len(d) < 20000:
        return None
    cut = d.sec.min() + (d.sec.max() - d.sec.min()) / 2
    d["pct"] = pct_from_is(d, sig, cut)
    d = d.dropna(subset=["pct"])
    d["dir"] = np.where(d.pct >= TOP_Q, 1, np.where(d.pct <= 1 - TOP_Q, -1, 0))
    res = {}
    for name, part in (("is", d[d.sec < cut]), ("oos", d[d.sec >= cut])):
        tr = part[part.dir != 0]
        pnl = tr.dir * tr[f"fwd_{h}"]
        cost = 2 * fee_bps + tr.sp
        res[f"{name}_n"] = len(tr)
        res[f"{name}_gross"] = float(pnl.mean()) if len(tr) else np.nan
        res[f"{name}_net"] = float((pnl - cost).mean()) if len(tr) else np.nan
        if name == "oos":
            res["oos_t"] = tstat_by_hour(tr.sec, pnl - cost) if len(tr) else np.nan
            res["oos_ic"] = float(part.pct.rank().corr(part[f"fwd_{h}"].rank()))
    return res


def study_flow(con, root: Path, fee_bps: float, n_sym: int, notes: list) -> list[str]:
    bbo, trd = src(root, "binance_perp", "bbo_ticks"), src(root, "binance_perp", "trade_ticks")
    if not bbo or not trd:
        return ["## A. Flujo / imbalance\n\nFaltan tablas bbo_ticks o trade_ticks.\n"]
    con.execute(f"""CREATE TABLE bars AS SELECT symbol, CAST(floor(ts_exchange_ns/1e9) AS BIGINT) AS sec,
        arg_max((bid_price+ask_price)/2, ts_exchange_ns) AS mid,
        arg_max((ask_price-bid_price)/((bid_price+ask_price)/2)*1e4, ts_exchange_ns) AS spread_bps,
        avg((bid_size-ask_size)/NULLIF(bid_size+ask_size,0)) AS imb
        FROM {bbo} WHERE ts_exchange_ns IS NOT NULL AND bid_price>0 AND ask_price>=bid_price GROUP BY 1,2""")
    sides = con.execute(f"SELECT side, COUNT(*) FROM {trd} GROUP BY 1").fetchall()
    notes.append(f"Valores de `side` en trade_ticks (se asume buy/b = +1, resto = -1): {sides}")
    con.execute(f"""CREATE TABLE tbars AS SELECT symbol, CAST(floor(ts_exchange_ns/1e9) AS BIGINT) AS sec,
        SUM(size*CASE WHEN lower(side) IN ('buy','b') THEN 1 ELSE -1 END) AS sv, SUM(size) AS v
        FROM {trd} WHERE ts_exchange_ns IS NOT NULL GROUP BY 1,2""")
    top = [r[0] for r in con.execute(f"SELECT symbol FROM bars GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT {n_sym}").fetchall()]
    frames = []
    for s in top:
        b = con.execute("SELECT * FROM bars WHERE symbol=? ORDER BY sec", [s]).df()
        tb = con.execute("SELECT sec, sv, v FROM tbars WHERE symbol=? ORDER BY sec", [s]).df()
        f = build_symbol_frame(b, tb)
        f["symbol"] = s
        frames.append(f)
    df = pd.concat(frames, ignore_index=True)
    lines = ["## A. Flujo de órdenes e imbalance (Binance perp)", "",
             f"Símbolos: {', '.join(top)}. Señal en el decil extremo (calibrado en la 1ª mitad), entrada +1 s, "
             f"costo = 2×{fee_bps} bps de fee + spread. Valores en bps por trade.", "",
             "| señal | horizonte | n OOS | bruto IS | bruto OOS | neto OOS | t (por hora) | IC OOS |", "|---|---|---|---|---|---|---|---|"]
    for sig in [f"ofi_{w}" for w in OFI_WINDOWS] + [f"imb_{w}" for w in OFI_WINDOWS]:
        for h in HORIZONS:
            r = eval_flow(df, sig, h, fee_bps)
            if r:
                lines.append(f"| {sig} | {h}s | {r['oos_n']:,} | {r['is_gross']:.2f} | {r['oos_gross']:.2f} | "
                             f"{r['oos_net']:.2f} | {r['oos_t']:.1f} | {r['oos_ic']:.3f} |")
    return lines + [""]


# ---------- Study B: liquidations ----------

def study_liq(con, root: Path, fee_bps: float) -> list[str]:
    liq = src(root, "binance_perp", "forced_liquidations")
    if not liq or "bars" not in [r[0] for r in con.execute("SHOW TABLES").fetchall()]:
        return ["## B. Liquidaciones\n\nFaltan datos.\n"]
    ev = con.execute(f"""SELECT DISTINCT symbol, CAST(floor(ts_exchange_ns/1e9) AS BIGINT) AS sec, upper(side) AS side,
        price*executed_qty AS notional FROM {liq} WHERE ts_exchange_ns IS NOT NULL AND executed_qty>0""").df()
    ev = ev.dropna()
    ev["pct"] = ev.groupby("symbol").notional.rank(pct=True)
    ev["bucket"] = pd.cut(ev.pct, [0, 0.9, 0.99, 1.0], labels=["<p90", "p90-99", ">=p99"])
    ev["dir"] = np.where(ev.side == "SELL", 1, -1)  # SELL = long liquidated -> fade by buying
    cut = ev.sec.min() + (ev.sec.max() - ev.sec.min()) / 2
    ev["half"] = np.where(ev.sec < cut, 1, 2)
    mids = {s: g.set_index("sec").mid for s, g in con.execute("SELECT symbol, sec, mid FROM bars").df().groupby("symbol")}
    sps = {s: g.set_index("sec").spread_bps for s, g in con.execute("SELECT symbol, sec, spread_bps FROM bars").df().groupby("symbol")}
    lines = ["## B. Liquidaciones forzadas (fade = comprar tras liquidar largos, vender tras liquidar cortos)", "",
             f"Entrada +1 s, costo = 2×{fee_bps} bps + spread. Valores en bps; `follow` es el signo opuesto (= -fade bruto).", "",
             "| tamaño | horizonte | n | fade bruto H1 | fade bruto H2 | fade neto H2 | acierto fade H2 |", "|---|---|---|---|---|---|---|"]
    for h in LIQ_HORIZONS:
        parts = []
        for s, g in ev.groupby("symbol"):
            if s not in mids:
                continue
            m = mids[s]
            e0 = m.reindex(g.sec.values + 1).values
            e1 = m.reindex(g.sec.values + 1 + h).values
            sp = sps[s].reindex(g.sec.values + 1).values
            gg = g.copy()
            gg["ret"] = gg.dir.values * (e1 / e0 - 1) * 1e4
            gg["net"] = gg.ret - (2 * fee_bps + sp)
            parts.append(gg.dropna(subset=["ret", "net"]))
        if not parts:
            continue
        r = pd.concat(parts)
        for bk in ["<p90", "p90-99", ">=p99"]:
            x = r[r.bucket == bk]
            h1, h2 = x[x.half == 1], x[x.half == 2]
            if len(x) < 30:
                continue
            lines.append(f"| {bk} | {h}s | {len(x):,} | {h1.ret.mean():.2f} | {h2.ret.mean():.2f} | "
                         f"{h2.net.mean():.2f} | {(h2.ret > 0).mean() * 100:.0f}% |")
    return lines + [""]


# ---------- Study C: pump.fun ----------

def study_pump(con, root: Path, fee_pct: float) -> list[str]:
    cr, tr, cp = src(root, "pumpfun", "pumpfun_creates"), src(root, "pumpfun", "pumpfun_trades"), src(root, "pumpfun", "pumpfun_completes")
    if not (cr and tr):
        return ["## C. Pump.fun\n\nFaltan datos.\n"]
    con.execute(f"""CREATE TABLE pt AS SELECT mint, ts_received_utc_ns AS ts, is_buy, "user" AS u, sol_amount,
        virtual_sol_reserves::DOUBLE/NULLIF(virtual_token_reserves,0) AS px FROM (SELECT DISTINCT * FROM {tr})
        WHERE virtual_token_reserves>0 AND virtual_sol_reserves>0""")
    con.execute(f"CREATE TABLE pc AS SELECT mint, MIN(ts_received_utc_ns) AS t0 FROM {cr} GROUP BY 1")
    grad = "SELECT DISTINCT mint FROM " + cp if cp else "SELECT NULL::VARCHAR AS mint WHERE false"
    con.execute(f"""CREATE TABLE pf AS SELECT pc.mint, pc.t0, CAST(pc.t0 + 60e9 AS BIGINT) AS te, COUNT(*) AS n,
        COUNT(DISTINCT u) FILTER (WHERE is_buy) AS buyers,
        SUM(CASE WHEN is_buy THEN sol_amount ELSE 0 END)/1e9 AS buy_sol,
        SUM(CASE WHEN is_buy THEN sol_amount ELSE -sol_amount END)/1e9 AS net_sol,
        (pc.mint IN ({grad})) AS graduated
        FROM pc JOIN pt USING(mint) WHERE pt.ts BETWEEN pc.t0 AND pc.t0 + 60e9 GROUP BY pc.mint, pc.t0, graduated""")
    maxts = con.execute("SELECT MAX(ts) FROM pt").fetchone()[0]
    sel, joins = ["pf.*", "e.px AS px0"], ["ASOF JOIN pt e ON pf.mint = e.mint AND pf.te >= e.ts"]
    for i, h in enumerate(PUMP_HORIZONS):
        sel += [f"x{i}.px AS px_{h}", f"x{i}.ts AS ts_{h}"]
        joins.append(f"ASOF JOIN pt x{i} ON pf.mint = x{i}.mint AND CAST(pf.te + {int(h * 1e9)} AS BIGINT) >= x{i}.ts")
    df = con.execute(f"SELECT {', '.join(sel)} FROM pf {' '.join(joins)} WHERE pf.te + {int(max(PUMP_HORIZONS) * 1e9)} <= {maxts}").df()
    df = df.dropna(subset=["px0"])
    cut = df.t0.median()
    df["half"] = np.where(df.t0 < cut, 1, 2)
    f = fee_pct / 100
    lines = ["## C. Pump.fun: features de los primeros 60 s", "",
             f"Entrada al precio del segundo 60 tras el create, fee {fee_pct}% por lado. Retornos en %. "
             "Sesgo: si el token deja de operar, el precio de salida es el último conocido (optimista); "
             "`stale` es la fracción de salidas sin trade en los 60 s previos.", "",
             f"Mints analizados: {len(df):,}. Graduados: {df.graduated.mean() * 100:.2f}%.", "",
             "| grupo | mitad | horizonte | n | bruto medio | neto medio | neto mediano | acierto neto | stale | graduados |", "|---|---|---|---|---|---|---|---|---|---|"]
    groups = [("todos", pd.Series(True, index=df.index))]
    for feat in ("buyers", "buy_sol", "net_sol"):
        thr = df.loc[df.half == 1, feat].quantile(TOP_Q)
        groups.append((f"top10% {feat}", df[feat] >= thr))
    for name, mask in groups:
        for h in PUMP_HORIZONS:
            for half in (1, 2):
                x = df[mask & (df.half == half)]
                x = x.dropna(subset=[f"px_{h}"])
                if len(x) < 30:
                    continue
                gross = x[f"px_{h}"] / x.px0 - 1
                net = x[f"px_{h}"] * (1 - f) / (x.px0 * (1 + f)) - 1
                stale = ((x.te + h * 1e9 - x[f"ts_{h}"]) > 60e9).mean()
                lines.append(f"| {name} | H{half} | {h}s | {len(x):,} | {gross.mean() * 100:.1f} | {net.mean() * 100:.1f} | "
                             f"{net.median() * 100:.1f} | {(net > 0).mean() * 100:.0f}% | {stale * 100:.0f}% | {x.graduated.mean() * 100:.1f}% |")
    return lines + [""]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/edge_scan_report.md"))
    ap.add_argument("--fee-bps", type=float, default=4.5, help="taker fee per side, Binance perp")
    ap.add_argument("--pump-fee-pct", type=float, default=1.0, help="pump.fun fee per side in %%")
    ap.add_argument("--symbols", type=int, default=6, help="top-N Binance symbols for study A")
    ap.add_argument("--only", choices=["A", "B", "C"], nargs="*", default=["A", "B", "C"])
    args = ap.parse_args()
    con = duckdb.connect()
    con.execute("PRAGMA temp_directory='.duckdb_tmp'")
    notes: list[str] = []
    out = [f"# Edge scan: `{args.root}`", "",
           "Calibrado en la 1ª mitad, evaluado en la 2ª. Con pocos días de datos, desconfiá de todo lo que no sea estable en ambas mitades.", ""]
    if "A" in args.only:
        out += study_flow(con, args.root, args.fee_bps, args.symbols, notes)
    if "B" in args.only:
        out += study_liq(con, args.root, args.fee_bps)
    if "C" in args.only:
        out += study_pump(con, args.root, args.pump_fee_pct)
    if notes:
        out += ["## Notas", ""] + [f"- {n}" for n in notes]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")


if __name__ == "__main__":
    main()
