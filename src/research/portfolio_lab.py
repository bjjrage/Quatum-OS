"""Laboratorio de carteras (días a semanas): las estrategias con más respaldo en estudios de cripto.

Cómo se mide (para no engañarnos):
  * Velas de 1 hora de varios años -> datos diarios. La señal usa el cierre del día (hora 23 UTC); se opera al
    cierre de la hora 00 siguiente (1 hora de demora: nada de mirar el futuro).
  * Cartera con exposición total 1 (la suma de |pesos| = 100% del capital). Costo 0,06% por cada peso que se
    mueve (0,04% comisión + 0,02% deslizamiento) y funding cobrado/pagado según la posición.
  * Tramo final (30%) reservado: una estrategia "pasa" solo si supera el umbral corregido por cantidad de
    pruebas en el entrenamiento Y sigue ganando en el tramo final.
  * Se compara con comprar y mantener BTC y con comprar y mantener todas por igual.
Sesgo conocido: solo cripto listadas HOY (las que murieron no están), lo que favorece a las estrategias que compran.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

NaN = float("nan")
BTC = "BTCUSDT"
COST_PER_TURNOVER = (4.0 + 2.0) / 1e4             # 0,06% por unidad de peso movida
WARMUP_DAYS = 150
HOLDOUT_FRACTION = 0.30


@dataclass
class Daily:
    days: List[int]                                    # epoch días (día UTC)
    sig: Dict[str, List[float]] = field(default_factory=dict)    # cierre hora 23 (señal)
    px: Dict[str, List[float]] = field(default_factory=dict)     # cierre hora 00 del día siguiente (ejecución)
    taker: Dict[str, List[float]] = field(default_factory=dict)  # compra agresiva / volumen del día
    fund: Dict[str, List[float]] = field(default_factory=dict)   # funding cobrado a un largo en (ejec d, ejec d+1]

    @property
    def n(self) -> int:
        return len(self.days)


def load_daily(hist_root: Path, min_days: int = 120) -> Daily:
    import duckdb
    root = Path(hist_root)
    con = duckdb.connect()
    data: Dict[str, Dict[int, Tuple[float, float, float, float]]] = {}
    for d in sorted((root / "klines_1h").glob("symbol=*")):
        sym = d.name.split("=", 1)[1]
        f = [p.as_posix() for p in d.glob("*.parquet")]
        rows = con.execute(f"SELECT open_time_ms // 3600000, close, volume, taker_buy_volume FROM read_parquet({f!r}) "
                           f"ORDER BY 1").fetchall()
        data[sym] = {int(h): (float(c), float(v), float(tb), 0.0) for h, c, v, tb in rows}
    if BTC not in data:
        raise FileNotFoundError("Faltan las velas de 1 hora de BTCUSDT: bajalas primero.")
    hb = sorted(data[BTC])
    d0, d1 = hb[0] // 24 + 1, hb[-1] // 24 - 1
    days = list(range(d0, d1 + 1))
    g = Daily(days=days)
    for sym, hm in data.items():
        sig, px, tk = [NaN] * len(days), [NaN] * len(days), [NaN] * len(days)
        for i, dd in enumerate(days):
            a = hm.get(dd * 24 + 23)
            b = hm.get((dd + 1) * 24)
            if a:
                sig[i] = a[0]
            if b:
                px[i] = b[0]
            vol = tb = 0.0
            for h in range(dd * 24, dd * 24 + 24):
                x = hm.get(h)
                if x:
                    vol += x[1]
                    tb += x[2]
            tk[i] = tb / vol if vol > 0 else NaN
        if sum(1 for x in px if x == x) >= min_days:
            g.sig[sym], g.px[sym], g.taker[sym] = sig, px, tk
    for sym in g.px:
        fr = [0.0] * len(days)
        fp = root / "funding" / f"symbol={sym}" / "funding.parquet"
        if fp.exists():
            for t_ms, rate in con.execute(f"SELECT funding_time_ms, funding_rate FROM read_parquet({fp.as_posix()!r})").fetchall():
                h = int(t_ms) // 3600000
                # la posición tomada al cierre de la hora 00 del día d+1 está abierta en (d+1)*24+1 .. (d+2)*24
                i = (h - 1) // 24 - 1 - d0
                if 0 <= i < len(days):
                    fr[i] += float(rate)
        g.fund[sym] = fr
    return g


# --------------------------------------------------------------------------- utilidades
def _r(x: List[float], d: int, L: int) -> float:
    if d - L < 0:
        return NaN
    a, b = x[d - L], x[d]
    return b / a - 1.0 if a == a and b == b and a > 0 else NaN


def _vol(x: List[float], d: int, L: int = 30) -> float:
    rs = [_r(x, k, 1) for k in range(d - L + 1, d + 1)]
    rs = [v for v in rs if v == v]
    if len(rs) < L * 0.8:
        return NaN
    m = sum(rs) / len(rs)
    return math.sqrt(sum((v - m) ** 2 for v in rs) / (len(rs) - 1))


def _norm(w: Dict[str, float]) -> Dict[str, float]:
    tot = sum(abs(v) for v in w.values())
    return {k: v / tot for k, v in w.items() if v} if tot > 0 else {}


def _alive(g: Daily, d: int, need: int) -> List[str]:
    return [s for s in g.px if g.sig[s][d] == g.sig[s][d] and d - need >= 0 and g.sig[s][d - need] == g.sig[s][d - need]
            and g.px[s][d] == g.px[s][d]]


def _rank_ls(scores: List[Tuple[float, str]], frac: float, long_high: bool, long_only: bool = False) -> Dict[str, float]:
    if len(scores) < 10:
        return {}
    scores.sort()
    k = max(1, int(len(scores) * frac))
    low, high = [s for _, s in scores[:k]], [s for _, s in scores[-k:]]
    longs, shorts = (high, low) if long_high else (low, high)
    w = {s: 1.0 for s in longs}
    if not long_only:
        for s in shorts:
            w[s] = w.get(s, 0.0) - 1.0
    return _norm(w)


# --------------------------------------------------------------------------- estrategias: f(g, d) -> pesos
def s_tsmom(L: int, long_only: bool, volw: bool):
    def f(g: Daily, d: int) -> Dict[str, float]:
        w = {}
        for s in _alive(g, d, L + 30):
            r = _r(g.sig[s], d, L)
            if r != r or r == 0:
                continue
            side = 1.0 if r > 0 else -1.0
            if long_only and side < 0:
                continue
            v = _vol(g.sig[s], d) if volw else 1.0
            if v == v and v > 0:
                w[s] = side / v
        return _norm(w)
    return f


def s_btc_filter(L: int, basket: bool):
    def f(g: Daily, d: int) -> Dict[str, float]:
        b = g.sig[BTC]
        if d < L:
            return {}
        ma = [x for x in b[d - L + 1:d + 1] if x == x]
        if len(ma) < L * 0.9 or not (b[d] > sum(ma) / len(ma)):
            return {}
        if not basket:
            return {BTC: 1.0}
        return _norm({s: 1.0 for s in _alive(g, d, 1)})
    return f


def s_xs(score: Callable[[Daily, str, int], float], need: int, long_high: bool, long_only: bool = False,
         frac: float = 0.2):
    def f(g: Daily, d: int) -> Dict[str, float]:
        sc = [(v, s) for s in _alive(g, d, need) for v in [score(g, s, d)] if v == v]
        return _rank_ls(sc, frac, long_high, long_only)
    return f


def sc_mom(L: int, skip: int = 0):
    return lambda g, s, d: _r(g.sig[s], d - skip, L)


def sc_vol(L: int):
    return lambda g, s, d: _vol(g.sig[s], d, L)


def sc_funding(L: int):
    def f(g, s, d):
        x = g.fund[s][max(0, d - 1 - L):d - 1]            # solo funding ya cobrado antes de la señal
        return sum(x) / len(x) if x else NaN
    return f


def sc_taker(L: int):
    def f(g, s, d):
        x = [v for v in g.taker[s][d - L + 1:d + 1] if v == v]
        return sum(x) / len(x) if len(x) >= L * 0.8 else NaN
    return f


def build_strategies() -> List[Tuple[str, str, Callable, int]]:
    """(familia, descripción, función de pesos, cada cuántos días se rebalancea)."""
    out: List[Tuple[str, str, Callable, int]] = []
    for L in (7, 14, 28, 56, 112):
        for lo in (False, True):
            out.append(("tendencia_por_activo", f"tendencia de {L} días en cada cripto (pesos por volatilidad), "
                        f"{'solo compras' if lo else 'compras y ventas'}", s_tsmom(L, lo, True), 1))
    for L in (20, 50, 100):
        out.append(("filtro_btc", f"tener BTC solo si está sobre su promedio de {L} días", s_btc_filter(L, False), 1))
        out.append(("filtro_btc", f"tener todas las cripto solo si BTC está sobre su promedio de {L} días",
                    s_btc_filter(L, True), 1))
    for L in (7, 14, 28, 56):
        for reb in (1, 7):
            out.append(("momentum_entre_cripto", f"comprar el 20% que más subió en {L} días y vender el 20% que menos, "
                        f"rebalanceo cada {reb} día(s)", s_xs(sc_mom(L, 1), L + 2, True), reb))
        out.append(("momentum_entre_cripto", f"solo comprar el 20% que más subió en {L} días, rebalanceo semanal",
                    s_xs(sc_mom(L, 1), L + 2, True, True), 7))
    for L in (1, 3, 7):
        out.append(("reversion_corta", f"comprar el 20% que más cayó en {L} día(s) y vender el que más subió, diario",
                    s_xs(sc_mom(L), L + 1, False), 1))
        out.append(("reversion_corta", f"solo comprar el 20% que más cayó en {L} día(s), diario",
                    s_xs(sc_mom(L), L + 1, False, True), 1))
    for L in (1, 7):
        out.append(("carry_funding", f"vender el 20% con funding más alto ({L} d) y comprar el más bajo, semanal",
                    s_xs(sc_funding(L), 2, False), 7))
    out.append(("baja_volatilidad", "comprar el 20% menos volátil (28 d) y vender el más volátil, semanal",
                s_xs(sc_vol(28), 30, False), 7))
    for L in (1, 7):
        for reb in (1, 7):
            out.append(("flujo_comprador", f"comprar el 20% con más compra agresiva ({L} d) y vender el de menos, "
                        f"rebalanceo cada {reb} día(s)", s_xs(sc_taker(L), L + 1, True), reb))
    return out


# --------------------------------------------------------------------------- motor
def backtest(g: Daily, weights_fn: Callable, reb: int = 1) -> List[Tuple[int, float, float]]:
    """Retornos diarios netos. Devuelve (índice de día, retorno neto, rotación)."""
    out: List[Tuple[int, float, float]] = []
    w: Dict[str, float] = {}
    for d in range(WARMUP_DAYS, g.n - 1):
        if (d - WARMUP_DAYS) % reb == 0:
            new = weights_fn(g, d)
        else:
            new = w
        turn = sum(abs(new.get(s, 0.0) - w.get(s, 0.0)) for s in set(new) | set(w))
        pnl = -COST_PER_TURNOVER * turn
        for s, wt in new.items():
            a, b = g.px[s][d], g.px[s][d + 1]
            if a == a and b == b and a > 0:
                pnl += wt * (b / a - 1.0) - wt * g.fund[s][d]
        out.append((d, pnl, turn))
        w = new
    return out


def stats(rows: List[Tuple[int, float, float]], btc: Optional[Dict[int, float]] = None) -> Dict[str, Any]:
    n = len(rows)
    if n < 20:
        return {"dias": n}
    x = [r for _, r, _ in rows]
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    eq, peak, dd = 1.0, 1.0, 0.0
    for v in x:
        eq *= 1.0 + v
        peak = max(peak, eq)
        dd = max(dd, 1.0 - eq / peak)
    out = {"dias": n, "retorno_diario_medio_pct": m * 100.0, "retorno_anual_pct": (eq ** (365.0 / n) - 1.0) * 100.0,
           "volatilidad_anual_pct": sd * math.sqrt(365) * 100.0,
           "sharpe": (m / sd * math.sqrt(365)) if sd > 0 else 0.0, "t_stat": (m / sd * math.sqrt(n)) if sd > 0 else 0.0,
           "caida_maxima_pct": dd * 100.0, "peor_dia_pct": min(x) * 100.0,
           "dias_positivos": sum(1 for v in x if v > 0) / n,
           "rotacion_diaria": sum(t for _, _, t in rows) / n}
    if btc:
        pairs = [(r, btc[d]) for d, r, _ in rows if d in btc]
        if len(pairs) > 20:
            mx = sum(p[0] for p in pairs) / len(pairs)
            my = sum(p[1] for p in pairs) / len(pairs)
            vy = sum((p[1] - my) ** 2 for p in pairs)
            out["beta_btc"] = sum((p[0] - mx) * (p[1] - my) for p in pairs) / vy if vy > 0 else 0.0
    return out


def run_portfolio_lab(g: Daily, strategies: Optional[list] = None, say=lambda m: None) -> Dict[str, Any]:
    strategies = strategies or build_strategies()
    split = WARMUP_DAYS + int((g.n - 1 - WARMUP_DAYS) * (1.0 - HOLDOUT_FRACTION))
    N = len(strategies)
    zthr = NormalDist().inv_cdf(1.0 - 0.05 / max(N, 1))
    btc_rows = backtest(g, lambda gg, d: {BTC: 1.0})
    btc_map = {d: r for d, r, _ in btc_rows}
    ew_rows = backtest(g, lambda gg, d: _norm({s: 1.0 for s in _alive(gg, d, 1)}))
    part = lambda rows: ([r for r in rows if r[0] < split], [r for r in rows if r[0] >= split])
    bench = {}
    for name, rows in (("comprar_y_mantener_BTC", btc_rows), ("comprar_y_mantener_todas", ew_rows)):
        a, b = part(rows)
        bench[name] = {"entrenamiento": stats(a, btc_map), "prueba_final": stats(b, btc_map)}
    res = []
    for i, (fam, desc, fn, reb) in enumerate(strategies):
        say(f"Probando estrategia {i + 1} de {N}: {desc[:70]}...")
        rows = backtest(g, fn, reb)
        a, b = part(rows)
        tr, ho = stats(a, btc_map), stats(b, btc_map)
        passed = bool(tr.get("t_stat", 0) >= zthr and ho.get("sharpe", 0) >= 0.75 and ho.get("retorno_diario_medio_pct", 0) > 0)
        res.append({"familia": fam, "estrategia": desc, "rebalanceo_dias": reb, "entrenamiento": tr,
                    "prueba_final": ho, "pasa": passed})
    res.sort(key=lambda r: -(r["entrenamiento"].get("t_stat") or -99))
    day0 = g.days[0]
    import datetime as _dt
    iso = lambda k: _dt.date.fromordinal(_dt.date(1970, 1, 1).toordinal() + g.days[k]).isoformat()
    return {"n_estrategias": N, "n_criptos": len(g.px), "desde": iso(WARMUP_DAYS), "corte": iso(split),
            "hasta": iso(g.n - 1), "dias_entrenamiento": split - WARMUP_DAYS, "dias_prueba_final": g.n - 1 - split,
            "umbral_t_corregido": zthr, "referencias": bench, "pasan": [r for r in res if r["pasa"]],
            "todas": res,
            "caveat": ("Solo cripto que existen hoy (las que desaparecieron no están): favorece a las estrategias que "
                       "compran. Una estrategia que pasa es candidata para paper trading, no una garantía.")}


def taker_robustness() -> List[Tuple[str, str, Callable, int]]:
    """Vecindario de parámetros de 'flujo comprador': si la idea es real, debería funcionar en casi todos, no en uno solo."""
    out = []
    for L in (3, 5, 7, 10, 14):
        for reb in (3, 5, 7, 10):
            for frac in (0.1, 0.2, 0.3):
                out.append(("flujo_comprador_vecinos", f"compra agresiva {L} d, rebalanceo {reb} d, {int(frac * 100)}% por lado",
                            s_xs(sc_taker(L), L + 1, True, False, frac), reb))
    return out
