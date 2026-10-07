"""DexScreener: tokens que PAGARON promoción (boosts) o perfil, en todas las chains. Gratis, sin clave.

Un boost es alguien pagando para empujar un token: la versión medible del "push" de influencers. Se consulta la API
pública cada `interval_s` (límite publicado: 60 pedidos/min por endpoint) y se guarda cada aparición nueva con hora:
  dexscreener/token_boosts    (chain_id, token_address, amount, total_amount)  -- una fila por cada aumento de total
  dexscreener/token_profiles  (chain_id, token_address)                        -- una fila por token
El "ya visto" vive en memoria: tras un reinicio puede repetirse una fila (los estudios usan la primera por token).

Además sigue el PRECIO de cada token promocionado durante `track_hours` (cada `price_every_s`), con la API pública de
pares (hasta 30 tokens por pedido, límite publicado 300/min). Así hay precio también para tokens ya graduados
(PumpSwap/Raydium) y de otras chains, que el recorder de pump.fun no ve:
  dexscreener/token_prices (chain_id, token_address, pair_address, dex_id, price_usd, liquidity_usd, fdv, volumen y
                            compras/ventas de los últimos 5 min) -- el par con más liquidez de cada token
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
PRICES_URL = "https://api.dexscreener.com/tokens/v1/{chain}/{addresses}"


def _num(x: Any) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def price_rows(pairs: Any, wanted: List[str], chain: str, now_ns: int) -> List[Dict[str, Any]]:
    """Una fila por token pedido: el par con más liquidez donde el token es la base."""
    want = {a.lower(): a for a in wanted}
    best: Dict[str, Dict[str, Any]] = {}
    for p in _items(pairs):
        base = str((p.get("baseToken") or {}).get("address") or "")
        if base.lower() not in want:
            continue
        liq = _num((p.get("liquidity") or {}).get("usd")) or 0.0
        if base.lower() not in best or liq > best[base.lower()]["liquidity_usd"]:
            vol, tx = p.get("volume") or {}, (p.get("txns") or {}).get("m5") or {}
            best[base.lower()] = {
                "ts_polled_utc_ns": now_ns, "chain_id": chain, "token_address": want[base.lower()],
                "pair_address": str(p.get("pairAddress") or ""), "dex_id": str(p.get("dexId") or ""),
                "price_usd": _num(p.get("priceUsd")), "price_native": _num(p.get("priceNative")),
                "liquidity_usd": liq, "fdv": _num(p.get("fdv")), "market_cap": _num(p.get("marketCap")),
                "volume_m5": _num(vol.get("m5")), "volume_h1": _num(vol.get("h1")),
                "buys_m5": int(tx.get("buys") or 0), "sells_m5": int(tx.get("sells") or 0),
                "pair_created_ms": int(_num(p.get("pairCreatedAt")) or 0)}
    return list(best.values())


def _items(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


class DexScreenerWatcher:
    def __init__(self, sink, http=None, interval_s: float = 30.0, price_every_s: float = 60.0,
                 track_hours: float = 24.0, max_tracked: int = 3000):
        self.sink, self.http, self.interval_s = sink, http, interval_s
        self.price_every_s, self.track_s, self.max_tracked = price_every_s, track_hours * 3600, max_tracked
        self.tracked: Dict[Tuple[str, str], float] = {}         # (chain, token) -> primera vez visto (s)
        self._last_prices = 0.0
        self.seen_boosts: Set[Tuple[str, str, float]] = set()
        self.seen_profiles: Set[Tuple[str, str]] = set()
        self.rows = {"token_boosts": 0, "token_profiles": 0, "token_prices": 0}

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

    def _track(self, rows: List[Dict[str, Any]], now_s: float) -> None:
        for r in rows:
            key = (r["chain_id"], r["token_address"])
            if key not in self.tracked and len(self.tracked) < self.max_tracked:
                self.tracked[key] = now_s

    async def prices_once(self, now_s: Optional[float] = None) -> int:
        now_s = now_s if now_s is not None else time.time()
        for k in [k for k, t0 in self.tracked.items() if now_s - t0 > self.track_s]:
            del self.tracked[k]
        by_chain: Dict[str, List[str]] = {}
        for chain, addr in self.tracked:
            by_chain.setdefault(chain, []).append(addr)
        n = 0
        for chain, addrs in by_chain.items():
            for i in range(0, len(addrs), 30):
                chunk = addrs[i:i + 30]
                payload = await self._get(PRICES_URL.format(chain=chain, addresses=",".join(chunk)))
                if payload is None:
                    continue
                for row in price_rows(payload, chunk, chain, time.time_ns()):
                    await self.sink.append("dexscreener", "token_prices", row)
                    self.rows["token_prices"] += 1
                    n += 1
        return n

    async def poll_once(self) -> int:
        n = 0
        for url, table, fn in ((BOOSTS_URL, "token_boosts", self.boost_rows),
                               (PROFILES_URL, "token_profiles", self.profile_rows)):
            payload = await self._get(url)
            if payload is None:
                continue
            rows = fn(payload, time.time_ns())
            self._track(rows, time.time())
            for row in rows:
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
                    if time.time() - self._last_prices >= self.price_every_s:
                        self._last_prices = time.time()
                        await self.prices_once()
                    await asyncio.sleep(self.interval_s)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"DexScreener: {type(e).__name__}: {str(e)[:150]}")
                    await asyncio.sleep(self.interval_s)
