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
    qvol: Dict[str, List[float]] = field(default_factory=dict)   # volumen del día en USDT

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
        rows = con.execute(f"SELECT open_time_ms // 3600000, close, volume, taker_buy_volume, quote_volume FROM read_parquet({f!r}) "
                           f"ORDER BY 1").fetchall()
        data[sym] = {int(h): (float(c), float(v), float(tb), float(qv or 0.0)) for h, c, v, tb, qv in rows}
    if BTC not in data:
        raise FileNotFoundError("Faltan las velas de 1 hora de BTCUSDT: bajalas primero.")
    hb = sorted(data[BTC])
    d0, d1 = hb[0] // 24 + 1, hb[-1] // 24 - 1
    days = list(range(d0, d1 + 1))
    g = Daily(days=days)
    for sym, hm in data.items():
        sig, px, tk, qv = [NaN] * len(days), [NaN] * len(days), [NaN] * len(days), [NaN] * len(days)
        for i, dd in enumerate(days):
            a = hm.get(dd * 24 + 23)
            b = hm.get((dd + 1) * 24)
            if a:
                sig[i] = a[0]
            if b:
                px[i] = b[0]
            vol = tb = q = 0.0
            for h in range(dd * 24, dd * 24 + 24):
                x = hm.get(h)
                if x:
                    vol += x[1]
                    tb += x[2]
                    q += x[3]
            tk[i] = tb / vol if vol > 0 else NaN
            qv[i] = q if vol > 0 else NaN
        if sum(1 for x in px if x == x) >= min_days:
            g.sig[sym], g.px[sym], g.taker[sym], g.qvol[sym] = sig, px, tk, qv
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
def backtest(g: Daily, weights_fn: Callable, reb: int = 1, cost: float = COST_PER_TURNOVER) -> List[Tuple[int, float, float]]:
    """Retornos diarios netos. Devuelve (índice de día, retorno neto, rotación)."""
    out: List[Tuple[int, float, float]] = []
    w: Dict[str, float] = {}
    for d in range(WARMUP_DAYS, g.n - 1):
        if (d - WARMUP_DAYS) % reb == 0:
            new = weights_fn(g, d)
        else:
            new = w
        turn = sum(abs(new.get(s, 0.0) - w.get(s, 0.0)) for s in set(new) | set(w))
        pnl = -cost * turn
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
    for i, spec in enumerate(strategies):
        fam, desc, fn, reb = spec[:4]
        say(f"Probando estrategia {i + 1} de {N}: {desc[:70]}...")
        rows = backtest(g, fn, reb, spec[4] if len(spec) > 4 else COST_PER_TURNOVER)
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


# --------------------------------------------------------------------------- versión 2 del flujo comprador
# Reglas fijadas ANTES de ver resultados (2026-10-04). Se prueban una sola vez.
COST_MAKER = 0.0003            # 0,03% por unidad movida con órdenes límite (supuesto: no todas se llenan a ese precio)


def sc_taker_z(L: int = 14, H: int = 90):
    """Compra agresiva de los últimos L días comparada con la normal de ESA cripto (últimos H días, antes de L)."""
    def f(g, s, d):
        x = g.taker[s]
        cur = [v for v in x[d - L + 1:d + 1] if v == v]
        base = [v for v in x[d - L - H + 1:d - L + 1] if v == v]
        if len(cur) < L * 0.8 or len(base) < H * 0.8:
            return NaN
        m = sum(base) / len(base)
        sd = math.sqrt(sum((v - m) ** 2 for v in base) / (len(base) - 1))
        return (sum(cur) / len(cur) - m) / sd if sd > 0 else NaN
    return f


