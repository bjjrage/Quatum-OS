"""Paper trading del FLUJO COMPRADOR V1 (la única estrategia que pasó las pruebas).

Regla (idéntica a la del backtest):
  * Universo: las ~65 cripto de futuros USD-M del laboratorio.
  * Señal: promedio de los últimos 14 días COMPLETOS de (compra agresiva / volumen) de cada cripto.
  * Cartera: comprar el 20% con señal más alta y vender en corto el 20% más baja, pesos iguales,
    exposición total = capital x apalancamiento (por defecto 1x: 50% comprado / 50% vendido).
  * Rebalanceo cada 7 días (el primero al arrancar), a los ~5 min de cerrar la vela diaria (00:05 UTC).
  * Costos: comisión 0,04% + deslizamiento 0,02% por cada dólar movido. Funding real cobrado/pagado.

Además, cada 5 minutos guarda una foto del libro de órdenes (cuánto hay para comprar/vender cerca del precio) y del
interés abierto de las 65 cripto, para probar en un mes si ese dato mejora la estrategia.

El estado se guarda en data/paper/flujo_v1/state.json: un reinicio NO pierde posiciones.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.common.logger import setup_logger

logger = setup_logger("flujo_paper")

FAPI = "https://fapi.binance.com"
ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "data" / "paper" / "flujo_v1"
FEE, SLIP = 0.0004, 0.0002
LOOKBACK_DAYS, FRAC, REB_DAYS = 14, 0.2, 7


# --------------------------------------------------------------------------- señal (funciones puras)
def taker_score(klines_1d: Sequence[Sequence[Any]], now_ms: int, L: int = LOOKBACK_DAYS) -> Optional[float]:
    """klines diarias de Binance: [open_time, o, h, l, c, volume, close_time, quote, trades, taker_buy_base, ...].
    Solo días COMPLETOS (close_time < ahora). Promedio de taker_buy/volume de los últimos L días."""
    done = [k for k in klines_1d if int(k[6]) < now_ms]
    ratios = []
    for k in done[-L:]:
        vol, tb = float(k[5]), float(k[9])
        if vol > 0:
            ratios.append(tb / vol)
    if len(ratios) < int(L * 0.8):
        return None
    return sum(ratios) / len(ratios)


def target_weights(scores: Dict[str, float], frac: float = FRAC) -> Dict[str, float]:
    sc = sorted((v, s) for s, v in scores.items() if v is not None and v == v)
    if len(sc) < 10:
        return {}
    k = max(1, int(len(sc) * frac))
    longs, shorts = [s for _, s in sc[-k:]], [s for _, s in sc[:k]]
    w = {s: 0.5 / k for s in longs}
    for s in shorts:
        w[s] = -0.5 / k
    return w


def book_metrics(depth: Dict[str, Any]) -> Dict[str, float]:
    """Foto del libro: USD para comprar/vender dentro de 0,5% y 1% del precio medio, desequilibrio y spread."""
    bids = [(float(p), float(q)) for p, q in depth.get("bids", [])]
    asks = [(float(p), float(q)) for p, q in depth.get("asks", [])]
    if not bids or not asks:
        return {}
    mid = 0.5 * (bids[0][0] + asks[0][0])
    out = {"mid": mid, "spread_bps": (asks[0][0] - bids[0][0]) / mid * 1e4}
    for pct, tag in ((0.005, "05"), (0.01, "1")):
        b = sum(p * q for p, q in bids if p >= mid * (1 - pct))
        a = sum(p * q for p, q in asks if p <= mid * (1 + pct))
        out[f"bid_usd_{tag}"], out[f"ask_usd_{tag}"] = b, a
        out[f"imbalance_{tag}"] = (b - a) / (b + a) if (b + a) > 0 else 0.0
    return out


# --------------------------------------------------------------------------- libro contable
class PaperBook:
    def __init__(self, state_dir: Path = STATE_DIR, capital: float = 10_000.0, leverage: float = 1.0):
        self.dir = Path(state_dir)
        self.path = self.dir / "state.json"
        self.s: Dict[str, Any] = {"capital_inicial": capital, "cash": capital, "apalancamiento": leverage,
                                  "posiciones": {}, "ultimo_rebalanceo_ms": 0, "rebalanceos": [],
                                  "funding_pagado": 0.0, "costos_pagados": 0.0, "equity_diaria": [],
                                  "funding_visto": {}, "creado": datetime.now(timezone.utc).isoformat()}
        if self.path.exists():
            try:
                state = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(state, dict):
                    raise ValueError("state.json must contain a JSON object")
                self.s.update(state)
            except (OSError, UnicodeError, ValueError) as exc:
                logger.error("state.json ilegible: NO se sobrescribe; revisar a mano.")
                raise UnreadableStateError(type(exc).__name__) from exc

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.s, indent=1), encoding="utf-8")
        tmp.replace(self.path)

    def equity(self, prices: Dict[str, float]) -> float:
        """Cash + valor de mercado de las posiciones (las cortas restan)."""
        return self.s["cash"] + sum(q * prices.get(sym, 0.0) for sym, q in self.s["posiciones"].items())

    def rebalance(self, weights: Dict[str, float], prices: Dict[str, float], now_ms: int,
                  fee: float = FEE, slip: float = SLIP, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        eq = self.equity(prices)
        gross = eq * float(self.s["apalancamiento"])
        pos = self.s["posiciones"]
        targets = {s: w * gross / prices[s] for s, w in weights.items() if prices.get(s)}
        moved = 0.0
        trades = []
        for sym in set(pos) | set(targets):
            px = prices.get(sym)
            if not px:
                continue
            dq = targets.get(sym, 0.0) - pos.get(sym, 0.0)
            if abs(dq) * px < 1e-6:
                continue
            fill = px * (1 + slip) if dq > 0 else px * (1 - slip)
            self.s["cash"] -= dq * fill
            cost = abs(dq) * px * fee
            self.s["cash"] -= cost
            self.s["costos_pagados"] += cost + abs(dq) * px * slip
            moved += abs(dq) * px
            trades.append({"symbol": sym, "cantidad": dq, "precio": fill})
            old_q = pos.get(sym, 0.0)
            new_q = old_q + dq
            ent = self.s.setdefault("entradas", {})
            if abs(new_q) * px < 1e-6:
                pos.pop(sym, None)
                ent.pop(sym, None)
            else:
                if old_q == 0 or (old_q > 0) != (new_q > 0):          # posición nueva o dada vuelta
                    ent[sym] = fill
                elif abs(new_q) > abs(old_q):                          # se agranda: promedio ponderado
                    ent[sym] = (ent.get(sym, fill) * abs(old_q) + fill * abs(dq)) / abs(new_q)
                pos[sym] = new_q
        rec = {"ts": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).isoformat(), "equity_antes": eq,
               "equity_despues": self.equity(prices), "movido_usd": moved, "n_largos": sum(1 for w in weights.values() if w > 0),
               "n_cortos": sum(1 for w in weights.values() if w < 0), "pesos": weights, **(extra or {})}
        self.s["rebalanceos"].append(rec)
        self.s["ultimo_rebalanceo_ms"] = now_ms
        self.save()
        return rec

    def entry_prices(self) -> Dict[str, float]:
        """Precio de entrada por posición. Si falta (posiciones de antes de este registro), se reconstruye exacto a
        partir del último rebalanceo: cantidad = peso x exposición / precio."""
        ent = dict(self.s.get("entradas") or {})
        last = self.s["rebalanceos"][-1] if self.s["rebalanceos"] else None
        if last:
            gross = float(last["equity_antes"]) * float(self.s["apalancamiento"])
            for sym, q in self.s["posiciones"].items():
                w = (last.get("pesos") or {}).get(sym)
                if sym not in ent and w and q:
                    px = w * gross / q
                    ent[sym] = px * (1 + SLIP) if q > 0 else px * (1 - SLIP)
        return ent

    def apply_funding(self, sym: str, rate: float, price: float) -> float:
        """Funding: un largo paga si la tasa es positiva, un corto cobra."""
        q = self.s["posiciones"].get(sym, 0.0)
        pay = q * price * rate
        self.s["cash"] -= pay
        self.s["funding_pagado"] += pay
        return pay

    def record_day(self, prices: Dict[str, float], day: str) -> None:
        hist = self.s["equity_diaria"]
        if hist and hist[-1]["dia"] == day:
            hist[-1]["equity"] = self.equity(prices)
        else:
            hist.append({"dia": day, "equity": self.equity(prices)})
        self.save()

    def summary(self, prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        eq = self.equity(prices) if prices else (self.s["equity_diaria"][-1]["equity"] if self.s["equity_diaria"] else self.s["cash"])
        c0 = self.s["capital_inicial"]
        hist = [h["equity"] for h in self.s["equity_diaria"]]
        peak, dd = c0, 0.0
        for e in hist:
            peak = max(peak, e)
            dd = max(dd, 1 - e / peak)
        return {"capital_inicial": c0, "equity": eq, "ganancia_pct": (eq / c0 - 1) * 100,
                "caida_maxima_pct": dd * 100, "rebalanceos": len(self.s["rebalanceos"]),
                "posiciones": len(self.s["posiciones"]), "funding_pagado": self.s["funding_pagado"],
                "costos_pagados": self.s["costos_pagados"], "apalancamiento": self.s["apalancamiento"],
                "desde": self.s["creado"]}


# --------------------------------------------------------------------------- otras estrategias en observación
PAPER_ROOT = ROOT / "data" / "paper"


def daily_returns(klines_1d: Sequence[Sequence[Any]], now_ms: int) -> List[float]:
    closes = [float(k[4]) for k in klines_1d if int(k[6]) < now_ms]
    return [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1] > 0]


def vol_score(klines_1d, now_ms: int, L: int = 28) -> Optional[float]:
    r = daily_returns(klines_1d, now_ms)[-L:]
    if len(r) < int(L * 0.8):
        return None
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1))


def funding_score(funding_rows: Sequence[Dict[str, Any]], now_ms: int, days: int = 7) -> Optional[float]:
    xs = [float(f["fundingRate"]) for f in funding_rows
          if now_ms - days * 86400_000 <= int(f["fundingTime"]) < now_ms]
    return sum(xs) / len(xs) if xs else None


def rank_weights(scores: Dict[str, float], long_high: bool, frac: float = FRAC) -> Dict[str, float]:
    w = target_weights(scores, frac)
    return w if long_high else {s: -v for s, v in w.items()}


def combine(*ws: Dict[str, float]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for w in ws:
        for s_, v in w.items():
            out[s_] = out.get(s_, 0.0) + v / len(ws)
    tot = sum(abs(v) for v in out.values())
    return {s_: v / tot for s_, v in out.items() if v} if tot else {}


def btc_trend_weight(btc_klines, now_ms: int, L: int = 50) -> Dict[str, float]:
    closes = [float(k[4]) for k in btc_klines if int(k[6]) < now_ms]
    if len(closes) < L:
        return {}
    return {"BTCUSDT": 1.0} if closes[-1] > sum(closes[-L:]) / L else {}


# nombre de cuenta -> (descripción, cada cuántos días rebalancea)
STRATEGIES: Dict[str, Tuple[str, int]] = {
    "flujo_v1": ("Flujo comprador 14 d (la que pasó las pruebas)", 7),
    "flujo_7d": ("Flujo comprador 7 d (versión rápida)", 7),
    "carry_funding": ("Carry de funding: vende funding alto, compra funding bajo", 7),
    "baja_vol": ("Baja volatilidad: compra las tranquilas, vende las locas", 7),
    "combinada": ("Combinación: flujo 14 d + carry + baja volatilidad", 7),
    "btc_tendencia": ("BTC solo cuando está sobre su promedio de 50 días", 1),
    "examen_2x": ("Ensayo paper interno: proxy legacy HyroTrader de 1 fase (no es la Challenge 2 fases)", 7),
}

# ---------------------------------------------------------------------------- examen de prop firm en paper
# Legacy paper-only proxy thresholds; not current two-phase HyroTrader rules or an official pass result.
# perder 6% del capital inicial = quema; mínimo 5 días operados; ningún día puede ser >= 40% de la ganancia.
# Se controla cada minuto con precios reales (más exigente que la simulación, que miraba solo el cierre).
# Al pasar o quemar: cierra todo, guarda el intento y arranca uno nuevo el día siguiente a las 00:05 UTC.
EXAMS: Dict[str, Dict[str, Any]] = {
    "examen_2x": {"base": "flujo_v1", "lev": 2.0, "target": 0.10, "daily": 0.04, "max": 0.06,
                  "min_days": 5, "best_day": 0.40},
}
LEVERAGE = {name: cfg["lev"] for name, cfg in EXAMS.items()}


def _new_exam(day: str, eq: float, intento: int, historial: list) -> Dict[str, Any]:
    return {"intento": intento, "estado": "EN_CURSO", "inicio": datetime.now(timezone.utc).isoformat(),
            "dia": day, "equity_inicio_dia": eq, "pnl_por_dia": {}, "dias_operados": [],
            "peor_momento_dia_usd": 0.0, "fin": None, "motivo": None, "historial": historial}


def exam_step(b: "PaperBook", rules: Dict[str, Any], prices: Dict[str, float], now_ms: int) -> Optional[str]:
    """Aplica las reglas del examen a la cuenta. Devuelve un evento ('PASO', 'QUEMO', 'REINICIO') o None."""
    t = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc)
    day = t.strftime("%Y-%m-%d")
    c0 = float(b.s["capital_inicial"])
    if any(s not in prices for s in b.s["posiciones"]):
        return None                                           # sin precio de alguna: no decidir a ciegas
    eq = b.equity(prices)
    ex = b.s.get("examen")
    if ex is None:
        ex = b.s["examen"] = _new_exam(day, eq, 1, [])
    if ex["estado"] != "EN_CURSO":                            # terminado: esperar al día siguiente 00:05 UTC
        if day > ex["fin"][:10] and t.hour == 0 and t.minute >= 5:
            hist = ex["historial"] + [{k: ex[k] for k in ("intento", "estado", "inicio", "fin", "motivo")}
                                      | {"equity_final": ex.get("equity_final"),
                                         "dias": len(ex["dias_operados"])}]
            b.s.update({"cash": c0, "posiciones": {}, "entradas": {}, "ultimo_rebalanceo_ms": 0,
                        "equity_diaria": [], "funding_visto": {}})
            b.s["examen"] = _new_exam(day, c0, ex["intento"] + 1, hist)
            b.save()
            return "REINICIO"
        return None
    if day != ex["dia"]:                                      # cambio de día: arranca la cuenta del día nuevo
        ex["dia"], ex["equity_inicio_dia"], ex["peor_momento_dia_usd"] = day, eq, 0.0
    day_pnl = eq - ex["equity_inicio_dia"]
    ex["pnl_por_dia"][day] = day_pnl
    ex["peor_momento_dia_usd"] = min(ex["peor_momento_dia_usd"], day_pnl)
    if b.s["posiciones"] and day not in ex["dias_operados"]:
        ex["dias_operados"].append(day)
    gain = eq - c0
    best = max(ex["pnl_por_dia"].values())
    motivo = None
    if day_pnl <= -rules["daily"] * min(ex["equity_inicio_dia"], c0):
        estado, motivo = "QUEMO", f"perdió {rules['daily']:.0%} en un día"
    elif eq <= c0 * (1 - rules["max"]):
        estado, motivo = "QUEMO", f"perdió {rules['max']:.0%} del capital inicial"
    elif gain >= rules["target"] * c0 and len(ex["dias_operados"]) >= rules["min_days"] \
            and best < rules["best_day"] * gain:
        estado, motivo = "PASO", f"llegó a +{rules['target']:.0%}"
    if motivo is None:
        return None
    b.rebalance({}, prices, now_ms, extra={"motivo": f"examen {estado}: {motivo}"})   # cierra todo
    ex.update({"estado": estado, "motivo": motivo, "fin": t.isoformat(), "equity_final": b.equity(prices)})
    b.save()
    return estado


def exam_view(b: "PaperBook", eq: Optional[float]) -> Optional[Dict[str, Any]]:
    """Resumen para la pantalla: cuánto falta para pasar y cuánto margen queda antes de quemar."""
    ex = b.s.get("examen")
    name = b.dir.name
    if ex is None or name not in EXAMS:
        return None
    r, c0 = EXAMS[name], float(b.s["capital_inicial"])
    out = {k: ex[k] for k in ("intento", "estado", "inicio", "fin", "motivo")}
    from src.research.hyro_rules import RULES_STATUS, RULE_VERSION
    out.update({"rules_status": RULES_STATUS, "rules_version": RULE_VERSION,
                "objetivo_usd": c0 * (1 + r["target"]), "piso_total_usd": c0 * (1 - r["max"]),
                "limite_diario_usd": r["daily"] * min(ex["equity_inicio_dia"], c0),
                "dias_operados": len(ex["dias_operados"]), "dias_minimos": r["min_days"],
                "mejor_dia_usd": max(ex["pnl_por_dia"].values()) if ex["pnl_por_dia"] else 0.0,
                "historial": ex["historial"], "reglas": r})
    if eq is not None and ex["estado"] == "EN_CURSO":
        day_pnl = eq - ex["equity_inicio_dia"]
        out.update({"falta_para_pasar_usd": max(0.0, out["objetivo_usd"] - eq),
                    "margen_total_usd": eq - out["piso_total_usd"],
                    "pnl_hoy_usd": day_pnl, "margen_hoy_usd": out["limite_diario_usd"] + day_pnl})
    return out


def compute_all_weights(kl: Dict[str, list], fund: Dict[str, list], now_ms: int) -> Dict[str, Dict[str, float]]:
    """Pesos objetivo de cada estrategia con los datos de hoy (solo días completos)."""
    t14 = {s_: v for s_ in kl for v in [taker_score(kl[s_], now_ms, 14)] if v is not None}
    t7 = {s_: v for s_ in kl for v in [taker_score(kl[s_], now_ms, 7)] if v is not None}
    vo = {s_: v for s_ in kl for v in [vol_score(kl[s_], now_ms, 28)] if v is not None}
    fu = {s_: v for s_ in fund for v in [funding_score(fund[s_], now_ms)] if v is not None}
    w_flujo, w_carry, w_vol = rank_weights(t14, True), rank_weights(fu, False), rank_weights(vo, False)
    return {"flujo_v1": w_flujo, "flujo_7d": rank_weights(t7, True), "carry_funding": w_carry,
            "baja_vol": w_vol, "combinada": combine(w_flujo, w_carry, w_vol) if (w_flujo and w_carry and w_vol) else {},
            "btc_tendencia": btc_trend_weight(kl.get("BTCUSDT", []), now_ms), "examen_2x": w_flujo}


def is_due(last_ms: int, now_ms: int, every_days: int) -> bool:
    """Primer rebalanceo al arrancar; después cada N días, entre 00:05 y 00:59 UTC."""
    if last_ms == 0:
        return True
    t = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc)
    return now_ms - last_ms >= every_days * 86400_000 - 3600_000 and t.hour == 0 and t.minute >= 5


class UnreadableStateError(ValueError):
    """A persisted paper ledger exists but cannot be loaded without risking data loss."""

    def __init__(self, error_type: str):
        self.error_type = error_type
        super().__init__(f"Paper state is unreadable ({error_type}); the file was left untouched.")


def load_books(root: Path = PAPER_ROOT, *, errors: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, "PaperBook"]:
    """Load available ledgers and isolate unreadable accounts without replacing their state files."""
    books: Dict[str, PaperBook] = {}
    for name in STRATEGIES:
        try:
            books[name] = PaperBook(root / name, leverage=LEVERAGE.get(name, 1.0))
        except UnreadableStateError as exc:
            if errors is not None:
                errors[name] = {"estado": "STATE_UNREADABLE", "error_type": exc.error_type}
            logger.error("Paper account %s unavailable: state is unreadable; it will not be written.", name)
    return books


# --------------------------------------------------------------------------- bucle en vivo (proceso aparte)
async def run_paper(symbols: Sequence[str], sink=None, state_dir: Path = STATE_DIR, stop_file: Optional[Path] = None,
                    snapshot_every_s: int = 300) -> None:
    import asyncio
    import aiohttp
    from src.common.runtime_health import RuntimeHealth
    paper_health = RuntimeHealth("paper_runtime")
    leader_health = RuntimeHealth("leader_paper")
    paper_health.update("STARTING", started=True)
    unavailable_accounts: Dict[str, Dict[str, str]] = {}
    books = load_books(Path(state_dir).parent, errors=unavailable_accounts)
    paper_status = "DEGRADED" if unavailable_accounts else "RUNNING"
    if unavailable_accounts:
        paper_health.update("DEGRADED", started=True,
                            error=RuntimeError("Unreadable paper state: " + ", ".join(unavailable_accounts)),
                            unavailable_accounts=unavailable_accounts)
    lider = None
    try:                                  # "líder explotó -> rezagadas + X" (src/paper/lider_paper.py)
        from src.common.secret_loader import get_secret
        from src.paper import lider_paper as lp
        cfg = lp.load_config()
        api_key = None if os.environ.get("QUANT_OS_NO_PAID_X") == "1" else get_secret("XAI_API_KEY")
        lider = lp.LiderPaper(Path(state_dir).parent, api_key=api_key,
                              daily_x_usd=float(cfg.get("lider_x_daily_usd", 1.0)))
        leader_health.update("RUNNING", started=True, success=True)
    except Exception as e:
        leader_health.update("ERROR", started=True, error=e)
        logger.warning(f"Líder paper apagado: {type(e).__name__}: {str(e)[:120]}")
    last_snap = 0.0
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as http:

        async def get(path, **params):
            async with http.get(FAPI + path, params=params or None) as r:
                if r.status != 200:
                    raise RuntimeError(f"{path} -> {r.status}")
                return await r.json()

        logger.info(f"Paper corriendo con {len(books)} cuentas: " + ", ".join(books))
        paper_health.update(paper_status, success=True, unavailable_accounts=unavailable_accounts)
        while not (stop_file and stop_file.exists()):
            try:
                now = time.time()
                now_ms = int(now * 1000)
                prices = {d["symbol"]: float(d["price"]) for d in await get("/fapi/v1/ticker/price")
                          if d.get("symbol") in symbols}
                paper_health.update(paper_status, success=True, unavailable_accounts=unavailable_accounts)
                # funding: cuando avanza nextFundingTime, se liquida la tasa vista justo antes (en cada cuenta)
                for d in await get("/fapi/v1/premiumIndex"):
                    sym = d.get("symbol")
                    if sym not in symbols:
                        continue
                    nxt, rate = int(d.get("nextFundingTime") or 0), float(d.get("lastFundingRate") or 0.0)
                    for b in list(books.values()) + (list(lider.books.values()) if lider else []):
                        seen = b.s.setdefault("funding_visto", {})
                        prev = seen.get(sym)
                        if prev and nxt > prev["next"] and sym in b.s["posiciones"] and prices.get(sym):
                            b.apply_funding(sym, prev["rate"], prices[sym])
                        seen[sym] = {"next": nxt, "rate": rate}
                # exámenes: control de reglas cada minuto (antes de rebalancear)
                for name, rules in EXAMS.items():
                    if name not in books:
                        continue
                    b = books[name]
                    syms_needed = set(b.s["posiciones"]) - set(prices)
                    if syms_needed:                               # alguna fuera del universo: pedir su precio
                        for d in await get("/fapi/v1/ticker/price"):
                            if d.get("symbol") in syms_needed:
                                prices[d["symbol"]] = float(d["price"])
                    ev = exam_step(b, rules, prices, now_ms)
                    if ev:
                        ex = b.s["examen"]
                        logger.info(f"EXAMEN [{name}] intento {ex['intento']}: {ev} "
                                    f"({ex.get('motivo') or 'nuevo intento'})")
                due = [n for n, b in books.items() if is_due(b.s["ultimo_rebalanceo_ms"], now_ms, STRATEGIES[n][1])
                       and (n not in EXAMS or (b.s.get("examen") or {}).get("estado", "EN_CURSO") == "EN_CURSO")]
                if due:
                    kl: Dict[str, list] = {}
                    fund: Dict[str, list] = {}
                    for sym in symbols:
                        try:
                            kl[sym] = await get("/fapi/v1/klines", symbol=sym, interval="1d", limit=60)
                            fund[sym] = await get("/fapi/v1/fundingRate", symbol=sym, limit=60)
                        except Exception:
                            continue
                        await asyncio.sleep(0.05)
                    allw = compute_all_weights(kl, fund, now_ms)
                    for name in due:
                        w = allw.get(name) or {}
                        b = books[name]
                        if not w and name != "btc_tendencia":
                            continue
                        if name == "btc_tendencia" and b.s["ultimo_rebalanceo_ms"] and \
                                (set(w) == set(b.s["posiciones"])):
                            b.s["ultimo_rebalanceo_ms"] = now_ms        # sin cambios: no operar, solo registrar
                            b.save()
                            continue
                        books_info = {}
                        if name == "flujo_v1":
                            for sym in w:
                                try:
                                    books_info[sym] = book_metrics(await get("/fapi/v1/depth", symbol=sym, limit=100))
                                except Exception:
                                    pass
                        rec = b.rebalance(w, prices, now_ms, extra={"libro_al_entrar": books_info} if books_info else None)
                        logger.info(f"Rebalanceo paper [{name}]: equity {rec['equity_despues']:.2f} USD, "
                                    f"{rec['n_largos']} largos / {rec['n_cortos']} cortos")
                if lider:
                    try:
                        lider.exits(prices, now_ms)
                        if lider.check_due(now_ms):
                            await lider.process(http, get, symbols, now_ms)
                    except Exception as e:
                        logger.warning(f"Líder paper: {type(e).__name__}: {str(e)[:150]}")
                day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                for b in list(books.values()) + (list(lider.books.values()) if lider else []):
                    b.record_day(prices, day)
                # foto del libro + interés abierto de todas (para el estudio de dentro de un mes)
                if sink is not None and now - last_snap >= snapshot_every_s:
                    last_snap = now
                    for sym in symbols:
                        if stop_file and stop_file.exists():
                            break
                        try:
                            bm = book_metrics(await get("/fapi/v1/depth", symbol=sym, limit=100))
                            oi = await get("/fapi/v1/openInterest", symbol=sym)
                            if bm:
                                await sink.append("binance_perp", "depth_snapshots", {
                                    "ts_utc_ns": time.time_ns(), "symbol": sym, **bm,
                                    "open_interest": float(oi.get("openInterest") or 0.0)})
                        except Exception:
                            pass
                        await asyncio.sleep(0.1)
            except Exception as e:
                paper_health.update("DEGRADED", error=e, unavailable_accounts=unavailable_accounts)
                logger.warning(f"Paper: {type(e).__name__}: {str(e)[:150]}")
            else:
                paper_health.update(paper_status, unavailable_accounts=unavailable_accounts)
                if lider:
                    leader_health.update("RUNNING")
            for _ in range(60):                       # esperar 1 min, pero atento al pedido de apagado
                if stop_file and stop_file.exists():
                    break
                await asyncio.sleep(1)
        for b in list(books.values()) + (list(lider.books.values()) if lider else []):
            b.save()
        paper_health.update("STOPPED")
        if lider:
            leader_health.update("STOPPED")
        logger.info("Paper detenido.")
