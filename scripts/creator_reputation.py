"""Does the creator's track record predict a new pump.fun token? Walk-forward, no look-ahead.

    uv run --with pandas --with numpy python scripts/creator_reputation.py --data "<ruta>/data/raw"

For each token, the creator's history uses ONLY earlier tokens whose 2 h outcome was already visible when the new
token was born (born <= new_born - 2 h). Creator buckets (fixed before looking at results):
  nuevo         no visible history
  serial_malo   >= 3 earlier tokens, none graduated and none reached 2x
  con_exitos    >= 1 earlier token graduated or reached 2x
  resto         some history, not enough for the above
Trade simulated on every token: enter at the first trade >= 60 s after the create (we see creates live), pump.fun fee
1.25% per side. Outcomes in 2 h: net at 15/60 min, 2x before -50%, max multiple, graduation. Reported by halves.
Times are this PC's receive time (consistent across pump.fun tables).
"""
import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from recordings_summary import is_valid_parquet

FEE = 0.0125
VISIBLE_S = 7200


def src(root: Path, table: str):
    d = root / "pumpfun" / f"table={table}"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
    return "read_parquet([" + ",".join(f"'{p}'" for p in files) + "], union_by_name=true)" if files else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/creator_reputation.md"))
    ap.add_argument("--entry-s", type=float, default=60.0)
    args = ap.parse_args()
    trs, crs, cps = (src(args.data, t) for t in ("pumpfun_trades", "pumpfun_creates", "pumpfun_completes"))
    if not trs or not crs:
        raise SystemExit("Faltan pumpfun_trades o pumpfun_creates")
    con = duckdb.connect()
    con.execute("PRAGMA temp_directory='.duckdb_tmp'")
    con.execute(f"""CREATE TABLE c AS SELECT mint, arg_min(creator, ts_received_utc_ns) AS creator,
        MIN(ts_received_utc_ns)/1e9 AS born FROM {crs} WHERE creator IS NOT NULL GROUP BY mint""")
    con.execute(f"CREATE TABLE g AS SELECT mint, MIN(ts_received_utc_ns)/1e9 AS gt FROM {cps} GROUP BY mint" if cps
                else "CREATE TABLE g (mint VARCHAR, gt DOUBLE)")
    con.execute(f"""CREATE TABLE t AS SELECT DISTINCT mint, ts_received_utc_ns/1e9 AS ts,
        (virtual_sol_reserves::DOUBLE/1e9)/(virtual_token_reserves::DOUBLE/1e6) AS px
        FROM {trs} WHERE virtual_token_reserves > 0 AND virtual_sol_reserves > 0 AND mint IN (SELECT mint FROM c)""")
    t_end = con.execute("SELECT MAX(ts) FROM t").fetchone()[0]
    # entry: first trade >= born + entry_s (within 10 min)
    con.execute(f"""CREATE TABLE e AS SELECT c.mint, c.creator, c.born, t.ts AS t_in, t.px AS p_in
        FROM c ASOF JOIN t ON c.mint = t.mint AND (c.born + {args.entry_s}) <= t.ts
        WHERE t.ts <= c.born + 600 AND c.born + {VISIBLE_S} <= {t_end}""")
    con.execute(f"""CREATE TABLE o AS SELECT e.mint,
            MAX(t.px) / ANY_VALUE(e.p_in) AS max_mult,
            MIN(t.ts) FILTER (WHERE t.px >= 2 * e.p_in) AS t2x,
            MIN(t.ts) FILTER (WHERE t.px <= 0.5 * e.p_in) AS t50,
            arg_max(t.px, t.ts) FILTER (WHERE t.ts <= e.t_in + 900) AS p15,
            arg_max(t.px, t.ts) FILTER (WHERE t.ts <= e.t_in + 3600) AS p60
        FROM e JOIN t ON t.mint = e.mint AND t.ts >= e.t_in AND t.ts <= e.t_in + {VISIBLE_S}
        GROUP BY e.mint""")
    # 2 h outcome of every token (for the creator history), whether or not we could enter it
    con.execute(f"""CREATE TABLE out2h AS SELECT c.mint, c.creator, c.born,
            (g.gt IS NOT NULL AND g.gt <= c.born + {VISIBLE_S}) AS grad2h,
            COALESCE(MAX(t.px) FILTER (WHERE t.ts <= c.born + {VISIBLE_S}) /
                     NULLIF(MIN(t.px) FILTER (WHERE t.ts <= c.born + 120), 0) >= 2, FALSE) AS hit2x
        FROM c LEFT JOIN g USING (mint) LEFT JOIN t USING (mint) GROUP BY c.mint, c.creator, c.born, g.gt""")
    con.execute(f"""CREATE TABLE hist AS SELECT mint,
            COUNT(*) OVER w AS n_prior,
            SUM(grad2h::INT) OVER w AS prior_grads,
            SUM(hit2x::INT) OVER w AS prior_2x
        FROM out2h WINDOW w AS (PARTITION BY creator ORDER BY born
                                RANGE BETWEEN UNBOUNDED PRECEDING AND {VISIBLE_S} PRECEDING)""")
    df = con.execute("""SELECT e.*, o.max_mult, o.t2x, o.t50, o.p15, o.p60, h.n_prior, h.prior_grads, h.prior_2x,
            (g.gt IS NOT NULL AND g.gt <= e.born + 7200) AS grad
        FROM e JOIN o USING (mint) JOIN hist h USING (mint) LEFT JOIN g USING (mint)""").df()
    per_creator = con.execute("SELECT COUNT(*) AS n FROM c GROUP BY creator").df().n
    if df.empty:
        args.output.write_text("# Reputación del creador\n\nSin datos suficientes.", encoding="utf-8")
        print("Sin datos suficientes")
        return
    for h in (15, 60):
        df[f"net{h}"] = df[f"p{h}"] * (1 - FEE) / (df.p_in * (1 + FEE)) - 1
    df["win2x"] = df.t2x.notna() & (df.t50.isna() | (df.t2x < df.t50))
    df["loss50"] = df.t50.notna() & (df.t2x.isna() | (df.t50 < df.t2x))
    n, gr, x2 = df.n_prior.fillna(0), df.prior_grads.fillna(0), df.prior_2x.fillna(0)
    df["bucket"] = np.select([n == 0, (n >= 3) & (gr == 0) & (x2 == 0), (gr + x2) >= 1],
                             ["nuevo", "serial_malo", "con_exitos"], "resto")
    cut = df.born.median()
    df["half"] = np.where(df.born < cut, "H1", "H2")

    def line(name, d):
        if len(d) < 20:
            return f"| {name} | {len(d)} | (pocos) |||||||"
        return (f"| {name} | {len(d):,} | {d.net15.median() * 100:.1f}% / {d.net15.mean() * 100:.1f}% | "
                f"{d.net60.median() * 100:.1f}% / {d.net60.mean() * 100:.1f}% | {d.win2x.mean() * 100:.1f}% | "
                f"{d.loss50.mean() * 100:.0f}% | {d.max_mult.median():.2f}x | {(d.max_mult >= 3).mean() * 100:.1f}% | "
                f"{d.grad.mean() * 100:.2f}% |")

    head = ("| grupo | n | neto 15m med./medio | neto 60m med./medio | 2x antes de -50% | -50% antes de 2x | "
            "máx. mult. mediano | llega a 3x | gradúa ≤2h |")
    sep = "|" + "---|" * 9
    out = ["# Reputación del creador en pump.fun (walk-forward, sin mirar el futuro)", "",
           f"- Tokens con entrada simulada a los {args.entry_s:.0f} s: {len(df):,}. Creadores distintos: {len(per_creator):,}; "
           f"tokens por creador: mediana {per_creator.median():.0f}, p90 {per_creator.quantile(.9):.0f}, máximo {per_creator.max():,}.",
           f"- Historial visible = tokens del mismo creador nacidos ≥ {VISIBLE_S // 3600} h antes. Fee {FEE * 100:.2f}% por lado.",
           f"- Distribución: " + ", ".join(f"{k} {v:,}" for k, v in df.bucket.value_counts().items()), "", head, sep,
           line("todos", df)]
    for b in ("nuevo", "serial_malo", "con_exitos", "resto"):
        out.append(line(b, df[df.bucket == b]))
    out += ["", "## Por mitades (lo que valga tiene que repetirse en las dos)", "", head, sep]
    for h in ("H1", "H2"):
        for b in ("serial_malo", "con_exitos", "nuevo"):
            out.append(line(f"{h} · {b}", df[(df.half == h) & (df.bucket == b)]))
    out += ["", "## Cómo leerlo", "",
            "- Si `serial_malo` es claramente peor que `todos` en H1 y H2: filtro útil (nunca entrar a sus tokens).",
            "- Si `con_exitos` es claramente mejor en las dos mitades: es una señal de entrada (o un multiplicador de tamaño).",
            "- Con ~2 días de datos el historial es corto: el filtro mejora a medida que se acumulan días.",
            "- Este estudio no mira el creador de la billetera ni bundles: un creador puede usar muchas billeteras."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")


if __name__ == "__main__":
    main()
