"""Vigilante de X para pump.fun: con las operaciones en vivo elige los tokens que se mueven distinto y le pregunta a
Grok (xAI, herramienta x_search) qué se dice de ellos en X en ese momento. Guarda el resultado con hora en
data/raw/pumpfun/table=x_mentions para después comparar tokens con y sin empuje en X.

Costo: xAI cobra US$5 cada 1.000 posts y US$10 cada 1.000 perfiles que trae la búsqueda. Hay un tope diario (USD)
en config/pumpfun.json -> "x_daily_usd" (por defecto 1). La clave se lee de .env (XAI_API_KEY) y nunca se loguea.
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from src.common.logger import setup_logger

logger = setup_logger("x_watcher")

XAI_URL = "https://api.x.ai/v1/responses"
DEFAULT_MODEL = "grok-4.20-0309-non-reasoning"
POST_USD, USER_USD = 5.0 / 1000, 10.0 / 1000
TOKEN_USD_PER_M = (2.0, 10.0)            # supuesto prudente de precio por millón de tokens (entrada, salida)

PROMPT = """Search X (Twitter) for posts about this Solana pump.fun token, created {age_min} minutes ago.
Contract address (mint): {mint}
Ticker: ${symbol}   Name: {name}
Look for posts that mention the contract address or the ${symbol} cashtag in the context of Solana/pump.fun.
Answer ONLY with a JSON object, no other text:
{{"posts_found": <int>, "earliest_post_utc": "<ISO time or null>",
  "accounts": [{{"handle": "<@handle>", "followers": <int or null>, "first_post_utc": "<ISO or null>"}}],
  "has_large_account": <true if any account has >= 50000 followers>,
  "coordinated_shilling": <true if many accounts post near-identical text>,
  "summary": "<one short sentence>"}}
