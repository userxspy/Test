import os
import random
import asyncio
from time import time as time_now
from datetime import datetime, timedelta

from Script import script
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database.ia_filterdb import (
    db_count_documents,
    get_file_details,
    delete_files
)

from database.users_chats_db import db

from info import (
    IS_PREMIUM,
    URL,
    BIN_CHANNEL,
    STICKERS,
    ADMINS,
    DELETE_TIME,
    LOG_CHANNEL,
    PICS,
    IS_STREAM,
    REACTIONS,
    PM_FILE_DELETE_TIME
)

from utils import (
    is_premium,
    get_settings,
    get_size,
    temp,
    get_readable_time,
    get_wish
)

# ─────────────────────────────────────
# HELPERS
# ─────────────────────────────────────
async def del_stk(msg):
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except:
        pass


# ─────────────────────────────────────
# /start
# ─────────────────────────────────────
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):

    # ───── GROUP START ─────
    if message.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            username = f"@{message.chat.username}" if message.chat.username else "Private"
            await client.send_message(
                LOG_CHANNEL,
                script.NEW_GROUP_TXT.format(
                    message.chat.title,
                    message.chat.id,
                    username,
                    total
                )
            )
            await db.add_chat(message.chat.id, message.chat.title)

        return await message.reply(
            f"<b>ʜᴇʏ {message.from_user.mention}, <i>{get_wish()}</i>\n"
            f"ʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>"
        )

    # ───── PRIVATE START ─────
    # reaction safe
    try:
        if REACTIONS:
            await message.react(random.choice(REACTIONS), big=True)
    except:
        pass

    # sticker safe
    if STICKERS:
        try:
            stk = await client.send_sticker(
                message.chat.id,
                random.choice(STICKERS)
            )
            asyncio.create_task(del_stk(stk))
        except:
            pass

    # ───── USER DB ─────
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(
            LOG_CHANNEL,
            script.NEW_USER_TXT.format(
                message.from_user.mention,
                message.from_user.id
            )
        )

    # ───── PREMIUM CHECK ─────
    if not await is_premium(message.from_user.id, client) and message.from_user.id not in ADMINS:
        return await message.reply_photo(
            random.choice(PICS),
            caption="❌ This bot is only for Premium users and Admins!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🤑 Buy Premium",
                    url=f"https://t.me/{temp.U_NAME}?start=premium"
                )
            ]])
        )

    # ─────────────────────────────────────────
    # 🔥 FILE OPEN HANDLER (MISSING PART FIXED)
    # ─────────────────────────────────────────
    if len(message.command) > 1 and message.command[1].startswith("file_"):

        try:
            _, grp_id, file_id = message.command[1].split("_", 2)
        except:
            return await message.reply("❌ Invalid file request")

        file = await get_file_details(file_id)
        if not file:
            return await message.reply("❌ File not found")

        settings = await get_settings(int(grp_id))

        caption = settings["caption"].format(
            file_name=file["file_name"],
            file_size=get_size(file["file_size"]),
            file_caption=file.get("caption", "")
        )

        # Buttons
        if IS_STREAM:
            buttons = [
                [
                    InlineKeyboardButton(
                        "▶️ Watch / Download",
                        callback_data=f"stream#{file_id}"
                    )
                ],
                [
                    InlineKeyboardButton("❌ Close", callback_data="close_data")
                ]
            ]
        else:
            buttons = [[InlineKeyboardButton("❌ Close", callback_data="close_data")]]

        sent = await client.send_cached_media(
            chat_id=message.chat.id,
            file_id=file["_id"],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(buttons),
            protect_content=False
        )

        # Auto delete in PM
        if PM_FILE_DELETE_TIME:
            await asyncio.sleep(PM_FILE_DELETE_TIME)
            try:
                await sent.delete()
            except:
                pass

        return

    # ───── NORMAL START UI ─────
    if len(message.command) == 1:
        return await message.reply_photo(
            random.choice(PICS),
            caption=script.START_TXT.format(
                message.from_user.mention,
                get_wish()
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "+ ADD ME TO YOUR GROUP +",
                        url=f"https://t.me/{temp.U_NAME}?startgroup=start"
                    )
                ],
                [
                    InlineKeyboardButton("👨‍🚒 HELP", callback_data="help"),
                    InlineKeyboardButton("📚 ABOUT", callback_data="about")
                ]
            ])
        )
