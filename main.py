# main.py

import asyncio
import logging

from telethon import TelegramClient, errors
from config  import API_ID, API_HASH, BOT_TOKEN
from handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

async def main():
    # 1) persistent session file named "bot.session" in /app (from docker-compose mount)
    client = TelegramClient("bot", API_ID, API_HASH)
    register_handlers(client)

    # 2) connect without importing
    await client.connect()

    # 3) only sign_in if not already authorized
    if not await client.is_user_authorized():
        while True:
            try:
                await client.sign_in(bot_token=BOT_TOKEN)
                logging.info("✅ Bot signed in successfully")
                break
            except errors.FloodWaitError as e:
                wait = e.seconds or 60
                logging.warning(f"⚠️ FloodWait on sign_in: sleeping {wait}s")
                await asyncio.sleep(wait)
            except Exception:
                logging.exception("Unexpected error during sign_in")
                await asyncio.sleep(30)

    # 4) now run handlers until the bot disconnects
    logging.info("🚀 Bot is up and running")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