def _liquid(g: Daily, d: int, syms: List[str], drop: float = 0.25, L: int = 30) -> List[str]:
    """Saca el 25% con menos volumen en dólares (promedio de 30 días)."""
    lv = []
    for s in syms:
        q = [v for v in g.qvol[s][d - L + 1:d + 1] if v == v] if g.qvol.get(s) else []
        if len(q) >= L * 0.8:
            lv.append((sum(q) / len(q), s))
    lv.sort()
    return [s for _, s in lv[int(len(lv) * drop):]]


def s_xs_buf(score, need: int, long_high: bool, frac: float = 0.2, keep: float = 0.3, liquid: bool = False):
    """Ranking con zona de tolerancia: una posición se mantiene mientras siga dentro del `keep` (30%) de su lado;
    se completa con las mejores hasta tener `frac` (20%) por lado. Menos rotación = menos costo."""
    state = {"L": [], "S": []}

    def f(g: Daily, d: int) -> Dict[str, float]:
        syms = _alive(g, d, need)
        if liquid:
            syms = _liquid(g, d, syms)
        sc = sorted((v, s) for s in syms for v in [score(g, s, d)] if v == v)
        if len(sc) < 10:
            state["L"], state["S"] = [], []
            return {}
        if not long_high:
            sc = [(-v, s) for v, s in sc][::-1]
        n = len(sc)
        k, kk = max(1, int(n * frac)), max(1, int(n * keep))
        top = [s for _, s in sc[::-1]]                       # de más fuerte a más débil
        bot = [s for _, s in sc]                             # de más débil a más fuerte
        longs = [s for s in state["L"] if s in top[:kk]]
        for s in top:
            if len(longs) >= k:
                break
            if s not in longs:
                longs.append(s)
        shorts = [s for s in state["S"] if s in bot[:kk] and s not in longs]
        for s in bot:
            if len(shorts) >= k:
                break
            if s not in shorts and s not in longs:
                shorts.append(s)
        state["L"], state["S"] = longs, shorts
        w = {s: 1.0 for s in longs}
        for s in shorts:
            w[s] = -1.0
        return _norm(w)
    return f


def s_combo(parts: List[Callable]):
    """Partes iguales de varias estrategias (cada una con exposición 1), re-normalizado a exposición 1."""
    def f(g: Daily, d: int) -> Dict[str, float]:
        w: Dict[str, float] = {}
        for p in parts:
            for s, v in p(g, d).items():
                w[s] = w.get(s, 0.0) + v / len(parts)
        return _norm(w)
    return f


def s_voltarget(base: Callable, target_annual: float = 0.15, cap: float = 2.0, L: int = 30):
    """Escala la exposición para que el riesgo estimado (con los últimos 30 días, solo pasado) sea ~15% anual."""
    tgt = target_annual / math.sqrt(365)

    def f(g: Daily, d: int) -> Dict[str, float]:
        w = base(g, d)
        if not w:
            return w
        rs = []
        for k in range(d - L + 1, d + 1):
            tot = 0.0
            for s, v in w.items():
                a, b = g.px[s][k - 1], g.px[s][k]
                if a == a and b == b and a > 0:
                    tot += v * (b / a - 1.0)
            rs.append(tot)
        m = sum(rs) / len(rs)
        sd = math.sqrt(sum((x - m) ** 2 for x in rs) / (len(rs) - 1))
        scale = min(cap, tgt / sd) if sd > 0 else 1.0
        return {s: v * scale for s, v in w.items()}
    return f


