"""Vigilante de X para pump.fun: con las operaciones en vivo elige los tokens que se mueven distinto y le pregunta a
Grok (xAI, herramienta x_search) qué se dice de ellos en X en ese momento. Guarda el resultado con hora en
data/raw/pumpfun/table=x_mentions para después comparar tokens con y sin empuje en X.

Costo: xAI cobra US$5 cada 1.000 posts y US$10 cada 1.000 perfiles que trae la búsqueda. Hay un tope diario (USD)
en config/pumpfun.json -> "x_daily_usd" (por defecto 1). La clave se lee de .env (XAI_API_KEY) y nunca se loguea.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections import deque
from pathlib import Path
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
        self.request_states: Dict[str, Dict[str, Any]] = {}

    def set_request_state(self, mint: str, status: str, now: float, retry_after: float = 0.0) -> None:
        state = self.request_states.setdefault(mint, {"attempts": 0})
        if status == "IN_FLIGHT":
            state["attempts"] = int(state.get("attempts", 0)) + 1
        state.update({"status": status, "updated_at": now, "retry_after": retry_after})
        if status in ("SUCCESS", "NO_DATA", "FAILED_FINAL", "NO_KEY"):
            self.asked.add(mint)
        elif status in ("PENDING", "FAILED_RETRYABLE"):
            self.asked.discard(mint)

    def on_create(self, ev: Dict[str, Any], now: float) -> None:
        self.meta[ev["mint"]] = {"symbol": ev.get("symbol") or "", "name": ev.get("name") or ""}
        self.first_seen.setdefault(ev["mint"], now)
        self.request_states.setdefault(ev["mint"], {"status": "PENDING", "attempts": 0, "updated_at": now,
                                                      "retry_after": 0.0})

    def on_trade(self, ev: Dict[str, Any], now: float) -> None:
        m = ev["mint"]
        self.first_seen.setdefault(m, now)
        self.request_states.setdefault(m, {"status": "PENDING", "attempts": 0, "updated_at": now,
                                             "retry_after": 0.0})
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
            req = self.request_states.get(m) or {}
            terminal = req.get("status") in ("IN_FLIGHT", "SUCCESS", "NO_DATA", "FAILED_FINAL", "NO_KEY")
            if m in self.asked or terminal or m not in self.meta:  # only observed tokens with known metadata
                continue
            if req.get("retry_after", 0.0) > now:
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
                 model: str = DEFAULT_MODEL, http=None, root: Optional[Path] = None):
        from src.common.x_budget import XBudgetLedger
        self.sink, self.activity, self.key = sink, activity, api_key
        self.daily_usd, self.model, self.http = daily_usd, model, http
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
        self.ledger = XBudgetLedger(self.root)
        self.spent_today, self._day = 0.0, time.strftime("%Y-%m-%d", time.gmtime())
        self.spent_hour, self._hour = 0.0, int(time.time() // 3600)
        self.queries = 0
        self.priority_source = lambda: ()
        self.consumer = "pump_x_watcher"

    def _budget_ok(self) -> bool:
        """Compatibility diagnostic; actual request authorization is atomic in the shared ledger."""
        day = time.strftime("%Y-%m-%d", time.gmtime())
        if day != self._day:
            self._day, self.spent_today = day, 0.0
        hour = int(time.time() // 3600)
        if hour != self._hour:
            self._hour, self.spent_hour = hour, 0.0
        used = self.ledger.snapshot()["spent_usd"] + self.spent_today
        return used + 1e-12 < min(float(self.daily_usd), self.ledger.limit_usd)

    async def _save_observation(self, mint: str, now: float, status: str, cost: float = 0.0,
                                answer: Optional[Dict[str, Any]] = None, query_hash: str = "",
                                request_id: Optional[str] = None) -> Dict[str, Any]:
        meta = self.activity.meta.get(mint, {})
        st = self.activity.stats(mint, now)
        ans = answer or {}
        accounts = ans.get("accounts") or []
        foll = [int(a.get("followers") or 0) for a in accounts if isinstance(a, dict)]
        row = {"ts_query_utc_ns": time.time_ns(), "mint": mint, "symbol": meta.get("symbol") or "",
               "name": meta.get("name") or "", "token_age_s": int(st["age_s"]),
               "unique_buyers_5m": int(st["unique_buyers_5m"]), "net_buy_sol_5m": float(st["net_buy_sol_5m"]),
               "posts_found": int(ans.get("posts_found") or 0) if status in ("X_POSITIVE", "X_NEGATIVE") else None,
               "earliest_post_utc": str(ans.get("earliest_post_utc") or ""),
               "accounts_json": json.dumps(accounts)[:4000], "max_followers": max(foll) if foll else 0,
               "total_followers": sum(foll), "has_large_account": bool(foll and max(foll) >= 50_000),
               "coordinated_shilling": bool(ans.get("coordinated_shilling")),
               "summary": str(ans.get("summary") or "")[:500], "cost_usd": float(cost), "model": self.model,
               "x_status": status, "consumer": self.consumer, "query_version": "x_search_v1",
               "query_hash": query_hash, "request_id": request_id}
        await self.sink.append("pumpfun", "x_mentions", row)
        return row

    async def ask(self, mint: str, now: float) -> Dict[str, Any]:
        from src.common.x_budget import DEFAULT_CALL_RESERVATION_USD
        from src.common.x_budget import XBudgetLedger
        from src.common.x_budget import QUERY_VERSION
        meta = self.activity.meta.get(mint, {})
        st = self.activity.stats(mint, now)
        query = PROMPT.format(mint=mint, symbol=meta.get("symbol") or "?", name=meta.get("name") or "?",
                              age_min=int(st["age_s"] // 60))
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        if not self.key:
            return await self._save_observation(mint, now, "NO_KEY", query_hash=query_hash)
        call_id = self.ledger.reserve(self.consumer, query, self.model,
                                      estimated_cost=max(DEFAULT_CALL_RESERVATION_USD, self.ledger.limit_usd))
        if not call_id:
            return await self._save_observation(mint, now, "BUDGET_EXHAUSTED", query_hash=query_hash)
        body = {"model": self.model, "input": [{"role": "user", "content": query}],
                "tools": [{"type": "x_search"}], "max_tool_calls": 1}
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        try:
            async with self.http.post(XAI_URL, json=body, headers=headers, timeout=90) as r:
                status_code = r.status
                resp = await r.json(content_type=None) if status_code == 200 else {}
                headers_out = getattr(r, "headers", {})
                request_id = resp.get("id") or headers_out.get("x-request-id") if hasattr(headers_out, "get") else resp.get("id")
        except asyncio.CancelledError:
            self.ledger.finish(call_id, "API_ERROR", None)
            raise
        except Exception as exc:
            self.ledger.finish(call_id, "API_ERROR", None)
            logger.warning(f"Consulta a X fall?: {type(exc).__name__}")
            return await self._save_observation(mint, now, "API_ERROR", DEFAULT_CALL_RESERVATION_USD,
                                                query_hash=query_hash)
        if status_code != 200:
            self.ledger.finish(call_id, "API_ERROR", None, request_id=str(request_id or "") or None)
            logger.warning(f"xAI respondi? {status_code} para {mint[:8]}?")
            return await self._save_observation(mint, now, "API_ERROR", DEFAULT_CALL_RESERVATION_USD,
                                                query_hash=query_hash,
                                                request_id=request_id)
        text = response_text(resp)
        ans = parse_json_answer(text)
        cost = estimate_cost(resp)
        if not any(k in (resp.get("usage") or {}) for k in ("cost_in_usd_ticks", "input_tokens", "output_tokens")) and not (resp.get("usage") or {}).get("server_side_tool_usage_details"):
            cost = DEFAULT_CALL_RESERVATION_USD
        parsed = isinstance(ans.get("posts_found"), int) and not isinstance(ans.get("posts_found"), bool)
        x_status = ("X_POSITIVE" if ans["posts_found"] > 0 else "X_NEGATIVE") if parsed else "NO_DATA"
        self.ledger.finish(call_id, x_status, cost, posts_count=int(ans["posts_found"]) if parsed else None,
                           narrative_link=bool(ans.get("narrative_link")) if parsed else None,
                           request_id=str(request_id or "") or None)
        self.spent_today += cost
        self.spent_hour += cost
        self.queries += 1
        return await self._save_observation(mint, now, x_status, cost, ans,
                                            query_hash,
                                            str(request_id or "") or None)

    async def run(self, interval_s: float = 30.0) -> None:
        from src.common.runtime_health import RuntimeHealth
        health = RuntimeHealth("x_watcher", self.root)
        health.update("STARTING", started=True)
        import aiohttp
        if self.key:
            session_context = aiohttp.ClientSession()
        else:
            logger.info("Sin XAI_API_KEY: el vigilante de X queda deshabilitado; registra NO_KEY sin llamadas externas.")
            session_context = None
            health.update("DISABLED", enabled=False)
        try:
            if session_context:
                self.http = await session_context.__aenter__()
            while True:
                try:
                    await asyncio.sleep(interval_s)
                    now = time.time()
                    if self.key:
                        health.update("RUNNING")
                    self.activity.prune(now)
                    prio = [m for m in list(self.priority_source()) if m not in self.activity.asked
                            and m in self.activity.meta]
                    for mint in list(dict.fromkeys(prio + self.activity.candidates(now)))[:3]:
                        state = self.activity.request_states.get(mint) or {}
                        attempt = int(state.get("attempts", 0)) + 1
                        self.activity.set_request_state(mint, "IN_FLIGHT", now)
                        try:
                            row = await self.ask(mint, now)
                            status = row["x_status"]
                            if status in ("X_POSITIVE", "X_NEGATIVE"):
                                self.activity.set_request_state(mint, "SUCCESS", now)
                                health.update("RUNNING", success=True)
                            elif status == "NO_DATA":
                                self.activity.set_request_state(mint, "NO_DATA", now)
                            elif status == "NO_KEY":
                                self.activity.set_request_state(mint, "NO_KEY", now)
                            elif status == "BUDGET_EXHAUSTED":
                                tomorrow = (int(now // 86400) + 1) * 86400
                                self.activity.set_request_state(mint, status, now, tomorrow)
                            elif status == "API_ERROR":
                                if attempt >= 3:
                                    self.activity.set_request_state(mint, "FAILED_FINAL", now)
                                else:
                                    self.activity.set_request_state(mint, "FAILED_RETRYABLE", now,
                                                                    now + (30.0, 120.0, 600.0)[attempt - 1])
                            if status.startswith("X_"):
                                logger.info(f"X: {row['symbol']} status={status} posts={row['posts_found']} "
                                            f"costo=${row['cost_usd']:.3f}")
                        except asyncio.CancelledError:
                            self.activity.set_request_state(mint, "FAILED_RETRYABLE", now, now + 30.0)
                            raise
                        except Exception as exc:
                            if attempt >= 3:
                                self.activity.set_request_state(mint, "FAILED_FINAL", now)
                            else:
                                self.activity.set_request_state(mint, "FAILED_RETRYABLE", now,
                                                                now + (30.0, 120.0, 600.0)[attempt - 1])
                            logger.warning(f"Consulta a X fall?: {type(exc).__name__}")
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    health.update("DEGRADED", error=exc)
                    logger.warning(f"Vigilante de X: {type(exc).__name__}: {str(exc)[:150]}")
        finally:
            if session_context:
                await session_context.__aexit__(None, None, None)
            health.update("STOPPED", enabled=bool(self.key))
