"""KOL / influencer cycle on pump.fun: who accumulates before the first X post, when the price peaks after it,
and whether exiting when the pre-post buyers start selling beats fixed exits.

    uv run --with pandas --with numpy python scripts/kol_event_study.py --data "<ruta>/data/raw"

Event = first X post about a mint (x_mentions.earliest_post_utc, first query per mint). Times use chain time
(ts_chain_s) to line up with X's UTC timestamps.
  1. Price path around the post (median, normalised to the price at the post).
  2. "Insiders" = wallets with net buys in the 30 min before the post. How fast do they sell after it?
  3. Trade: enter L seconds after the post (fill after the next trade, fee per side), exit at
     (a) fixed 5/15/60 min, or (b) when insiders have sold >= --insider-exit of what they held (cap 60 min).
Everything also split by halves of time: a rule that works in only one half is noise.
"""
import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from recordings_summary import is_valid_parquet

PATH_MIN = (-30, -15, -5, -1, 0, 1, 5, 15, 30, 60, 120)
PRE_MIN = 30
POST_MAX_MIN = 120


def src(root: Path, table: str):
    d = root / "pumpfun" / f"table={table}"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
    return "read_parquet([" + ",".join(f"'{p}'" for p in files) + "], union_by_name=true)" if files else None


def price_at(t: np.ndarray, px: np.ndarray, when: float) -> float:
    i = np.searchsorted(t, when, side="right") - 1
    return px[i] if i >= 0 else np.nan


def fill_after(t: np.ndarray, px: np.ndarray, when: float):
    i = np.searchsorted(t, when, side="left")
    return (t[i], px[i]) if i < len(t) else (np.nan, np.nan)


