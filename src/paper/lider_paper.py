"""Paper trading de "el líder del segmento explotó -> rezagadas + X" (cripto de Binance que no son memes).

Idea de Marcelo: cuando el token líder de un segmento explota, las otras del mismo segmento que todavía no se movieron
y que tienen narrativa detrás y gente hablando en X, pueden ser las próximas.

Qué hace (una vez por día, entre 00:05 y 06:00 UTC, con las velas diarias completas; solo mira el pasado):
  1. Segmentos (src/research/niches.py) con >= 4 miembros con datos.
  2. LÍDER: subió >= +30% en 3 días Y su volumen de 3 días es >= 2 veces el promedio de los 30 días anteriores.
  3. REZAGADAS: del mismo segmento, retorno 3 d entre -10% y +5% (no se movieron), que no son líderes.
     Máximo 8 (las más líquidas). Máximo un evento por segmento cada 7 días.
  4. X (Grok, x_search, 1 búsqueda por rezagada): ¿hay conversación REAL sobre esta cripto en las últimas 48 h y la
     vincula con la misma narrativa que el líder? Regla fija: posts_found >= 5 Y narrative_link = verdadero.
     Tope de gasto en config/pumpfun.json -> "lider_x_daily_usd" (por defecto 1,0 USD por día; el gasto se guarda en disco).
  5. Se abren posiciones de 1.000 USD por evento y por cuenta (repartidas en partes iguales), se mantienen 7 días,
     sin stops, con comisión 0,04% + deslizamiento 0,02% por lado y funding real. Cuentas de 10.000 USD, sin apalancar:
       - lider_x:      compra las rezagadas que pasan el filtro de X.
       - lider_sin_x:  compra todas las rezagadas (sin filtro). Si lider_x le gana, X agrega algo.
       - lider_azar:   CONTROL: la misma cantidad de cripto al azar de OTROS segmentos.
       - lider_corto:  HIPÓTESIS NUEVA (salió de mirar los datos del estudio, todavía no probada): vender en corto al líder.
  6. Medida principal: retorno de cada posición menos el del mercado (promedio de las 65 cripto) en los mismos 7 días.
Estado: data/paper/lider_*/state.json y data/paper/lider_eventos.json (eventos, respuestas de X, gasto).
"""
from __future__ import annotations

import hashlib
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from src.common.logger import setup_logger
from src.paper.flujo_paper import FEE, SLIP, PaperBook

logger = setup_logger("lider_paper")

ROOT = Path(__file__).resolve().parents[2]
PAPER_ROOT = ROOT / "data" / "paper"
EVENTS_FILE = PAPER_ROOT / "lider_eventos.json"

LEADER = {"ret3": 0.30, "vol_mult": 2.0, "min_members": 4}
LAG = {"lo": -0.10, "hi": 0.05}
MAX_LAGGARDS = 8
COOLDOWN_DAYS = 7
HOLD_DAYS = 7
EVENT_USD = 1000.0
X_MIN_POSTS = 5
WINDOW = (5, 6 * 60)                     # minutos desde las 00:00 UTC en los que se puede procesar el día

LIDER_ACCOUNTS: Dict[str, str] = {
    "lider_x": "Líder explotó -> rezagadas CON X a favor (conversación + misma narrativa)",
    "lider_sin_x": "Líder explotó -> todas las rezagadas, sin filtro de X",
    "lider_azar": "CONTROL: cripto al azar de otros segmentos, mismo momento",
    "lider_corto": "HIPÓTESIS sin probar: vender en corto al líder que explotó",
}

SEGMENT_ES = {"ia": "IA", "memes": "memes", "l1": "capa 1", "l2": "capa 2", "defi": "DeFi", "gaming": "gaming",
              "infra": "infraestructura", "rwa": "activos reales"}

