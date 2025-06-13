# main.py

import asyncio
import logging

from telethon import TelegramClient, errors
from config import API_ID, API_HASH, BOT_TOKEN
from handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

async def main():
    # 1) create a persistent client session called "bot"
    client = TelegramClient("bot", API_ID, API_HASH)
    register_handlers(client)

    # 2) connect (won’t re-import bot auth if session exists)
    await client.connect()

    # 3) sign in only if needed
    if not await client.is_user_authorized():
        while True:
            try:
                await client.sign_in(bot_token=BOT_TOKEN)
                logging.info("✅ Bot signed in")
                break
            except errors.FloodWaitError as e:
                wait = e.seconds or 60
                logging.warning(f"FloodWait, retrying sign_in in {wait}s")
                await asyncio.sleep(wait)

    # 4) now run handlers until disconnected
    logging.info("🚀 Bot is up and running")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