def n_accounts(raw) -> int:
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
        return len(v) if isinstance(v, (list, dict)) else 0
    except (ValueError, TypeError):
        return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/kol_event_study.md"))
    ap.add_argument("--fee", type=float, default=1.25, help="cost per side in %%")
    ap.add_argument("--latencies", type=float, nargs="*", default=[10, 60, 300], help="entry delay after the post, s")
    ap.add_argument("--insider-exit", type=float, default=0.3)
    args = ap.parse_args()
    xs, ts = src(args.data, "x_mentions"), src(args.data, "pumpfun_trades")
    if not xs or not ts:
        raise SystemExit("Faltan x_mentions o pumpfun_trades")
    con = duckdb.connect()
    ev = con.execute(f"""SELECT * EXCLUDE (rn) FROM (
        SELECT mint, CAST(epoch(TRY_CAST(earliest_post_utc AS TIMESTAMPTZ)) AS BIGINT) AS post_s, max_followers, posts_found, accounts_json,
               has_large_account, ROW_NUMBER() OVER (PARTITION BY mint ORDER BY ts_query_utc_ns) AS rn
        FROM {xs} WHERE earliest_post_utc IS NOT NULL AND posts_found > 0) WHERE rn = 1 AND post_s IS NOT NULL""").df()
    if ev.empty:
        raise SystemExit("No hay posts con fecha en x_mentions")
    ev["n_accounts"] = ev.accounts_json.map(n_accounts)
    con.register("ev", ev[["mint", "post_s"]])
    tr = con.execute(f"""SELECT DISTINCT t.mint, (CASE WHEN t.ts_chain_s IS NOT NULL AND ABS(t.ts_chain_s - t.ts_received_utc_ns / 1e9) <= 600 THEN t.ts_chain_s ELSE CAST(t.ts_received_utc_ns / 1e9 AS BIGINT) END) AS s, t.slot, t."user" AS u, t.is_buy,
            t.token_amount::DOUBLE AS tok, (t.virtual_sol_reserves::DOUBLE/1e9)/(t.virtual_token_reserves::DOUBLE/1e6) AS px
        FROM {ts} t JOIN ev ON t.mint = ev.mint
        WHERE t.virtual_token_reserves > 0 AND (CASE WHEN t.ts_chain_s IS NOT NULL AND ABS(t.ts_chain_s - t.ts_received_utc_ns / 1e9) <= 600 THEN t.ts_chain_s ELSE CAST(t.ts_received_utc_ns / 1e9 AS BIGINT) END) BETWEEN ev.post_s - {PRE_MIN * 60} AND ev.post_s + {POST_MAX_MIN * 60}
        ORDER BY t.mint, s, t.slot""").df()
    first_s, last_s = (tr.s.min(), tr.s.max()) if len(tr) else (0, 0)
    f = args.fee / 100
    paths, rows = [], []
    by_mint = dict(tuple(tr.groupby("mint")))
    for e in ev.itertuples():
        g = by_mint.get(e.mint)
        p0s = e.post_s
        if g is None or p0s - PRE_MIN * 60 < first_s or p0s + POST_MAX_MIN * 60 > last_s:
            continue  # need the full window inside the recording
        t, px = g.s.values.astype(float), g.px.values
        p0 = price_at(t, px, p0s)
        if not np.isfinite(p0) or p0 <= 0:
            continue
        paths.append({m: price_at(t, px, p0s + m * 60) / p0 for m in PATH_MIN})
        post = g[g.s >= p0s]
        peak_min = (post.s.values[np.argmax(post.px.values)] - p0s) / 60 if len(post) else np.nan
        pre = g[g.s < p0s]
        net = (pre.tok * np.where(pre.is_buy, 1, -1)).groupby(pre.u).sum()
        insiders = net[net > 0]
        held = insiders.sum()
        sells = post[post.u.isin(insiders.index) & ~post.is_buy]
        cum = sells.tok.cumsum().values / held if held > 0 else np.array([])
        sold_at = {m: (cum[sells.s.values <= p0s + m * 60][-1] if len(cum) and (sells.s.values <= p0s + m * 60).any() else 0.0)
                   for m in (5, 15, 30, 60)}
        hit = np.argmax(cum >= args.insider_exit) if len(cum) and (cum >= args.insider_exit).any() else None
        insider_exit_s = sells.s.values[hit] if hit is not None else np.inf
        r = {"mint": e.mint, "post_s": p0s, "peak_min": peak_min, "n_insiders": len(insiders),
             "max_followers": e.max_followers, "n_accounts": e.n_accounts,
             **{f"ins_sold_{m}m": v for m, v in sold_at.items()},
             "pre_ret": price_at(t, px, p0s) / price_at(t, px, p0s - PRE_MIN * 60) - 1}
        for lat in args.latencies:
            te, pin = fill_after(t, px, p0s + lat)
            if not np.isfinite(pin):
                continue
            for m in (5, 15, 60):
                _, pout = fill_after(t, px, te + m * 60)
                pout = pout if np.isfinite(pout) else price_at(t, px, te + m * 60)
                r[f"L{int(lat)}_fix{m}"] = pout * (1 - f) / (pin * (1 + f)) - 1
            x_s = min(max(insider_exit_s, te), te + 3600)
            _, pout = fill_after(t, px, x_s)
            pout = pout if np.isfinite(pout) else price_at(t, px, x_s)
            r[f"L{int(lat)}_ins"] = pout * (1 - f) / (pin * (1 + f)) - 1
        rows.append(r)
    df = pd.DataFrame(rows)
    out = ["# Ciclo influencer en pump.fun: acumulación → post en X → pico → dump", "",
           f"Eventos con ventana completa ({PRE_MIN} min antes, {POST_MAX_MIN} min después del primer post): {len(df)} "
           f"de {len(ev)} tokens con post. Fee {args.fee}% por lado. Insiders = billeteras con compra neta en los "
           f"{PRE_MIN} min previos al post.", ""]
    if df.empty:
        args.output.write_text("\n".join(out + ["Sin eventos suficientes."]), encoding="utf-8")
        print("Sin eventos suficientes")
        return
    cut = df.post_s.median()
    df["half"] = np.where(df.post_s < cut, "H1", "H2")
    pth = pd.DataFrame(paths)
    out += ["## 1. Precio alrededor del post (mediana, 1.00 = precio al momento del post)", "",
            "| " + " | ".join(f"{m:+d}m" for m in PATH_MIN) + " |", "|" + "---|" * len(PATH_MIN),
            "| " + " | ".join(f"{pth[m].median():.2f}" for m in PATH_MIN) + " |", "",
            f"- Suba en los {PRE_MIN} min previos al post (mediana): {df.pre_ret.median() * 100:.0f}% "
            f"(el que llega con el post, llega tarde por esto).",
            f"- Minuto del pico tras el post: mediana {df.peak_min.median():.1f}; "
            + ", ".join(f"≤{k} min: {(df.peak_min <= k).mean() * 100:.0f}%" for k in (1, 5, 15, 30)), "",
            "## 2. Cuándo venden los insiders (fracción de lo que tenían, mediana / p75)", "",
            "| +5m | +15m | +30m | +60m | insiders por token (mediana) |", "|---|---|---|---|---|",
            "| " + " | ".join(f"{df[f'ins_sold_{m}m'].median() * 100:.0f}% / {df[f'ins_sold_{m}m'].quantile(.75) * 100:.0f}%"
                           for m in (5, 15, 30, 60)) + f" | {df.n_insiders.median():.0f} |", "",
            "## 3. Entrar tras el post: salida fija vs salida cuando venden los insiders", "",
            f"Retorno neto en %, medio / mediano / acierto. `ins` = salir cuando los insiders vendieron "
            f"≥{args.insider_exit:.0%} (tope 60 min).", "",
            "| latencia | mitad | n | fijo 5m | fijo 15m | fijo 60m | ins |", "|---|---|---|---|---|---|---|"]
    for lat in args.latencies:
        L = f"L{int(lat)}"
        for half in ("H1", "H2"):
            d = df[df.half == half]
            cells = []
            for k in ("fix5", "fix15", "fix60", "ins"):
                v = d.get(f"{L}_{k}", pd.Series(dtype=float)).dropna()
                cells.append(f"{v.mean() * 100:.1f} / {v.median() * 100:.1f} / {(v > 0).mean() * 100:.0f}%" if len(v) else "-")
            n = d.get(f"{L}_fix5", pd.Series(dtype=float)).notna().sum()
            out.append(f"| {int(lat)}s | {half} | {n} | " + " | ".join(cells) + " |")
    out += ["", "## Cómo leerlo", "",
            "- Si la suba previa al post es grande y el pico llega en pocos minutos: el post ES la salida de los insiders; "
            "entrar con el post solo sirve con latencia de segundos y salida muy rápida.",
            "- Si `ins` gana a las salidas fijas en H1 y H2: vender cuando venden los que entraron antes es una regla de salida real.",
            "- El edge de entrada no está en el post: está en detectar a los insiders ANTES (los grupos de pump_paper). "
            "Este estudio dice cuánto vale llegar antes y cuándo salir."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")


if __name__ == "__main__":
    main()
