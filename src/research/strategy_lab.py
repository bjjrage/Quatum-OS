"""Laboratorio de estrategias: prueba muchas ideas con el mismo juicio estricto y dice cuáles aguantan.

Diseño (para no engañarnos):
  * Velas de 1 hora (se arman desde el historial de 1 minuto de Binance). Operaciones de horas, donde los
    costos pesan poco frente al movimiento.
  * Las señales usan SOLO datos pasados. Se entra a la apertura de la vela siguiente (sin mirar el futuro).
  * Costos reales descontados: 0,04% comisión + 0,02% deslizamiento por lado (0,12% ida y vuelta).
  * "Ventaja sobre el azar" = lo que gana la señal por encima del movimiento promedio del mercado en ese mismo
    plazo (así una estrategia que solo compra en un mercado alcista no parece buena por suerte).
  * Se corrige por la cantidad de ideas probadas (Bonferroni) y se separa un tramo final (30%) que NO se usa
    para elegir: una idea "pasa" solo si también gana ahí.
"""
from __future__ import annotations

import math
from array import array
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

NaN = float("nan")
BTC, ETH = "BTCUSDT", "ETHUSDT"
COST_ROUNDTRIP = 2.0 * (4.0 + 2.0) / 1e4          # 0,12%
WARMUP = 340                                      # horas de calentamiento (volatilidad de 168 h)
HOLDOUT_FRACTION = 0.30


# --------------------------------------------------------------------------- datos
@dataclass
class Hourly:
    n: int
    h0: int                                       # primera hora (epoch horas)
    o: Dict[str, array] = field(default_factory=dict)
    c: Dict[str, array] = field(default_factory=dict)
    funding: Dict[str, List[Tuple[int, float]]] = field(default_factory=dict)   # (índice de hora, tasa)
    sig: Dict[str, array] = field(default_factory=dict)

    def symbols(self) -> List[str]:
        return list(self.c)