Only include posts actually about THIS token (same address or clearly the same coin). If none, posts_found = 0."""


def parse_json_answer(text: str) -> Dict[str, Any]:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def response_text(resp: Dict[str, Any]) -> str:
    if isinstance(resp.get("output_text"), str):
        return resp["output_text"]
    out = []
    for item in resp.get("output") or []:
        for c in (item.get("content") or []) if isinstance(item, dict) else []:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                out.append(c["text"])
    return "\n".join(out)


def estimate_cost(resp: Dict[str, Any]) -> float:
    u = resp.get("usage") or {}
    ticks = u.get("cost_in_usd_ticks")
    if isinstance(ticks, (int, float)) and ticks > 0:
        return float(ticks) / 1e10                      # costo exacto informado por xAI (1 tick = 1e-10 USD)
    d = u.get("server_side_tool_usage_details") or resp.get("server_side_tool_usage_details") or {}
    posts = float(d.get("x_posts_fetched") or 0)
    users = float(d.get("x_users_fetched") or 0)
    tin = float(u.get("input_tokens") or 0)
    tout = float(u.get("output_tokens") or 0)
    return posts * POST_USD + users * USER_USD + tin / 1e6 * TOKEN_USD_PER_M[0] + tout / 1e6 * TOKEN_USD_PER_M[1]


class TokenActivity:
    """Actividad reciente por token (ventana de 5 min) para elegir candidatos sin mirar el futuro."""

    def __init__(self, window_s: int = 300):
        self.window_s = window_s
        self.trades: Dict[str, Deque[Tuple[float, str, float, bool]]] = {}
        self.meta: Dict[str, Dict[str, Any]] = {}
        self.first_seen: Dict[str, float] = {}
        self.asked: set = set()

    def on_create(self, ev: Dict[str, Any], now: float) -> None:
        self.meta[ev["mint"]] = {"symbol": ev.get("symbol") or "", "name": ev.get("name") or ""}
        self.first_seen.setdefault(ev["mint"], now)

    def on_trade(self, ev: Dict[str, Any], now: float) -> None:
        m = ev["mint"]
        self.first_seen.setdefault(m, now)
        dq = self.trades.setdefault(m, deque())
        dq.append((now, ev["user"], ev["sol_amount"] / 1e9, bool(ev["is_buy"])))
        while dq and now - dq[0][0] > self.window_s:
            dq.popleft()

    def stats(self, mint: str, now: float) -> Dict[str, float]:
        dq = self.trades.get(mint) or deque()
        buys = [t for t in dq if t[3] and now - t[0] <= self.window_s]
        sells = [t for t in dq if not t[3] and now - t[0] <= self.window_s]
        return {"unique_buyers_5m": len({t[1] for t in buys}),
                "net_buy_sol_5m": sum(t[2] for t in buys) - sum(t[2] for t in sells),
                "age_s": now - self.first_seen.get(mint, now)}

    def candidates(self, now: float, min_buyers: int = 50, min_net_sol: float = 10.0, max_age_s: int = 3600) -> List[str]:
        out = []
        for m in list(self.trades):
            if m in self.asked or m not in self.meta:        # solo tokens que vimos nacer (nombre y edad reales)
                continue
            st = self.stats(m, now)
            if st["age_s"] <= max_age_s and st["unique_buyers_5m"] >= min_buyers and st["net_buy_sol_5m"] >= min_net_sol:
                out.append(m)
        return out

    def prune(self, now: float, idle_s: int = 1800) -> None:
        for m in [m for m, dq in self.trades.items() if not dq or now - dq[-1][0] > idle_s]:
            self.trades.pop(m, None)
            if now - self.first_seen.get(m, now) > 6 * 3600:
                self.first_seen.pop(m, None)
                self.meta.pop(m, None)


class XWatcher:
    def __init__(self, sink, activity: TokenActivity, api_key: Optional[str], daily_usd: float = 1.0,
                 model: str = DEFAULT_MODEL, http=None):
        self.sink, self.activity, self.key = sink, activity, api_key
        self.daily_usd, self.model, self.http = daily_usd, model, http
        self.spent_today, self._day = 0.0, time.strftime("%Y-%m-%d", time.gmtime())
        self.spent_hour, self._hour = 0.0, int(time.time() // 3600)
        self.queries = 0
        self.priority_source = lambda: ()          # tokens con señal de GRUPO: se consultan primero

    def _budget_ok(self) -> bool:
        """Tope diario y además ritmo por hora (1/24 del día, con lo no usado de horas anteriores) para que dure."""
        day = time.strftime("%Y-%m-%d", time.gmtime())
        if day != self._day:
            self._day, self.spent_today = day, 0.0
        hour = int(time.time() // 3600)
        if hour != self._hour:
            self._hour, self.spent_hour = hour, 0.0
        hours_left = 24 - time.gmtime().tm_hour
        hourly = max(self.daily_usd - self.spent_today + self.spent_hour, 0.0) / max(hours_left, 1)
        return self.spent_today < self.daily_usd and self.spent_hour < hourly

    async def ask(self, mint: str, now: float) -> Optional[Dict[str, Any]]:
        meta = self.activity.meta.get(mint, {})
        st = self.activity.stats(mint, now)
        body = {"model": self.model,
                "input": [{"role": "user", "content": PROMPT.format(mint=mint, symbol=meta.get("symbol") or "?",
                                                                    name=meta.get("name") or "?",
                                                                    age_min=int(st["age_s"] // 60))}],
                "tools": [{"type": "x_search"}],
                "max_tool_calls": 1}                     # una sola búsqueda por token: el costo es casi todo búsqueda
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        async with self.http.post(XAI_URL, json=body, headers=headers, timeout=90) as r:
            status = r.status
            resp = await r.json(content_type=None) if status == 200 else {}
        if status != 200:
            logger.warning(f"xAI respondió {status} para {mint[:8]}…")
            return None
        ans = parse_json_answer(response_text(resp))
        cost = estimate_cost(resp)
        self.spent_today += cost
        self.spent_hour += cost
        self.queries += 1
        accounts = ans.get("accounts") or []
        foll = [int(a.get("followers") or 0) for a in accounts if isinstance(a, dict)]
        row = {"ts_query_utc_ns": time.time_ns(), "mint": mint, "symbol": meta.get("symbol") or "",
               "name": meta.get("name") or "", "token_age_s": int(st["age_s"]),
               "unique_buyers_5m": int(st["unique_buyers_5m"]), "net_buy_sol_5m": float(st["net_buy_sol_5m"]),
               "posts_found": int(ans.get("posts_found") or 0), "earliest_post_utc": str(ans.get("earliest_post_utc") or ""),
               "accounts_json": json.dumps(accounts)[:4000], "max_followers": max(foll) if foll else 0,
               "total_followers": sum(foll), "has_large_account": bool(foll and max(foll) >= 50_000),
               "coordinated_shilling": bool(ans.get("coordinated_shilling")),
               "summary": str(ans.get("summary") or "")[:500], "cost_usd": cost, "model": self.model}
        await self.sink.append("pumpfun", "x_mentions", row)
        return row

    async def run(self, interval_s: float = 30.0) -> None:
        if not self.key:
            logger.info("Sin XAI_API_KEY en .env: el vigilante de X queda apagado.")
            return
        import aiohttp
        async with aiohttp.ClientSession() as session:
            self.http = session
            while True:
                try:
                    await asyncio.sleep(interval_s)
                    now = time.time()
                    self.activity.prune(now)
                    if not self._budget_ok():
                        continue
                    prio = [m for m in list(self.priority_source()) if m not in self.activity.asked
                            and m in self.activity.meta]
                    for mint in (prio + self.activity.candidates(now))[:3]:   # máx 3 consultas por vuelta
                        self.activity.asked.add(mint)
                        if not self._budget_ok():
                            break
                        try:
                            row = await self.ask(mint, now)
                            if row:
                                logger.info(f"X: {row['symbol']} posts={row['posts_found']} "
                                            f"max_seguidores={row['max_followers']} costo=${row['cost_usd']:.3f} "
                                            f"(hoy ${self.spent_today:.2f}/{self.daily_usd:.0f})")
                        except Exception as e:
                            logger.warning(f"Consulta a X falló: {type(e).__name__}")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Vigilante de X: {type(e).__name__}: {str(e)[:150]}")
