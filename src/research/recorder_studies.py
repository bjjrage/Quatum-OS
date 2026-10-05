"""Estudios con los datos del recorder (segundos y minutos).

A) BTC -> alts: cuando BTC se mueve fuerte en 5 segundos, ¿cuántos segundos tarda cada alt en seguirlo, y se gana
   algo entrando en la alt 1-5 segundos después (pagando comisión y la diferencia compra/venta reales)?
B) Polymarket vs Binance: en los mercados "¿sube o baja?" de BTC/ETH/SOL, la probabilidad que implica el precio de
   Binance (modelo simple) contra el precio de Polymarket. ¿Apostar a favor de la diferencia ganaba al resolverse?

Todo se lee de data/raw (solo lectura). Los tiempos de Binance usan la hora del exchange; los de Polymarket se pasan
a esa misma hora corrigiendo el desfase del reloj de la PC (medido con Binance).
"""
from __future__ import annotations

import json
import math
import re
from array import array
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import NormalDist
from typing import Any, Dict, List, Optional, Sequence, Tuple

NaN = float("nan")
BTC = "BTCUSDT"
TAKER_FEE = 0.0004                     # 0,04% por lado en Binance futuros
POLY_CRYPTO_TAKER_FEE_RATE = 0.07     # current official formula; historical market fee schedule is not captured
POLY_FEE_MODEL_VERSION = "polymarket_crypto_taker_rate_2026-07"
POLY_FEE_SOURCE_URL = "https://help.polymarket.com/en/articles/13364478-trading-fees"
_N = NormalDist()


# --------------------------------------------------------------------------- lectura
def _files(base: Path, venue: str, table: str) -> List[str]:
    return [p.as_posix() for p in Path(base).glob(f"{venue}/table={table}/**/*.parquet")]


def _has_capture_source(files: Sequence[str]) -> bool:
    import pyarrow.parquet as pq
    return any("capture_source" in pq.read_schema(path).names for path in files)


def binance_seconds(base: Path, symbols: Optional[Sequence[str]] = None,
                    include_rest_fallback: bool = False) -> Tuple[int, Dict[str, Tuple[array, array]], int]:
    """Mejor compra/venta de Binance por segundo (último valor de cada segundo, hora del exchange), con relleno hacia
    adelante. Devuelve (segundo inicial, {símbolo: (bid, ask)}, desfase mediano recibido-exchange en ns)."""
    import duckdb
    f = _files(base, "binance_perp", "bbo_ticks")
    if not f:
        raise FileNotFoundError("El recorder no tiene bbo_ticks de Binance.")
    con = duckdb.connect()
    where = "bid_price > 0 AND ask_price > 0 AND ts_exchange_ns IS NOT NULL"
    if not include_rest_fallback and _has_capture_source(f):
        where += " AND COALESCE(capture_source, 'unknown') != 'rest_fallback'"
    if symbols:
        where += " AND symbol IN (" + ",".join(f"'{s}'" for s in symbols) + ")"
    off = con.execute(f"SELECT median(ts_received_utc_ns - ts_exchange_ns) FROM read_parquet({f!r}, union_by_name=true) "
                      f"WHERE {where} AND symbol = '{BTC}'").fetchone()[0]
    q_sql = f"""
        SELECT symbol, CAST(ts_exchange_ns // 1000000000 AS BIGINT) AS s,
               arg_max(bid_price, ts_exchange_ns) AS b, arg_max(ask_price, ts_exchange_ns) AS a
        FROM read_parquet({f!r}, union_by_name=true) WHERE {where} GROUP BY 1, 2
    """
    con.execute(f"CREATE TEMP TABLE sec AS {q_sql}")
    s0, s1 = con.execute(f"SELECT min(s), max(s) FROM sec WHERE symbol = '{BTC}'").fetchone()
    if s0 is None:
        raise ValueError("No hay datos de BTC en el recorder.")
    n = int(s1 - s0 + 1)
    out: Dict[str, Tuple[array, array]] = {}
    reader = con.execute("SELECT symbol, s, b, a FROM sec ORDER BY symbol, s").fetch_record_batch(200_000)
    for batch in reader:                           # por partes: nunca millones de objetos en memoria a la vez
        cols = [batch.column(i).to_pylist() for i in range(4)]
        for sy, sec, b, a in zip(*cols):
            if sy not in out:
                out[sy] = (array("d", [NaN]) * n, array("d", [NaN]) * n)
            i = sec - s0
            if 0 <= i < n:
                out[sy][0][i], out[sy][1][i] = b, a
    return s0, out, int(off or 0)