def load_hourly(hist_root: Path, symbols: Sequence[str], start_ms: Optional[int] = None,
                end_ms: Optional[int] = None, min_minutes: int = 45) -> Hourly:
    import duckdb
    con = duckdb.connect()
    where = ""
    if start_ms is not None:
        where += f" AND open_time_ms >= {int(start_ms)}"
    if end_ms is not None:
        where += f" AND open_time_ms <= {int(end_ms)}"
    raw: Dict[str, list] = {}
    for s in symbols:
        f = [p.as_posix() for p in Path(hist_root).glob(f"klines_1m/symbol={s}/*.parquet")]
        if not f:
            continue
        rows = con.execute(
            f"SELECT CAST(open_time_ms // 3600000 AS BIGINT) AS h, arg_min(open, open_time_ms), "
            f"arg_max(close, open_time_ms), count(*) FROM read_parquet({f!r}) WHERE TRUE {where} "
            f"GROUP BY 1 ORDER BY 1").fetchall()
        if rows:
            raw[s] = rows
    if BTC not in raw:
        raise FileNotFoundError("Falta el historial de BTCUSDT (es la referencia).")
    h0, h1 = raw[BTC][0][0], raw[BTC][-1][0]
    n = int(h1 - h0 + 1)
    g = Hourly(n=n, h0=int(h0))
    for s, rows in raw.items():
        o = array("d", [NaN]) * n
        c = array("d", [NaN]) * n
        for h, op, cl, cnt in rows:
            i = int(h - h0)
            if 0 <= i < n and cnt >= min_minutes:
                o[i], c[i] = float(op), float(cl)
        if sum(1 for x in c if x == x) > 24 * 30:     # al menos 30 días con datos
            g.o[s], g.c[s] = o, c
    for s in g.c:
        fp = Path(hist_root) / "funding" / f"symbol={s}" / "funding.parquet"
        if fp.exists():
            rows = con.execute(f"SELECT funding_time_ms, funding_rate FROM read_parquet({fp.as_posix()!r}) "
                               f"ORDER BY 1").fetchall()
            g.funding[s] = [(int(t // 3600000 - h0), float(r)) for t, r in rows if 0 <= int(t // 3600000 - h0) < n]
    return g


# --------------------------------------------------------------------------- utilidades de señal
def _sigma_1h(c: array, win: int = 168) -> array:
    """Desvío estándar de los retornos de 1 hora en las últimas `win` horas (solo pasado, hasta t inclusive)."""
    n = len(c)
    ps, ps2, pn = [0.0] * (n + 1), [0.0] * (n + 1), [0] * (n + 1)
    for i in range(n):
        r = c[i] / c[i - 1] - 1.0 if i > 0 and c[i] == c[i] and c[i - 1] == c[i - 1] and c[i - 1] > 0 else None
        ps[i + 1] = ps[i] + (r if r is not None else 0.0)
        ps2[i + 1] = ps2[i] + (r * r if r is not None else 0.0)
        pn[i + 1] = pn[i] + (1 if r is not None else 0)
    out = array("d", [NaN]) * n
    for t in range(win, n):
        k = pn[t + 1] - pn[t + 1 - win]
        if k >= win * 0.8:
            m = (ps[t + 1] - ps[t + 1 - win]) / k
            v = (ps2[t + 1] - ps2[t + 1 - win]) / k - m * m
            out[t] = math.sqrt(v) if v > 0 else NaN
    return out


def _ret(c: array, t: int, L: int) -> float:
    if t - L < 0:
        return NaN
    a, b = c[t - L], c[t]
    return b / a - 1.0 if a == a and b == b and a > 0 else NaN


Trade = Tuple[int, str, int, int, float]          # (hora de señal, cripto, lado +1/-1, horas de tenencia, pnl de funding)


# --------------------------------------------------------------------------- familias
def fam_ts(g: Hourly, L: int, k: float, H: int, mode: str, long_only: bool) -> List[Trade]:
    """Cada cripto por separado: movimiento fuerte de L horas -> seguirlo (momentum) o apostar a la vuelta (reversión)."""
    out: List[Trade] = []
    for s in g.symbols():
        if s in (BTC,):
            continue
        c, sg = g.c[s], g.sig[s]
        t = WARMUP
        while t < g.n - H - 2:
            r, sd = _ret(c, t, L), sg[t]
            if r == r and sd == sd and sd > 0:
                z = r / (sd * math.sqrt(L))
                side = 0
                if z >= k:
                    side = 1 if mode == "mom" else -1
                elif z <= -k:
                    side = -1 if mode == "mom" else 1
                if side and not (long_only and side < 0):
                    out.append((t, s, side, H, 0.0))
                    t += H
                    continue
            t += 1
    return out


def fam_xs(g: Hourly, L: int, H: int, mode: str, long_only: bool, frac: float = 0.2) -> List[Trade]:
    """Ranking entre cripto: cada H horas, comprar las más fuertes (o más débiles) y vender las contrarias."""
    out: List[Trade] = []
    syms = [s for s in g.symbols() if s != BTC]
    for t in range(WARMUP, g.n - H - 2, H):
        rk = [(r, s) for s in syms for r in [_ret(g.c[s], t, L)] if r == r]
        if len(rk) < 20:
            continue
        rk.sort()
        k = max(1, int(len(rk) * frac))
        low, high = [s for _, s in rk[:k]], [s for _, s in rk[-k:]]
        longs, shorts = (high, low) if mode == "mom" else (low, high)
        out += [(t, s, 1, H, 0.0) for s in longs]
        if not long_only:
            out += [(t, s, -1, H, 0.0) for s in shorts]
    return out


def fam_lag(g: Hourly, L: int, k: float, H: int, long_only: bool) -> List[Trade]:
    """Altcoin rezagada: BTC se movió fuerte y la alt todavía no lo siguió -> entrar en la dirección de BTC."""
    out: List[Trade] = []
    btc, sb = g.c[BTC], g.sig[BTC]
    last: Dict[str, int] = {}
    for t in range(WARMUP, g.n - H - 2):
        rb, sd = _ret(btc, t, L), sb[t]
        if not (rb == rb and sd == sd and sd > 0):
            continue
        if abs(rb) < k * sd * math.sqrt(L):
            continue
        d = 1 if rb > 0 else -1
        if long_only and d < 0:
            continue
        for s in g.symbols():
            if s in (BTC, ETH) or last.get(s, -10**9) > t:
                continue
            ra = _ret(g.c[s], t, L)
            if ra == ra and d * ra < 0.5 * abs(rb):
                out.append((t, s, d, H, 0.0))
                last[s] = t + H
    return out


def fam_funding(g: Hourly, H: int, short_only: bool, frac: float = 0.2) -> List[Trade]:
    """Funding extremo: vender las cripto con funding más alto (y comprar las más bajo); se cobra/paga el funding."""
    out: List[Trade] = []
    by_t: Dict[int, List[Tuple[float, str]]] = {}
    for s, ev in g.funding.items():
        for t, r in ev:
            by_t.setdefault(t, []).append((r, s))
    steps = max(1, H // 8)
    for j, t in enumerate(sorted(by_t)):
        if j % steps or t < WARMUP or t >= g.n - H - 2:
            continue
        rk = sorted(by_t[t])
        if len(rk) < 20:
            continue
        k = max(1, int(len(rk) * frac))
        picks = [(s, -1) for _, s in rk[-k:]] + ([] if short_only else [(s, 1) for _, s in rk[:k]])
        for s, side in picks:
            fsum = sum(r for te, r in g.funding[s] if t + 1 < te <= t + H)
            out.append((t, s, side, H, -side * fsum))        # largo paga funding positivo, corto lo cobra
    return out


def fam_hour(g: Hourly, hour: int, H: int) -> List[Trade]:
    """Hora del día: comprar todo a una hora fija (UTC) y mantener H horas."""
    out: List[Trade] = []
    for t in range(WARMUP, g.n - H - 2):
        if (g.h0 + t + 1) % 24 == hour:
            out += [(t, s, 1, H, 0.0) for s in g.symbols() if s != BTC]
    return out


def build_configs() -> List[Tuple[str, str, Callable[[Hourly], List[Trade]], int]]:
    """(familia, descripción en castellano, función, horas de tenencia)."""
    cfgs: List[Tuple[str, str, Callable, int]] = []
    for mode, nm in (("mom", "seguir la tendencia"), ("rev", "apostar a la vuelta")):
        for L in (3, 12, 48):
            for k in (1.5, 2.5):
                for H in (6, 24):
                    for lo in (False, True):
                        cfgs.append(("movimiento_fuerte", f"{nm}: tras un movimiento de {L} h de {k} desvíos, "
                                     f"mantener {H} h, {'solo compras' if lo else 'compras y ventas'}",
                                     (lambda g, L=L, k=k, H=H, m=mode, lo=lo: fam_ts(g, L, k, H, m, lo)), H))
    for mode, nm in (("mom", "comprar las más fuertes"), ("rev", "comprar las más débiles")):
        for L in (24, 72, 168):
            for H in (24, 72):
                for lo in (False, True):
                    cfgs.append(("ranking", f"ranking: {nm} de las últimas {L} h, rotar cada {H} h, "
                                 f"{'solo compras' if lo else 'compras y ventas'}",
                                 (lambda g, L=L, H=H, m=mode, lo=lo: fam_xs(g, L, H, m, lo)), H))
    for L in (1, 3, 6):
        for k in (1.5, 2.5):
            for H in (3, 12):
                for lo in (False, True):
                    cfgs.append(("alt_rezagada", f"altcoin rezagada: BTC se movió {k} desvíos en {L} h, seguirlo "
                                 f"{H} h, {'solo compras' if lo else 'compras y ventas'}",
                                 (lambda g, L=L, k=k, H=H, lo=lo: fam_lag(g, L, k, H, lo)), H))
    for H in (8, 24, 72):
        for so in (True, False):
            cfgs.append(("funding", f"funding extremo: vender el 20% con funding más alto"
                         f"{'' if so else ' y comprar el 20% más bajo'}, mantener {H} h",
                         (lambda g, H=H, so=so: fam_funding(g, H, so)), H))
    for hour in range(24):
        for H in (1, 4):
            cfgs.append(("hora_del_dia", f"comprar todo a las {hour:02d}:00 UTC y mantener {H} h",
                         (lambda g, hour=hour, H=H: fam_hour(g, hour, H)), H))
    return cfgs


# --------------------------------------------------------------------------- evaluación
def _drift(g: Hourly, H: int, lo: int, hi: int) -> float:
    """Retorno promedio de comprar cualquier cripto en cualquier hora (movimiento general del mercado)."""
    tot, cnt = 0.0, 0
    for s in g.symbols():
        o, c = g.o[s], g.c[s]
        for t in range(max(lo, WARMUP), min(hi, g.n - H - 2), 3):
            a, b = o[t + 1], c[t + H]
            if a == a and b == b and a > 0:
                tot += b / a - 1.0
                cnt += 1
    return tot / cnt if cnt else 0.0


def _summ(rows: List[Tuple[int, float, float]], days: float) -> Dict[str, Any]:
    """rows = (hora, neto crudo, neto sobre el azar). t-stat sobre promedios diarios (las operaciones del mismo día no
    son independientes: contarlas por separado inflaría la confianza)."""
    n = len(rows)
    if n == 0:
        return {"n_trades": 0}
    daily: Dict[int, List[float]] = {}
    for t, _, ex in rows:
        daily.setdefault(t // 24, []).append(ex)
    ser = [sum(v) / len(v) for v in daily.values()]
    m = sum(ser) / len(ser)
    sd = math.sqrt(sum((x - m) ** 2 for x in ser) / (len(ser) - 1)) if len(ser) > 1 else 0.0
    return {"n_trades": n, "por_dia": n / max(days, 1e-9), "aciertos": sum(1 for _, r, _ in rows if r > 0) / n,
            "neto_medio_pct": sum(r for _, r, _ in rows) / n * 100.0,
            "exceso_neto_pct": sum(e for _, _, e in rows) / n * 100.0,
            "t_stat": (m / (sd / math.sqrt(len(ser)))) if sd > 0 else 0.0, "dias_con_datos": len(ser)}


def evaluate_config(g: Hourly, trades: List[Trade], H: int, split: int, drift: Dict[Tuple[int, str], float]
                    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    tr, ho = [], []
    for t, s, side, hold, fund in trades:
        o, c = g.o[s], g.c[s]
        a, b = o[t + 1], c[t + hold]
        if not (a == a and b == b and a > 0):
            continue
        r = b / a - 1.0
        raw = side * r + fund - COST_ROUNDTRIP
        if t + hold < split:
            tr.append((t, raw, side * (r - drift[(hold, "train")]) + fund - COST_ROUNDTRIP))
        elif t >= split:
            ho.append((t, raw, side * (r - drift[(hold, "test")]) + fund - COST_ROUNDTRIP))
    return (_summ(tr, split / 24.0), _summ(ho, (g.n - split) / 24.0))


def run_lab(hist_root: Path, symbols: Sequence[str], days: float = 365.0, on_status=None,
            configs: Optional[list] = None) -> Dict[str, Any]:
    say = on_status or (lambda m: None)
    import time as _t
    end_ms = int(_t.time() * 1000)
    say("Leyendo el historial por horas...")
    g = load_hourly(hist_root, list(symbols), start_ms=end_ms - int(days * 86400_000))
    g.sig = {s: _sigma_1h(c) for s, c in g.c.items()}
    return run_lab_on(g, configs or build_configs(), say)


def run_lab_on(g: Hourly, cfgs: list, say=lambda m: None) -> Dict[str, Any]:
    split = int(g.n * (1.0 - HOLDOUT_FRACTION))
    hs = sorted({h for _, _, _, h in cfgs})
    drift = {}
    for h in hs:
        drift[(h, "train")] = _drift(g, h, WARMUP, split - h)
        drift[(h, "test")] = _drift(g, h, split, g.n)
    N = len(cfgs)
    zthr = NormalDist().inv_cdf(1.0 - 0.05 / max(N, 1))
    rows = []
    for i, (fam, desc, fn, H) in enumerate(cfgs):
        say(f"Probando idea {i + 1} de {N}: {desc[:60]}...")
        trades = fn(g)
        tr, ho = evaluate_config(g, trades, H, split, drift)
        passed = bool(tr.get("n_trades", 0) >= 100 and ho.get("n_trades", 0) >= 50
                      and tr.get("t_stat", 0) >= zthr and ho.get("t_stat", 0) >= 1.65
                      and ho.get("exceso_neto_pct", 0) > 0 and ho.get("neto_medio_pct", 0) > 0)
        rows.append({"familia": fam, "idea": desc, "horas": H, "entrenamiento": tr, "prueba_final": ho, "pasa": passed})
    rows.sort(key=lambda r: -(r["entrenamiento"].get("t_stat") or -99))
    fams: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        f = fams.setdefault(r["familia"], {"ideas": 0, "pasan": 0, "mejor_t_entrenamiento": -99.0})
        f["ideas"] += 1
        f["pasan"] += 1 if r["pasa"] else 0
        f["mejor_t_entrenamiento"] = max(f["mejor_t_entrenamiento"], r["entrenamiento"].get("t_stat") or -99.0)
    return {"n_ideas": N, "n_criptos": len(g.symbols()), "dias_entrenamiento": split / 24.0,
            "dias_prueba_final": (g.n - split) / 24.0, "umbral_t_corregido": zthr,
            "costo_ida_y_vuelta_pct": COST_ROUNDTRIP * 100.0, "pasan": [r for r in rows if r["pasa"]],
            "por_familia": fams, "top_entrenamiento": rows[:15], "todas": rows,
            "caveat": ("Una idea 'pasa' solo si supera el umbral corregido por cantidad de pruebas en el tramo de "
                       "entrenamiento Y gana en el tramo final que no se usó para elegir. Aun así, es evidencia "
                       "preliminar: hace falta paper trading antes de arriesgar dinero.")}
