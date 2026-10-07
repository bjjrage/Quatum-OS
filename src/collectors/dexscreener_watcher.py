"""DexScreener: tokens que PAGARON promoción (boosts) o perfil, en todas las chains. Gratis, sin clave.

Un boost es alguien pagando para empujar un token: la versión medible del "push" de influencers. Se consulta la API
pública cada `interval_s` (límite publicado: 60 pedidos/min por endpoint) y se guarda cada aparición nueva con hora:
  dexscreener/token_boosts    (chain_id, token_address, amount, total_amount)  -- una fila por cada aumento de total
  dexscreener/token_profiles  (chain_id, token_address)                        -- una fila por token
El "ya visto" vive en memoria: tras un reinicio puede repetirse una fila (los estudios usan la primera por token).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from src.common.logger import setup_logger

logger = setup_logger("dexscreener_watcher")

BOOSTS_URL = "https://api.dexscreener.com/token-boosts/latest/v1"
PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"


def _items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


class DexScreenerWatcher:
    def __init__(self, sink, http=None, interval_s: float = 30.0):
        self.sink, self.http, self.interval_s = sink, http, interval_s
        self.seen_boosts: Set[Tuple[str, str, float]] = set()
        self.seen_profiles: Set[Tuple[str, str]] = set()
        self.rows = {"token_boosts": 0, "token_profiles": 0}

    def boost_rows(self, payload: Any, now_ns: int) -> List[Dict[str, Any]]:
        out = []
        for it in _items(payload):
            chain, addr = str(it.get("chainId") or ""), str(it.get("tokenAddress") or "")
            total = float(it.get("totalAmount") or 0)
            key = (chain, addr, total)
            if not chain or not addr or key in self.seen_boosts:
                continue
            self.seen_boosts.add(key)
            out.append({"ts_polled_utc_ns": now_ns, "chain_id": chain, "token_address": addr,
                        "amount": float(it.get("amount") or 0), "total_amount": total,
                        "url": str(it.get("url") or "")[:300], "description": str(it.get("description") or "")[:500],
                        "links_json": json.dumps(it.get("links") or [])[:2000]})
        return out

    def profile_rows(self, payload: Any, now_ns: int) -> List[Dict[str, Any]]:
        out = []
        for it in _items(payload):
            chain, addr = str(it.get("chainId") or ""), str(it.get("tokenAddress") or "")
            if not chain or not addr or (chain, addr) in self.seen_profiles:
                continue
            self.seen_profiles.add((chain, addr))
            out.append({"ts_polled_utc_ns": now_ns, "chain_id": chain, "token_address": addr,
                        "url": str(it.get("url") or "")[:300], "description": str(it.get("description") or "")[:500],
                        "links_json": json.dumps(it.get("links") or [])[:2000]})
        return out

    async def _get(self, url: str) -> Optional[Any]:
        async with self.http.get(url, timeout=20) as r:
            if r.status != 200:
                logger.warning(f"DexScreener respondió {r.status} en {url.rsplit('/', 3)[-3]}")
                return None
            return await r.json(content_type=None)

    async def poll_once(self) -> int:
        n = 0
        for url, table, fn in ((BOOSTS_URL, "token_boosts", self.boost_rows),
                               (PROFILES_URL, "token_profiles", self.profile_rows)):
            payload = await self._get(url)
            if payload is None:
                continue
            for row in fn(payload, time.time_ns()):
                await self.sink.append("dexscreener", table, row)
                self.rows[table] += 1
                n += 1
        return n

    async def run(self) -> None:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            self.http = session
            logger.info("Vigilante de DexScreener (boosts y perfiles pagos) activo.")
            while True:
                try:
                    await self.poll_once()
                    await asyncio.sleep(self.interval_s)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"DexScreener: {type(e).__name__}: {str(e)[:150]}")
                    await asyncio.sleep(self.interval_s)
