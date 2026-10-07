"""Quién FONDEÓ la billetera creadora de cada token de pump.fun con tracción (la "billetera madre").

Los devs lanzan cada token desde una billetera nueva, pero la cargan con SOL desde la misma billetera madre: la
reputación real está ahí, no en la creadora. Para no gastar RPC en los ~40 mil tokens/día que mueren en segundos,
solo se consultan los creadores de tokens que juntan >= `min_buyers` compradores distintos en sus primeros minutos.

Por cada creador: getSignaturesForAddress (hasta 50, la más vieja primero) y getTransaction de las más antiguas hasta
encontrar la transferencia de SOL (system transfer / createAccount) que la fondeó:
  pumpfun/creator_funding (mint, creator, funder, lamports, funding_signature, funding_block_time, n_signatures, ...)
RPC: Helius si hay HELIUS_API_KEY en .env (más estable), si no la pública de Solana; tope `max_rpm` pedidos/min.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from src.common.logger import setup_logger

logger = setup_logger("funder_tracker")

PUBLIC_RPC = "https://api.mainnet-beta.solana.com"
HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={key}"


def _instructions(tx: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Todas las instrucciones parseadas (externas e internas) de una transacción jsonParsed."""
    out = list((((tx or {}).get("transaction") or {}).get("message") or {}).get("instructions") or [])
    for inner in ((tx or {}).get("meta") or {}).get("innerInstructions") or []:
        out.extend(inner.get("instructions") or [])
    return [i for i in out if isinstance(i, dict)]


def find_funding(tx: Dict[str, Any], wallet: str) -> Optional[Tuple[str, int]]:
    """(billetera que envió SOL a `wallet`, lamports) si la transacción la fondea; None si no."""
    if not tx or ((tx.get("meta") or {}).get("err") is not None):
        return None
    best: Optional[Tuple[str, int]] = None
    for ins in _instructions(tx):
        if ins.get("program") != "system":
            continue
        p = ins.get("parsed") or {}
        info = p.get("info") or {}
        kind = p.get("type")
        dest = info.get("destination") if kind in ("transfer", "transferWithSeed") else \
            info.get("newAccount") if kind in ("createAccount", "createAccountWithSeed") else None
        src = info.get("source")
        lam = int(info.get("lamports") or 0)
        if dest == wallet and src and src != wallet and lam > 0 and (best is None or lam > best[1]):
            best = (src, lam)
    return best


