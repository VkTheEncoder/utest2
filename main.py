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
    # 1) use a persistent session file named "bot.session"
    client = TelegramClient("session/bot", API_ID, API_HASH)
    register_handlers(client)

    # 2) retry start() if we hit FloodWaitError
    while True:
        try:
            await client.start(bot_token=BOT_TOKEN)
            logging.info("✅ Bot started successfully")
            break
        except errors.FloodWaitError as e:
            # e.seconds tells you how long to wait
            wait = getattr(e, "seconds", 60)
            logging.warning(f"⚠️ FloodWaitError: sleeping for {wait}s before retry")
            await asyncio.sleep(wait)
        except Exception as e:
            logging.exception("Unexpected error during start()")
            # optional back-off before retry
            await asyncio.sleep(30)

    # 3) run until disconnected
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
