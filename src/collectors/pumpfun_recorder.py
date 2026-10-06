"""pump.fun recorder (Solana): escucha el programa de pump.fun en vivo y guarda cada compra/venta, token nuevo y
graduación, decodificando los eventos que el programa escribe en sus logs ("Program data: <base64>").

Fuente por defecto: RPC pública de Solana (gratis, sin créditos). Si config/pumpfun.json pide "helius" y existe
config/helius_key.txt, usa Helius con un tope diario de MB (Helius cobra 2 créditos cada 0,1 MB).
La clave nunca se escribe en logs.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import struct
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.common.logger import setup_logger

logger = setup_logger("pumpfun_recorder")

PUMP_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUBLIC_WSS = "wss://api.mainnet-beta.solana.com"
HELIUS_WSS = "wss://mainnet.helius-rpc.com/?api-key={key}"
ROOT = Path(__file__).resolve().parents[2]


def _disc(name: str) -> bytes:
    """Discriminador de evento Anchor: primeros 8 bytes de sha256('event:<Nombre>')."""
    return hashlib.sha256(f"event:{name}".encode()).digest()[:8]


DISC_TRADE, DISC_CREATE, DISC_COMPLETE = _disc("TradeEvent"), _disc("CreateEvent"), _disc("CompleteEvent")

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    pad = len(data) - len(data.lstrip(b"\0"))
    return "1" * pad + out


class _Reader:
    def __init__(self, buf: bytes, pos: int = 0):
        self.b, self.p = buf, pos

    def left(self) -> int:
        return len(self.b) - self.p

    def pubkey(self) -> str:
        v = self.b[self.p:self.p + 32]
        if len(v) < 32:
            raise ValueError("short")
        self.p += 32
        return b58(v)

    def u64(self) -> int:
        v = struct.unpack_from("<Q", self.b, self.p)[0]
        self.p += 8
        return v

    def i64(self) -> int:
        v = struct.unpack_from("<q", self.b, self.p)[0]
        self.p += 8
        return v

    def boolean(self) -> bool:
        v = self.b[self.p]
        self.p += 1
        return v != 0

    def string(self) -> str:
        n = struct.unpack_from("<I", self.b, self.p)[0]
        self.p += 4
        if n > 2000:
            raise ValueError("string too long")
        v = self.b[self.p:self.p + n]
        self.p += n
        return v.decode("utf-8", errors="replace")


def _clip(v: int) -> int:
    return v if v < 2**63 else 2**63 - 1


def decode_event(raw: bytes) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Devuelve ('trade'|'create'|'complete', campos) o None. Tolera campos nuevos al final (versiones futuras)."""
    if len(raw) < 8:
        return None
    d, r = raw[:8], _Reader(raw, 8)
    try:
        if d == DISC_TRADE:
            ev = {"mint": r.pubkey(), "sol_amount": _clip(r.u64()), "token_amount": _clip(r.u64()),
                  "is_buy": r.boolean(), "user": r.pubkey(), "ts_chain_s": r.i64(),
                  "virtual_sol_reserves": _clip(r.u64()), "virtual_token_reserves": _clip(r.u64()),
                  "real_sol_reserves": _clip(r.u64()), "real_token_reserves": _clip(r.u64()),
                  "creator": None, "fee": None, "creator_fee": None}
            if r.left() >= 32 + 8 + 8 + 32 + 8 + 8:                 # fee_recipient, fee_bps, fee, creator, ...
                r.pubkey()
                r.u64()
                ev["fee"] = _clip(r.u64())
                ev["creator"] = r.pubkey()
                r.u64()
                ev["creator_fee"] = _clip(r.u64())
            return "trade", ev
        if d == DISC_CREATE:
            ev = {"name": r.string()[:200], "symbol": r.string()[:50], "uri": r.string()[:500],
                  "mint": r.pubkey(), "bonding_curve": r.pubkey(), "user": r.pubkey(), "creator": None, "ts_chain_s": None}
            if r.left() >= 32 + 8:
                ev["creator"] = r.pubkey()
                ev["ts_chain_s"] = r.i64()
            return "create", ev
        if d == DISC_COMPLETE:
            return "complete", {"user": r.pubkey(), "mint": r.pubkey(), "bonding_curve": r.pubkey(),
                                "ts_chain_s": r.i64() if r.left() >= 8 else None}
    except (ValueError, struct.error, IndexError):
        return None
    return None


