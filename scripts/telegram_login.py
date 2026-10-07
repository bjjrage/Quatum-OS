"""Crear la sesión de Telegram UNA vez y listar tus canales para elegir cuáles seguir.

    uv run python scripts/telegram_login.py

Pide tu teléfono (formato +595...) y el código que te llega por Telegram (y tu contraseña de 2 pasos si la tenés).
Guarda la sesión en config/telegram.session (ignorado por git: NO lo compartas, da acceso a tu cuenta).
Después imprime tus canales y grupos con su @usuario o id, para copiarlos a config/telegram_channels.txt.
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.collectors.telegram_watcher import SESSION, read_secret  # noqa: E402


async def main() -> None:
    from telethon import TelegramClient
    api_id, api_hash = read_secret("TELEGRAM_API_ID"), read_secret("TELEGRAM_API_HASH")
    if not api_id or not api_hash:
        raise SystemExit("Poné TELEGRAM_API_ID y TELEGRAM_API_HASH en .env (de https://my.telegram.org).")
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(SESSION.with_suffix("")), int(api_id), api_hash)
    await client.start()
    me = await client.get_me()
    print(f"\nSesión lista para {me.first_name} (@{me.username}). Tus canales y grupos:\n")
    async for d in client.iter_dialogs():
        if d.is_channel or d.is_group:
            handle = f"@{d.entity.username}" if getattr(d.entity, "username", None) else str(d.id)
            print(f"  {handle:<40} {d.name}")
    print("\nCopiá los que publican calls de memecoins a config/telegram_channels.txt (uno por línea).")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
