"""Análisis "activos parecidos a PYR": ¿la estrategia de rebote funciona en cripto volátiles de capitalización chica?

Lo que hace (todo con el historial de Binance ya descargado):
  1. Perfila cada cripto con un tramo de ENTRENAMIENTO (volatilidad en velas de 5 min, caídas fuertes por día).
  2. Arma dos grupos con ese perfil: "parecidas a PYR" (las más volátiles) y "tranquilas" (las menos), más "todas".
  3. Prueba la estrategia SOLO en un tramo posterior que no se usó para elegir (tramo de PRUEBA),
     con varias salidas y varios niveles de costos, y la compara contra entrar al azar con la misma salida.

PYR (2022) no está en el historial descargado: se usa como referencia "chica, volátil, de juegos".
"""
from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from src.research.str002_replay import (BTC, ETH, VARIANTS, ReplayConfig, _run_cfg, btc_move_sigmas,
                                        data_coverage, historical_range, load_panel_historical,
                                        random_baseline, resample_panel, summarize)

# Cripto chicas / volátiles / de juegos y metaverso, listadas en futuros de Binance (las que no existan
# se saltan solas: el descargador cuenta "no existe en Binance").
PYR_CANDIDATES: List[str] = [
    "PYRUSDT", "GALAUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT", "IMXUSDT", "ENJUSDT", "GMTUSDT", "APEUSDT",
    "ILVUSDT", "YGGUSDT", "MAGICUSDT", "GMXUSDT", "MASKUSDT", "ALICEUSDT", "CHZUSDT", "DYDXUSDT",
    "PIXELUSDT", "PORTALUSDT", "BEAMXUSDT", "RONINUSDT", "ACEUSDT", "XAIUSDT", "ARKMUSDT", "1000BONKUSDT",
    "1000FLOKIUSDT", "1000SHIBUSDT", "ONDOUSDT", "WLDUSDT", "STRKUSDT", "DYMUSDT", "ALTUSDT", "MANTAUSDT",
    "AEVOUSDT", "SAGAUSDT", "TNSRUSDT", "ZETAUSDT", "SUPERUSDT", "VANRYUSDT", "NOTUSDT", "1000SATSUSDT",
]

COST_SCENARIOS: Dict[str, Tuple[float, float]] = {          # (fee_bps por lado, slippage_bps por lado)
    "sin_costos": (0.0, 0.0),
    "costo_bajo": (2.0, 1.0),
    "costo_real": (4.0, 2.0),
}


def analysis_symbols(base: Sequence[str]) -> List[str]:
    out = list(base)
    for s in PYR_CANDIDATES:
        if s not in out:
            out.append(s)
    return out


# ------------------------------------------------------------------ perfil
def _closes_5m(hist_root: Path, sym: str, start_ms: int, end_ms: int) -> List[float]:
    import duckdb
    f = [p.as_posix() for p in Path(hist_root).glob(f"klines_1m/symbol={sym}/*.parquet")]
    if not f:
        return []
    rows = duckdb.connect().execute(
        f"SELECT arg_max(close, open_time_ms) FROM read_parquet({f!r}) "
        f"WHERE open_time_ms BETWEEN {start_ms} AND {end_ms} GROUP BY open_time_ms // 300000 "
        f"ORDER BY open_time_ms // 300000").fetchall()
    return [float(r[0]) for r in rows]