class FunderTracker:
    def __init__(self, sink, activity, rpc_url: str = PUBLIC_RPC, min_buyers: int = 15, check_after_s: int = 180,
                 give_up_after_s: int = 900, max_rpm: int = 60, http=None):
        self.sink, self.activity, self.rpc_url, self.http = sink, activity, rpc_url, http
        self.min_buyers, self.check_after_s, self.give_up_after_s = min_buyers, check_after_s, give_up_after_s
        self.max_rpm = max_rpm
        self.pending: Dict[str, Tuple[str, float]] = {}       # mint -> (creator, visto)
        self.queue: Deque[Tuple[str, str]] = deque()          # (mint, creator) a resolver
        self.done_creators: Dict[str, Optional[str]] = {}     # creator -> funder (cache)
        self._calls: Deque[float] = deque()
        self.stats = {"encolados": 0, "resueltos": 0, "sin_fondeo": 0, "errores_rpc": 0}
        self.error_types: Dict[str, int] = {}                 # visible in the 10-min log line
        self.using_helius = "helius" in rpc_url

    # ---------------------------------------------------------------- selección (sin red, testeable)
    def on_create(self, ev: Dict[str, Any], now: float) -> None:
        creator = ev.get("creator") or ev.get("user")
        if ev.get("mint") and creator:
            self.pending[ev["mint"]] = (str(creator), now)

    def select(self, now: float) -> int:
        """Mueve a la cola los tokens con tracción; descarta los que no la tuvieron a tiempo."""
        n = 0
        for mint, (creator, seen) in list(self.pending.items()):
            age = now - seen
            if age < self.check_after_s:
                continue
            if self.activity.stats(mint, now).get("unique_buyers_5m", 0) >= self.min_buyers:
                self.queue.append((mint, creator))
                self.stats["encolados"] += 1
                n += 1
                del self.pending[mint]
            elif age > self.give_up_after_s:
                del self.pending[mint]
        return n

    # ---------------------------------------------------------------- RPC
    async def _rpc(self, method: str, params: list) -> Any:
        while True:
            now = time.monotonic()
            while self._calls and now - self._calls[0] > 60:
                self._calls.popleft()
            if len(self._calls) < self.max_rpm:
                break
            await asyncio.sleep(60 - (now - self._calls[0]) + 0.05)
        self._calls.append(time.monotonic())
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        async with self.http.post(self.rpc_url, json=body, timeout=20) as r:
            if r.status != 200:
                raise RuntimeError(f"RPC {r.status}")
            data = await r.json(content_type=None)
        if data.get("error"):
            raise RuntimeError(f"RPC error {data['error'].get('code')}")
        return data.get("result")

    async def resolve(self, mint: str, creator: str) -> Dict[str, Any]:
        row = {"ts_query_utc_ns": time.time_ns(), "mint": mint, "creator": creator, "funder": None, "lamports": None,
               "funding_signature": None, "funding_block_time": None, "n_signatures": 0, "reached_oldest": False,
               "cached": False}
        if creator in self.done_creators:
            row["funder"], row["cached"] = self.done_creators[creator], True
            return row
        sigs = await self._rpc("getSignaturesForAddress", [creator, {"limit": 50}]) or []
        row["n_signatures"] = len(sigs)
        row["reached_oldest"] = len(sigs) < 50
        for s in list(reversed(sigs))[:4]:                     # las más antiguas primero
            tx = await self._rpc("getTransaction", [s["signature"], {"encoding": "jsonParsed",
                                                                     "maxSupportedTransactionVersion": 0}])
            f = find_funding(tx, creator)
            if f:
                row.update(funder=f[0], lamports=f[1], funding_signature=s["signature"],
                           funding_block_time=int(s.get("blockTime") or 0))
                break
        self.done_creators[creator] = row["funder"]
        if len(self.done_creators) > 200_000:
            self.done_creators.clear()
        return row

    async def run(self) -> None:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            self.http = session
            logger.info(f"Rastreador de fondeo activo (creadores de tokens con >= {self.min_buyers} compradores; "
                        f"tope {self.max_rpm} pedidos/min; RPC {'Helius' if self.using_helius else 'pública'}).")
            last_log = time.time()
            while True:
                try:
                    self.select(time.time())
                    if not self.queue:
                        await asyncio.sleep(5)
                    else:
                        mint, creator = self.queue.popleft()
                        try:
                            row = await self.resolve(mint, creator)
                        except Exception as e:
                            self.stats["errores_rpc"] += 1
                            kind = str(e)[:40] if isinstance(e, RuntimeError) else type(e).__name__
                            self.error_types[kind] = self.error_types.get(kind, 0) + 1
                            limited = "429" in kind or "-32429" in kind or "rate" in kind.lower()
                            if limited and self.queue.maxlen is None:
                                self.queue.appendleft((mint, creator))      # retry it after backing off
                            await asyncio.sleep(15 if limited else 2)
                            continue
                        self.stats["resueltos" if row["funder"] else "sin_fondeo"] += 1
                        await self.sink.append("pumpfun", "creator_funding", row)
                    if time.time() - last_log > 600:
                        last_log = time.time()
                        logger.info(f"Fondeo: {self.stats} | errores por tipo {self.error_types} | "
                                    f"RPC {'Helius' if self.using_helius else 'pública'} | cola {len(self.queue)} | "
                                    f"pendientes {len(self.pending)}")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Rastreador de fondeo: {type(e).__name__}: {str(e)[:150]}")
                    await asyncio.sleep(5)
