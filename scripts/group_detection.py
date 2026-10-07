"""Real coordinated groups vs bots on pump.fun: rebuild groups with the current pump_paper rule and with a stricter
rule, then check which one predicts anything out of sample.

    uv run --with pandas --with numpy python scripts/group_detection.py --data "<ruta>/data/raw"

Detection uses only the first half of the recording (H1); signals and outcomes are measured in the second (H2).
  Old rule: src.paper.pump_paper.GroupGraph, fed exactly like the live paper bot.
  New rule:
    1. Drop bot wallets: snipers (buy within 3 slots of the create in most tokens), flippers (median hold < 90 s),
       hyperactive (> 30 tokens/day), fixed size (>= 5 buys with near-identical SOL amounts).
    2. Co-buy within 2 slots, only between minute 1 and 30 of the token (launch sniping does not count),
       in >= 3 tokens and >= 30% of the smaller wallet's tokens.
    3. Co-occurrence >= 10x what their activity would produce by chance (lift).
    4. They also SELL together (first sells <= 5 min apart) in >= 50% of the shared tokens.
    5. Not copy-trading: if one wallet buys after the other in >= 90% of the shared tokens, the follower is a bot.
Signal (same as pump_paper): >= 2 wallets of one group buy a token <= 30 min old within 10 min, < 40 wallets in it.
Outcome: enter after the next trade (+2 s), fee per side as pump_paper. Control: a random token of the same age
window and crowd at the same moment.
"""
import argparse
import random
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from recordings_summary import is_valid_parquet  # noqa: E402
from src.paper.pump_paper import FEE, GROUP, SIGNAL, GroupGraph  # noqa: E402

BOT = {"sniper_slots": 3, "sniper_frac": 0.5, "min_hold_s": 90, "max_tokens_day": 30, "max_cv": 0.02, "cv_min_buys": 5}
NEW = {"window_slots": 2, "min_age_s": 60, "max_age_s": 1800, "min_shared": 3, "min_overlap": 0.3, "min_lift": 10,
       "cosell_s": 300, "min_cosell": 0.5, "copy_frac": 0.9}


def src(root: Path, table: str):
    d = root / "pumpfun" / f"table={table}"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
    return "read_parquet([" + ",".join(f"'{p}'" for p in files) + "], union_by_name=true)" if files else None


def components(edges) -> dict:
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    return {u: find(u) for u in parent}


def group_stats(groups: dict) -> str:
    if not groups:
        return "0 grupos"
    sizes = pd.Series(groups).value_counts()
    return (f"{len(sizes):,} grupos, {len(groups):,} billeteras; tamaño mediano {sizes.median():.0f}, "
            f"p90 {sizes.quantile(.9):.0f}, máximo {sizes.max():,}")


def old_rule(con, cut) -> dict:
    g = GroupGraph()
    cur = con.execute(f"SELECT mint, u, slot FROM t WHERE s < {cut} AND is_buy ORDER BY slot")
    while True:
        rows = cur.fetchmany(200_000)
        if not rows:
            break
        for mint, u, slot in rows:
            g.on_buy(mint, u, int(slot))
    edges = [(a, b) for a, bs in g.links.items() if g.is_member(a) for b in bs if g.is_member(b)]
    return components(edges)


