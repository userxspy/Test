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
    PRE_DAY_AMOUNT,
    RECEIPT_SEND_USERNAME,
    URL,
    BIN_CHANNEL,
    STICKERS,
    INDEX_CHANNELS,
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
    upload_image,
    get_settings,
    get_size,
    is_check_admin,
    save_group_settings,
    temp,
    get_readable_time,
    get_wish
)

# ─────────────────────────────────────
# HELPERS
# ─────────────────────────────────────
def progress_bar(value, total, size=12):
    if total <= 0:
        return "░" * size
    filled = int((value / total) * size)
    return "█" * filled + "░" * (size - filled)


async def del_stk(s):
    await asyncio.sleep(3)
    try:
        await s.delete()
    except:
        pass


# ─────────────────────────────────────
# /start
# ─────────────────────────────────────
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):

    # ───── GROUP START ─────
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(message.chat.id)
            username = f'@{message.chat.username}' if message.chat.username else 'Private'
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

        await message.reply(
            f"<b>ʜᴇʏ {message.from_user.mention}, <i>{get_wish()}</i>\n"
            f"ʜᴏᴡ ᴄᴀɴ ɪ ʜᴇʟᴘ ʏᴏᴜ??</b>"
        )
        return

    # ───── PRIVATE START ─────

    # reaction safe
    try:
        if REACTIONS:
            await message.react(random.choice(REACTIONS), big=True)
        else:
            await message.react("⚡️", big=True)
    except:
        pass

    # sticker safe
    if STICKERS:
        try:
            stk = await client.send_sticker(message.chat.id, random.choice(STICKERS))
            asyncio.create_task(del_stk(stk))
        except:
            pass

    # user db
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

    # ───── FILE DEEP LINK (FIXED) ─────
    if len(message.command) == 2 and message.command[1].startswith("file_"):
        try:
            _, grp_id, file_id = message.command[1].split("_", 2)
            grp_id = int(grp_id)
        except:
            return await message.reply("❌ Invalid file link")

        file = await get_file_details(file_id)
        if not file:
            return await message.reply("❌ File not found or deleted")

        settings = await get_settings(grp_id)

        caption = settings["caption"].format(
            file_name=file["file_name"],
            file_size=get_size(file["file_size"]),
            file_caption=file.get("caption", "")
        )

        btn = None
        if IS_STREAM:
            btn = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "▶️ Watch / Download",
                    callback_data=f"stream#{file_id}"
                )
            ]])

        sent = await client.send_cached_media(
            chat_id=message.chat.id,
            file_id=file["_id"],
            caption=caption,
            reply_markup=btn,
            protect_content=False
        )

        await asyncio.sleep(PM_FILE_DELETE_TIME)
        try:
            await sent.delete()
        except:
            pass

        return

    # ───── NORMAL START UI ─────
    if len(message.command) == 1:
        await message.reply_photo(
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
        return


# ─────────────────────────────────────
# STATS (SINGLE DB + PROGRESS)
# ─────────────────────────────────────
@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats(_, message):

    files = db_count_documents()
    primary = files.get("primary", 0)
    cloud = files.get("cloud", 0)
    archive = files.get("archive", 0)
    total_files = files.get("total", 0)

    users = await db.total_users_count()
    chats = await db.total_chat_count()
    prm = db.get_premium_count()

    p_bar = progress_bar(primary, total_files)
    c_bar = progress_bar(cloud, total_files)
    a_bar = progress_bar(archive, total_files)

    p_pct = round((primary / total_files) * 100, 1) if total_files else 0
    c_pct = round((cloud / total_files) * 100, 1) if total_files else 0
    a_pct = round((archive / total_files) * 100, 1) if total_files else 0

    used_data_db_size = get_size(await db.get_data_db_size())
    uptime = get_readable_time(time_now() - temp.START_TIME)

    text = f"""
📊 <b>Bot Statistics</b>

👥 Users   : {users}
💎 Premium : {prm}
👥 Chats   : {chats}

📁 <b>Files Distribution</b>

Primary   {p_bar}  {primary} ({p_pct}%)
Cloud     {c_bar}  {cloud} ({c_pct}%)
Archive   {a_bar}  {archive} ({a_pct}%)

🧮 Total Files : {total_files}
💾 DB Size     : {used_data_db_size}
⏰ Uptime      : {uptime}
"""

    await message.reply_text(text, parse_mode=enums.ParseMode.HTML)


# ─────────────────────────────────────
# GROUP SETTINGS UI (USED BY pm_filter)
# ─────────────────────────────────────
async def get_grp_stg(group_id):
    settings = await get_settings(group_id)

    return [
        [
            InlineKeyboardButton(
                "✏️ Edit File Caption",
                callback_data=f"caption_setgs#{group_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"🗑 Auto Delete {'✅' if settings.get('auto_delete') else '❌'}",
                callback_data=f"bool_setgs#auto_delete#{settings.get('auto_delete')}#{group_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"👋 Welcome {'✅' if settings.get('welcome') else '❌'}",
                callback_data=f"bool_setgs#welcome#{settings.get('welcome')}#{group_id}"
            )
        ],
        [
            InlineKeyboardButton(
                f"⏱ Delete Time: {get_readable_time(DELETE_TIME)}",
                callback_data="noop"
            )
        ]
    ]
