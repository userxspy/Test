import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logging.getLogger('hydrogram').setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

import os
import time
import asyncio
import uvloop
from typing import Union, Optional, AsyncGenerator

from aiohttp import web
from hydrogram import Client, types
from hydrogram.errors import FloodWait

from web import web_app
from info import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    PORT,
    ADMINS,
    LOG_CHANNEL,
    INDEX_CHANNELS,
    SUPPORT_GROUP,
    BIN_CHANNEL,
    DATABASE_URL,
    DATABASE_NAME
)

from utils import temp, get_readable_time, check_premium
from database.users_chats_db import db

from pymongo import MongoClient


# -------------------- EVENT LOOP (PY 3.11 SAFE) --------------------
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

uvloop.install()


# -------------------- BOT CLASS --------------------
class Bot(Client):
    def __init__(self):
        super().__init__(
            name="Auto_Filter_Bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins={"root": "plugins"}
        )

    async def start(self):
        await super().start()
        temp.START_TIME = time.time()

        # Load banned users & chats
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats

        # Restart message handling
        if os.path.exists("restart.txt"):
            with open("restart.txt") as f:
                chat_id, msg_id = map(int, f.read().split())
            try:
                await self.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text="✅ Restarted Successfully!"
                )
            except Exception:
                pass
            os.remove("restart.txt")

        # Bot identity
        temp.BOT = self
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name

        # Web server (stream / health check)
        runner = web.AppRunner(web_app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", PORT).start()

        # Premium expiry checker
        asyncio.create_task(check_premium(self))

        # Startup log
        try:
            await self.send_message(
                LOG_CHANNEL,
                f"<b>{me.mention} restarted successfully 🤖</b>"
            )
        except Exception:
            logger.error("Bot is not admin in LOG_CHANNEL")
            exit()

        logger.info(f"@{me.username} started successfully")

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot stopped. Bye 👋")

    # Custom iterator (indexing safe)
    async def iter_messages(
        self: Client,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0
    ) -> Optional[AsyncGenerator["types.Message", None]]:

        current = offset
        while current < limit:
            diff = min(200, limit - current)
            messages = await self.get_messages(
                chat_id,
                list(range(current, current + diff))
            )
            for message in messages:
                yield message
                current += 1


# -------------------- SAFE START --------------------
async def main():
    bot = Bot()
    await bot.start()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
