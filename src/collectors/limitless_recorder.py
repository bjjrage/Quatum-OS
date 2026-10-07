"""Limitless Exchange (Base): mercados cripto cortos tipo "¿BTC arriba de X a las HH:MM?". API pública, sin clave.

Misma idea que Polymarket up/down: grabar el libro de los mercados que vencen pronto para probar después si su
precio se queda atrás de Binance. Endpoints (https://api.limitless.exchange, docs en /api-v1):
  GET /markets/active?page=&limit=&tradeType=clob   -> {"data": [...], "totalMarketsCount": n}
  GET /markets/{slug}/orderbook                       -> {"bids": [{price,size}], "asks": [...], "adjustedMidpoint",
                                                          "lastTradePrice", "tokenId", ...}
Tablas:
  limitless/limitless_markets  una fila la primera vez que se ve cada mercado (con el JSON crudo, para parsear después
                               el activo y el precio de referencia de la pregunta)
  limitless/limitless_book     mejor bid/ask y 5 niveles por lado, cada `book_every_s`, solo de mercados cripto que
                               vencen dentro de `horizon_h` horas
"""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from src.common.logger import setup_logger

logger = setup_logger("limitless_recorder")

API = "https://api.limitless.exchange"
_CRYPTO = re.compile(r"\b(BTC|ETH|SOL|XRP|DOGE|BNB|bitcoin|ethereum|solana)\b", re.I)


def expiration_s(m: Dict[str, Any]) -> Optional[float]:
    v = m.get("expirationTimestamp")
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v / 1000 if v > 1e12 else v


def is_short_crypto(m: Dict[str, Any], now_s: float, horizon_h: float) -> bool:
    exp = expiration_s(m)
    if exp is None or not (now_s < exp <= now_s + horizon_h * 3600) or m.get("expired"):
        return False
    text = " ".join([str(m.get("title") or ""), str(m.get("slug") or ""),
                     json.dumps(m.get("categories") or []), json.dumps(m.get("tags") or [])])
    return bool(_CRYPTO.search(text))


def market_row(m: Dict[str, Any], now_ns: int) -> Dict[str, Any]:
    exp = expiration_s(m)
    return {"ts_polled_utc_ns": now_ns, "slug": str(m.get("slug") or ""), "market_id": str(m.get("id") or ""),
            "title": str(m.get("title") or "")[:500], "status": str(m.get("status") or ""),
            "expiration_ms": int(exp * 1000) if exp else None, "trade_type": str(m.get("tradeType") or ""),
            "market_type": str(m.get("marketType") or ""),
            "categories_json": json.dumps(m.get("categories") or [])[:1000],
            "tags_json": json.dumps(m.get("tags") or [])[:1000], "raw_json": json.dumps(m, default=str)[:8000]}


def _num(x: Any) -> Optional[float]:
    if isinstance(x, dict):
        x = x.get("price", x.get("value"))
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _levels(side: Any) -> List[Tuple[float, float]]:
    out = []
    for lv in side or []:
        try:
            p, s = float(lv.get("price")), float(lv.get("size"))
        except (TypeError, ValueError, AttributeError):
            continue
        if p > 0 and s > 0:
            out.append((p, s))
    return out


def book_row(slug: str, book: Dict[str, Any], now_ns: int) -> Optional[Dict[str, Any]]:
    """Ordena los niveles (la API no garantiza el orden) y guarda el mejor nivel y los 5 primeros por lado."""
    bids = sorted(_levels(book.get("bids")), key=lambda t: -t[0])
    asks = sorted(_levels(book.get("asks")), key=lambda t: t[0])
    if not bids and not asks:
        return None
    return {"ts_received_utc_ns": now_ns, "slug": slug, "token_id": str(book.get("tokenId") or ""),
            "best_bid": bids[0][0] if bids else None, "bid_size": bids[0][1] if bids else None,
            "best_ask": asks[0][0] if asks else None, "ask_size": asks[0][1] if asks else None,
            "adjusted_mid": _num(book.get("adjustedMidpoint")), "last_trade": _num(book.get("lastTradePrice")),
            "bids_json": json.dumps(bids[:5]), "asks_json": json.dumps(asks[:5])}


class LimitlessRecorder:
    def __init__(self, sink, http=None, discover_every_s: float = 60.0, book_every_s: float = 5.0,
                 horizon_h: float = 26.0, max_rps: float = 5.0, max_pages: int = 20):
        self.sink, self.http = sink, http
        self.discover_every_s, self.book_every_s, self.horizon_h = discover_every_s, book_every_s, horizon_h
        self.min_gap_s, self.max_pages = 1.0 / max_rps, max_pages
        self.seen: set = set()
        self.tracked: Dict[str, float] = {}       # slug -> vencimiento (s)
        self._last_req = 0.0
        self.stats = {"mercados": 0, "seguidos": 0, "libros": 0, "errores": 0}

    async def _get(self, path: str, params: Optional[dict] = None) -> Optional[Any]:
        wait = self.min_gap_s - (time.monotonic() - self._last_req)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_req = time.monotonic()
        async with self.http.get(API + path, params=params, timeout=15) as r:
            if r.status != 200:
                self.stats["errores"] += 1
                return None
            return await r.json(content_type=None)

    async def discover_once(self, now_s: Optional[float] = None) -> int:
        now_s = now_s if now_s is not None else time.time()
        new = 0
        for page in range(1, self.max_pages + 1):
            data = await self._get("/markets/active", {"page": page, "limit": 25, "tradeType": "clob"})
            items = (data or {}).get("data") if isinstance(data, dict) else data
            if not items:
                break
            for m in items:
                if not isinstance(m, dict) or not m.get("slug"):
                    continue
                if m["slug"] not in self.seen:
                    self.seen.add(m["slug"])
                    await self.sink.append("limitless", "limitless_markets", market_row(m, time.time_ns()))
                    self.stats["mercados"] += 1
                    new += 1
                if is_short_crypto(m, now_s, self.horizon_h):
                    self.tracked[m["slug"]] = expiration_s(m)
            if len(items) < 25:
                break
        for slug in [s for s, exp in self.tracked.items() if exp < now_s - 60]:
            del self.tracked[slug]
        self.stats["seguidos"] = len(self.tracked)
        return new

    async def books_once(self) -> int:
        n = 0
        for slug in list(self.tracked):
            book = await self._get(f"/markets/{slug}/orderbook")
            row = book_row(slug, book, time.time_ns()) if isinstance(book, dict) else None
            if row:
                await self.sink.append("limitless", "limitless_book", row)
                self.stats["libros"] += 1
                n += 1
        return n

    async def run(self) -> None:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            self.http = session
            logger.info("Recorder de Limitless activo (mercados cripto cortos, libro cada "
                        f"{self.book_every_s:g} s).")
            last_disc = last_log = 0.0
            while True:
                try:
                    t0 = time.time()
                    if t0 - last_disc >= self.discover_every_s:
                        last_disc = t0
                        await self.discover_once(t0)
                    await self.books_once()
                    if t0 - last_log >= 600:
                        last_log = t0
                        logger.info(f"Limitless: {self.stats}")
                    await asyncio.sleep(max(0.5, self.book_every_s - (time.time() - t0)))
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Limitless: {type(e).__name__}: {str(e)[:150]}")
                    await asyncio.sleep(10)
