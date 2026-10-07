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

--key funder: group by the wallet that FUNDED the creator (pumpfun/creator_funding, written by the recorder's
funder tracker) instead of the creator wallet; tokens without a resolved funder keep their creator. Funders are only
looked up for tokens with traction at ~3 min, so the entry is moved to >= 240 s to avoid using that future information.
"""
import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from recordings_summary import is_valid_parquet

FEE = 0.0125
SLIP = 0.005                      # extra cost per side for the bonding-curve price impact of a small order
TPS = (1.5, 2.0, 3.0)             # take-profit multiples tested
SLS = (0.7, 0.5)                  # stop-loss multiples tested
HOLD_S = 3600                     # time stop
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
    ap.add_argument("--key", choices=["creator", "funder"], default="creator")
    ap.add_argument("--max-funder-creators", type=int, default=100,
                    help="funders with more distinct creators than this are exchanges/services (hot wallets), not a "
                         "mother: their tokens fall back to the creator wallet")
    args = ap.parse_args()
    if args.key == "funder" and args.entry_s < 240:
        args.entry_s = 240.0
    trs, crs, cps = (src(args.data, t) for t in ("pumpfun_trades", "pumpfun_creates", "pumpfun_completes"))
    if not trs or not crs:
        raise SystemExit("Faltan pumpfun_trades o pumpfun_creates")
    con = duckdb.connect()
    con.execute("PRAGMA temp_directory='.duckdb_tmp'")
    con.execute(f"""CREATE TABLE c AS SELECT mint, arg_min(creator, ts_received_utc_ns) AS creator,
        MIN(ts_received_utc_ns)/1e9 AS born FROM {crs} WHERE creator IS NOT NULL GROUP BY mint""")
    n_funded = 0
    if args.key == "funder":
        fnd = src(args.data, "creator_funding")
        if not fnd:
            raise SystemExit("No hay pumpfun/creator_funding todavía: dejar correr el rastreador de fondeo.")
        con.execute(f"CREATE TABLE f0 AS SELECT mint, arg_min(funder, ts_query_utc_ns) AS funder, "
                    f"arg_min(creator, ts_query_utc_ns) AS fcreator FROM {fnd} WHERE funder IS NOT NULL GROUP BY mint")
        con.execute(f"CREATE TABLE svc AS SELECT funder, COUNT(DISTINCT fcreator) AS n_cre, COUNT(*) AS n_tok FROM f0 "
                    f"GROUP BY funder HAVING COUNT(DISTINCT fcreator) > {args.max_funder_creators}")
        n_svc, n_svc_tok = con.execute("SELECT COUNT(*), COALESCE(SUM(n_tok), 0) FROM svc").fetchone()
        con.execute("CREATE TABLE f AS SELECT mint, funder FROM f0 WHERE funder NOT IN (SELECT funder FROM svc)")
        n_funded = con.execute("SELECT COUNT(*) FROM f").fetchone()[0]
        con.execute("CREATE OR REPLACE TABLE c AS SELECT c.mint, COALESCE(f.funder, c.creator) AS creator, c.born "
                    "FROM c LEFT JOIN f USING (mint)")
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
            arg_max(t.px, t.ts) FILTER (WHERE t.ts <= e.t_in + 3600) AS p60""" + "".join(
        f""",
            MIN(t.ts) FILTER (WHERE t.px >= {tp} * e.p_in) AS ttp{int(tp * 100)},
            arg_min(t.px, t.ts) FILTER (WHERE t.px >= {tp} * e.p_in) AS ptp{int(tp * 100)}""" for tp in TPS) + "".join(
        f""",
            MIN(t.ts) FILTER (WHERE t.px <= {sl} * e.p_in) AS tsl{int(sl * 100)},
            arg_min(t.px, t.ts) FILTER (WHERE t.px <= {sl} * e.p_in) AS psl{int(sl * 100)}""" for sl in SLS) + f"""
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
    ocols = "".join(f", o.ttp{int(tp * 100)}, o.ptp{int(tp * 100)}" for tp in TPS) + "".join(
        f", o.tsl{int(sl * 100)}, o.psl{int(sl * 100)}" for sl in SLS)
    df = con.execute(f"""SELECT e.*, o.max_mult, o.t2x, o.t50, o.p15, o.p60{ocols}, h.n_prior, h.prior_grads, h.prior_2x,
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
    title = "billetera madre (quien fondeó al creador)" if args.key == "funder" else "creador"
    out = [f"# Reputación por {title} en pump.fun (walk-forward, sin mirar el futuro)", "",
           *([f"- Tokens con billetera madre resuelta: {n_funded:,} (el resto se agrupa por su creador). "
              f"Excluidas {n_svc} billeteras que fondearon a más de {args.max_funder_creators} creadores distintos "
              f"({n_svc_tok:,} tokens): son exchanges o servicios, no una madre."] if args.key == "funder" else []),
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
    # ---- exit rules: enter at the entry trade, take profit / stop at the first trade that crosses, else exit at +60 min
    df["volatil"] = (n >= 5) & (x2 / n.where(n > 0, 1) >= 0.12)
    cost = FEE + SLIP
    rules = [(tp, sl) for tp in TPS for sl in SLS]

    def rule_net(d, tp, sl):
        ttp, tsl = d[f"ttp{int(tp * 100)}"], d[f"tsl{int(sl * 100)}"]
        hz = d.t_in + HOLD_S
        tp_ok = ttp.notna() & (ttp <= hz)
        sl_ok = tsl.notna() & (tsl <= hz)
        use_tp = tp_ok & (~sl_ok | (ttp < tsl))
        use_sl = sl_ok & ~use_tp
        px = np.where(use_tp, d[f"ptp{int(tp * 100)}"], np.where(use_sl, d[f"psl{int(sl * 100)}"], d.p60))
        return px * (1 - cost) / (d.p_in * (1 + cost)) - 1

    rule_cols = [f"TP +{int((tp - 1) * 100)}% / SL -{int((1 - sl) * 100)}%" for tp, sl in rules]
    groups = [("todos", df), ("nuevo", df[df.bucket == "nuevo"]), ("serial_malo", df[df.bucket == "serial_malo"]),
              ("con_exitos", df[df.bucket == "con_exitos"]), ("volátil (≥5 previos, ≥12% con 2x)", df[df.volatil]),
              ("todos menos serial_malo", df[df.bucket != "serial_malo"])]
    out += ["", f"## Reglas de salida simuladas (entrada al trade de {args.entry_s:.0f} s, stop/toma al primer trade que cruza, "
            f"si no sale a los {HOLD_S // 60} min; costo {cost * 100:.2f}% por lado)", "",
            "Cada celda: retorno neto medio por operación (n). Positivo en negrita.", "",
            "| grupo | " + " | ".join(rule_cols) + " |", "|---|" + "---|" * len(rules)]
    nets = {}
    for name, d in groups:
        cells = []
        for (tp, sl), col in zip(rules, rule_cols):
            if len(d) < 30:
                cells.append("(pocos)")
                continue
            r = rule_net(d, tp, sl)
            nets[(name, col)] = r
            m = r.mean() * 100
            cells.append(f"**{m:+.2f}%** ({len(d):,})" if m > 0 else f"{m:+.2f}% ({len(d):,})")
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    pos = [(name, col) for (name, col), r in nets.items() if r.mean() > 0]
    if pos:
        out += ["", "### Combinaciones con resultado medio positivo, por mitades y por día (para ver si es racha)", "",
                "| grupo | regla | n | medio | 1ª mitad | 2ª mitad | aciertos | mejor día / peor día |", "|---|---|---|---|---|---|---|---|"]
        for name, col in pos:
            d = dict(groups)[name]
            r = nets[(name, col)]
            hh = d.half.values
            day = pd.Series(r.values).groupby((d.born.values // 86400).astype(int)).mean() * 100
            out.append(f"| {name} | {col} | {len(d):,} | {r.mean() * 100:+.2f}% | {r[hh == 'H1'].mean() * 100:+.2f}% | "
                       f"{r[hh == 'H2'].mean() * 100:+.2f}% | {(r > 0).mean() * 100:.0f}% | {day.max():+.1f}% / {day.min():+.1f}% |")
    else:
        out += ["", "Ninguna combinación de grupo y regla da resultado medio positivo."]
    out += ["", f"Probé {len(groups) * len(rules)} combinaciones: alguna positiva puede ser azar; sirve solo si es positiva en las dos mitades "
            "y en la mayoría de los días."]
    if args.key == "funder":
        g = df.groupby("creator")
        tab = g.agg(n=("mint", "count"), win2x=("win2x", "mean"), loss50=("loss50", "mean"), grad=("grad", "mean"),
                    mult=("max_mult", "median"), net60=("net60", "median")).reset_index()
        tab = tab[tab.n >= 5].sort_values("n", ascending=False).head(25)
        out += ["", "## Por madre (≥ 5 tokens con entrada simulada), de más a menos tokens", "",
                "| madre | tokens | 2x antes de -50% | -50% antes de 2x | máx. mult. mediano | gradúa ≤2h | neto 60m mediano |",
                "|---|---|---|---|---|---|---|"]
        for _, r in tab.iterrows():
            out.append(f"| `{r.creator[:6]}…{r.creator[-4:]}` | {int(r.n)} | {r.win2x * 100:.0f}% | {r.loss50 * 100:.0f}% | "
                       f"{r.mult:.2f}x | {r.grad * 100:.1f}% | {r.net60 * 100:.1f}% |")
        out += ["", "Referencia: la fila 'todos' de arriba. Una madre solo importa si lo suyo es claramente distinto "
                "y se repite en las dos mitades; con pocos tokens por madre, mucha de esta tabla es azar."]
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
