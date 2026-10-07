"""Tabla de cruce de señales de pump.fun: una fila por token en el momento en que llega a su compra N°10.

Para cada token se guardan las señales visibles en ese instante (solo pasado) y qué pasó después (precio de la curva
durante las 2 horas siguientes). Sirve para ver qué señales predicen y cuáles son ruido, y para medir las salidas.
Precio = reservas virtuales SOL / reservas virtuales tokens. Entrada = la operación SIGUIENTE a la señal (con 1,25% de
comisión); salida con 1,25%.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import numpy as np
import pandas as pd

FEE = 0.0125
HORIZON = 7200
K_BUYER = 10                      # el momento de decisión es la compra N°10 del token
LEVELS = (1.5, 2.0, 3.0, 5.0, 10.0)
SL = 0.5


def load(base: Path):
    con = duckdb.connect()
    t = con.execute(f"""SELECT slot, ts_chain_s AS ts, mint, "user" AS u, is_buy, sol_amount/1e9 AS sol,
            virtual_sol_reserves/virtual_token_reserves::DOUBLE AS px
        FROM read_parquet('{(base / 'pumpfun_trades.parquet').as_posix()}')
        WHERE ts_chain_s BETWEEN 1700000000 AND 1900000000 AND virtual_token_reserves > 0
        ORDER BY mint, slot, ts_chain_s""").df()
    c = con.execute(f"""SELECT mint, any_value(creator) creator, any_value("user") cu, min(ts_chain_s) born,
            any_value(symbol) AS symbol, any_value("name") AS name
        FROM read_parquet('{(base / 'pumpfun_creates.parquet').as_posix()}') GROUP BY 1""").df()
    return t, c


def sim_ladder(m: np.ndarray, t: np.ndarray, take=2.0, frac=0.5, trail=0.35, sl=SL) -> float:
    """Escalera actual sobre la ruta de múltiplos m (tiempos t en segundos desde la entrada). Devuelve retorno neto."""
    cost = 1.0 + FEE
    cash, qty, peak, took = 0.0, 1.0, 1.0, False
    for mi, ti in zip(m, t):
        peak = max(peak, mi)
        if not took:
            if mi <= sl:
                return (cash + qty * mi * (1 - FEE)) / cost - 1
            if mi >= take:
                cash += frac * mi * (1 - FEE)
                qty -= frac
                took = True
        elif mi <= peak * (1 - trail):
            return (cash + qty * mi * (1 - FEE)) / cost - 1
    last = m[-1] if len(m) else 1.0
    return (cash + qty * last * (1 - FEE)) / cost - 1


def sim_fixed(m: np.ndarray, tp: float, sl: float = SL) -> float:
    cost = 1.0 + FEE
    for mi in m:
        if mi <= sl:
            return sl * (1 - FEE) / cost - 1
        if mi >= tp:
            return tp * (1 - FEE) / cost - 1
    last = m[-1] if len(m) else 1.0
    return last * (1 - FEE) / cost - 1


def sim_trail(m: np.ndarray, trail: float, sl: float = SL) -> float:
    cost = 1.0 + FEE
    peak = 1.0
    for mi in m:
        peak = max(peak, mi)
        if mi <= sl and peak < 1.2:
            return mi * (1 - FEE) / cost - 1
        if peak >= 1.2 and mi <= peak * (1 - trail):
            return mi * (1 - FEE) / cost - 1
    last = m[-1] if len(m) else 1.0
    return last * (1 - FEE) / cost - 1


def build(base: Path) -> pd.DataFrame:
    t, c = load(base)
    tmax = int(t["ts"].max())
    born = dict(zip(c["mint"], c["born"]))
    creator = dict(zip(c["mint"], c["creator"].fillna(c["cu"])))
    name = dict(zip(c["mint"], (c["name"].fillna("") + " " + c["symbol"].fillna(""))))
    # billeteras que compran MUCHOS tokens distintos entre sus primeras compras = bots
    buys = t[t["is_buy"]]
    first_buys = buys.groupby("mint").head(20)
    wal_tokens = first_buys.groupby("u")["mint"].nunique()
    bots = set(wal_tokens[wal_tokens >= 30].index)
    ts_a, px_a, sol_a, buy_a = t["ts"].to_numpy(), t["px"].to_numpy(), t["sol"].to_numpy(), t["is_buy"].to_numpy()
    u_a, sl_a = t["u"].to_numpy(), t["slot"].to_numpy()
    mint_a = t["mint"].to_numpy()
    bounds = np.flatnonzero(np.r_[True, mint_a[1:] != mint_a[:-1], True])
    rows: List[Dict[str, Any]] = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        mint = mint_a[a]
        if mint not in born:
            continue
        isb = buy_a[a:b]
        bi = np.flatnonzero(isb)
        if len(bi) < K_BUYER:
            continue
        i = a + bi[K_BUYER - 1]                       # índice global de la compra N°10
        t0 = ts_a[i]
        if t0 + HORIZON > tmax or i + 1 >= b:
            continue
        age = t0 - born[mint]
        if age < 0 or age > 1800:
            continue
        j = i + 1                                      # entrada: la operación siguiente
        p0 = px_a[j]
        fut = (ts_a[j:b] <= t0 + HORIZON)
        pf = px_a[j:b][fut]
        tf = (ts_a[j:b][fut] - ts_a[j]).astype(float)
        m = pf / p0
        # señales visibles hasta i
        seg = slice(a, i + 1)
        ub = pd.unique(u_a[seg][buy_a[seg]])
        sell_sol = sol_a[seg][~buy_a[seg]].sum()
        buy_sol = sol_a[seg][buy_a[seg]].sum()
        last60 = (ts_a[seg] >= t0 - 60) & buy_a[seg]
        first_sol = sol_a[seg][buy_a[seg]]
        top1 = first_sol.max() / buy_sol if buy_sol > 0 else 0.0
        cr = creator.get(mint)
        creator_buys = bool(((u_a[seg] == cr) & buy_a[seg]).any()) if cr else False
        creator_sold = bool(((u_a[seg] == cr) & ~buy_a[seg]).any()) if cr else False
        row = {"mint": mint, "t0": int(t0), "edad_s": int(age), "compradores": len(ub),
               "vendedores": len(pd.unique(u_a[seg][~buy_a[seg]])), "sol_compra": float(buy_sol),
               "sol_venta": float(sell_sol), "neto_sol": float(buy_sol - sell_sol),
               "ratio_venta": float(sell_sol / buy_sol) if buy_sol > 0 else 0.0,
               "sol_compra_60s": float(sol_a[seg][last60].sum()), "top1_comprador": float(top1),
               "bots_entre_compradores": int(sum(1 for x in ub if x in bots)),
               "creador_compra": creator_buys, "creador_vendio": creator_sold,
               "subio_desde_inicio": float(px_a[i] / px_a[a]), "segs_en_10": int(t0 - ts_a[a + bi[0]]),
               "mismo_slot_creacion": int((sl_a[a:i + 1][buy_a[a:i + 1]][:K_BUYER] == sl_a[a]).sum()),
               "nombre": name.get(mint, "")}
        if len(m) == 0:
            continue
        net = m * (1 - FEE) / (1 + FEE) - 1
        row.update({"mfe": float(m.max()), "mae": float(m.min()), "final": float(m[-1]),
                    "retorno_final_neto": float(net[-1])})
        for L in LEVELS:                               # ¿llega a L antes de caer a -50%?
            hit = np.flatnonzero(m >= L)
            stop = np.flatnonzero(m <= SL)
            row[f"llega_{L}x"] = bool(len(hit) and (not len(stop) or hit[0] < stop[0]))
        stop = np.flatnonzero(m <= SL)
        row["cae_50"] = bool(len(stop))
        row["max_antes_de_caer"] = float(m[: stop[0]].max()) if len(stop) and stop[0] > 0 else (1.0 if len(stop) else float(m.max()))
        row["ladder"] = sim_ladder(m, tf)
        row["fijo_2x"] = sim_fixed(m, 2.0)
        row["fijo_1.5x"] = sim_fixed(m, 1.5)
        row["fijo_3x"] = sim_fixed(m, 3.0)
        row["trail_35"] = sim_trail(m, 0.35)
        row["trail_20"] = sim_trail(m, 0.20)
        row["aguantar_2h"] = float(net[-1])
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    base = Path(sys.argv[1])
    df = build(base)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tabla_pump.parquet")
    df.to_parquet(out)
    print(len(df), "tokens ->", out)