def bbo_source_counts(base: Path) -> Dict[str, Any]:
    """Counts provenance including legacy rows whose added column is absent."""
    import duckdb
    files = _files(base, "binance_perp", "bbo_ticks")
    counts = {"rows_websocket": 0, "rows_rest_fallback": 0, "rows_unknown": 0, "fallback_pct": 0.0}
    if not files:
        return counts
    if not _has_capture_source(files):
        counts["rows_unknown"] = int(duckdb.connect().execute(
            f"SELECT count(*) FROM read_parquet({files!r}, union_by_name=true)"
        ).fetchone()[0])
        return counts
    rows = duckdb.connect().execute(
        f"SELECT COALESCE(capture_source, 'unknown'), count(*) FROM read_parquet({files!r}, union_by_name=true) GROUP BY 1"
    ).fetchall()
    for source, count in rows:
        key = {"websocket": "rows_websocket", "rest_fallback": "rows_rest_fallback"}.get(source, "rows_unknown")
        counts[key] += int(count)
    total = sum(counts[k] for k in ("rows_websocket", "rows_rest_fallback", "rows_unknown"))
    counts["fallback_pct"] = counts["rows_rest_fallback"] * 100.0 / total if total else 0.0
    return counts


def _mid(b: array, a: array, i: int) -> float:
    return 0.5 * (b[i] + a[i]) if 0 <= i < len(b) and b[i] == b[i] and a[i] == a[i] else NaN


def quote_at_or_before(b: array, a: array, i: int, max_staleness_s: int) -> Optional[Tuple[float, float]]:
    """Latest valid bid/ask at or before i. Future observations are never inspected."""
    if max_staleness_s < 0:
        raise ValueError("max_staleness_s must be >= 0")
    for k in range(max_staleness_s + 1):
        j = i - k
        if 0 <= j < len(b) and b[j] == b[j] and a[j] == a[j] and 0 < b[j] <= a[j]:
            return float(b[j]), float(a[j])
    return None


def mid_at_or_before(b: array, a: array, i: int, max_staleness_s: int = 30) -> float:
    """Causal feature with an explicit staleness bound; NaN if no quote is valid."""
    quote = quote_at_or_before(b, a, i, max_staleness_s)
    return (quote[0] + quote[1]) / 2 if quote else NaN


def mid_near_resolution(b: array, a: array, i: int, max_staleness_s: int = 30) -> float:
    """Outcome mark: last observed mid before resolution. Never use this as a predictor."""
    return mid_at_or_before(b, a, i, max_staleness_s)


def polymarket_cost_components(outcome: float, bid_up: float, ask_up: float, side: str) -> Dict[str, float]:
    """One-share illustrative economics. Outcome is resolution payout for the selected side (0 or 1)."""
    mid_up = (bid_up + ask_up) / 2.0
    if side == "up":
        mid, execution = mid_up, ask_up
    elif side == "down":
        mid, execution = 1.0 - mid_up, 1.0 - bid_up
    else:
        raise ValueError("side must be 'up' or 'down'")
    gross = float(outcome) - mid
    spread_slippage = execution - mid
    fee_estimate = POLY_CRYPTO_TAKER_FEE_RATE * execution * (1.0 - execution)
    return {"gross_per_share": gross, "fees_per_share_estimate": fee_estimate,
            "spread_slippage_per_share": spread_slippage,
            "net_per_share_estimate": gross - fee_estimate - spread_slippage,
            "execution_price": execution}


