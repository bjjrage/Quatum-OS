"""Daily-return resampling for exploratory, model-only prop-firm projections.

These projections are not an authoritative HyroTrader pass/fail result. The
account's drawdown mode, intraday equity, trade-level qualifying days, fees,
and manually reviewed position-loss rule are not available to this simulator.
See :mod:`src.research.hyro_rules` for versioned rule facts and limitations.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Sequence

from src.research.hyro_rules import RULES_STATUS, TWO_STEP_RULES, daily_floor, max_loss_breached

RULES = {
    "HyroTrader_1F": [{"target": 0.10, "daily": 0.04, "max": 0.06, "min_days": 5}],
    "HyroTrader_2F": [{"target": 0.10, "daily": 0.05, "max": 0.10, "min_days": 5,
                       "profit_distribution_cap": 0.40},
                      {"target": 0.05, "daily": 0.05, "max": 0.10, "min_days": 5,
                       "profit_distribution_cap": 0.40}],
}


def run_phase(path_iter, phase: Dict[str, float], lev: float, max_days: int, daily_buffer: float = 0.0):
    """Daily-return projection only; output is model-only, not an authoritative challenge result."""
    eq, days, counted = 1.0, 0, 0.0
    initial = 1.0
    while days < max_days:
        r = next(path_iter) * lev
        days += 1
        day_start = eq
        day_pnl = r * eq
        eq *= 1.0 + r
        daily_pct = max(0.0, float(phase["daily"]) - float(daily_buffer))
        if eq < daily_floor(initial, day_start, daily_pct):
            return "RISK_LIMIT_REACHED_MODEL_ONLY", days
        if max_loss_breached(eq, initial, float(phase["max"])):
            return "RISK_LIMIT_REACHED_MODEL_ONLY", days
        cap = phase["target"] * float(phase.get("profit_distribution_cap", 0.40))
        counted += min(day_pnl, cap) if day_pnl > 0 else day_pnl
        if counted >= phase["target"] and days >= phase["min_days"]:
            return "TARGET_REACHED_MODEL_ONLY", days
    return "HORIZON_END_MODEL_ONLY", days


def simulate(daily: Sequence[float], rules: List[Dict[str, float]], lev: float, n: int = 3000,
             max_days: int = 365, block: int = 10, seed: int = 1) -> Dict[str, Any]:
    rnd = random.Random(seed)
    N = len(daily)

    def path():
        while True:
            i = rnd.randrange(0, max(1, N - block))
            for k in range(block):
                yield daily[i + k]

    target_hits, risk_hits, horizon_ends, days_to_target = 0, 0, 0, []
    for _ in range(n):
        it = path()
        total, reached_all = 0, True
        for phase in rules:
            result, days = run_phase(it, phase, lev, max_days - total)
            total += days
            if result != "TARGET_REACHED_MODEL_ONLY":
                reached_all = False
                if result == "RISK_LIMIT_REACHED_MODEL_ONLY":
                    risk_hits += 1
                else:
                    horizon_ends += 1
                break
        if reached_all:
            target_hits += 1
            days_to_target.append(total)
    days_to_target.sort()
    q = lambda f: days_to_target[int(f * (len(days_to_target) - 1))] if days_to_target else None
    return {"apalancamiento": lev, "rules_status": RULES_STATUS,
            "target_hit_pct_model_only": target_hits / n * 100,
            "risk_limit_hit_pct_model_only": risk_hits / n * 100,
            "horizon_end_pct_model_only": horizon_ends / n * 100,
            "simulation_horizon_days": max_days,
            "days_to_target_median_model_only": q(0.5),
            "days_to_target_p25_model_only": q(0.25),
            "days_to_target_p75_model_only": q(0.75),
            "limitations": ["No trade-level evidence for 5 valid days per phase.",
                            "No intraday equity path or selected fixed/trailing drawdown mode.",
                            "Manual max-loss-per-position check cannot be evaluated from daily returns."]}


def attempts_needed(p_pass: float) -> Optional[float]:
    """Intentos esperados hasta pasar (cada fallo = pagar el examen de nuevo)."""
    return 1.0 / p_pass if p_pass > 0 else None


def exam_table(daily: Sequence[float], levs: Sequence[float] = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0), n: int = 3000) -> Dict[str, Any]:
    out = {}
    for name, rules in RULES.items():
        rows = []
        for lev in levs:
            r = simulate(daily, rules, lev, n=n)
            r["expected_runs_to_target_model_only"] = attempts_needed(r["target_hit_pct_model_only"] / 100)
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
    out: Dict[str, Any] = {"nota": __doc__.split("Reglas")[0].strip(), "rules_status": RULES_STATUS, "hyro_rules": TWO_STEP_RULES}
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