def taker_v2() -> list:
    """V1 de referencia + 4 versiones fijadas de antemano."""
    def taker_v2b():
        return s_xs_buf(sc_taker_z(14, 90), 14 + 90 + 2, True, liquid=True)

    def combo():
        return s_combo([taker_v2b(),
                        s_xs_buf(sc_funding(7), 9, False, liquid=True),
                        s_xs_buf(sc_vol(28), 30, False, liquid=True)])
    return [
        ("flujo_v2", "V1 referencia: compra agresiva 14 d, semanal, 20% por lado, costo a mercado",
         s_xs(sc_taker(14), 15, True), 7, COST_PER_TURNOVER),
        ("flujo_v2", "V2a costos: igual con órdenes límite y zona de tolerancia (se mantiene dentro del 30%)",
         s_xs_buf(sc_taker(14), 15, True), 7, COST_MAKER),
        ("flujo_v2", "V2b señal: compra agresiva contra su propia normal de 90 d, sin el 25% menos líquido",
         taker_v2b(), 7, COST_MAKER),
        ("flujo_v2", "V2c combinación: V2b + carry de funding + baja volatilidad, partes iguales",
         combo(), 7, COST_MAKER),
        ("flujo_v2", "V2d riesgo: V2c con riesgo constante de 15% anual (apalancamiento máx 2x)",
         s_voltarget(combo()), 7, COST_MAKER),
    ]


# --------------------------------------------------------------------------- nichos (rotación de sectores)
# Hipótesis de Marcelo (2026-10-05): la cripto se mueve fuerte por nichos que rotan. Reglas fijadas ANTES de ver
# resultados; se prueban una sola vez, con el mismo corte de entrenamiento / prueba final y la misma corrección.
def _sector_members(g: Daily, d: int, need: int) -> Dict[str, List[str]]:
    from src.research.niches import sector_of
    out: Dict[str, List[str]] = {}
    for s in _alive(g, d, need):
        sec = sector_of(s)
        if sec:
            out.setdefault(sec, []).append(s)
    return {k: v for k, v in out.items() if len(v) >= 2}


def _sector_score(g: Daily, d: int, need: int, score: Callable[[Daily, str, int], float]) -> Dict[str, Tuple[float, List[str]]]:
    out = {}
    for sec, mem in _sector_members(g, d, need).items():
        xs = [v for s in mem for v in [score(g, s, d)] if v == v]
        if len(xs) >= 2:
            out[sec] = (sum(xs) / len(xs), mem)
    return out


def s_sector_rot(score: Callable[[Daily, str, int], float], need: int, top: int = 2, long_only: bool = False,
                 long_high: bool = True):
    """Comprar los `top` nichos con puntaje más alto (pesos iguales dentro del nicho) y vender los `top` más bajos."""
    def f(g: Daily, d: int) -> Dict[str, float]:
        sc = _sector_score(g, d, need, score)
        if len(sc) < 2 * top + 1:
            return {}
        order = sorted(sc, key=lambda k: sc[k][0], reverse=long_high)
        w: Dict[str, float] = {}
        for k in order[:top]:
            for s in sc[k][1]:
                w[s] = w.get(s, 0.0) + 1.0 / (top * len(sc[k][1]))
        if not long_only:
            for k in order[-top:]:
                for s in sc[k][1]:
                    w[s] = w.get(s, 0.0) - 1.0 / (top * len(sc[k][1]))
        return _norm(w)
    return f