def gap_report(q: Dict[str, Tuple[array, array]], s0: int, sym: str = BTC, min_gap: int = 31) -> Dict[str, Any]:
    """Huecos del recorder (sin precio > 30 s): cuántos, cuánto suman y en qué minuto de la hora empiezan."""
    b, a = q[sym]
    gaps, i, n = [], 0, len(b)
    while i < n:
        if b[i] != b[i]:
            j = i
            while j < n and b[j] != b[j]:
                j += 1
            gaps.append((i, j - i))
            i = j
        else:
            i += 1
    by_min: Dict[int, int] = {}
    for st, ln in gaps:
        mm = ((s0 + st) // 60) % 60
        by_min[mm] = by_min.get(mm, 0) + 1
    top = sorted(by_min.items(), key=lambda x: -x[1])[:5]
    return {"huecos": len(gaps), "segundos_perdidos": sum(l for _, l in gaps),
            "hueco_mas_largo_seg": max((l for _, l in gaps), default=0),
            "minuto_de_la_hora_mas_frecuente": [{"minuto": m, "huecos": c} for m, c in top]}


# --------------------------------------------------------------------------- A) BTC -> alts
def study_btc_lead(s0: int, q: Dict[str, Tuple[array, array]], win: int = 5, quantile: float = 0.999,
                   gap: int = 60, lags: Sequence[int] = (0, 1, 2, 3, 5, 10, 20, 30, 60),
                   delays: Sequence[int] = (1, 2, 5), holds: Sequence[int] = (10, 30, 60)) -> Dict[str, Any]:
    bb, ba = q[BTC]
    n = len(bb)
    r = [abs(mid_at_or_before(bb, ba, t, 30) / mid_at_or_before(bb, ba, t - win, 30) - 1.0)
         for t in range(win, n)]
    rv = sorted(x for x in r if x == x)
    if len(rv) < 1000:
        return {"status": "POCOS_DATOS"}
    thr = rv[int(len(rv) * quantile)]
    events, last = [], -10**9
    for t in range(win, n - 120):
        m1, m0 = mid_at_or_before(bb, ba, t, 30), mid_at_or_before(bb, ba, t - win, 30)
        if m1 == m1 and m0 == m0 and abs(m1 / m0 - 1.0) >= thr and t - last >= gap:
            events.append((t, 1 if m1 > m0 else -1, m1 / m0 - 1.0))
            last = t
    alts = [s for s in q if s != BTC]
    # respuesta: movimiento de la alt desde el inicio de la ventana de BTC (t-win) hasta t+lag, en la dirección de BTC
    resp = {L: [] for L in lags}
    trades = {(d, h): [] for d in delays for h in holds}
    per_event = {(d, h): [] for d in delays for h in holds}
    for t, sg, br in events:
        ev = {(d, h): [] for d in delays for h in holds}
        for s in alts:
            b, a = q[s]
            base = mid_at_or_before(b, a, t - win, 30)
            fin = mid_near_resolution(b, a, t + 60, 30)
            if not (base == base and fin == fin):
                continue
            for L in lags:
                m = mid_near_resolution(b, a, t + L, 30)
                if m == m:
                    resp[L].append(sg * (m / base - 1.0))
            for d in delays:
                for h in holds:
                    i, j = t + d, t + d + h
                    if j >= n:
                        continue
                    entry_quote = quote_at_or_before(b, a, i, 30)
                    exit_quote = quote_at_or_before(b, a, j, 30)
                    if not entry_quote or not exit_quote:
                        continue
                    if sg > 0:
                        ent, ex = entry_quote[1], exit_quote[0]
                        g = ex / ent - 1.0
                    else:
                        ent, ex = entry_quote[0], exit_quote[1]
                        g = ent / ex - 1.0
                    if g == g:
                        net = g - 2 * TAKER_FEE
                        trades[(d, h)].append(net)
                        ev[(d, h)].append(net)
        for k, v in ev.items():
            if v:
                per_event[k].append(sum(v) / len(v))
    full = sum(resp[60]) / len(resp[60]) if resp[60] else NaN
    resp_out = [{"segundos": L, "movimiento_medio_pct": (sum(v) / len(v) * 100.0) if v else None,
                 "porcentaje_del_total": (sum(v) / len(v) / full * 100.0) if v and full and full == full else None}
                for L, v in resp.items()]
    tr_out = []
    for (d, h), v in trades.items():
        pe = per_event[(d, h)]
        m = sum(pe) / len(pe) if pe else NaN
        sd = math.sqrt(sum((x - m) ** 2 for x in pe) / (len(pe) - 1)) if len(pe) > 1 else NaN
        tr_out.append({"entrar_a_los_seg": d, "mantener_seg": h, "operaciones": len(v),
                       "neto_medio_pct": (sum(v) / len(v) * 100.0) if v else None,
                       "aciertos": (sum(1 for x in v if x > 0) / len(v)) if v else None,
                       "t_stat_por_evento": (m / (sd / math.sqrt(len(pe)))) if pe and sd and sd == sd else None})
    return {"status": "OK", "horas_de_datos": n / 3600.0, "umbral_movimiento_btc_pct": thr * 100.0,
            "eventos_btc": len(events), "n_alts": len(alts), "respuesta_alts": resp_out, "operaciones": tr_out,
            "costo_ida_y_vuelta_pct": 2 * TAKER_FEE * 100.0}


# --------------------------------------------------------------------------- B) Polymarket vs Binance
_RANGE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*-\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*ET", re.I)
_SINGLE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*ET", re.I)
_ASSET = {"bitcoin": "BTCUSDT", "btc": "BTCUSDT", "ethereum": "ETHUSDT", "eth": "ETHUSDT",
          "solana": "SOLUSDT", "sol": "SOLUSDT"}


def _mins(h: str, m: Optional[str], ap: str) -> int:
    hh = int(h) % 12 + (12 if ap.upper() == "PM" else 0)
    return hh * 60 + int(m or 0)


def window_minutes(question: str) -> Optional[int]:
    """Duración de la ventana a partir de la pregunta ('3:15PM-3:30PM ET' -> 15, '3PM ET' -> 60, 'on October 4' -> 1440)."""
    m = _RANGE.search(question)
    if m:
        d = _mins(m.group(4), m.group(5), m.group(6)) - _mins(m.group(1), m.group(2), m.group(3))
        return d if d > 0 else d + 1440
    if _SINGLE.search(question):
        return 60
    if re.search(r"\bon\s+[A-Z][a-z]+\s+\d{1,2}\b", question):
        return 1440
    return None


def updown_markets(base: Path) -> List[Dict[str, Any]]:
    import duckdb
    f = _files(base, "polymarket", "polymarket_metadata_history")
    if not f:
        return []
    rows = duckdb.connect().execute(f"""
        SELECT market_id, arg_max(question, ts_polled_utc_ns), arg_max(end_date_iso, ts_polled_utc_ns),
               arg_max(clob_token_ids_json, ts_polled_utc_ns), arg_max(outcomes_json, ts_polled_utc_ns),
               arg_max(fee_schedule_raw_json, ts_polled_utc_ns)
        FROM read_parquet({f!r}, union_by_name=true) WHERE question ILIKE '%up or down%' GROUP BY 1
    """).fetchall()
    out = []
    for mid, qn, end, toks, outs, fee in rows:
        asset = next((v for k, v in _ASSET.items() if re.search(rf"\b{k}\b", qn or "", re.I)), None)
        dur = window_minutes(qn or "")
        try:
            toks_l, outs_l = json.loads(toks or "[]"), json.loads(outs or "[]")
            if isinstance(outs_l, str):
                outs_l = json.loads(outs_l)
            end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        except Exception:
            continue
        if not asset or not dur or len(toks_l) != 2 or len(outs_l) != 2:
            continue
        up_i = next((i for i, o in enumerate(outs_l) if str(o).lower() == "up"), None)
        if up_i is None:
            continue
        out.append({"market_id": str(mid), "question": qn, "asset": asset, "minutes": dur,
                    "end_s": int(end_dt.timestamp()), "start_s": int(end_dt.timestamp()) - dur * 60,
                    "up_token": str(toks_l[up_i]), "fee_raw": (fee or "")[:300]})
    return out


def poly_quotes(base: Path, tokens: Sequence[str], offset_ns: int, bucket_s: int = 5) -> Dict[str, Dict[int, Tuple[float, float]]]:
    """Mejor compra/venta del token 'Up' cada 5 s, pasado a hora del exchange (restando el desfase de la PC)."""
    import duckdb
    f = _files(base, "polymarket", "bbo_ticks")
    if not f or not tokens:
        return {}
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE tk(t VARCHAR)")
    con.executemany("INSERT INTO tk VALUES (?)", [(t,) for t in tokens])
    rows = con.execute(f"""
        SELECT symbol, CAST((ts_received_utc_ns - {int(offset_ns)}) // {bucket_s * 1_000_000_000} AS BIGINT) AS k,
               arg_max(bid_price, ts_received_utc_ns), arg_max(ask_price, ts_received_utc_ns)
        FROM read_parquet({f!r}, union_by_name=true) WHERE symbol IN (SELECT t FROM tk)
          AND bid_price > 0 AND ask_price > 0 AND bid_price <= ask_price GROUP BY 1, 2
    """).fetchall()
    out: Dict[str, Dict[int, Tuple[float, float]]] = {}
    for sym, k, b, a in rows:
        out.setdefault(str(sym), {})[int(k) * bucket_s] = (float(b), float(a))
    return out


_PREFIX: Dict[int, Tuple[List[float], List[float], List[int]]] = {}


def _prefix(b: array, a: array) -> Tuple[List[float], List[float], List[int]]:
    key = id(b)
    if key not in _PREFIX:
        n = len(b)
        ps, ps2, pc = [0.0] * (n + 1), [0.0] * (n + 1), [0] * (n + 1)
        prev = NaN
        for i in range(n):
            m = mid_at_or_before(b, a, i, 30)
            r = math.log(m / prev) if (m == m and prev == prev and prev > 0) else None
            ps[i + 1] = ps[i] + (r or 0.0)
            ps2[i + 1] = ps2[i] + (r * r if r is not None else 0.0)
            pc[i + 1] = pc[i] + (1 if r is not None else 0)
            prev = m
        _PREFIX[key] = (ps, ps2, pc)
    return _PREFIX[key]


def model_prob(b: array, a: array, s0: int, start_s: int, t_s: int, end_s: int, vol_win: int = 1800) -> float:
    """P(sube) = Φ( ln(S_t / S_inicio) / (σ·√τ) ), σ = volatilidad de 1 s de los últimos 30 min (solo pasado)."""
    i0, it = start_s - s0, t_s - s0
    S0, St = mid_at_or_before(b, a, i0, 30), mid_at_or_before(b, a, it, 30)
    if not (S0 == S0 and St == St) or it - vol_win < 1 or it >= len(b):
        return NaN
    ps, ps2, pc = _prefix(b, a)
    k = pc[it + 1] - pc[it + 1 - vol_win]
    if k < vol_win * 0.8:
        return NaN
    mu = (ps[it + 1] - ps[it + 1 - vol_win]) / k
    var = (ps2[it + 1] - ps2[it + 1 - vol_win]) / k - mu * mu
    sig = math.sqrt(var) if var > 0 else 0.0
    tau = end_s - t_s
    if sig <= 0 or tau <= 0:
        return NaN
    return _N.cdf(math.log(St / S0) / (sig * math.sqrt(tau)))


def study_poly(base: Path, s0: int, q: Dict[str, Tuple[array, array]], offset_ns: int,
               thresholds: Sequence[float] = (0.03, 0.05, 0.10), delay_s: int = 5) -> Dict[str, Any]:
    all_mk = updown_markets(base)
    n = len(q[BTC][0])
    s1 = s0 + n - 1
    mk = [m for m in all_mk if m["asset"] in q and m["start_s"] - 1800 >= s0 and m["end_s"] + 5 <= s1]
    diag = {"mercados_up_down_en_metadata": len(all_mk),
            "por_duracion_todos": {str(k): sum(1 for m in all_mk if m["minutes"] == k) for k in sorted({m["minutes"] for m in all_mk})},
            "dentro_del_periodo_grabado": len(mk),
            "ejemplos_preguntas": sorted({m["question"] for m in all_mk})[:8]}
    if not mk:
        return {"status": "SIN_MERCADOS", "diagnostico": diag}
    quotes = poly_quotes(base, [m["up_token"] for m in mk], offset_ns)
    diag["con_precios_grabados"] = sum(1 for m in mk if quotes.get(m["up_token"]))
    res = {thr: [] for thr in thresholds}
    brier_poly, brier_model, ambiguous, used = [], [], 0, 0
    by_minutes: Dict[int, int] = {}
    why: Dict[str, int] = {}
    diag["muestra"] = []
    for m in mk:
        b, a = q[m["asset"]]
        S0 = mid_at_or_before(b, a, m["start_s"] - s0, 30)
        S1 = mid_near_resolution(b, a, m["end_s"] - s0, 30)
        if len(diag["muestra"]) < 6:
            qt0 = quotes.get(m["up_token"], {})
            diag["muestra"].append({"q": m["question"], "asset": m["asset"], "min": m["minutes"],
                                    "inicio": datetime.fromtimestamp(m["start_s"], tz=timezone.utc).isoformat(),
                                    "fin": datetime.fromtimestamp(m["end_s"], tz=timezone.utc).isoformat(),
                                    "S0": S0, "S1": S1, "n_cotiz": len(qt0),
                                    "primera_cotiz": datetime.fromtimestamp(min(qt0), tz=timezone.utc).isoformat() if qt0 else None,
                                    "ultima_cotiz": datetime.fromtimestamp(max(qt0), tz=timezone.utc).isoformat() if qt0 else None})
        if not (S0 == S0 and S1 == S1):
            why["sin_precio_binance"] = why.get("sin_precio_binance", 0) + 1
            continue
        move = S1 / S0 - 1.0
        if abs(move) < 0.0001:                         # demasiado cerca: la fuente oficial podría dar otra cosa
            ambiguous += 1
            continue
        up = 1.0 if move > 0 else 0.0
        qt = quotes.get(m["up_token"], {})
        if not qt:
            why["sin_cotizaciones"] = why.get("sin_cotizaciones", 0) + 1
            continue
        used += 1
        by_minutes[m["minutes"]] = by_minutes.get(m["minutes"], 0) + 1
        mid_t = m["start_s"] + (m["end_s"] - m["start_s"]) // 2       # punto medio: comparar quién predice mejor
        qm = qt.get(mid_t - mid_t % 5)
        pm = model_prob(b, a, s0, m["start_s"], mid_t, m["end_s"])
        if qm and pm == pm:
            brier_poly.append((0.5 * (qm[0] + qm[1]) - up) ** 2)
            brier_model.append((pm - up) ** 2)
        done = set()
        for t in range(m["start_s"] + 60, m["end_s"] - 30, 5):
            if len(done) == len(thresholds):
                break
            qq = qt.get(t)
            nxt = qt.get(t + delay_s)
            if not qq or not nxt:
                continue
            p = model_prob(b, a, s0, m["start_s"], t, m["end_s"])
            if p != p:
                continue
            bid, ask = qq
            for thr in thresholds:
                if thr in done:
                    continue
                nb, na = nxt                                         # se ejecuta 5 s después, al precio de ese momento
                if p - ask >= thr:
                    costs = polymarket_cost_components(up, nb, na, "up")
                    res[thr].append({**costs, "pnl_before_fees": up - na, "precio": na, "lado": "sube", "dif": p - ask, "min": m["minutes"]})
                    done.add(thr)
                elif bid - p >= thr:
                    costs = polymarket_cost_components(1.0 - up, nb, na, "down")
                    res[thr].append({**costs, "pnl_before_fees": (1.0 - up) - (1.0 - nb), "precio": 1.0 - nb,
                                     "lado": "baja", "dif": bid - p, "min": m["minutes"]})
                    done.add(thr)
    out_t = []
    for thr, v in res.items():
        pn = [x["pnl_before_fees"] for x in v]
        if not pn:
            out_t.append({"umbral_pts": thr * 100, "apuestas": 0})
            continue
        mu = sum(pn) / len(pn)
        sd = math.sqrt(sum((x - mu) ** 2 for x in pn) / (len(pn) - 1)) if len(pn) > 1 else NaN
        out_t.append({"umbral_pts": thr * 100, "apuestas": len(pn),
                      "gross_per_share_mean": sum(x["gross_per_share"] for x in v) / len(v),
                      "fees_per_share_estimate_mean": sum(x["fees_per_share_estimate"] for x in v) / len(v),
                      "spread_slippage_per_share_mean": sum(x["spread_slippage_per_share"] for x in v) / len(v),
                      "net_per_share_estimate_mean": sum(x["net_per_share_estimate"] for x in v) / len(v),
                      "economics_status": "ECONOMICS_UNVERIFIED",
                      "aciertos": sum(1 for x in pn if x > 0) / len(pn),
                      "precio_medio_pagado": sum(x["precio"] for x in v) / len(v),
                      "t_stat": (mu / (sd / math.sqrt(len(pn)))) if sd and sd == sd else None,
                      "por_duracion_min": {str(k): sum(1 for x in v if x["min"] == k) for k in sorted({x["min"] for x in v})}})
    bp = sum(brier_poly) / len(brier_poly) if brier_poly else None
    bm = sum(brier_model) / len(brier_model) if brier_model else None
    diag["descartes"] = why
    return {"status": "OK", "diagnostico": diag, "mercados_usados": used, "mercados_ambiguos": ambiguous, "por_duracion_min": by_minutes,
            "error_prediccion_polymarket": bp, "error_prediccion_modelo": bm, "comparaciones_punto_medio": len(brier_poly),
            "apuestas": out_t, "ejemplo_fee_raw": next((m["fee_raw"] for m in mk if m["fee_raw"]), ""),
            "fee_model_version": POLY_FEE_MODEL_VERSION, "fee_source_url": POLY_FEE_SOURCE_URL,
            "economics_status": "ECONOMICS_UNVERIFIED",
            "nota": ("Economics status is ECONOMICS_UNVERIFIED: gross, estimated current fees, spread/slippage, and estimated net are reported separately. "
                     "Historical market fee schedules are not captured. Error de predicción = promedio de "
                     "(probabilidad - resultado)^2: más bajo es mejor.")}


def run_recorder_studies(base: Path, say=lambda m: None) -> Dict[str, Any]:
    say("Leyendo precios de Binance segundo a segundo del recorder (puede tardar unos minutos)...")
    s0, q, off = binance_seconds(base)
    say("Estudio A: BTC contra las alts...")
    a = study_btc_lead(s0, q)
    say("Estudio B: Polymarket contra Binance...")
    try:
        b = study_poly(base, s0, q, off)
    except Exception as ex:
        b = {"status": "ERROR", "error": f"{type(ex).__name__}: {ex}"}
    iso = lambda s: datetime.fromtimestamp(s, tz=timezone.utc).isoformat()
    return {"desde": iso(s0), "hasta": iso(s0 + len(q[BTC][0]) - 1), "desfase_reloj_pc_seg": off / 1e9,
            "binance_bbo_provenance": bbo_source_counts(base),
            "huecos_binance_btc": gap_report(q, s0),
            "simbolos_binance": len(q), "btc_vs_alts": a, "polymarket_vs_binance": b}