def events_from_logs(logs: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
    out = []
    for line in logs or []:
        if not line.startswith("Program data: "):
            continue
        try:
            raw = base64.b64decode(line[len("Program data: "):].strip())
        except Exception:
            continue
        ev = decode_event(raw)
        if ev:
            out.append(ev)
    return out


TABLE = {"trade": "pumpfun_trades", "create": "pumpfun_creates", "complete": "pumpfun_completes"}


def load_source_config(root: Path = ROOT) -> Dict[str, Any]:
    """config/pumpfun.json (opcional): {"source": "public"|"helius", "helius_daily_mb": 1500}."""
    cfg = {"source": "public", "helius_daily_mb": 1500.0, "enabled": True}
    p = root / "config" / "pumpfun.json"
    if p.exists():
        try:
            cfg.update(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            logger.warning("config/pumpfun.json ilegible: se usan valores por defecto.")
    return cfg


def resolve_url(cfg: Dict[str, Any], root: Path = ROOT) -> Tuple[str, str]:
    if cfg.get("source") == "helius":
        from src.common.secrets import get_secret
        key = get_secret("HELIUS_API_KEY", root) or ""
        if key:
            return HELIUS_WSS.format(key=key), "helius"
        logger.warning("Se pidió Helius pero no hay HELIUS_API_KEY en .env: se usa la RPC pública.")
    return PUBLIC_WSS, "public"


class PumpfunRecorder:
    def __init__(self, sink, root: Path = ROOT):
        self.sink = sink
        self.root = root
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.events = {"trade": 0, "create": 0, "complete": 0}
        self.bytes_today = 0
        self._day = time.strftime("%Y-%m-%d", time.gmtime())
        from src.collectors.x_watcher import TokenActivity
        self.activity = TokenActivity()
        self._x_task: Optional[asyncio.Task] = None
        self._extra_tasks: List[asyncio.Task] = []      # DexScreener y Telegram
        self.paper = None                         # paper de grupos + nichos (src/paper/pump_paper.py)
        self._paper_tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        cfg = load_source_config(self.root)
        if not cfg.get("enabled", True):
            logger.info("pump.fun recorder desactivado en config/pumpfun.json.")
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        if cfg.get("paper_enabled", True):
            self._paper_tasks.append(asyncio.create_task(self._start_paper()))
        if cfg.get("x_enabled", True):
            from src.collectors.x_watcher import DEFAULT_MODEL, XWatcher
            from src.common.secrets import get_secret
            xw = XWatcher(self.sink, self.activity, get_secret("XAI_API_KEY", self.root),
                          daily_usd=float(cfg.get("x_daily_usd", 1.0)), model=str(cfg.get("x_model") or DEFAULT_MODEL))
            xw.priority_source = lambda: self.paper.x_queue if self.paper is not None else ()
            self._x_task = asyncio.create_task(xw.run())
        if cfg.get("dexscreener_enabled", True):
            from src.collectors.dexscreener_watcher import DexScreenerWatcher
            self._extra_tasks.append(asyncio.create_task(
                DexScreenerWatcher(self.sink, interval_s=float(cfg.get("dexscreener_interval_s", 30))).run()))
        if cfg.get("telegram_enabled", True):
            from src.collectors.telegram_watcher import TelegramWatcher
            self._extra_tasks.append(asyncio.create_task(TelegramWatcher(self.sink, self.root).run()))

    async def _start_paper(self) -> None:
        try:
            from src.paper.pump_paper import PumpPaper
            paper = PumpPaper(activity=self.activity)
            n = await asyncio.to_thread(paper.warmup, self.root / "data" / "raw")
            logger.info(f"pump paper listo ({n} operaciones repasadas).")
            self.paper = paper
            self._paper_tasks.append(asyncio.create_task(paper.run_ticks()))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"pump paper no arrancó: {type(e).__name__}: {str(e)[:200]}")

    async def stop(self) -> None:
        self._running = False
        for t in self._paper_tasks:
            t.cancel()
        if self.paper is not None:
            try:
                self.paper.save()
            except Exception:
                pass
        if self._task:
            self._task.cancel()
        if self._x_task:
            self._x_task.cancel()
        for t in self._extra_tasks:
            t.cancel()
        logger.info(f"pump.fun recorder stopped. Eventos: {self.events}")

    def _budget_ok(self, source: str, cfg: Dict[str, Any]) -> bool:
        day = time.strftime("%Y-%m-%d", time.gmtime())
        if day != self._day:
            self._day, self.bytes_today = day, 0
        return source != "helius" or self.bytes_today < float(cfg.get("helius_daily_mb", 1500)) * 1e6

    async def handle_message(self, raw_msg: str) -> int:
        """Procesa una notificación logsSubscribe. Devuelve cuántos eventos guardó."""
        try:
            msg = json.loads(raw_msg)
        except Exception:
            return 0
        if msg.get("method") != "logsNotification":
            return 0
        res = (msg.get("params") or {}).get("result") or {}
        val = res.get("value") or {}
        if val.get("err") is not None:
            return 0                                   # transacción fallida: no pasó nada
        slot = int((res.get("context") or {}).get("slot") or 0)
        sig = str(val.get("signature") or "")
        ts = time.time_ns()
        n = 0
        for kind, ev in events_from_logs(val.get("logs") or []):
            row = {"ts_received_utc_ns": ts, "slot": slot, "signature": sig, **ev}
            await self.sink.append("pumpfun", TABLE[kind], row)
            self.events[kind] += 1
            now = ts / 1e9
            if kind == "trade":
                self.activity.on_trade(ev, now)
            elif kind == "create":
                self.activity.on_create(ev, now)
            if self.paper is not None:
                try:
                    if kind == "trade":
                        self.paper.on_trade({**ev, "slot": slot}, now)
                    elif kind == "create":
                        self.paper.on_create(ev, now)
                    else:
                        self.paper.on_complete(ev, now)
                except Exception as e:
                    logger.warning(f"pump paper: {type(e).__name__}: {str(e)[:150]}")
            n += 1
        return n

    async def _loop(self) -> None:
        import websockets
        backoff = 1.0
        last_report = time.time()
        while self._running:
            cfg = load_source_config(self.root)
            url, source = resolve_url(cfg, self.root)
            if not self._budget_ok(source, cfg):
                logger.warning("Tope diario de Helius alcanzado: pump.fun en pausa hasta mañana (UTC).")
                await asyncio.sleep(300)
                continue
            try:
                logger.info(f"Conectando pump.fun via {source}...")
                async with websockets.connect(url, ping_interval=20, ping_timeout=60, open_timeout=20,
                                              max_size=8 * 2**20, max_queue=8192, close_timeout=5.0) as ws:
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe",
                                              "params": [{"mentions": [PUMP_PROGRAM]}, {"commitment": "confirmed"}]}))
                    logger.info(f"Suscripto a pump.fun ({source}).")
                    backoff = 1.0
                    async for msg in ws:
                        if not self._running:
                            break
                        self.bytes_today += len(msg)
                        await self.handle_message(msg)
                        if time.time() - last_report > 600:
                            last_report = time.time()
                            logger.info(f"pump.fun: {self.events} | {self.bytes_today / 1e6:.0f} MB hoy ({source})")
                        if not self._budget_ok(source, cfg):
                            break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"pump.fun WS desconectado ({source}): {type(e).__name__}: {str(e)[:200]}. "
                               f"Reintento en {backoff:.0f}s")
                await asyncio.sleep(backoff)
                backoff = min(60.0, backoff * 2)
