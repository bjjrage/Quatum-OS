"""Telegram: canales de "calls" de memecoins. Gratis, con TU cuenta (API de Telegram vía Telethon).

Escucha en vivo los canales listados en config/telegram_channels.txt (uno por línea: @usuario, enlace t.me o id) y
guarda cada dirección de contrato que aparezca en un mensaje, con la hora del mensaje y la de recepción:
  telegram/calls  (ts_message_utc_ns, ts_received_utc_ns, channel, channel_id, message_id, chain, token_address, ...)

Credenciales (gratis, de https://my.telegram.org -> API development tools), en .env:
  TELEGRAM_API_ID=...   TELEGRAM_API_HASH=...
La sesión se crea UNA vez con `uv run python scripts/telegram_login.py` (pide tu teléfono y el código que te llega
por Telegram) y queda en config/telegram.session (ignorado por git). Solo LEE mensajes: nunca escribe ni se une.
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.common.logger import setup_logger

logger = setup_logger("telegram_watcher")

ROOT = Path(__file__).resolve().parents[2]
SESSION = ROOT / "config" / "telegram.session"
CHANNELS_FILE = ROOT / "config" / "telegram_channels.txt"

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_SOL_RE = re.compile(r"(?<![1-9A-HJ-NP-Za-km-z])[1-9A-HJ-NP-Za-km-z]{32,44}(?![1-9A-HJ-NP-Za-km-z])")
_EVM_RE = re.compile(r"(?<![0-9a-fA-Fx])0x[0-9a-fA-F]{40}(?![0-9a-fA-F])")


def _b58_len(s: str) -> int:
    n = 0
    for c in s:
        n = n * 58 + _B58.index(c)
    return (n.bit_length() + 7) // 8 + (len(s) - len(s.lstrip("1")))


def extract_addresses(text: str) -> List[Tuple[str, str]]:
    """(chain, address) de cada contrato del texto. Solana: base58 que decodifica a 32 bytes. EVM: 0x + 40 hex."""
    out: List[Tuple[str, str]] = []
    seen = set()
    for a in _EVM_RE.findall(text or ""):
        if a.lower() not in seen:
            seen.add(a.lower())
            out.append(("evm", a))
    for a in _SOL_RE.findall(text or ""):
        if a not in seen and _b58_len(a) == 32:
            seen.add(a)
            out.append(("solana", a))
    return out


def read_secret(name: str, root: Path = ROOT) -> Optional[str]:
    """Variable de entorno o línea NAME=valor del .env. No usa src.common.secrets (no está en el repo)."""
    if os.environ.get(name):
        return os.environ[name]
    env = root / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == name and v.strip():
                return v.strip().strip('"').strip("'")
    return None


def load_channels(path: Path = CHANNELS_FILE) -> List[Any]:
    if not path.exists():
        return []
    out: List[Any] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.split("#", 1)[0].strip()
        if not s:
            continue
        s = s.replace("https://", "").replace("http://", "").replace("t.me/", "").lstrip("@").strip("/")
        out.append(int(s) if s.lstrip("-").isdigit() else s)
    return out


def call_rows(text: str, msg_ts_ns: int, now_ns: int, channel: str, channel_id: int, message_id: int,
              views: Optional[int], is_forward: bool) -> List[Dict[str, Any]]:
    return [{"ts_message_utc_ns": msg_ts_ns, "ts_received_utc_ns": now_ns, "channel": channel[:100],
             "channel_id": int(channel_id or 0), "message_id": int(message_id or 0), "chain": chain,
             "token_address": addr, "views": int(views or 0), "is_forward": bool(is_forward),
             "text": (text or "")[:500]} for chain, addr in extract_addresses(text)]


class TelegramWatcher:
    def __init__(self, sink, root: Path = ROOT):
        self.sink, self.root = sink, root
        self.rows = 0

    def ready(self) -> Tuple[bool, str]:
        if not read_secret("TELEGRAM_API_ID", self.root) or not read_secret("TELEGRAM_API_HASH", self.root):
            return False, "faltan TELEGRAM_API_ID / TELEGRAM_API_HASH en .env"
        if not SESSION.exists():
            return False, "falta la sesión: correr scripts/telegram_login.py una vez"
        if not load_channels():
            return False, "config/telegram_channels.txt vacío o inexistente"
        try:
            import telethon  # noqa: F401
        except ImportError:
            return False, "falta el paquete telethon (uv sync)"
        return True, ""

    async def run(self) -> None:
        ok, why = self.ready()
        if not ok:
            logger.info(f"Vigilante de Telegram apagado: {why}.")
            return
        from telethon import TelegramClient, events
        client = TelegramClient(str(SESSION.with_suffix("")), int(read_secret("TELEGRAM_API_ID", self.root)),
                                read_secret("TELEGRAM_API_HASH", self.root))
        await client.connect()
        if not await client.is_user_authorized():
            logger.warning("Sesión de Telegram no autorizada: correr scripts/telegram_login.py.")
            await client.disconnect()
            return
        chats = []
        for c in load_channels():
            try:
                chats.append(await client.get_input_entity(c))
            except Exception as e:
                logger.warning(f"Canal de Telegram no encontrado: {c} ({type(e).__name__})")

        @client.on(events.NewMessage(chats=chats))
        async def handler(ev):
            msg = ev.message
            chat = await ev.get_chat()
            name = getattr(chat, "username", None) or getattr(chat, "title", "") or str(ev.chat_id)
            rows = call_rows(msg.message or "", int(msg.date.timestamp() * 1e9), time.time_ns(), name, ev.chat_id,
                             msg.id, getattr(msg, "views", None), msg.fwd_from is not None)
            for row in rows:
                await self.sink.append("telegram", "calls", row)
                self.rows += 1

        logger.info(f"Vigilante de Telegram activo en {len(chats)} canales.")
        try:
            await client.run_until_disconnected()
        except asyncio.CancelledError:
            pass
        finally:
            await client.disconnect()
