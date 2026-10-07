"""Paper trading EN VIVO: mercados "¿sube o baja?" de Polymarket (BTC/ETH/SOL, 5 y 15 min) contra Binance.

La misma regla que pasó el backtest (scripts/poly_edge_check.py, src/research/recorder_studies.model_prob):
  * P(sube) = Φ( ln(S_t / S_inicio) / (σ·√τ) ), S = mid de Binance perp, σ = volatilidad de 1 s de los últimos
    30 min (solo pasado), τ = segundos que faltan.
  * Si P − ask(Up) ≥ umbral → comprar Up.  Si (1 − P) − ask(Down) ≥ umbral → comprar Down.
  * Una apuesta por mercado (la primera señal), entre el segundo 60 desde el inicio y 30 s antes del cierre.
Ejecución simulada honesta:
  * Orden límite al precio visto, que se "envía" `delay_s` después: se llena SOLO si en ese momento el mejor ask sigue
    ≤ ese precio (si no, queda registrada como `miss`). Tamaño = mín(tope en US$, lo que hay en el mejor nivel).
  * Fee de Polymarket por mercado (acciones × p × rate × (p(1−p))^exp, de su feeSchedule).
  * Se liquida con el precio de Binance al cierre (al instante) y después con la resolución OFICIAL de Polymarket.
No envía órdenes reales. Todo queda en data/paper/poly_updown/events.jsonl.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Any, Deque, Dict, List, Optional, Tuple

from src.common.logger import setup_logger

logger = setup_logger("poly_updown_paper")

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "paper" / "poly_updown"
GAMMA = "https://gamma-api.polymarket.com/markets"
POLY_WS = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
BINANCE_WS = "wss://fstream.binance.com/public/stream"
ASSETS = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT"}
DURATIONS = {"5m": 300, "15m": 900}
_N = NormalDist()


@dataclass
class Config:
    threshold: float = 0.05          # puntos de probabilidad de ventaja mínima (0.05 = 5 pts)
    delay_s: float = 2.0             # retraso simulado entre ver la señal y que la orden llegue
    max_usd: float = 25.0            # tope por apuesta
    vol_window_s: int = 1800
    min_vol_coverage: float = 0.8
    trade_after_start_s: int = 60
    stop_before_end_s: int = 30


# --------------------------------------------------------------------------- lógica pura (testeable)
def fee_per_share(price: float, fee: Optional[Tuple[float, float]]) -> float:
    if fee:
        rate, exp = fee
        return price * rate * (price * (1 - price)) ** exp
    return max(price * 0.07 * (price * (1 - price)), price * 0.25 * (price * (1 - price)) ** 2)


def parse_fee(raw: Any) -> Optional[Tuple[float, float]]:
    try:
        d = json.loads(raw) if isinstance(raw, str) else raw
        return float(d["rate"]), float(d.get("exponent", 1))
    except Exception:
        return None


def model_prob(s0: float, st: float, sigma: float, tau_s: float) -> float:
    if not (s0 > 0 and st > 0 and sigma > 0 and tau_s > 0):
        return float("nan")
    return _N.cdf(math.log(st / s0) / (sigma * math.sqrt(tau_s)))


class SecondMids:
    """Mid de Binance segundo a segundo (último valor de cada segundo) con la volatilidad de 1 s del pasado."""

    def __init__(self, keep_s: int = 7200):
        self.keep_s = keep_s
        self.mids: Dict[int, float] = {}

    def set(self, sec: int, mid: float) -> None:
        if mid > 0:
            self.mids[sec] = mid
        if len(self.mids) > self.keep_s + 600:
            cut = sec - self.keep_s
            for k in [k for k in self.mids if k < cut]:
                del self.mids[k]

    def at(self, sec: int, max_gap: int = 120) -> float:
        for d in range(max_gap + 1):
            for s in (sec - d, sec + d) if d else (sec,):
                if s in self.mids:
                    return self.mids[s]
        return float("nan")

    def sigma(self, now_sec: int, window: int, min_cov: float) -> float:
        rets = []
        prev = self.mids.get(now_sec - window)
        for s in range(now_sec - window + 1, now_sec + 1):
            m = self.mids.get(s)
            if m is not None and prev is not None and prev > 0:
                rets.append(math.log(m / prev))
            prev = m
        if len(rets) < window * min_cov:
            return float("nan")
        mu = sum(rets) / len(rets)
        var = sum(r * r for r in rets) / len(rets) - mu * mu
        return math.sqrt(var) if var > 0 else float("nan")


@dataclass
class Market:
    slug: str
    asset: str                # BTCUSDT ...
    minutes: int
    start_s: int
    end_s: int
    up_token: str
    down_token: str
    fee: Optional[Tuple[float, float]] = None
    s0: Optional[float] = None
    bet: Optional[Dict[str, Any]] = None
    pending: Optional[Dict[str, Any]] = None
    settled: bool = False
    resolved: bool = False


@dataclass
class Quote:
    bid: float = 0.0
    bid_size: float = 0.0
    ask: float = 0.0
    ask_size: float = 0.0
    ts: float = 0.0


def decide(p: float, up: Optional[Quote], down: Optional[Quote], threshold: float) -> Optional[Tuple[str, float, float]]:
    """(lado, precio límite, tamaño en acciones disponible) o None. Down se compra en su propio libro; si no hay,
    con el bid de Up (en el CLOB, comprar Down a 1−b equivale a vender Up a b)."""
    if p != p:
        return None
    if up and 0 < up.ask < 1 and p - up.ask >= threshold:
        return "up", up.ask, up.ask_size
    if down and 0 < down.ask < 1 and (1 - p) - down.ask >= threshold:
        return "down", down.ask, down.ask_size
    if (not down or not 0 < down.ask < 1) and up and 0 < up.bid < 1 and up.bid - p >= threshold:
        return "down", 1 - up.bid, up.bid_size
    return None


def settle_pnl(bet: Dict[str, Any], up_won: bool) -> float:
    win = 1.0 if (bet["side"] == "up") == up_won else 0.0
    return bet["shares"] * (win - bet["price"] - bet["fee_per_share"])


def apply_book_event(quotes: Dict[str, Quote], ev: Dict[str, Any], now: float) -> None:
    """Actualiza el mejor bid/ask por token con eventos del WS de Polymarket (book, price_change, best_bid_ask)."""
    et = ev.get("event_type") or ev.get("type")
    if et == "book":
        tok = str(ev.get("asset_id") or "")
        bids = sorted(((float(x["price"]), float(x["size"])) for x in ev.get("bids") or [] if float(x.get("size", 0)) > 0),
                      key=lambda t: -t[0])
        asks = sorted(((float(x["price"]), float(x["size"])) for x in ev.get("asks") or [] if float(x.get("size", 0)) > 0),
                      key=lambda t: t[0])
        q = quotes.setdefault(tok, Quote())
        q.bid, q.bid_size = bids[0] if bids else (0.0, 0.0)
        q.ask, q.ask_size = asks[0] if asks else (0.0, 0.0)
        q.ts = now
    elif et == "price_change":
        for ch in ev.get("price_changes") or []:
            tok = str(ch.get("asset_id") or ev.get("asset_id") or "")
            bb, ba = float(ch.get("best_bid") or 0), float(ch.get("best_ask") or 0)
            if bb <= 0 or ba <= 0 or bb > ba:
                continue
            q = quotes.setdefault(tok, Quote())
            px, sz, sd = float(ch.get("price") or 0), float(ch.get("size") or 0), str(ch.get("side", "")).upper()
            if bb != q.bid:
                q.bid_size = 0.0
            if ba != q.ask:
                q.ask_size = 0.0
            q.bid, q.ask, q.ts = bb, ba, now
            if sd == "BUY" and abs(px - bb) < 1e-12:
                q.bid_size = sz
            if sd == "SELL" and abs(px - ba) < 1e-12:
                q.ask_size = sz
    elif et == "best_bid_ask":
        tok = str(ev.get("asset_id") or "")
        bb, ba = float(ev.get("best_bid") or 0), float(ev.get("best_ask") or 0)
        if bb > 0 and ba > 0 and bb <= ba:
            q = quotes.setdefault(tok, Quote())
            q.bid, q.ask, q.ts = bb, ba, now
            q.bid_size, q.ask_size = float(ev.get("bid_size") or q.bid_size), float(ev.get("ask_size") or q.ask_size)


def market_from_gamma(item: Dict[str, Any], coin: str, label: str, start_s: int) -> Optional[Market]:
    try:
        toks = item.get("clobTokenIds")
        toks = json.loads(toks) if isinstance(toks, str) else toks
        outs = item.get("outcomes")
        outs = json.loads(outs) if isinstance(outs, str) else outs
        up_i = [str(o).lower() for o in outs].index("up")
    except Exception:
        return None
    if not toks or len(toks) != 2:
        return None
    return Market(slug=str(item.get("slug") or ""), asset=ASSETS[coin], minutes=DURATIONS[label] // 60,
                  start_s=start_s, end_s=start_s + DURATIONS[label], up_token=str(toks[up_i]),
                  down_token=str(toks[1 - up_i]), fee=parse_fee(item.get("feeSchedule") or item.get("fee")))


def official_up_won(item: Dict[str, Any]) -> Optional[bool]:
    """True/False si Polymarket ya resolvió, None si no."""
    if not item.get("closed"):
        return None
    try:
        outs = item.get("outcomes")
        outs = json.loads(outs) if isinstance(outs, str) else outs
        prices = [float(x) for x in (json.loads(item.get("outcomePrices") or "[]"))]
        up_i = [str(o).lower() for o in outs].index("up")
    except Exception:
        return None
    if len(prices) != 2 or max(prices) < 0.99:
        return None
    return prices[up_i] >= 0.99


# --------------------------------------------------------------------------- motor
class PolyUpDownPaper:
    def __init__(self, cfg: Config = Config(), out_dir: Path = OUT_DIR):
        self.cfg, self.out_dir = cfg, out_dir
        self.mids = {a: SecondMids() for a in ASSETS.values()}
        self.last_mid: Dict[str, float] = {}
        self.last_mid_t: Dict[str, float] = {}
        self.quotes: Dict[str, Quote] = {}
        self.markets: Dict[str, Market] = {}
        self.started = time.time()
        self.stats = {"señales": 0, "llenadas": 0, "no_llenadas": 0, "liquidadas": 0, "pnl_usd": 0.0,
                      "invertido_usd": 0.0, "oficiales": 0, "pnl_oficial_usd": 0.0}
        out_dir.mkdir(parents=True, exist_ok=True)
        self._log = (out_dir / "events.jsonl").open("a", encoding="utf-8")

    def log(self, kind: str, **kw) -> None:
        self._log.write(json.dumps({"ts": time.time(), "kind": kind, **kw}, default=str) + "\n")
        self._log.flush()

    def on_binance(self, symbol: str, bid: float, ask: float, now: float) -> None:
        if symbol in self.mids and bid > 0 and ask > 0:
            self.last_mid[symbol] = (bid + ask) / 2
            self.last_mid_t[symbol] = now

    def tick(self, now: float) -> None:
        sec = int(now)
        for sym, m in self.last_mid.items():
            if now - self.last_mid_t.get(sym, 0) <= 5:     # Binance caído: no inventar precios
                self.mids[sym].set(sec, m)
        for mk in list(self.markets.values()):
            self._step_market(mk, now)

    def _step_market(self, mk: Market, now: float) -> None:
        sec = int(now)
        mids = self.mids[mk.asset]
        if mk.s0 is None and sec >= mk.start_s:
            s0 = mids.at(mk.start_s, max_gap=5)
            if s0 == s0:
                mk.s0 = s0
        # orden pendiente: llega al libro tras el retraso
        if mk.pending and now >= mk.pending["send_at"]:
            pd = mk.pending
            mk.pending = None
            q = self.quotes.get(pd["token"])
            book_px = (1 - q.bid if pd["via_up_bid"] else q.ask) if q else 0.0
            book_sz = (q.bid_size if pd["via_up_bid"] else q.ask_size) if q else 0.0
            if q and 0 < book_px <= pd["limit"] + 1e-9 and book_sz > 0:
                shares = min(self.cfg.max_usd / book_px, book_sz)
                fps = fee_per_share(book_px, mk.fee)
                mk.bet = {"side": pd["side"], "price": book_px, "shares": shares, "usd": shares * book_px,
                          "fee_per_share": fps, "p_model": pd["p"], "edge": pd["edge"], "t": now}
                self.stats["llenadas"] += 1
                self.stats["invertido_usd"] += shares * book_px
                self.log("fill", slug=mk.slug, asset=mk.asset, minutes=mk.minutes, **mk.bet)
            else:
                self.stats["no_llenadas"] += 1
                self.log("miss", slug=mk.slug, side=pd["side"], limit=pd["limit"], book_px=book_px, book_size=book_sz)
                mk.bet = {"side": pd["side"], "missed": True}
        # buscar señal
        if (mk.bet is None and mk.pending is None and mk.s0 is not None
                and mk.start_s + self.cfg.trade_after_start_s <= sec <= mk.end_s - self.cfg.stop_before_end_s):
            sig = mids.sigma(sec, self.cfg.vol_window_s, self.cfg.min_vol_coverage)
            p = model_prob(mk.s0, mids.at(sec, max_gap=2), sig, mk.end_s - now)
            d = decide(p, self.quotes.get(mk.up_token), self.quotes.get(mk.down_token), self.cfg.threshold)
            if d:
                side, limit, _ = d
                down_q = self.quotes.get(mk.down_token)
                via_up_bid = side == "down" and not (down_q and 0 < down_q.ask < 1)
                token = mk.up_token if (side == "up" or via_up_bid) else mk.down_token
                edge = (p - limit) if side == "up" else ((1 - p) - limit)
                mk.pending = {"side": side, "limit": limit, "token": token, "via_up_bid": via_up_bid,
                              "send_at": now + self.cfg.delay_s, "p": p, "edge": edge}
                self.stats["señales"] += 1
                self.log("signal", slug=mk.slug, asset=mk.asset, minutes=mk.minutes, side=side, p_model=p,
                         limit=limit, edge=edge, sigma=sig, tau_s=mk.end_s - now)
        # liquidación con Binance al cierre
        if not mk.settled and sec >= mk.end_s + 2:
            s1 = mids.at(mk.end_s, max_gap=5)
            mk.settled = True
            if mk.bet and not mk.bet.get("missed") and mk.s0 and s1 == s1:
                up_won = s1 > mk.s0
                pnl = settle_pnl(mk.bet, up_won)
                mk.bet["pnl_binance"] = pnl
                self.stats["liquidadas"] += 1
                self.stats["pnl_usd"] += pnl
                self.log("settle", slug=mk.slug, up_won_binance=up_won, s0=mk.s0, s1=s1, pnl=pnl, **{
                    k: mk.bet[k] for k in ("side", "price", "shares", "usd")})

    def on_official(self, mk: Market, up_won: bool) -> None:
        mk.resolved = True
        if mk.bet and not mk.bet.get("missed"):
            pnl = settle_pnl(mk.bet, up_won)
            self.stats["oficiales"] += 1
            self.stats["pnl_oficial_usd"] += pnl
            self.log("resolve", slug=mk.slug, up_won_official=up_won, pnl_official=pnl,
                     agrees_with_binance=(mk.bet.get("pnl_binance") is not None
                                          and (mk.bet["pnl_binance"] > 0) == (pnl > 0)))

    def save_state(self) -> None:
        st = {"stats": self.stats, "desde": self.started, "config": asdict(self.cfg),
              "abiertas": [m.slug for m in self.markets.values() if m.bet and not m.bet.get("missed") and not m.settled]}
        tmp = self.out_dir / "state.json.tmp"
        tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        tmp.replace(self.out_dir / "state.json")

    # ----------------------------------------------------------------------- red
    async def _discover(self, http, ws_send) -> None:
        now = time.time()
        new_tokens: List[str] = []
        for coin in ASSETS:
            for label, step in DURATIONS.items():
                t0 = int(now // step) * step
                for k in (0, 1):
                    start = t0 + k * step
                    slug = f"{coin}-updown-{label}-{start}"
                    if slug in self.markets:
                        continue
                    try:
                        async with http.get(GAMMA, params={"slug": slug}, timeout=10) as r:
                            if r.status != 200:
                                continue
                            payload = await r.json(content_type=None)
                    except Exception:
                        continue
                    items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
                    for it in items:
                        mk = market_from_gamma(it, coin, label, start) if isinstance(it, dict) else None
                        if mk:
                            self.markets[slug] = mk
                            new_tokens += [mk.up_token, mk.down_token]
        if new_tokens:
            await ws_send(new_tokens)
        # olvidar mercados viejos ya liquidados y resueltos (o de hace > 3 h)
        for slug in [s for s, m in self.markets.items() if (m.settled and m.resolved) or now - m.end_s > 10800]:
            self.markets.pop(slug, None)

    async def _resolve(self, http) -> None:
        now = time.time()
        for mk in [m for m in self.markets.values() if m.settled and not m.resolved and now >= m.end_s + 60]:
            if not mk.bet or mk.bet.get("missed"):
                mk.resolved = True
                continue
            try:
                async with http.get(GAMMA, params={"slug": mk.slug}, timeout=10) as r:
                    payload = await r.json(content_type=None) if r.status == 200 else None
            except Exception:
                continue
            items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
            for it in items:
                won = official_up_won(it) if isinstance(it, dict) else None
                if won is not None:
                    self.on_official(mk, won)

    async def _binance_loop(self) -> None:
        import websockets
        params = [f"{s.lower()}@bookTicker" for s in ASSETS.values()]
        while True:
            try:
                async with websockets.connect(BINANCE_WS, ping_interval=20, close_timeout=5) as ws:
                    await ws.send(json.dumps({"method": "SUBSCRIBE", "params": params, "id": 1}))
                    logger.info("Binance conectado (BTC/ETH/SOL bookTicker).")
                    async for raw in ws:
                        msg = json.loads(raw)
                        d = msg.get("data", msg)
                        if d.get("e") == "bookTicker" or "b" in d and "a" in d and "s" in d:
                            self.on_binance(str(d.get("s")), float(d.get("b") or 0), float(d.get("a") or 0), time.time())
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Binance WS: {type(e).__name__}: {str(e)[:120]}; reconecto en 3 s")
                await asyncio.sleep(3)

    async def _poly_loop(self, http) -> None:
        import websockets
        while True:
            try:
                async with websockets.connect(POLY_WS, ping_interval=None, close_timeout=5) as ws:
                    subscribed: set = set()

                    async def send(tokens: List[str]) -> None:
                        new = [t for t in tokens if t not in subscribed]
                        if not new:
                            return
                        first = not subscribed
                        subscribed.update(new)
                        msg = ({"assets_ids": new, "type": "market", "custom_feature_enabled": True} if first
                               else {"assets_ids": new, "operation": "subscribe"})
                        await ws.send(json.dumps(msg))

                    self._ws_send = send
                    await send([t for m in self.markets.values() for t in (m.up_token, m.down_token)])
                    logger.info("Polymarket conectado.")

                    async def ping():
                        while True:
                            await asyncio.sleep(10)
                            await ws.send("PING")

                    pinger = asyncio.create_task(ping())
                    try:
                        async for raw in ws:
                            if raw == "PONG":
                                continue
                            try:
                                data = json.loads(raw)
                            except ValueError:
                                continue
                            for ev in data if isinstance(data, list) else [data]:
                                if isinstance(ev, dict):
                                    apply_book_event(self.quotes, ev, time.time())
                    finally:
                        pinger.cancel()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning(f"Polymarket WS: {type(e).__name__}: {str(e)[:120]}; reconecto en 3 s")
                self._ws_send = None
                await asyncio.sleep(3)

    async def run(self) -> None:
        import aiohttp
        from src.common.dns_patch import apply_dns_fallback
        apply_dns_fallback()                  # igual que el recorder: algunos DNS locales no resuelven polymarket.com
        self._ws_send = None
        async with aiohttp.ClientSession() as http:
            tasks = [asyncio.create_task(self._binance_loop()), asyncio.create_task(self._poly_loop(http))]
            logger.info(f"Paper Polymarket up/down: umbral {self.cfg.threshold * 100:.0f} pts, retraso {self.cfg.delay_s:g} s, "
                        f"tope US$ {self.cfg.max_usd:g}. Calienta {self.cfg.vol_window_s // 60} min antes de operar.")
            last_disc = last_res = last_save = last_report = 0.0
            try:
                while True:
                    now = time.time()
                    self.tick(now)
                    if now - last_disc >= 30:
                        last_disc = now

                        async def sender(tokens):
                            if self._ws_send:
                                await self._ws_send(tokens)
                        await self._discover(http, sender)
                    if now - last_res >= 60:
                        last_res = now
                        await self._resolve(http)
                    if now - last_save >= 30:
                        last_save = now
                        self.save_state()
                    if now - last_report >= 600:
                        last_report = now
                        s = self.stats
                        logger.info(f"Paper up/down: señales {s['señales']}, llenadas {s['llenadas']}, no llenadas "
                                    f"{s['no_llenadas']}, PnL Binance US$ {s['pnl_usd']:.2f}, PnL oficial US$ "
                                    f"{s['pnl_oficial_usd']:.2f} ({s['oficiales']} resueltas)")
                    await asyncio.sleep(1.0 - (time.time() % 1.0))
            finally:
                for t in tasks:
                    t.cancel()
                self.save_state()


# --------------------------------------------------------------------------- resumen (panel del OS y script)
def _tstat(x: List[float]) -> Optional[float]:
    n = len(x)
    if n < 3:
        return None
    mu = sum(x) / n
    sd = math.sqrt(sum((v - mu) ** 2 for v in x) / (n - 1))
    return mu / (sd / math.sqrt(n)) if sd > 0 else None


def summarize_events(events: List[Dict[str, Any]], recent: int = 15) -> Dict[str, Any]:
    """Resumen del paper a partir de events.jsonl. Criterio para plata real fijado de antemano."""
    fills = {e["slug"]: e for e in events if e.get("kind") == "fill"}
    settles = {e["slug"]: e for e in events if e.get("kind") == "settle"}
    res = {e["slug"]: e for e in events if e.get("kind") == "resolve"}
    signals = sum(1 for e in events if e.get("kind") == "signal")
    misses = sum(1 for e in events if e.get("kind") == "miss")
    pnl_o = [res[s]["pnl_official"] for s in fills if s in res]
    usd_o = sum(fills[s]["usd"] for s in fills if s in res)
    windows: Dict[str, List[float]] = {}
    for s in fills:
        if s in res:
            windows.setdefault(s.rsplit("-", 1)[-1], []).append(res[s]["pnl_official"])
    t_win = _tstat([sum(v) / len(v) for v in windows.values()])
    span_d = (events[-1]["ts"] - events[0]["ts"]) / 86400 if len(events) > 1 else 0.0
    by: Dict[str, Dict[str, Any]] = {}
    for key in ("minutes", "asset", "side"):
        g: Dict[str, List[float]] = {}
        for s, f in fills.items():
            if s in res:
                g.setdefault(str(f.get(key)), []).append(res[s]["pnl_official"])
        by[key] = {k: {"n": len(v), "pnl": sum(v)} for k, v in sorted(g.items())}
    last = []
    for s, f in list(fills.items())[-recent:][::-1]:
        last.append({"mercado": s, "lado": f["side"], "precio": f["price"], "usd": f["usd"], "edge": f.get("edge"),
                     "pnl_binance": settles.get(s, {}).get("pnl"), "pnl_oficial": res.get(s, {}).get("pnl_official"),
                     "t": f.get("t")})
    criterio = len(pnl_o) >= 300 and sum(pnl_o) > 0 and (t_win or 0) > 2
    return {"dias": span_d, "senales": signals, "llenadas": len(fills), "no_llenadas": misses,
            "pct_no_llenadas": misses / signals * 100 if signals else None,
            "invertido_usd": sum(f["usd"] for f in fills.values()),
            "pnl_binance_usd": sum(settles[s]["pnl"] for s in fills if s in settles),
            "resueltas": len(pnl_o), "pnl_oficial_usd": sum(pnl_o),
            "pnl_por_usd_pct": sum(pnl_o) / usd_o * 100 if usd_o else None,
            "pnl_por_dia_usd": sum(pnl_o) / span_d if span_d >= 0.5 else None,
            "aciertos_pct": sum(1 for x in pnl_o if x > 0) / len(pnl_o) * 100 if pnl_o else None,
            "t_por_ventana": t_win, "ventanas": len(windows), "por": by, "ultimas": last,
            "criterio": {"cumple": criterio, "min_resueltas": 300, "texto":
                         "≥300 apuestas resueltas, PnL oficial > 0 y t por ventana > 2"}}


def load_events(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    path = path or OUT_DIR / "events.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out