def profile_symbols(hist_root: Path, symbols: Sequence[str], start_ns: int, end_ns: int,
                    drop_pct: float = 1.5, min_days: float = 20.0) -> List[Dict[str, Any]]:
    """Por cripto: volatilidad en 5 min, caídas fuertes por día y qué pasó 30 min después de cada caída."""
    out = []
    for sym in symbols:
        c = _closes_5m(hist_root, sym, start_ns // 1_000_000, end_ns // 1_000_000)
        days = len(c) * 5 / 1440.0
        if days < min_days:
            continue
        r = [c[i] / c[i - 1] - 1.0 for i in range(1, len(c))]
        mu = sum(r) / len(r)
        sd = math.sqrt(sum((x - mu) ** 2 for x in r) / max(1, len(r) - 1))
        thr = -drop_pct / 100.0
        fwd = []
        n_drops = 0
        for i, x in enumerate(r, start=1):
            if x <= thr:
                n_drops += 1
                if i + 6 < len(c):
                    fwd.append(c[i + 6] / c[i] - 1.0)           # 30 min después del cierre de la caída
        out.append({"symbol": sym, "days": round(days, 1), "sigma5_pct": sd * 100.0,
                    "drops_per_day": n_drops / days,
                    "rebound_30m_gross_pct": (sum(fwd) / len(fwd) * 100.0) if fwd else None,
                    "n_drops": n_drops})
    return out


def split_groups(profile: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    alts = [p for p in profile if p["symbol"] not in (BTC, ETH)]
    alts.sort(key=lambda p: -p["sigma5_pct"])
    k = max(3, len(alts) // 3)
    return {"parecidas_a_PYR": [p["symbol"] for p in alts[:k]],
            "tranquilas": [p["symbol"] for p in alts[-k:]],
            "todas": [p["symbol"] for p in alts]}


# ------------------------------------------------------------------ prueba
def entry_variants() -> Dict[str, ReplayConfig]:
    return {"1min": VARIANTS["B_marcelo"], "5min": VARIANTS["D_marcelo_5m"]}


def exit_variants_for(entry: ReplayConfig) -> Dict[str, ReplayConfig]:
    """Salida actual (trailing) vs la que pidió Marcelo: mitad al +1% y el resto con trailing."""
    hold = 60 if entry.bar_min == 1 else 12
    trail_cfg = entry                                              # lo que ya se probó
    half_cfg = replace(entry, exit_mode="half_trail", tp_pct=0.01, tp_fraction=0.5, trail_pct=0.005,
                       init_stop_pct=0.01, max_hold_min=hold)
    return {"trailing_actual": trail_cfg, "mitad_1pct_y_trailing": half_cfg}


def evaluate(panel, groups: Dict[str, List[str]], baseline_runs: int = 100) -> List[Dict[str, Any]]:
    span_days = data_coverage(panel)["usable_minutes"] / 1440.0
    rows: List[Dict[str, Any]] = []
    zc: Dict[Tuple, List[float]] = {}
    panels: Dict[int, Any] = {}
    sigs: Dict[int, List[float]] = {}
    for ename, ecfg in entry_variants().items():
        for xname, xcfg in exit_variants_for(ecfg).items():
            if xcfg.bar_min not in panels:
                panels[xcfg.bar_min] = resample_panel(panel, xcfg.bar_min)
                sigs[xcfg.bar_min] = btc_move_sigmas(panels[xcfg.bar_min].bars[BTC].c, xcfg)
            pn, sg = panels[xcfg.bar_min], sigs[xcfg.bar_min]
            for cname, (fee, slip) in COST_SCENARIOS.items():
                cfg = replace(xcfg, fee_bps=fee, slip_bps=slip)
                for gname, syms in groups.items():
                    alts = [s for s in syms if s in pn.bars]
                    if not alts:
                        continue
                    trades = _run_cfg(pn, cfg, alts, zc, sg)
                    sm = summarize(trades, span_days)
                    row = {"grupo": gname, "n_criptos": len(alts), "entrada": ename, "salida": xname,
                           "costos": cname, "n_trades": sm.get("n_trades", 0),
                           "por_dia": sm.get("trades_per_day", 0.0), "aciertos": sm.get("win_rate"),
                           "neto_medio_pct": sm.get("mean_net_pct"), "bruto_medio_pct": sm.get("mean_gross_pct"),
                           "suma_neta_pct": sm.get("sum_net_pct"), "profit_factor": sm.get("profit_factor"),
                           "t_stat": sm.get("naive_t_stat")}
                    # contra el azar solo con costo bajo/real/sin costos para los grupos principales (carga acotada)
                    if sm.get("n_trades", 0) >= 30 and gname != "todas":
                        bl = random_baseline(pn, cfg, alts, sm["n_trades"], sm.get("mean_net_pct"),
                                             runs=baseline_runs, btc_sig=sg)
                        row["vs_azar"] = bl.get("verdict")
                        row["azar_mediana_pct"] = bl.get("random_median_net_pct")
                    rows.append(row)
    return rows


def run_pyr_analysis(hist_root: Path, base_symbols: Sequence[str], train_days: float = 90.0,
                     test_days: float = 60.0, on_status=None) -> Dict[str, Any]:
    say = on_status or (lambda m: None)
    rng = historical_range(hist_root)
    if rng is None:
        raise FileNotFoundError("No hay historial de Binance descargado.")
    end_ns = rng[1]
    test_start = end_ns - int(test_days * 86400 * 1e9)
    train_start = max(rng[0], test_start - int(train_days * 86400 * 1e9))
    symbols = analysis_symbols(base_symbols)
    say("Perfilando las criptos en el tramo de entrenamiento...")
    prof = profile_symbols(hist_root, symbols, train_start, test_start - 1)
    groups = split_groups(prof)
    say(f"Leyendo el tramo de prueba ({test_days:g} días, {len(prof)} criptos con datos)...")
    panel = load_panel_historical(hist_root, [BTC, ETH] + groups["todas"], start_ns=test_start, end_ns=end_ns)
    say("Probando la estrategia (salidas × costos × grupos) y comparando con el azar...")
    rows = evaluate(panel, groups)
    return {"train_days": (test_start - train_start) / 86400e9, "test_days": test_days,
            "profile": sorted(prof, key=lambda p: -p["sigma5_pct"]), "groups": groups, "rows": rows,
            "missing_candidates": [s for s in PYR_CANDIDATES if s not in {p["symbol"] for p in prof}],
            "caveat": ("Los grupos se eligen con el tramo de entrenamiento y la estrategia se mide solo en el tramo "
                       "posterior. Se comparan varias combinaciones sobre los mismos datos: tomar el mejor resultado "
                       "como real sería engañarse.")}