PROMPT = """Search X (Twitter) for posts from the last 48 hours about the crypto asset ${symbol} (Binance perpetual {symbol}USDT).
Context: it belongs to the crypto segment "{segment}". The leading coin of that segment, ${leader}, just rose {r3:.0%} in 3 days.
Question: is there real, specific conversation about ${symbol} itself, and do those posts tie ${symbol} to the same
narrative or theme as ${leader} ({segment})? Ignore generic price spam and unrelated meanings of the ticker.
Answer ONLY with a JSON object, no other text:
{{"posts_found": <int, posts clearly about this asset in the last 48h>,
  "narrative_link": <true if the posts connect it to the {segment} narrative or to {leader}>,
  "has_large_account": <true if any account with >= 50000 followers talks about it>,
  "summary": "<one short sentence>"}}"""


# --------------------------------------------------------------------------- detección (funciones puras)
def kline_stats(kl: List[List[Any]], now_ms: int) -> Optional[Dict[str, float]]:
    """De las velas diarias de Binance (solo días completos): retorno 3 d, salto de volumen y volumen medio de 30 d."""
    done = [k for k in kl if int(k[6]) < now_ms]
    if len(done) < 35:
        return None
    c = [float(k[4]) for k in done]
    qv = [float(k[7]) for k in done]
    base = qv[-33:-3]
    if c[-4] <= 0 or len(base) < 24:
        return None
    b = sum(base) / len(base)
    if b <= 0:
        return None
    return {"r3": c[-1] / c[-4] - 1.0, "vs": (sum(qv[-3:]) / 3.0) / b, "qv30": b, "close": c[-1]}


def find_events(stats: Dict[str, Dict[str, float]], seg_map: Dict[str, str]) -> List[Dict[str, Any]]:
    by: Dict[str, List[str]] = {}
    for s in stats:
        if seg_map.get(s):
            by.setdefault(seg_map[s], []).append(s)
    out = []
    for seg, mem in by.items():
        if len(mem) < LEADER["min_members"]:
            continue
        leaders = [s for s in mem if stats[s]["r3"] >= LEADER["ret3"] and stats[s]["vs"] >= LEADER["vol_mult"]]
        lag = [s for s in mem if s not in leaders and LAG["lo"] <= stats[s]["r3"] <= LAG["hi"]]
        if not leaders or not lag:
            continue
        lag.sort(key=lambda s: -stats[s]["qv30"])
        out.append({"segmento": seg,
                    "lideres": [{"symbol": s, "r3": stats[s]["r3"], "vs": stats[s]["vs"]} for s in
                                sorted(leaders, key=lambda s: -stats[s]["r3"])],
                    "rezagadas": [{"symbol": s, "r3": stats[s]["r3"], "vs": stats[s]["vs"]} for s in lag[:MAX_LAGGARDS]],
                    "miembros": len(mem)})
    return out


def x_ok(lag: Dict[str, Any]) -> bool:
    x = lag.get("x")
    return bool(x) and x.get("x_status") == "X_POSITIVE" and int(x.get("posts_found") or 0) >= X_MIN_POSTS and bool(x.get("narrative_link"))


def basket_return(entry: Dict[str, float], prices: Dict[str, float]) -> Optional[float]:
    rs = [prices[s] / p - 1.0 for s, p in entry.items() if p > 0 and prices.get(s)]
    return sum(rs) / len(rs) if rs else None