def s_laggards(L: int, top: int = 2, hedge: bool = True):
    """Dentro de los `top` nichos que más subieron en L días, comprar la mitad que MENOS subió (las rezagadas que
    suelen alcanzar). Con cobertura: vender en partes iguales todas las cripto vivas (neutral al mercado)."""
    def f(g: Daily, d: int) -> Dict[str, float]:
        sc = _sector_score(g, d, L + 2, sc_mom(L))
        if len(sc) < 3:
            return {}
        w: Dict[str, float] = {}
        for k in sorted(sc, key=lambda k: sc[k][0], reverse=True)[:top]:
            mem = sorted((r, s) for s in sc[k][1] for r in [_r(g.sig[s], d, L)] if r == r)
            lag = [s for _, s in mem[:max(1, len(mem) // 2)]]
            for s in lag:
                w[s] = w.get(s, 0.0) + 1.0 / (top * len(lag))
        if hedge:
            alive = _alive(g, d, 1)
            for s in alive:
                w[s] = w.get(s, 0.0) - 1.0 / len(alive)
        return _norm(w)
    return f


def sc_vol_surge(S: int = 3, B: int = 30):
    """Volumen en USDT de los últimos S días contra el promedio de los B anteriores (inicio de un nicho)."""
    def f(g, s, d):
        q = g.qvol[s]
        a = [v for v in q[d - S + 1:d + 1] if v == v]
        b = [v for v in q[d - S - B + 1:d - S + 1] if v == v]
        if len(a) < S or len(b) < B * 0.8:
            return NaN
        base = sum(b) / len(b)
        return (sum(a) / len(a)) / base if base > 0 else NaN
    return f


def s_sector_start(S: int = 3, top: int = 2):
    """Inicio de nicho: los nichos con más aumento de volumen Y que suben en esos días; vender los de menos aumento."""
    surge, mom = sc_vol_surge(S, 30), sc_mom(S)

    def f(g: Daily, d: int) -> Dict[str, float]:
        sv = _sector_score(g, d, S + 32, surge)
        sm = _sector_score(g, d, S + 32, mom)
        keys = [k for k in sv if k in sm]
        if len(keys) < 2 * top + 1:
            return {}
        hot = [k for k in sorted(keys, key=lambda k: sv[k][0], reverse=True) if sm[k][0] > 0][:top]
        cold = sorted(keys, key=lambda k: sv[k][0])[:top]
        if not hot:
            return {}
        w: Dict[str, float] = {}
        for k in hot:
            for s in sv[k][1]:
                w[s] = w.get(s, 0.0) + 1.0 / (len(hot) * len(sv[k][1]))
        for k in cold:
            if k in hot:
                continue
            for s in sv[k][1]:
                w[s] = w.get(s, 0.0) - 1.0 / (len(cold) * len(sv[k][1]))
        return _norm(w)
    return f


def niche_strategies() -> list:
    flujo = s_xs(sc_taker(14), 15, True)
    out = []
    for L in (3, 7, 14, 28):
        for reb in ((1, 7) if L <= 7 else (7,)):
            out.append(("nichos_rotacion", f"comprar los 2 nichos que más subieron en {L} d y vender los 2 que menos, "
                        f"rebalanceo cada {reb} d", s_sector_rot(sc_mom(L), L + 2), reb))
        out.append(("nichos_rotacion", f"solo comprar los 2 nichos que más subieron en {L} d, rebalanceo semanal",
                    s_sector_rot(sc_mom(L), L + 2, long_only=True), 7))
    for L in (3, 7, 14):
        out.append(("nichos_rezagadas", f"rezagadas de los 2 nichos más calientes ({L} d), cubierto con todo el mercado, "
                    f"cada {min(L, 7)} d", s_laggards(L), min(L, 7)))
        out.append(("nichos_rezagadas", f"rezagadas de los 2 nichos más calientes ({L} d), solo compras, cada {min(L, 7)} d",
                    s_laggards(L, hedge=False), min(L, 7)))
    for S in (3, 7):
        out.append(("nichos_inicio", f"inicio de nicho: más aumento de volumen {S} d y subiendo vs menos aumento, "
                    f"cada {S} d", s_sector_start(S), S))
    for L in (7, 14):
        out.append(("nichos_flujo", f"compra agresiva promedio del nicho ({L} d): 2 nichos más compradores vs 2 menos, "
                    f"semanal", s_sector_rot(sc_taker(L), L + 1), 7))
    out.append(("nichos_combinado", "flujo comprador V1 + rotación de nichos 7 d (mitad y mitad), semanal",
                s_combo([flujo, s_sector_rot(sc_mom(7), 9)]), 7))
    out.append(("nichos_combinado", "flujo comprador V1 + inicio de nicho 7 d (mitad y mitad), semanal",
                s_combo([flujo, s_sector_start(7)]), 7))
    out.append(("referencia", "flujo comprador V1 (referencia, misma corrida)", flujo, 7))
    return out
