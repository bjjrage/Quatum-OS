"""Inteligencia de billeteras en pump.fun, con lo que graba el recorder (data/raw/pumpfun).

1) Ficha por billetera: tokens operados, ganancia en SOL (realizada + marcada al último precio), aciertos,
   minuto de entrada desde el lanzamiento, tiempo de tenencia.
2) Habilidad vs suerte: se puntúa con la primera parte del período y se comprueba en la segunda.
3) Grupos: billeteras que compran el mismo token en los mismos segundos, repetido en varios tokens.
4) Creadores: cuántos tokens lanzó cada creador y cómo terminaron.
5) Señal: cuando compran billeteras "hábiles" (puntuadas solo con datos anteriores), ¿cuánto rinde entrar ahí,
   contra entradas en otros tokens de la misma edad y tamaño en el mismo período? Costos de Solana incluidos.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

LAMPORTS = 1e9
TOKEN_UNITS = 1e6
SUPPLY_TOKENS = 1e9                      # suministro de un token de pump.fun
ROUND_TRIP_COST = 0.03                   # 1% comisión pump.fun x2 + deslizamiento/prioridad ~1% (supuesto conservador)


def price_sol(vsol: float, vtok: float) -> float:
    """Precio en SOL por token según las reservas virtuales de la curva."""
    return (vsol / LAMPORTS) / (vtok / TOKEN_UNITS) if vtok and vsol else float("nan")


def load_trades(base: Path, start_s: Optional[int] = None, end_s: Optional[int] = None) -> List[tuple]:
    """(ts_s, slot, mint, user, is_buy, sol, tokens, precio_despues) ordenado por slot."""
    import duckdb
    f = [p.as_posix() for p in Path(base).glob("pumpfun/table=pumpfun_trades/**/*.parquet")]
    if not f:
        return []
    w = "TRUE"
    if start_s:
        w += f" AND ts_chain_s >= {int(start_s)}"
    if end_s:
        w += f" AND ts_chain_s <= {int(end_s)}"
    rows = duckdb.connect().execute(f"""
        SELECT DISTINCT ON (signature, mint, "user", is_buy, sol_amount, token_amount)
               ts_chain_s, slot, mint, "user", is_buy, sol_amount, token_amount, virtual_sol_reserves, virtual_token_reserves
        FROM read_parquet({f!r}, union_by_name=true) WHERE {w}
    """).fetchall()
    out = [(int(t), int(sl), m, u, bool(b), s / LAMPORTS, tk / TOKEN_UNITS, price_sol(vs, vt))
           for t, sl, m, u, b, s, tk, vs, vt in rows if t is not None]
    out.sort(key=lambda r: (r[1], r[0]))
    return out


def load_creates(base: Path) -> Dict[str, Dict[str, Any]]:
    import duckdb
    f = [p.as_posix() for p in Path(base).glob("pumpfun/table=pumpfun_creates/**/*.parquet")]
    if not f:
        return {}
    rows = duckdb.connect().execute(f"""SELECT mint, any_value(creator), any_value("user"), min(slot), min(ts_chain_s),
        any_value(symbol) FROM read_parquet({f!r}, union_by_name=true) GROUP BY 1""").fetchall()
    return {m: {"creator": c or u, "slot": sl, "ts": ts, "symbol": sy} for m, c, u, sl, ts, sy in rows}


def load_completes(base: Path) -> Dict[str, int]:
    import duckdb
    f = [p.as_posix() for p in Path(base).glob("pumpfun/table=pumpfun_completes/**/*.parquet")]
    if not f:
        return {}
    return {m: int(t or 0) for m, t in duckdb.connect().execute(
        f"SELECT mint, min(ts_chain_s) FROM read_parquet({f!r}, union_by_name=true) GROUP BY 1").fetchall()}


# --------------------------------------------------------------------------- 1) fichas
def wallet_token_pnl(trades: Sequence[tuple], until_s: Optional[int] = None) -> Dict[Tuple[str, str], Dict[str, float]]:
    """Resultado por (billetera, token): SOL gastado, recibido, tokens que le quedan, marcado al último precio."""
    pos: Dict[Tuple[str, str], Dict[str, float]] = {}
    last_px: Dict[str, float] = {}
    first_ts: Dict[str, int] = {}
    for ts, sl, m, u, buy, sol, tk, px in trades:
        if until_s is not None and ts > until_s:
            break
        first_ts.setdefault(m, ts)
        if px == px:
            last_px[m] = px
        p = pos.setdefault((u, m), {"spent": 0.0, "recv": 0.0, "tok": 0.0, "first": ts, "last": ts,
                                    "entry_age": ts - first_ts[m], "n": 0})
        p["n"] += 1
        p["last"] = ts
        if buy:
            p["spent"] += sol
            p["tok"] += tk
        else:
            p["recv"] += sol
            p["tok"] -= tk
    for (u, m), p in pos.items():
        mark = max(p["tok"], 0.0) * last_px.get(m, 0.0)
        p["pnl"] = p["recv"] + mark - p["spent"]
        p["roi"] = p["pnl"] / p["spent"] if p["spent"] > 0 else float("nan")
    return pos


def wallet_profiles(pos: Dict[Tuple[str, str], Dict[str, float]], min_tokens: int = 3) -> Dict[str, Dict[str, Any]]:
    by: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    for (u, m), p in pos.items():
        if p["spent"] > 0:
            by[u].append(p)
    out = {}
    for u, ps in by.items():
        if len(ps) < min_tokens:
            continue
        pn = [p["pnl"] for p in ps]
        ages = sorted(p["entry_age"] for p in ps)
        out[u] = {"tokens": len(ps), "pnl_sol": sum(pn), "spent_sol": sum(p["spent"] for p in ps),
                  "aciertos": sum(1 for x in pn if x > 0) / len(pn),
                  "edad_entrada_mediana_s": ages[len(ages) // 2]}
    return out


# --------------------------------------------------------------------------- 2) habilidad vs suerte
def skill_persistence(trades: Sequence[tuple], split_s: int, min_tokens: int = 3) -> Dict[str, Any]:
    """Puntúa con la primera mitad (tokens que nacieron antes del corte) y mira la segunda."""
    first_ts: Dict[str, int] = {}
    for t in trades:
        first_ts.setdefault(t[2], t[0])
    a = [t for t in trades if first_ts[t[2]] < split_s]
    b = [t for t in trades if first_ts[t[2]] >= split_s]
    pa, pb = wallet_profiles(wallet_token_pnl(a), min_tokens), wallet_profiles(wallet_token_pnl(b), min_tokens)
    both = [u for u in pa if u in pb]
    if len(both) < 20:
        return {"status": "POCOS_DATOS", "billeteras_en_ambos": len(both)}
    xs = [pa[u]["pnl_sol"] / max(pa[u]["spent_sol"], 1e-9) for u in both]
    ys = [pb[u]["pnl_sol"] / max(pb[u]["spent_sol"], 1e-9) for u in both]
    rx, ry = _ranks(xs), _ranks(ys)
    top = sorted(both, key=lambda u: -xs[both.index(u)])[: max(5, len(both) // 10)]
    rest = [u for u in both if u not in set(top)]
    agg = lambda us: sum(pb[u]["pnl_sol"] for u in us) / max(sum(pb[u]["spent_sol"] for u in us), 1e-9)
    return {"status": "OK", "billeteras_en_ambos": len(both), "correlacion_rangos": _corr(rx, ry),
            "top10pct_roi_tramo2": agg(top), "resto_roi_tramo2": agg(rest), "n_top": len(top)}


def _ranks(v: List[float]) -> List[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    for k, i in enumerate(order):
        r[i] = float(k)
    return r


def _corr(x: List[float], y: List[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else 0.0


# --------------------------------------------------------------------------- 3) grupos
def co_buy_groups(trades: Sequence[tuple], window_slots: int = 2, min_shared_tokens: int = 3,
                  max_buyers_per_burst: int = 40) -> Dict[str, Any]:
    """Pares de billeteras que compran el mismo token con <= 2 slots (~1 s) de diferencia, en >= 3 tokens distintos.
    Los grupos son los componentes conectados de esos pares."""
    buys: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
    for ts, sl, m, u, buy, sol, tk, px in trades:
        if buy:
            buys[m].append((sl, u))
    pair_tokens: Dict[Tuple[str, str], set] = defaultdict(set)
    for m, lst in buys.items():
        lst.sort()
        j = 0
        for i in range(len(lst)):
            while lst[i][0] - lst[j][0] > window_slots:
                j += 1
            burst = {u for _, u in lst[j:i + 1]}
            if len(burst) > max_buyers_per_burst:          # momentos de locura: no es coordinación, es multitud
                continue
            ui = lst[i][1]
            for uj in burst:
                if uj != ui:
                    pair_tokens[tuple(sorted((ui, uj)))].add(m)
    edges = [(a, b, len(t)) for (a, b), t in pair_tokens.items() if len(t) >= min_shared_tokens]
    parent: Dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, _ in edges:
        parent[find(a)] = find(b)
    comps: Dict[str, List[str]] = defaultdict(list)
    for x in parent:
        comps[find(x)].append(x)
    groups = sorted((g for g in comps.values() if len(g) >= 2), key=len, reverse=True)
    return {"pares_coordinados": len(edges), "grupos": len(groups),
            "tamanos": [len(g) for g in groups[:20]], "miembros": {i: g for i, g in enumerate(groups[:200])}}


# --------------------------------------------------------------------------- 4) creadores
def creator_stats(creates: Dict[str, Dict[str, Any]], completes: Dict[str, int]) -> Dict[str, Any]:
    by: Dict[str, List[str]] = defaultdict(list)
    for m, c in creates.items():
        by[c["creator"]].append(m)
    serial = {c: ms for c, ms in by.items() if len(ms) >= 3}
    grad = lambda ms: sum(1 for m in ms if m in completes)
    return {"creadores": len(by), "creadores_seriales_3mas": len(serial),
            "tokens_de_seriales": sum(len(v) for v in serial.values()),
            "graduacion_seriales": (sum(grad(v) for v in serial.values()) / max(1, sum(len(v) for v in serial.values()))),
            "graduacion_resto": (sum(grad(v) for c, v in by.items() if c not in serial) /
                                 max(1, sum(len(v) for c, v in by.items() if c not in serial)))}


# --------------------------------------------------------------------------- 5) señal: billeteras hábiles
def _forward(trades_by_mint: Dict[str, List[tuple]], m: str, ts: int, horizon_s: int,
             ts_index: Optional[Dict[str, List[int]]] = None) -> Optional[float]:
    """Retorno del precio desde la primera operación posterior a ts hasta la última <= ts+horizon."""
    import bisect
    lst = trades_by_mint[m]
    keys = ts_index[m] if ts_index is not None else [t[0] for t in lst]
    i = bisect.bisect_right(keys, ts)
    j = bisect.bisect_right(keys, ts + horizon_s) - 1
    lo = next((lst[k] for k in range(i, len(lst)) if lst[k][7] == lst[k][7]), None)
    if lo is None:
        return None
    hi = next((lst[k] for k in range(j, i - 1, -1) if lst[k][7] == lst[k][7]), None)
    if hi is None or lst.index(hi) < lst.index(lo):
        return None
    return hi[7] / lo[7] - 1.0


def smart_money_signal(trades: Sequence[tuple], split_s: int, k_wallets: int = 2, window_s: int = 60,
                       horizons: Sequence[int] = (300, 1800), top_frac: float = 0.05, min_tokens: int = 5,
                       seed: int = 7) -> Dict[str, Any]:
    """Billeteras hábiles = top 5% por ROI con >= 5 tokens, medido SOLO con tokens nacidos antes del corte.
    Señal (solo después del corte): >= k de ellas compran el mismo token dentro de 60 s. Se entra en la operación
    siguiente. Control: compras en otros tokens de la misma edad (±50%) y tamaño (±50%) en la misma hora."""
    first_ts: Dict[str, int] = {}
    for t in trades:
        first_ts.setdefault(t[2], t[0])
    prof = wallet_profiles(wallet_token_pnl([t for t in trades if first_ts[t[2]] < split_s]), min_tokens)
    ranked = sorted(prof.items(), key=lambda kv: -kv[1]["pnl_sol"] / max(kv[1]["spent_sol"], 1e-9))
    smart = {u for u, _ in ranked[: max(10, int(len(ranked) * top_frac))]}
    by_mint: Dict[str, List[tuple]] = defaultdict(list)
    for t in trades:
        by_mint[t[2]].append(t)
    for lst in by_mint.values():
        lst.sort(key=lambda t: (t[0], t[1]))
    ts_index = {m: [t[0] for t in lst] for m, lst in by_mint.items()}
    signals = []
    for m, lst in by_mint.items():
        if first_ts[m] < split_s:
            continue
        recent: List[Tuple[int, str]] = []
        for t in lst:
            if t[4] and t[3] in smart:
                recent = [(ts, u) for ts, u in recent if t[0] - ts <= window_s] + [(t[0], t[3])]
                if len({u for _, u in recent}) >= k_wallets and t[7] == t[7]:
                    signals.append((t[0], m, t[0] - first_ts[m], t[7] * SUPPLY_TOKENS))
                    break
    if len(signals) < 10:
        return {"status": "POCOS_DATOS", "senales": len(signals), "billeteras_habiles": len(smart)}
    # control: compras de cualquiera en tokens de edad y tamaño parecidos, misma hora
    pool: Dict[int, List[tuple]] = defaultdict(list)          # por hora: el control se busca en la misma hora
    for t in trades:
        if t[4] and first_ts[t[2]] >= split_s and t[7] == t[7]:
            pool[t[0] // 3600].append((t[0], t[2], t[0] - first_ts[t[2]], t[7] * SUPPLY_TOKENS))
    rnd = random.Random(seed)
    out = {}
    for h in horizons:
        sig_r, ctl_r = [], []
        for ts, m, age, mcap in signals:
            r = _forward(by_mint, m, ts, h, ts_index)
            if r is None:
                continue
            near = pool.get(ts // 3600, []) + pool.get(ts // 3600 - 1, []) + pool.get(ts // 3600 + 1, [])
            cands = [p for p in near if abs(p[0] - ts) <= 3600 and p[1] != m and 0.5 * age <= p[2] <= 1.5 * max(age, 1)
                     and 0.5 * mcap <= p[3] <= 1.5 * mcap]
            if not cands:
                continue
            c = cands[rnd.randrange(len(cands))]
            rc = _forward(by_mint, c[1], c[0], h, ts_index)
            if rc is None:
                continue
            sig_r.append(r - ROUND_TRIP_COST)
            ctl_r.append(rc - ROUND_TRIP_COST)
        if len(sig_r) < 10:
            out[str(h)] = {"comparaciones": len(sig_r)}
            continue
        diff = [a - b for a, b in zip(sig_r, ctl_r)]
        md = sum(diff) / len(diff)
        sd = math.sqrt(sum((x - md) ** 2 for x in diff) / (len(diff) - 1))
        med = lambda v: sorted(v)[len(v) // 2]
        out[str(h)] = {"comparaciones": len(sig_r), "senal_media": sum(sig_r) / len(sig_r), "senal_mediana": med(sig_r),
                       "control_media": sum(ctl_r) / len(ctl_r), "control_mediana": med(ctl_r),
                       "senal_ganan": sum(1 for x in sig_r if x > 0) / len(sig_r),
                       "control_ganan": sum(1 for x in ctl_r if x > 0) / len(ctl_r),
                       "diferencia_media": md, "t_stat": md / (sd / math.sqrt(len(diff))) if sd else None}
    return {"status": "OK", "billeteras_habiles": len(smart), "senales": len(signals), "por_horizonte_s": out,
            "costo_ida_vuelta_supuesto": ROUND_TRIP_COST}


def run_intel(base: Path, say=lambda m: None) -> Dict[str, Any]:
    say("Leyendo operaciones de pump.fun...")
    trades = load_trades(base)
    if len(trades) < 1000:
        return {"status": "POCOS_DATOS", "operaciones": len(trades)}
    t0, t1 = trades[0][0], trades[-1][0]
    split = t0 + (t1 - t0) // 2
    say("Fichas de billeteras...")
    pos = wallet_token_pnl(trades)
    prof = wallet_profiles(pos)
    top = sorted(prof.items(), key=lambda kv: -kv[1]["pnl_sol"])[:25]
    say("Habilidad vs suerte...")
    pers = skill_persistence(trades, split)
    say("Grupos coordinados...")
    grp = co_buy_groups(trades)
    say("Creadores...")
    cs = creator_stats(load_creates(base), load_completes(base))
    say("Señal de billeteras hábiles contra control...")
    sig = smart_money_signal(trades, split)
    return {"status": "OK", "horas": (t1 - t0) / 3600, "operaciones": len(trades),
            "tokens": len({t[2] for t in trades}), "billeteras": len({t[3] for t in trades}),
            "billeteras_con_3_tokens": len(prof), "top_billeteras": [{"billetera": u, **v} for u, v in top],
            "habilidad_vs_suerte": pers, "grupos": {k: v for k, v in grp.items() if k != "miembros"},
            "creadores": cs, "senal_billeteras_habiles": sig}
