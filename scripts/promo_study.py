"""Paid push (DexScreener boost/profile) x on-chain x Telegram on pump.fun tokens.

    uv run --with pandas --with numpy python scripts/promo_study.py --data "<ruta>/data/raw"

Event = first time a pump.fun token shows up in DexScreener's paid boosts or paid profiles (someone paid to push it).
All clocks are this PC's receive time (pump.fun trades, DexScreener polls and Telegram share it).
  Before the push (on-chain): token age, price run-up in the previous 30 min, unique buyers in the previous 10 min,
    share of the bought supply still held by the EARLY wallets (bought in the first 5 min of the token).
  Social: was there a Telegram call for the token before the push? (calls in the 2 h before)
  After the push: net return at +5/+15/+60 min (entry = first trade >= push + latency, pump.fun fee per side),
    2x before -50% in 2 h, graduation in 2 h, how much the early wallets sold by +15 min.
  Control: up to 3 tokens of similar age with trades in the previous 10 min, at the same moment, never pushed.
Split by the on-chain/social features and by halves of time. Tokens that graduate stop trading on the curve:
their exit is the last curve price (the graduation price), flagged in `gradúa`.
"""
import argparse
import json
import random
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from recordings_summary import is_valid_parquet

FEE = 0.0125
HORIZONS = (5, 15, 60)


def src(root: Path, venue: str, table: str):
    d = root / venue / f"table={table}"
    files = [str(f).replace("\\", "/") for f in d.rglob("*.parquet") if is_valid_parquet(f)] if d.exists() else []
    return "read_parquet([" + ",".join(f"'{p}'" for p in files) + "], union_by_name=true)" if files else None


def outcome(ts: np.ndarray, px: np.ndarray, users: np.ndarray, buys: np.ndarray, toks: np.ndarray,
            t_event: float, latency: float, early: set, early_held: float):
    """Net returns after entering at the first trade >= t_event + latency, plus path stats and early selling."""
    i = np.searchsorted(ts, t_event + latency, side="left")
    if i >= len(ts) or ts[i] > t_event + 600:
        return None
    pin, tin = px[i], ts[i]
    r = {}
    for h in HORIZONS:
        j = np.searchsorted(ts, tin + h * 60, side="right") - 1
        r[f"net{h}"] = px[j] * (1 - FEE) / (pin * (1 + FEE)) - 1
    w = (ts > tin) & (ts <= tin + 7200)
    up = np.where(px[w] >= 2 * pin)[0]
    dn = np.where(px[w] <= 0.5 * pin)[0]
    r["win2x"] = len(up) > 0 and (len(dn) == 0 or up[0] < dn[0])
    r["loss50"] = len(dn) > 0 and (len(up) == 0 or dn[0] < up[0])
    r["max_mult"] = px[w].max() / pin if w.any() else 1.0
    if early and early_held > 0:
        m = (ts > t_event) & (ts <= t_event + 900) & ~buys & np.isin(users, list(early))
        r["early_sold_15m"] = min(toks[m].sum() / early_held, 1.0)
    else:
        r["early_sold_15m"] = np.nan
    return r