# --------------------------------------------------------------------------- libro con lotes
class LotBook(PaperBook):
    """Cuenta de paper con posiciones por lote (cada evento abre sus propios lotes, con su propia fecha de salida)."""

    def __init__(self, state_dir: Path, capital: float = 10_000.0):
        super().__init__(state_dir, capital=capital, leverage=1.0)
        self.s.setdefault("lotes", [])
        self.s.setdefault("cerrados", [])

    def _agg(self) -> None:
        agg: Dict[str, float] = {}
        for lot in self.s["lotes"]:
            agg[lot["symbol"]] = agg.get(lot["symbol"], 0.0) + lot["qty"]
        self.s["posiciones"] = {k: v for k, v in agg.items() if abs(v) > 1e-12}

    def open_lot(self, event_id: str, symbol: str, usd: float, side: int, price: float, now_ms: int,
                 hold_days: int = HOLD_DAYS) -> Dict[str, Any]:
        fill = price * (1 + SLIP) if side > 0 else price * (1 - SLIP)
        qty = side * usd / fill
        fee = abs(qty) * price * FEE
        self.s["cash"] -= qty * fill + fee
        self.s["costos_pagados"] += fee + abs(qty) * price * SLIP
        lot = {"evento": event_id, "symbol": symbol, "side": side, "qty": qty, "usd": usd, "entrada_px": price,
               "entrada_fill": fill, "entrada_fee": fee, "entrada_ms": now_ms,
               "salida_ms": now_ms + hold_days * 86400_000}
        self.s["lotes"].append(lot)
        self._agg()
        self.save()
        return lot

    def close_lot(self, lot: Dict[str, Any], price: float, now_ms: int, basket_ret: Optional[float]) -> Dict[str, Any]:
        dq = -lot["qty"]
        fill = price * (1 + SLIP) if dq > 0 else price * (1 - SLIP)
        fee = abs(dq) * price * FEE
        self.s["cash"] -= dq * fill + fee
        self.s["costos_pagados"] += fee + abs(dq) * price * SLIP
        pnl = lot["qty"] * (fill - lot["entrada_fill"]) - lot["entrada_fee"] - fee
        gross = price / lot["entrada_px"] - 1.0
        rec = {"evento": lot["evento"], "symbol": lot["symbol"], "side": lot["side"], "usd": lot["usd"],
               "ret_bruto": gross, "ret_neto": pnl / lot["usd"], "pnl_usd": pnl,
               "exceso_vs_mercado": (lot["side"] * (gross - basket_ret)) if basket_ret is not None else None,
               "entrada": datetime.fromtimestamp(lot["entrada_ms"] / 1000, tz=timezone.utc).isoformat(),
               "salida": datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).isoformat()}
        self.s["lotes"] = [x for x in self.s["lotes"] if x is not lot]
        self.s["cerrados"] = (self.s["cerrados"] + [rec])[-500:]
        self._agg()
        self.save()
        return rec


