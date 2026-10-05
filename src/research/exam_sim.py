"""Simulador del examen de prop firm con los resultados DIARIOS reales (historia) de nuestras estrategias.

Se arman miles de caminos posibles remuestreando bloques de días seguidos de la historia (mantiene rachas buenas y
malas) y se aplican las reglas del examen a distintos apalancamientos. Resultado: probabilidad de pasar, de quemar
la cuenta, y cuántos días tarda.

Reglas (HyroTrader, verificar antes de pagar):
  1 fase:  objetivo 10%; pérdida diaria 4%; pérdida máxima 6% (desde el capital inicial); mínimo 5 días.
  2 fases: fase 1 10% y fase 2 5%; pérdida diaria 5%; pérdida máxima 10%; mínimo 5 días por fase.
  Regla del 40%: ningún día puede aportar >= 40% de la ganancia total (si pasa, hay que seguir operando).
Simplificaciones: se mira el cierre diario (dentro del día puede ser peor: la pérdida diaria real es más exigente).
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence

RULES = {
    "HyroTrader_1F": [{"target": 0.10, "daily": 0.04, "max": 0.06, "min_days": 5}],
    "HyroTrader_2F": [{"target": 0.10, "daily": 0.05, "max": 0.10, "min_days": 5},
                      {"target": 0.05, "daily": 0.05, "max": 0.10, "min_days": 5}],
}


def run_phase(path_iter, phase: Dict[str, float], lev: float, max_days: int, daily_buffer: float = 0.0):
    """Devuelve ('PASA'|'QUEMA'|'TIEMPO', días). daily_buffer: margen extra que se deja contra el límite diario."""
    eq, best_day, days = 1.0, 0.0, 0
    while days < max_days:
        r = next(path_iter) * lev
        days += 1
        day_pnl = r * eq
        if r <= -(phase["daily"] - daily_buffer) or day_pnl <= -phase["daily"]:   # pérdida diaria sobre el saldo inicial del día
            return "QUEMA", days
        eq *= 1.0 + r
        if eq <= 1.0 - phase["max"]:
            return "QUEMA", days
        best_day = max(best_day, day_pnl)
        gain = eq - 1.0
        if gain >= phase["target"] and days >= phase["min_days"] and best_day < 0.40 * gain:
            return "PASA", days
    return "TIEMPO", days


def simulate(daily: Sequence[float], rules: List[Dict[str, float]], lev: float, n: int = 3000,
             max_days: int = 365, block: int = 10, seed: int = 1) -> Dict[str, Any]:
    rnd = random.Random(seed)
    N = len(daily)

    def path():
        while True:
            i = rnd.randrange(0, max(1, N - block))
            for k in range(block):
                yield daily[i + k]

    passed, burned, timeout, days_pass = 0, 0, 0, []
    for _ in range(n):
        it = path()
        total, ok = 0, True
        for ph in rules:
            res, d = run_phase(it, ph, lev, max_days - total)
            total += d
            if res != "PASA":
                ok = False
                if res == "QUEMA":
                    burned += 1
                else:
                    timeout += 1
                break
        if ok:
            passed += 1
            days_pass.append(total)
    days_pass.sort()
    q = lambda f: days_pass[int(f * (len(days_pass) - 1))] if days_pass else None
    return {"apalancamiento": lev, "pasa_pct": passed / n * 100, "quema_pct": burned / n * 100,
            "no_llega_en_1_anio_pct": timeout / n * 100, "dias_mediana": q(0.5), "dias_p25": q(0.25), "dias_p75": q(0.75)}


def attempts_needed(p_pass: float) -> Optional[float]:
    """Intentos esperados hasta pasar (cada fallo = pagar el examen de nuevo)."""
    return 1.0 / p_pass if p_pass > 0 else None


def exam_table(daily: Sequence[float], levs: Sequence[float] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0), n: int = 3000) -> Dict[str, Any]:
    out = {}
    for name, rules in RULES.items():
        rows = []
        for lev in levs:
            r = simulate(daily, rules, lev, n=n)
            r["intentos_esperados"] = attempts_needed(r["pasa_pct"] / 100)
            rows.append(r)
        out[name] = rows
    return out


def run_exam_study(hist_root, say=lambda m: None, n: int = 3000) -> Dict[str, Any]:
    from src.research.portfolio_lab import (HOLDOUT_FRACTION, WARMUP_DAYS, backtest, load_daily, s_combo, s_xs,
                                            sc_funding, sc_taker, sc_vol)
    say("Leyendo historia diaria...")
    g = load_daily(hist_root)
    split = WARMUP_DAYS + int((g.n - 1 - WARMUP_DAYS) * (1.0 - HOLDOUT_FRACTION))
    strategies = {
        "flujo_14d": (s_xs(sc_taker(14), 15, True), 7),
        "flujo_7d": (s_xs(sc_taker(7), 8, True), 7),
        "combinada": (s_combo([s_xs(sc_taker(14), 15, True), s_xs(sc_funding(7), 9, False),
                               s_xs(sc_vol(28), 30, False)]), 7),
    }
    out: Dict[str, Any] = {"nota": __doc__.split("Reglas")[0].strip()}
    for name, (fn, reb) in strategies.items():
        say(f"Backtest {name}...")
        rows = backtest(g, fn, reb)
        full = [r for _, r, _ in rows]
        recent = [r for d, r, _ in rows if d >= split]
        say(f"Simulando exámenes con {name}...")
        out[name] = {"toda_la_historia": exam_table(full, n=n), "ultimo_anio_y_medio": exam_table(recent, n=n),
                     "dias": len(full)}
        if name == "flujo_14d":
            m = sum(full) / len(full)
            out["control_sin_ventaja"] = exam_table([r - m for r in full], n=n)   # misma volatilidad, ganancia media 0
    return out