def new_rule(con, cut, span_days, notes) -> tuple:
    ws = con.execute(f"""
        WITH pos AS (SELECT u, mint, MIN(slot) FILTER (WHERE is_buy) AS fb_slot, MIN(s) FILTER (WHERE is_buy) AS fb_s,
                            MIN(s) FILTER (WHERE NOT is_buy) AS fs_s FROM t WHERE s < {cut} GROUP BY u, mint),
             sz AS (SELECT u, COUNT(*) AS nb, STDDEV_POP(sol) / NULLIF(AVG(sol), 0) AS cv
                    FROM t WHERE s < {cut} AND is_buy GROUP BY u)
        SELECT p.u, COUNT(*) FILTER (WHERE fb_s IS NOT NULL) AS n_tok,
               AVG(CASE WHEN c.cslot IS NOT NULL AND fb_slot IS NOT NULL
                        THEN (fb_slot - c.cslot <= {BOT['sniper_slots']})::INT END) AS sniper_frac,
               MEDIAN(fs_s - fb_s) FILTER (WHERE fs_s >= fb_s) AS med_hold, ANY_VALUE(sz.nb) AS nb, ANY_VALUE(sz.cv) AS cv
        FROM pos p LEFT JOIN c USING (mint) LEFT JOIN sz USING (u) GROUP BY p.u""").df()
    act = ws[ws.n_tok >= NEW["min_shared"]].copy()
    reasons = {
        "sniper": act.sniper_frac.fillna(0) > BOT["sniper_frac"],
        "flipper": act.med_hold.fillna(1e9) < BOT["min_hold_s"],
        "hiperactiva": act.n_tok / max(span_days, 1e-9) > BOT["max_tokens_day"],
        "monto fijo": (act.nb.fillna(0) >= BOT["cv_min_buys"]) & (act.cv.fillna(1) < BOT["max_cv"]),
    }
    bot = np.zeros(len(act), dtype=bool)
    for m in reasons.values():
        bot |= m.values
    notes.append(f"Billeteras con ≥{NEW['min_shared']} tokens en H1: {len(act):,}. Marcadas como bot: {bot.sum():,} "
                 f"({bot.mean() * 100:.0f}%). Por motivo (se superponen): "
                 + ", ".join(f"{k} {int(v.sum()):,}" for k, v in reasons.items()))
    con.register("ok", act.loc[~bot, ["u", "n_tok"]])
    pr = con.execute(f"""
        WITH fb AS (SELECT p.u, p.mint, p.slot, p.s, p.fs_s FROM (
                SELECT u, mint, MIN(slot) FILTER (WHERE is_buy) AS slot, MIN(s) FILTER (WHERE is_buy) AS s,
                       MIN(s) FILTER (WHERE NOT is_buy) AS fs_s FROM t WHERE s < {cut} GROUP BY u, mint) p
            JOIN c USING (mint) JOIN ok USING (u)
            WHERE p.s IS NOT NULL AND p.s - c.cs BETWEEN {NEW['min_age_s']} AND {NEW['max_age_s']})
        SELECT a.u AS u1, b.u AS u2, COUNT(DISTINCT a.mint) AS co,
               SUM((b.slot > a.slot)::INT) AS a_first, SUM((a.slot > b.slot)::INT) AS b_first,
               SUM((a.fs_s IS NOT NULL AND b.fs_s IS NOT NULL AND ABS(a.fs_s - b.fs_s) <= {NEW['cosell_s']})::INT) AS cosell
        FROM fb a JOIN fb b ON a.mint = b.mint AND a.u < b.u AND ABS(a.slot - b.slot) <= {NEW['window_slots']}
        GROUP BY 1, 2 HAVING COUNT(DISTINCT a.mint) >= {NEW['min_shared']}""").df()
    n_mints = con.execute(f"SELECT COUNT(*) FROM c WHERE cs < {cut}").fetchone()[0] or 1
    ntok = dict(zip(act.u, act.n_tok))
    funnel = [("pares que co-compran en ≥3 tokens (sin bots, minuto 1-30)", len(pr))]
    if pr.empty:
        return {}, funnel, pr
    n1, n2 = pr.u1.map(ntok), pr.u2.map(ntok)
    pr["overlap"] = pr.co / np.minimum(n1, n2)
    pr["lift"] = pr.co / (n1 * n2 / n_mints)
    pr["cosell_frac"] = pr.cosell / pr.co
    pr["is_copy"] = (np.maximum(pr.a_first, pr.b_first) >= NEW["copy_frac"] * pr.co) & (pr.a_first + pr.b_first == pr.co)
    keep = pr.overlap >= NEW["min_overlap"]
    funnel.append((f"+ solapamiento ≥{NEW['min_overlap']:.0%}", int(keep.sum())))
    keep &= pr.lift >= NEW["min_lift"]
    funnel.append((f"+ lift ≥{NEW['min_lift']}x sobre el azar", int(keep.sum())))
    funnel.append(("  (de esos, copytrading descartado)", int((keep & pr.is_copy).sum())))
    keep &= ~pr.is_copy
    funnel.append(("+ no es copytrading", int(keep.sum())))
    keep &= pr.cosell_frac >= NEW["min_cosell"]
    funnel.append((f"+ venden juntos en ≥{NEW['min_cosell']:.0%} de los tokens", int(keep.sum())))
    good = pr[keep]
    return components(zip(good.u1, good.u2)), funnel, good


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/group_detection.md"))
    args = ap.parse_args()
    trs, crs = src(args.data, "pumpfun_trades"), src(args.data, "pumpfun_creates")
    cps, xs = src(args.data, "pumpfun_completes"), src(args.data, "x_mentions")
    if not trs or not crs:
        raise SystemExit("Faltan pumpfun_trades o pumpfun_creates")
    con = duckdb.connect()
    con.execute("PRAGMA temp_directory='.duckdb_tmp'")
    con.execute(f"""CREATE TABLE t AS SELECT DISTINCT mint, (CASE WHEN ts_chain_s IS NOT NULL AND ABS(ts_chain_s - ts_received_utc_ns / 1e9) <= 600 THEN ts_chain_s ELSE CAST(ts_received_utc_ns / 1e9 AS BIGINT) END) AS s, slot, "user" AS u, is_buy,
        sol_amount::DOUBLE AS sol, (virtual_sol_reserves::DOUBLE/1e9)/(virtual_token_reserves::DOUBLE/1e6) AS px
        FROM {trs} WHERE virtual_token_reserves > 0 AND virtual_sol_reserves > 0""")
    con.execute(f"CREATE TABLE c AS SELECT mint, MIN(slot) AS cslot, MIN((CASE WHEN ts_chain_s IS NOT NULL AND ABS(ts_chain_s - ts_received_utc_ns / 1e9) <= 600 THEN ts_chain_s ELSE CAST(ts_received_utc_ns / 1e9 AS BIGINT) END)) AS cs FROM {crs} GROUP BY 1")
    s0, s1 = con.execute("SELECT MIN(s), MAX(s) FROM t").fetchone()
    cut = (s0 + s1) / 2
    span_days = (cut - s0) / 86400
    bad = con.execute(f"SELECT COUNT(*) FILTER (WHERE ts_chain_s IS NULL OR ABS(ts_chain_s - ts_received_utc_ns / 1e9) > 600), "
                      f"COUNT(*) FROM {trs}").fetchone()
    notes = [f"Datos: {(s1 - s0) / 3600:.1f} h. Detección en H1 ({span_days * 24:.1f} h), evaluación en H2.",
             f"Filas con hora de cadena inválida (se usó la hora de recepción): {bad[0]:,} de {bad[1]:,}."]

    print("Regla vieja (GroupGraph de pump_paper)...", flush=True)
    old = old_rule(con, cut)
    print("Regla nueva...", flush=True)
    new, funnel, good = new_rule(con, cut, span_days, notes)

    print("Evaluando señales en H2...", flush=True)
    tr = con.execute("SELECT mint, s, u, is_buy, px FROM t ORDER BY mint, s, slot").df()
    by = {m: (g.s.values.astype(float), g.px.values) for m, g in tr.groupby("mint", sort=False)}
    fb = con.execute("SELECT mint, MIN(s) AS s FROM t WHERE is_buy GROUP BY mint, u").df()
    crowd_t = {m: np.sort(g.s.values.astype(float)) for m, g in fb.groupby("mint", sort=False)}
    born = dict(con.execute("SELECT mint, cs FROM c").fetchall())
    born_sorted = sorted((v, k) for k, v in born.items())
    born_ts = np.array([b for b, _ in born_sorted], dtype=float)
    grads = dict(con.execute(f"SELECT mint, MIN((CASE WHEN ts_chain_s IS NOT NULL AND ABS(ts_chain_s - ts_received_utc_ns / 1e9) <= 600 THEN ts_chain_s ELSE CAST(ts_received_utc_ns / 1e9 AS BIGINT) END)) FROM {cps} GROUP BY 1").fetchall()) if cps else {}
    xpost = {}
    if xs:
        xpost = dict(con.execute(f"""SELECT mint, MIN(epoch(TRY_CAST(earliest_post_utc AS TIMESTAMPTZ)))
            FROM {xs} WHERE earliest_post_utc IS NOT NULL GROUP BY 1""").fetchall())

    def crowd(m, t):
        a = crowd_t.get(m)
        return int(np.searchsorted(a, t, side="left")) if a is not None else 0

    def outcome(m, t):
        if m not in by or t + 3600 > s1:
            return None
        ts, px = by[m]
        i = np.searchsorted(ts, t + 2, side="left")
        if i >= len(ts):
            return None
        pin, te = px[i], ts[i]
        r = {}
        for h in (15, 60):
            j = min(np.searchsorted(ts, te + h * 60, side="left"), len(ts) - 1)
            r[f"net{h}"] = px[j] * (1 - FEE) / (pin * (1 + FEE)) - 1
        w = (ts > te) & (ts <= te + 7200)
        up = np.where(px[w] >= 2 * pin)[0]
        dn = np.where(px[w] <= 0.5 * pin)[0]
        r["win2x"] = len(up) > 0 and (len(dn) == 0 or up[0] < dn[0])
        r["loss50"] = len(dn) > 0 and (len(up) == 0 or dn[0] < up[0])
        r["grad"] = m in grads and te < grads[m] <= te + 7200
        r["xpost"] = m in xpost and xpost[m] is not None and te < xpost[m] <= te + 7200
        return r

    def signals(groups):
        if not groups:
            return []
        gb = tr[(tr.s >= cut) & tr.is_buy & tr.u.isin(list(groups))]
        out = []
        for m, g in gb.groupby("mint", sort=False):
            if m not in born:
                continue
            recent: dict = {}
            for s, u in zip(g.s.values, g.u.values):
                if s - born[m] > SIGNAL["max_age_s"]:
                    break
                gid = groups[u]
                d = recent.setdefault(gid, {})
                d[u] = s
                live = [w for w, ts_ in d.items() if s - ts_ <= SIGNAL["within_s"]]
                if len(live) >= SIGNAL["min_members"] and crowd(m, s) < SIGNAL["max_crowd"]:
                    out.append((m, float(s)))
                    break
        return out

    rnd = random.Random(7)

    def evaluate(sigs):
        res, ctl = [], []
        for m, t in sigs:
            o = outcome(m, t)
            if o is None:
                continue
            res.append(o)
            lo, hi = np.searchsorted(born_ts, t - SIGNAL["max_age_s"]), np.searchsorted(born_ts, t)
            pool = [born_sorted[k][1] for k in range(lo, hi)
                    if born_sorted[k][1] != m and crowd(born_sorted[k][1], t) < SIGNAL["max_crowd"]]
            rnd.shuffle(pool)
            for cm in pool[:20]:
                oc = outcome(cm, t)
                if oc is not None:
                    ctl.append(oc)
                    break
        return pd.DataFrame(res), pd.DataFrame(ctl)

    def line(name, d):
        if d.empty:
            return f"| {name} | 0 | - | - | - | - | - | - |"
        return (f"| {name} | {len(d):,} | {d.net15.mean() * 100:.1f} / {d.net15.median() * 100:.1f} | "
                f"{d.net60.mean() * 100:.1f} / {d.net60.median() * 100:.1f} | {d.win2x.mean() * 100:.0f}% | "
                f"{d.loss50.mean() * 100:.0f}% | {d.grad.mean() * 100:.1f}% | {d.xpost.mean() * 100:.1f}% |")

    rows = []
    for name, groups in (("regla vieja", old), ("regla nueva", new)):
        sig, ctl = evaluate(signals(groups))
        rows += [line(f"{name}: señales", sig), line(f"{name}: control al azar", ctl)]

    out = ["# Grupos reales vs bots en pump.fun", ""] + [f"- {n}" for n in notes] + ["",
           "## Cuántos grupos encuentra cada regla (H1)", "",
           f"- Regla vieja (pump_paper, {GROUP}): {group_stats(old)}",
           f"- Regla nueva: {group_stats(new)}", "",
           "### Embudo de la regla nueva (pares de billeteras)", "", "| paso | pares |", "|---|---|"]
    out += [f"| {k} | {v:,} |" for k, v in funnel]
    if len(good):
        top = good.sort_values("co", ascending=False).head(10)
        out += ["", "### Pares más fuertes (regla nueva)", "",
                "| billetera 1 | billetera 2 | tokens juntos | lift | venden juntos |", "|---|---|---|---|---|"]
        out += [f"| `{r.u1[:8]}…` | `{r.u2[:8]}…` | {r.co} | {r.lift:.0f}x | {r.cosell_frac:.0%} |" for r in top.itertuples()]
    out += ["", "## ¿Predicen algo? (señales en H2, grupos detectados solo con H1)", "",
            f"Fee {FEE * 100:.2f}% por lado, entrada tras el siguiente trade. Retornos netos en %, medio / mediano. "
            "Ventana de 2 h para 2x, -50%, graduación y post en X (el vigilante de X no consulta todos los tokens).", "",
            "| regla | n | neto 15m | neto 60m | toca 2x antes de -50% | toca -50% antes de 2x | gradúa ≤2h | post en X ≤2h |",
            "|---|---|---|---|---|---|---|---|"] + rows + ["",
            "## Cómo leerlo", "",
            "- Una regla sirve si sus señales ganan claramente a su control al azar (mismo momento, misma edad y gente).",
            "- Si la nueva gana y la vieja no, los 'grupos' viejos eran bots: cambiar la regla de pump_paper.",
            "- Con ~1 día de evaluación, n chico: buscar diferencias grandes, no décimas."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")


if __name__ == "__main__":
    main()