# --------------------------------------------------------------------------- controlador
class LiderPaper:
    def __init__(self, root: Path = PAPER_ROOT, api_key: Optional[str] = None, daily_x_usd: float = 1.0,
                 model: Optional[str] = None, events_file: Optional[Path] = None):
        from src.collectors.x_watcher import DEFAULT_MODEL
        self.root = Path(root)
        self.books = {n: LotBook(self.root / n) for n in LIDER_ACCOUNTS}
        self.key, self.daily_x_usd, self.model = api_key, daily_x_usd, model or DEFAULT_MODEL
        self.events_file = Path(events_file) if events_file else self.root / "lider_eventos.json"
        self.ev: Dict[str, Any] = {"ultimo_chequeo_dia": "", "checkpoints": {}, "eventos": [],
                                   "segmento_ultimo": {}, "gasto_x": {}, "descartados": []}
        from src.common.x_budget import XBudgetLedger
        self.x_ledger = XBudgetLedger(self.root)
        from src.common.runtime_health import RuntimeHealth
        self.health = RuntimeHealth("leader_paper", self.root)
        self.health.update("RUNNING", started=True, success=True)
        if self.events_file.exists():
            self.ev.update(json.loads(self.events_file.read_text(encoding="utf-8")))
        self.ev.setdefault("checkpoints", {})
        for day, amount in (self.ev.get("gasto_x") or {}).items():
            self.x_ledger.seed_legacy(day, "leader_paper_legacy", float(amount or 0.0))

    def _save_events(self) -> None:
        self.events_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.events_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.ev, indent=1), encoding="utf-8")
        tmp.replace(self.events_file)

    # ------------------------------------------------------------------ cuándo
    def check_due(self, now_ms: int) -> bool:
        t = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc)
        minute = t.hour * 60 + t.minute
        day = t.strftime("%Y-%m-%d")
        checkpoint = (self.ev.get("checkpoints") or {}).get(day, {})
        completed = checkpoint.get("status") == "COMPLETED" or day == self.ev.get("ultimo_chequeo_dia")
        return WINDOW[0] <= minute < WINDOW[1] and not completed

    # ------------------------------------------------------------------ X
    def _x_budget_ok(self, day: str) -> bool:
        return self.x_ledger.snapshot(day).get("remaining_usd", 0.0) > 0

    async def _ask_x(self, http, ev: Dict[str, Any], lag: Dict[str, Any], day: str) -> Dict[str, Any]:
        from src.collectors.x_watcher import XAI_URL, estimate_cost, parse_json_answer, response_text
        from src.common.x_budget import DEFAULT_CALL_RESERVATION_USD
        import hashlib
        query = PROMPT.format(symbol=lag["symbol"].replace("USDT", ""),
                              segment=SEGMENT_ES.get(ev["segmento"], ev["segmento"]),
                              leader=ev["lideres"][0]["symbol"].replace("USDT", ""),
                              r3=ev["lideres"][0]["r3"])
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        if not self.key:
            return {"x_status": "NO_KEY", "posts_found": None, "narrative_link": None,
                    "consumer": "leader_paper", "model": self.model, "query_version": "leader_x_v1",
                    "query_hash": query_hash, "cost_usd": 0.0, "request_id": None}
        call_id = self.x_ledger.reserve("leader_paper", query, self.model,
                                        estimated_cost=max(DEFAULT_CALL_RESERVATION_USD, self.x_ledger.limit_usd))
        if not call_id:
            return {"x_status": "BUDGET_EXHAUSTED", "posts_found": None, "narrative_link": None,
                    "consumer": "leader_paper", "model": self.model, "query_version": "leader_x_v1",
                    "query_hash": query_hash, "cost_usd": 0.0, "request_id": None}
        body = {"model": self.model, "input": [{"role": "user", "content": query}],
                "tools": [{"type": "x_search"}], "max_tool_calls": 1}
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        try:
            async with http.post(XAI_URL, json=body, headers=headers, timeout=120) as r:
                status_code = r.status
                resp = await r.json(content_type=None) if status_code == 200 else {}
                response_id = resp.get("id")
        except Exception as exc:
            self.x_ledger.finish(call_id, "API_ERROR", None)
            return {"x_status": "API_ERROR", "posts_found": None, "narrative_link": None,
                    "retryable": True, "error_type": type(exc).__name__, "consumer": "leader_paper",
                    "model": self.model, "query_version": "leader_x_v1", "query_hash": query_hash,
                    "cost_usd": DEFAULT_CALL_RESERVATION_USD, "request_id": None}
        if status_code != 200:
            self.x_ledger.finish(call_id, "API_ERROR", 0.0, request_id=str(response_id or "") or None)
            return {"x_status": "API_ERROR", "posts_found": None, "narrative_link": None,
                    "retryable": status_code == 429 or status_code >= 500, "http_status": status_code,
                    "consumer": "leader_paper", "model": self.model, "query_version": "leader_x_v1",
                    "query_hash": query_hash, "cost_usd": 0.0, "request_id": str(response_id or "") or None}
        ans = parse_json_answer(response_text(resp))
        cost = estimate_cost(resp)
        if not any(k in (resp.get("usage") or {}) for k in ("cost_in_usd_ticks", "input_tokens", "output_tokens")) and not (resp.get("usage") or {}).get("server_side_tool_usage_details"):
            cost = DEFAULT_CALL_RESERVATION_USD
        valid = isinstance(ans.get("posts_found"), int) and not isinstance(ans.get("posts_found"), bool)
        status = ("X_POSITIVE" if ans["posts_found"] > 0 else "X_NEGATIVE") if valid else "NO_DATA"
        self.x_ledger.finish(call_id, status, cost, posts_count=int(ans["posts_found"]) if valid else None,
                             narrative_link=bool(ans.get("narrative_link")) if valid else None,
                             request_id=str(response_id or "") or None)
        return {"x_status": status, "posts_found": int(ans["posts_found"]) if valid else None,
                "narrative_link": bool(ans.get("narrative_link")) if valid else None,
                "has_large_account": bool(ans.get("has_large_account")),
                "summary": str(ans.get("summary") or "")[:300], "cost_usd": cost,
                "consumer": "leader_paper", "model": self.model, "query_version": "leader_x_v1",
                "query_hash": query_hash, "request_id": str(response_id or "") or None}

    async def process(self, http, get: Callable[..., Awaitable[Any]], symbols, now_ms: int,
                      ask: Optional[Callable[..., Awaitable[Any]]] = None) -> List[Dict[str, Any]]:
        day = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        checkpoint = (self.ev["checkpoints"].get(day) or {})
        if checkpoint.get("status") == "COMPLETED" or day == self.ev.get("ultimo_chequeo_dia"):
            return []
        self.ev["checkpoints"][day] = {"status": "STARTED", "started_at": datetime.fromtimestamp(
            now_ms / 1000, tz=timezone.utc).isoformat()}
        self._save_events()
        try:
            made = await self._process_attempt(http, get, symbols, now_ms, ask)
            self.ev["checkpoints"][day] = {"status": "COMPLETED", "completed_at": datetime.fromtimestamp(
                now_ms / 1000, tz=timezone.utc).isoformat()}
            self.ev["ultimo_chequeo_dia"] = day
            self._save_events()
            self.health.update("RUNNING", success=True)
            return made
        except Exception as exc:
            self.ev["checkpoints"][day] = {"status": "FAILED_RETRYABLE", "failed_at": datetime.fromtimestamp(
                now_ms / 1000, tz=timezone.utc).isoformat(), "last_error_type": type(exc).__name__}
            try:
                self._save_events()
            except OSError:
                logger.error("No se pudo persistir el checkpoint FAILED_RETRYABLE.")
            self.health.update("DEGRADED", error=exc)
            raise

    # ------------------------------------------------------------------ abrir posiciones de un evento
    def open_event(self, ev: Dict[str, Any], prices: Dict[str, float], stats: Dict[str, Dict[str, float]],
                   now_ms: int) -> Dict[str, List[str]]:
        eid = ev["id"]
        lags = [l["symbol"] for l in ev["rezagadas"] if prices.get(l["symbol"])]
        lx = [l["symbol"] for l in ev["rezagadas"] if x_ok(l) and prices.get(l["symbol"])]
        lead = [l["symbol"] for l in ev["lideres"] if prices.get(l["symbol"])]
        seg_syms = {l["symbol"] for l in ev["rezagadas"]} | {l["symbol"] for l in ev["lideres"]}
        pool = sorted(s for s in stats if s not in seg_syms and prices.get(s)
                      and (ev.get("miembros_syms") is None or s not in ev["miembros_syms"]))
        rnd = random.Random(eid)
        rnd_pick = rnd.sample(pool, min(len(lags), len(pool))) if lags else []
        plan = {"lider_x": (lx, 1), "lider_sin_x": (lags, 1), "lider_azar": (rnd_pick, 1), "lider_corto": (lead, -1)}
        done: Dict[str, List[str]] = {}
        for name, (syms, side) in plan.items():
            if not syms:
                done[name] = []
                continue
            usd = EVENT_USD / len(syms)
            opened = {lot["symbol"] for lot in self.books[name].s["lotes"] if lot["evento"] == eid}
            for s in syms:
                if s not in opened:
                    self.books[name].open_lot(eid, s, usd, side, prices[s], now_ms)
            done[name] = list(syms)
        return done

    # ------------------------------------------------------------------ salidas
    def exits(self, prices: Dict[str, float], now_ms: int) -> int:
        n = 0
        entries = {e["id"]: e.get("mercado_entrada") or {} for e in self.ev["eventos"]}
        for b in self.books.values():
            for lot in list(b.s["lotes"]):
                px = prices.get(lot["symbol"])
                if lot["salida_ms"] <= now_ms and px:
                    b.close_lot(lot, px, now_ms, basket_return(entries.get(lot["evento"], {}), prices))
                    n += 1
        return n

    # ------------------------------------------------------------------ proceso diario
    async def _process_attempt(self, http, get: Callable[..., Awaitable[Any]], symbols, now_ms: int,
                      ask: Optional[Callable[..., Awaitable[Any]]] = None) -> List[Dict[str, Any]]:
        import asyncio
        from src.research.niches import sector_of
        day = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        stats: Dict[str, Dict[str, float]] = {}
        for sym in symbols:
            try:
                st = kline_stats(await get("/fapi/v1/klines", symbol=sym, interval="1d", limit=40), now_ms)
            except Exception:
                continue
            if st:
                stats[sym] = st
            await asyncio.sleep(0.05)
        if not stats:
            raise RuntimeError("No se obtuvo ninguna serie diaria válida para completar el checkpoint de Leader.")
        seg_map = {s: sector_of(s) for s in stats if sector_of(s)}
        events = find_events(stats, seg_map)
        made: List[Dict[str, Any]] = []
        for ev in events:
            last = self.ev["segmento_ultimo"].get(ev["segmento"])
            if last:
                gap = (datetime.strptime(day, "%Y-%m-%d") - datetime.strptime(last, "%Y-%m-%d")).days
                if gap < COOLDOWN_DAYS:
                    self.ev["descartados"] = (self.ev["descartados"] + [{"dia": day, "segmento": ev["segmento"],
                                              "motivo": f"ya hubo un evento hace {gap} d"}])[-100:]
                    continue
            ev["id"] = f"{day}_{ev['segmento']}"
            if any(existing.get("id") == ev["id"] for existing in self.ev["eventos"]):
                continue
            ev["dia"] = day
            ev["miembros_syms"] = [s for s, g_ in seg_map.items() if g_ == ev["segmento"]]
            for lag in ev["rezagadas"]:
                try:
                    observation = await (ask(ev, lag, day) if ask else self._ask_x(http, ev, lag, day))
                    observation = dict(observation or {})
                    if not observation.get("x_status"):
                        if isinstance(observation.get("posts_found"), int):
                            observation["x_status"] = "X_POSITIVE" if observation["posts_found"] > 0 else "X_NEGATIVE"
                        else:
                            observation["x_status"] = "NO_DATA"
                    observation.setdefault("consumer", "leader_paper")
                    observation.setdefault("model", self.model)
                    observation.setdefault("query_version", "leader_x_v1")
                    lag["x"] = observation
                except Exception as e:
                    logger.warning(f"X fall? para {lag['symbol']}: {type(e).__name__}")
                    lag["x"] = {"x_status": "API_ERROR", "posts_found": None, "narrative_link": None,
                                 "consumer": "leader_paper", "model": self.model,
                                 "query_version": "leader_x_v1", "error_type": type(e).__name__}
            try:
                prices = {d["symbol"]: float(d["price"]) for d in await get("/fapi/v1/ticker/price")
                          if d.get("symbol") in set(symbols)}
            except Exception:
                logger.warning("Sin precios: el evento se pierde (no se opera a ciegas).")
                continue
            ev["mercado_entrada"] = dict(prices)
            ev["abrio"] = self.open_event(ev, prices, stats, now_ms)
            ev["ts"] = datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc).isoformat()
            self.ev["eventos"].append(ev)
            self.ev["segmento_ultimo"][ev["segmento"]] = day
            made.append(ev)
            logger.info(f"LÍDER explotó: {ev['lideres'][0]['symbol']} (+{ev['lideres'][0]['r3']:.0%} en 3 d) en "
                        f"{ev['segmento']}: {len(ev['rezagadas'])} rezagadas, "
                        f"{sum(1 for l in ev['rezagadas'] if x_ok(l))} con X a favor")
        self.ev["eventos"] = self.ev["eventos"][-200:]
        self._save_events()
        return made


def load_config(root: Path = ROOT) -> Dict[str, Any]:
    p = Path(root) / "config" / "pumpfun.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}
