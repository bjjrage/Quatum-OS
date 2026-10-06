"""Does X (sentiment) add anything to on-chain data on pump.fun? Uses what the recorder already saved.

    uv run --with pandas --with numpy python scripts/x_vs_onchain.py --data "<ruta>/data/raw"

For every mint the X watcher queried (first query per mint), simulate entering after the query and compare
outcomes by X features (posts found, large account, coordinated shilling) INSIDE the same on-chain strength
bucket (unique buyers in 5 min). If X has value, it must separate winners from losers among tokens that look the
same on-chain. Calibrated on the first half by time, every number also shown for the second half.

Execution: fill at the price after the first trade >= query time + latency (we arrive late), cost per side
--fee (default 1.25%) as in src/paper/pump_paper.py. Exits: fixed horizons, and the pump_paper ladder trigger
(does it touch 2x before -50% within 2 h?).
Bias warning: a token that stops trading keeps its last price (optimistic); `stale` reports how often.
"""
import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from recordings_summary import is_valid_parquet

HORIZONS_MIN = (5, 15, 60)


def src(root: Path, table: str):
    d = root / "pumpfun" / f"table={table}"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
    return "read_parquet([" + ",".join(f"'{p}'" for p in files) + "], union_by_name=true)" if files else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/x_vs_onchain_report.md"))
    ap.add_argument("--fee", type=float, default=1.25, help="cost per side in %%")
    ap.add_argument("--latency-s", type=float, default=2.0)
    args = ap.parse_args()
    xs, ts = src(args.data, "x_mentions"), src(args.data, "pumpfun_trades")
    if not xs or not ts:
        raise SystemExit("Faltan x_mentions o pumpfun_trades")
    con = duckdb.connect()
    con.execute(f"""CREATE TABLE pt AS SELECT DISTINCT mint, ts_received_utc_ns AS ts,
        (virtual_sol_reserves::DOUBLE/1e9)/(virtual_token_reserves::DOUBLE/1e6) AS px
        FROM {ts} WHERE virtual_token_reserves>0 AND virtual_sol_reserves>0""")
    con.execute("CREATE INDEX IF NOT EXISTS pt_m ON pt(mint)")
    status = con.execute(f"SELECT x_status, COUNT(*) FROM {xs} GROUP BY 1 ORDER BY 2 DESC").fetchall()
    consumers = con.execute(f"SELECT consumer, COUNT(*) FROM {xs} GROUP BY 1 ORDER BY 2 DESC").fetchall()
    cost_usd = con.execute(f"SELECT SUM(cost_usd) FROM {xs}").fetchone()[0]
    con.execute(f"""CREATE TABLE xm AS SELECT * EXCLUDE (rn) FROM (
        SELECT mint, ts_query_utc_ns AS tq, CAST(ts_query_utc_ns + {int(args.latency_s * 1e9)} AS BIGINT) AS te,
               unique_buyers_5m, net_buy_sol_5m, token_age_s, posts_found, max_followers, total_followers,
               has_large_account, coordinated_shilling, x_status, consumer,
               ROW_NUMBER() OVER (PARTITION BY mint ORDER BY ts_query_utc_ns) AS rn
        FROM {xs} WHERE posts_found IS NOT NULL) WHERE rn = 1""")
    # entry: first trade at/after te (ASOF on the reversed inequality)
    con.execute("""CREATE TABLE en AS SELECT xm.*, t.ts AS ts_in, t.px AS px_in
        FROM xm ASOF JOIN pt t ON xm.mint = t.mint AND xm.te <= t.ts""")
    maxts = con.execute("SELECT MAX(ts) FROM pt").fetchone()[0]
    sel, joins = ["en.*"], []
    for i, h in enumerate(HORIZONS_MIN):
        sel += [f"x{i}.px AS px_{h}", f"x{i}.ts AS tx_{h}"]
        joins.append(f"ASOF JOIN pt x{i} ON en.mint = x{i}.mint AND CAST(en.ts_in + {h * 60 * 10**9} AS BIGINT) >= x{i}.ts")
    con.execute(f"CREATE TABLE ex AS SELECT {', '.join(sel)} FROM en {' '.join(joins)} "
                f"WHERE en.ts_in + {max(HORIZONS_MIN) * 60 * 10**9} <= {maxts}")
    path = con.execute("""SELECT ex.mint,
            MIN(t.ts) FILTER (WHERE t.px >= 2 * ex.px_in) AS t2x,
            MIN(t.ts) FILTER (WHERE t.px <= 0.5 * ex.px_in) AS thalf,
            MAX(t.px) / ANY_VALUE(ex.px_in) AS max_mult
        FROM ex JOIN pt t ON t.mint = ex.mint AND t.ts > ex.ts_in AND t.ts <= ex.ts_in + 7200 * 1000000000::BIGINT
        GROUP BY ex.mint""").df()
    df = con.execute("SELECT * FROM ex").df().merge(path, on="mint", how="left")
    if df.empty:
        raise SystemExit("No hay consultas de X con precio de entrada y salida dentro de los datos")

    f = args.fee / 100
    for h in HORIZONS_MIN:
        df[f"net_{h}"] = df[f"px_{h}"] * (1 - f) / (df.px_in * (1 + f)) - 1
        df[f"stale_{h}"] = (df.ts_in + h * 60e9 - df[f"tx_{h}"]) > 120e9
    df["ladder_win"] = df.t2x.notna() & (df.thalf.isna() | (df.t2x < df.thalf))
    df["ladder_loss"] = df.thalf.notna() & (df.t2x.isna() | (df.thalf < df.t2x))
    cut = df.tq.median()
    df["half"] = np.where(df.tq < cut, "H1", "H2")
    q = df.loc[df.half == "H1", "unique_buyers_5m"].quantile([1 / 3, 2 / 3]).values
    df["onchain"] = pd.cut(df.unique_buyers_5m, [-np.inf, q[0], q[1], np.inf], labels=["bajo", "medio", "alto"])
    df["x_posts"] = np.where(df.posts_found.fillna(0) > 0, "con posts", "sin posts")
    fol_thr = df.loc[df.half == "H1", "max_followers"].quantile(0.75)
    df["x_reach"] = np.where(df.max_followers.fillna(0) >= fol_thr, "alcance alto", "alcance bajo")

    def row(name, x):
        if len(x) < 15:
            return None
        cells = [name, f"{len(x)}"]
        for h in HORIZONS_MIN:
            n = x[f"net_{h}"].dropna()
            cells.append(f"{n.mean() * 100:.1f} / {n.median() * 100:.1f}")
        cells += [f"{x.ladder_win.mean() * 100:.0f}%", f"{x.ladder_loss.mean() * 100:.0f}%",
                  f"{x.max_mult.median():.2f}x", f"{x['stale_15'].mean() * 100:.0f}%"]
        return "| " + " | ".join(cells) + " |"

    head = ("| grupo | n | " + " | ".join(f"neto {h}m medio/mediano %" for h in HORIZONS_MIN)
            + " | toca 2x antes de -50% | toca -50% antes de 2x | máx. múltiplo mediano 2h | stale 15m |")
    sep = "|" + "---|" * (len(HORIZONS_MIN) + 6)
    out = ["# X (sentimiento) vs on-chain en pump.fun", "",
           f"Consultas de X: {len(df)} mints con entrada y salida dentro de los datos. Costo por lado {args.fee}%, "
           f"latencia {args.latency_s}s. Gasto total registrado en X: US$ {cost_usd or 0:.2f}.", "",
           f"- `x_status`: {status}", f"- `consumer`: {consumers}",
           f"- Cortes on-chain (unique_buyers_5m, calibrados en H1): {q[0]:.0f} / {q[1]:.0f}. "
           f"Alcance alto = max_followers ≥ {fol_thr:.0f}.", ""]
    for half in ("H1", "H2", "todo"):
        d = df if half == "todo" else df[df.half == half]
        out += [f"## {half}", "", head, sep]
        rows = [row("todos", d)]
        for oc in ("bajo", "medio", "alto"):
            g = d[d.onchain == oc]
            rows.append(row(f"on-chain {oc}", g))
            for col, vals in (("x_posts", ("con posts", "sin posts")), ("x_reach", ("alcance alto", "alcance bajo"))):
                for v in vals:
                    rows.append(row(f"  on-chain {oc} · {v}", g[g[col] == v]))
            for flag, lab in (("has_large_account", "cuenta grande"), ("coordinated_shilling", "shilling coordinado")):
                rows.append(row(f"  on-chain {oc} · {lab}", g[g[flag] == True]))  # noqa: E712
        out += [r for r in rows if r] + [""]
    out += ["## Cómo leerlo", "",
            "- X sirve solo si, dentro del MISMO nivel on-chain, `con posts` / `alcance alto` gana a su contraparte "
            "en H1 **y** en H2.",
            "- Si solo gana en una mitad, es ruido. Si gana `sin posts`, X llega tarde (el pump ya pasó).",
            "- `toca 2x antes de -50%` es la regla de la escalera de pump_paper: es la métrica más cercana a cómo operás."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")


if __name__ == "__main__":
    main()