def features(ts, px, users, buys, toks, born, t_event):
    pre = ts < t_event
    if not pre.any():
        return None
    p_now = px[pre][-1]
    k30 = np.searchsorted(ts, t_event - 1800, side="right") - 1
    p30 = px[k30] if k30 >= 0 else px[0]
    m10 = (ts >= t_event - 600) & pre
    first5 = (ts <= born + 300) & buys
    early = set(users[first5])
    signed = np.where(buys, toks, -toks)
    held = pd.Series(signed[pre]).groupby(users[pre]).sum()
    total = held[held > 0].sum()
    early_held = held[held.index.isin(list(early)) & (held > 0)].sum()
    return {"age_min": (t_event - born) / 60, "runup_30m": p_now / p30 - 1 if p30 > 0 else np.nan,
            "buyers_10m": len(set(users[m10 & buys])), "early_share": early_held / total if total > 0 else np.nan,
            "_early": early, "_early_held": early_held}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("-o", "--output", type=Path, default=Path("docs/promo_study.md"))
    ap.add_argument("--latency-s", type=float, default=30.0, help="DexScreener se consulta cada 30 s: llegamos tarde")
    ap.add_argument("--orders", type=Path, default=Path("data/research/dex_orders.jsonl"),
                    help="resultado de dex_orders_backfill.py: pagos históricos con hora exacta (si existe se usa)")
    args = ap.parse_args()
    trs, crs, cps = (src(args.data, "pumpfun", t) for t in ("pumpfun_trades", "pumpfun_creates", "pumpfun_completes"))
    bst, prf = src(args.data, "dexscreener", "token_boosts"), src(args.data, "dexscreener", "token_profiles")
    calls = src(args.data, "telegram", "calls")
    if not trs or not crs or not (bst or prf):
        raise SystemExit("Faltan datos: pumpfun_trades/creates y al menos una tabla de dexscreener.")
    con = duckdb.connect()
    con.execute("PRAGMA temp_directory='.duckdb_tmp'")
    con.execute(f"CREATE TABLE born AS SELECT mint, MIN(ts_received_utc_ns)/1e9 AS born FROM {crs} GROUP BY 1")
    promos = []
    if bst:
        promos.append(f"SELECT token_address AS mint, ts_polled_utc_ns/1e9 AS t, 'boost' AS kind, total_amount AS amt FROM {bst} WHERE chain_id='solana'")
    if prf:
        promos.append(f"SELECT token_address AS mint, ts_polled_utc_ns/1e9 AS t, 'perfil' AS kind, NULL::DOUBLE AS amt FROM {prf} WHERE chain_id='solana'")
    watcher_promos = list(promos)
    n_ord, delay_line, queried = 0, None, set()
    if args.orders.exists():
        rows = []
        for ln in args.orders.read_text(encoding="utf-8").splitlines():
            try:
                j = json.loads(ln)
            except ValueError:
                continue
            queried.add(j["mint"])
            for o in j.get("orders") or []:
                if o.get("status") not in (None, "approved") or not o.get("paymentTimestamp"):
                    continue
                kind = {"tokenProfile": "perfil", "communityTakeover": "cto"}.get(o.get("type"), "ad")
                rows.append((j["mint"], o["paymentTimestamp"] / 1000.0, kind))
            for b in j.get("boosts") or []:
                tb = b.get("paymentTimestamp") or b.get("timestamp") or b.get("date")
                if tb:
                    rows.append((j["mint"], tb / 1000.0 if tb > 1e11 else float(tb), "boost"))
        if rows:
            con.register("ordf", pd.DataFrame(rows, columns=["mint", "t", "kind"]))
            con.execute("CREATE TABLE ord AS SELECT * FROM ordf")
            n_ord = con.execute("SELECT COUNT(DISTINCT mint) FROM ord").fetchone()[0]
            promos.append("SELECT mint, t, kind, NULL::DOUBLE AS amt FROM ord")
            if watcher_promos:
                d = con.execute(f"""SELECT w.t - o.t AS d FROM (SELECT mint, MIN(t) AS t FROM ({' UNION ALL '.join(watcher_promos)})
                    GROUP BY 1) w JOIN (SELECT mint, MIN(t) AS t FROM ord GROUP BY 1) o USING (mint)
                    WHERE w.t - o.t BETWEEN -600 AND 7200""").df().d
                if len(d) >= 5:
                    delay_line = (f"- Retraso entre el pago y que nuestro vigilante lo ve (en {len(d)} tokens vistos por los dos): "
                                  f"mediana {d.median():.0f} s, p25 {d.quantile(.25):.0f} s, p75 {d.quantile(.75):.0f} s, "
                                  f"p90 {d.quantile(.9):.0f} s. Con `--latency-s` por debajo de la mediana se simula una "
                                  f"velocidad que el vigilante actual no tiene.")
    con.execute(f"""CREATE TABLE ev AS SELECT p.mint, MIN(p.t) AS t, arg_min(p.kind, p.t) AS kind, MAX(p.amt) AS amt, ANY_VALUE(b.born) AS born
        FROM ({' UNION ALL '.join(promos)}) p JOIN born b USING (mint) GROUP BY p.mint""")
    n_promo_all = con.execute(f"SELECT COUNT(DISTINCT mint) FROM ({' UNION ALL '.join(promos)})").fetchone()[0]
    con.execute(f"""CREATE TABLE tr AS SELECT DISTINCT mint, ts_received_utc_ns/1e9 AS ts, "user" AS u, is_buy,
        token_amount::DOUBLE AS tok, (virtual_sol_reserves::DOUBLE/1e9)/(virtual_token_reserves::DOUBLE/1e6) AS px
        FROM {trs} WHERE virtual_token_reserves > 0 AND virtual_sol_reserves > 0""")
    t0, t1 = con.execute("SELECT MIN(ts), MAX(ts) FROM tr").fetchone()
    ev = con.execute(f"SELECT * FROM ev WHERE t BETWEEN {t0 + 1800} AND {t1 - 3600} ORDER BY t").df()
    grads = dict(con.execute(f"SELECT mint, MIN(ts_received_utc_ns)/1e9 FROM {cps} GROUP BY 1").fetchall()) if cps else {}
    call_t = {}
    if calls:
        for m, t in con.execute(f"SELECT token_address, ts_received_utc_ns/1e9 FROM {calls} WHERE chain='solana'").fetchall():
            call_t.setdefault(m, []).append(t)
    promoted = set(con.execute(f"SELECT DISTINCT mint FROM ({' UNION ALL '.join(promos)})").df().mint)
    con.execute("CREATE TABLE act AS SELECT mint, CAST(floor(ts/600) AS BIGINT) AS b10 FROM tr GROUP BY 1, 2")
    rnd = random.Random(11)

    def arrays(mints):
        if not mints:
            return {}
        con.register("want", pd.DataFrame({"mint": list(mints)}))
        d = con.execute("SELECT tr.* FROM tr JOIN want USING (mint) ORDER BY mint, ts").df()
        return {m: (g.ts.values, g.px.values, g.u.values, g.is_buy.values.astype(bool), g.tok.values)
                for m, g in d.groupby("mint", sort=False)}

    rows = []
    for e in ev.itertuples():
        age = e.t - e.born
        cands = con.execute(f"""SELECT a.mint FROM act a JOIN born b USING (mint)
            WHERE a.b10 = {int((e.t - 1) // 600)} AND b.born BETWEEN {e.t - age * 1.5} AND {e.t - age * 0.5}""").df().mint
        # with the paid-orders backfill a token we never queried could be promoted without us knowing: controls only from queried ones
        cands = [m for m in cands if m not in promoted and m != e.mint and (not queried or m in queried)]
        rnd.shuffle(cands)
        arr = arrays([e.mint] + cands[:6])
        for role, m in [("push", e.mint)] + [("control", c) for c in cands[:6]]:
            if m not in arr:
                continue
            a = arr[m]
            born = e.born if role == "push" else con.execute(f"SELECT born FROM born WHERE mint='{m}'").fetchone()[0]
            f = features(*a, born, e.t)
            if f is None:
                continue
            o = outcome(*a, e.t, args.latency_s, f["_early"], f["_early_held"])
            if o is None:
                continue
            ct = call_t.get(m, [])
            rows.append({"role": role, "event": e.mint, "mint": m, "t": e.t, "kind": e.kind if role == "push" else "",
                         "tg_before": any(e.t - 7200 <= x < e.t for x in ct), "grad": m in grads and e.t < grads[m] <= e.t + 7200,
                         **{k: v for k, v in f.items() if not k.startswith("_")}, **o})
            if role == "control" and sum(1 for r in rows if r["event"] == e.mint and r["role"] == "control") >= 3:
                break
    df = pd.DataFrame(rows)
    out = ["# Push pago (DexScreener) × on-chain × Telegram en pump.fun", "",
           f"Tokens de Solana con boost/perfil pago visto: {n_promo_all}; de pump.fun nacidos dentro de lo grabado y "
           f"con ventana completa: {len(ev)}. Entrada {args.latency_s:.0f} s después del push, fee {FEE * 100:.2f}% por lado.",
           *([f"- Pagos históricos reconstruidos con la API de órdenes de DexScreener: {n_ord:,} tokens con alguna promoción "
              f"paga (la hora del evento es la hora del pago)."] if n_ord else []),
           *([delay_line] if delay_line else []), ""]
    if df.empty or not (df.role == "push").any():
        args.output.write_text("\n".join(out + ["Sin eventos suficientes todavía: dejar grabando más días."]), encoding="utf-8")
        print("Sin eventos suficientes")
        return
    cut = df[df.role == "push"].t.median()
    df["half"] = np.where(df.t < cut, "H1", "H2")
    push = df[df.role == "push"]
    head = ("| grupo | n | neto 5m med. | neto 15m med. / medio | neto 60m med. / medio | 2x antes de -50% | -50% antes de 2x | "
            "máx. mult. mediano | gradúa ≤2h | tempranas vendieron ≤15m |")
    sep = "|" + "---|" * 10

    def line(name, d):
        if len(d) < 5:
            return f"| {name} | {len(d)} | (pocos) |||||||| |"
        return (f"| {name} | {len(d)} | {d.net5.median() * 100:.1f}% | {d.net15.median() * 100:.1f}% / {d.net15.mean() * 100:.1f}% | "
                f"{d.net60.median() * 100:.1f}% / {d.net60.mean() * 100:.1f}% | {d.win2x.mean() * 100:.0f}% | "
                f"{d.loss50.mean() * 100:.0f}% | {d.max_mult.median():.2f}x | {d.grad.mean() * 100:.0f}% | "
                f"{d.early_sold_15m.median() * 100:.0f}% |")

    q_early = push.early_share.median()
    q_run = push.runup_30m.median()
    out += ["## Antes del push (mediana)", "",
            f"- Edad del token: {push.age_min.median():.0f} min. Suba en los 30 min previos: {q_run * 100:.0f}%. "
            f"Compradores en los 10 min previos: {push.buyers_10m.median():.0f}.",
            f"- Lo que todavía tienen las billeteras tempranas (primeros 5 min): {q_early * 100:.0f}% de lo comprado.",
            f"- Con call en Telegram en las 2 h previas: {push.tg_before.mean() * 100:.0f}%.", "",
            "## Después del push vs control (mismo momento, misma edad, sin push)", "", head, sep,
            line("push: todos", push), line("control", df[df.role == "control"])]
    for h in ("H1", "H2"):
        out.append(line(f"push {h}", push[push.half == h]))
        out.append(line(f"control {h}", df[(df.role == "control") & (df.half == h)]))
    ctl = df[df.role == "control"]

    def welch(a, b):
        a, b = np.asarray(a, float), np.asarray(b, float)
        if len(a) < 10 or len(b) < 10:
            return np.nan, np.nan
        se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        return (a.mean() - b.mean()) * 100, (a.mean() - b.mean()) / se if se > 0 else np.nan

    cuts = [("push: todos", push), ("push H1", push[push.half == "H1"]), ("push H2", push[push.half == "H2"]),
            (f"suba previa < mediana ({push.runup_30m.median() * 100:.0f}%)", push[push.runup_30m < push.runup_30m.median()]),
            ("suba previa ≥ mediana", push[push.runup_30m >= push.runup_30m.median()]),
            ("tempranas aún tienen ≥ mediana", push[push.early_share >= push.early_share.median()]),
            ("tempranas ya vendieron", push[push.early_share < push.early_share.median()]),
            ("con call en Telegram antes", push[push.tg_before]), ("sin call en Telegram antes", push[~push.tg_before])]
    out += ["", "## Diferencia con el control (retorno MEDIO del push menos el del control, en puntos) y su t de Welch", "",
            "| grupo | n push | 15 min: dif. (t) | 60 min: dif. (t) |", "|---|---|---|---|"]
    for name, d in cuts:
        d15, t15 = welch(d.net15, ctl.net15)
        d60, t60 = welch(d.net60, ctl.net60)
        out.append(f"| {name} | {len(d)} | " + (f"{d15:+.1f} (t {t15:.1f}) | {d60:+.1f} (t {t60:.1f}) |"
                                                 if d15 == d15 else "(pocos) | (pocos) |"))
    out += ["", "Con |t| < 2 la diferencia puede ser azar. Probé varios cortes: uno suelto con t ≈ 2 no alcanza."]
    out += ["", "## ¿Qué on-chain / social separa los push que funcionan?", "", head, sep,
            line(f"tempranas aún tienen ≥ mediana ({q_early * 100:.0f}%)", push[push.early_share >= q_early]),
            line("tempranas ya vendieron (< mediana)", push[push.early_share < q_early]),
            line(f"suba previa ≥ mediana ({q_run * 100:.0f}%)", push[push.runup_30m >= q_run]),
            line("suba previa < mediana", push[push.runup_30m < q_run]),
            line("con call en Telegram antes", push[push.tg_before]),
            line("sin call en Telegram antes", push[~push.tg_before]),
            line("boost", push[push.kind == "boost"]), line("perfil pago", push[push.kind == "perfil"]),
            "", "## Cómo leerlo", "",
            "- El push sirve si sus números le ganan al control en H1 **y** H2 (no solo en total).",
            "- Si gana cuando las tempranas AÚN tienen y pierde cuando ya vendieron: el push es la salida de los "
            "insiders, y la regla es entrar solo si todavía no vendieron y salir cuando empiezan.",
            "- `tempranas vendieron ≤15m` alto = el push se usó para descargar: esa es la señal de salida.",
            "- Con pocos días de datos los n son chicos: buscar diferencias grandes y consistentes.",
            "- Si la mediana y el promedio cuentan historias distintas, hay grupos mezclados: mirar los cortes de abajo."]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(out), encoding="utf-8")
    print(f"Reporte escrito en {args.output}")


if __name__ == "__main__":
    main()
