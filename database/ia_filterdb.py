import asyncio
import re
import math

from hydrogram import Client, filters, enums
from hydrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from info import (
    ADMINS,
    DELETE_TIME,
    MAX_BTN,
)

from utils import (
    is_premium,
    get_size,
    is_check_admin,
    get_readable_time,
    temp,
    get_settings,
)

from database.users_chats_db import db
from database.ia_filterdb import get_search_results

BUTTONS = {}
CAP = {}

# ─────────────────────────────────────────────
# 🔍 PRIVATE SEARCH (ADMIN + PREMIUM)
# ─────────────────────────────────────────────
@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_search(client, message):
    if message.text.startswith("/"):
        return

    if not await is_premium(message.from_user.id, client) and message.from_user.id not in ADMINS:
        return await message.reply_text(
            "❌ This bot is only for Premium users and Admins!"
        )

    # Direct ultra-fast search
    await auto_filter(client, message, collection="primary")


# ─────────────────────────────────────────────
# 🔍 GROUP SEARCH
# ─────────────────────────────────────────────
@Client.on_message(filters.group & filters.text & filters.incoming)
async def group_search(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0

    if not user_id:
        return

    if message.text.startswith("/"):
        return

    if not await is_premium(user_id, client) and user_id not in ADMINS:
        return

    # admin mention handler
    if "@admin" in message.text.lower() or "@admins" in message.text.lower():
        if await is_check_admin(client, chat_id, user_id):
            return

        admins = []
        async for member in client.get_chat_members(
            chat_id, enums.ChatMembersFilter.ADMINISTRATORS
        ):
            if not member.user.is_bot:
                admins.append(member.user.id)

        hidden = "".join(f"[\u2064](tg://user?id={i})" for i in admins)
        await message.reply_text("Report sent!" + hidden)
        return

    # block links for non-admins
    if re.findall(r"https?://\S+|www\.\S+|t\.me/\S+|@\w+", message.text):
        if await is_check_admin(client, chat_id, user_id):
            return
        await message.delete()
        return await message.reply("Links not allowed here!")

    # Direct ultra-fast search
    await auto_filter(client, message, collection="primary")


# ─────────────────────────────────────────────
# 🔁 NAVIGATION (PREV/NEXT)
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^nav_"))
async def navigate_page(bot, query):
    try:
        _, req, key, offset, collection = query.data.split("_", 4)
        req = int(req)
        offset = int(offset)
    except:
        return await query.answer("Invalid request!", show_alert=True)

    if req != query.from_user.id:
        return await query.answer("Not for you!", show_alert=True)

    search = BUTTONS.get(key)
    if not search:
        return await query.answer("Search expired!", show_alert=True)

    # Get results
    files, next_offset, total = await get_search_results(
        search,
        max_results=MAX_BTN,
        offset=offset,
        collection_type=collection
    )
    
    if not files:
        return await query.answer("No more results!", show_alert=True)

    temp.FILES[key] = files

    # Build results
    files_text = ""
    for file in files:
        files_text += (
            f"📁 <a href='https://t.me/{temp.U_NAME}"
            f"?start=file_{query.message.chat.id}_{file['_id']}'>"
            f"[{get_size(file['file_size'])}] {file['file_name']}</a>\n\n"
        )

    # Calculate pages
    current_page = (offset // MAX_BTN) + 1
    total_pages = math.ceil(total / MAX_BTN) if total > 0 else 1

    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total: {total}\n"
        f"📚 Source: {collection.upper()}\n"
        f"📄 Page: {current_page}/{total_pages}</b>\n\n"
    )

    # Build buttons
    buttons = []
    
    # Navigation row
    nav_row = []
    prev_offset = offset - MAX_BTN
    
    if prev_offset >= 0:
        nav_row.append(
            InlineKeyboardButton("« ᴘʀᴇᴠ", callback_data=f"nav_{req}_{key}_{prev_offset}_{collection}")
        )
    
    nav_row.append(
        InlineKeyboardButton(f"📄 {current_page}/{total_pages}", callback_data="pages")
    )
    
    if next_offset:
        nav_row.append(
            InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"nav_{req}_{key}_{next_offset}_{collection}")
        )
    
    buttons.append(nav_row)

    # Collection row
    coll_row = []
    for coll in ["primary", "cloud", "archive"]:
        emoji = "✅" if coll == collection else "📂"
        coll_row.append(
            InlineKeyboardButton(
                f"{emoji} {coll.upper()[:3]}",
                callback_data=f"coll_{req}_{key}_{coll}"
            )
        )
    buttons.append(coll_row)

    # Close button
    buttons.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_data")])

    await query.message.edit_text(
        cap + files_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer()


# ─────────────────────────────────────────────
# 🗂️ COLLECTION SWITCH
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^coll_"))
async def switch_collection(bot, query):
    try:
        _, req, key, collection = query.data.split("_", 3)
        req = int(req)
    except:
        return await query.answer("Invalid request!", show_alert=True)

    if req != query.from_user.id:
        return await query.answer("Not for you!", show_alert=True)

    search = BUTTONS.get(key)
    if not search:
        return await query.answer("Search expired!", show_alert=True)

    # Search in new collection from start
    files, next_offset, total = await get_search_results(
        search,
        max_results=MAX_BTN,
        offset=0,
        collection_type=collection
    )
    
    if not files:
        return await query.answer(f"No results in {collection.upper()}!", show_alert=True)

    temp.FILES[key] = files

    # Build results
    files_text = ""
    for file in files:
        files_text += (
            f"📁 <a href='https://t.me/{temp.U_NAME}"
            f"?start=file_{query.message.chat.id}_{file['_id']}'>"
            f"[{get_size(file['file_size'])}] {file['file_name']}</a>\n\n"
        )

    total_pages = math.ceil(total / MAX_BTN) if total > 0 else 1

    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total: {total}\n"
        f"📚 Source: {collection.upper()}\n"
        f"📄 Page: 1/{total_pages}</b>\n\n"
    )

    # Build buttons
    buttons = []
    
    # Navigation row
    nav_row = [InlineKeyboardButton(f"📄 1/{total_pages}", callback_data="pages")]
    
    if next_offset:
        nav_row.append(
            InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"nav_{req}_{key}_{next_offset}_{collection}")
        )
    
    buttons.append(nav_row)

    # Collection row
    coll_row = []
    for coll in ["primary", "cloud", "archive"]:
        emoji = "✅" if coll == collection else "📂"
        coll_row.append(
            InlineKeyboardButton(
                f"{emoji} {coll.upper()[:3]}",
                callback_data=f"coll_{req}_{key}_{coll}"
            )
        )
    buttons.append(coll_row)

    # Close button
    buttons.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_data")])

    await query.message.edit_text(
        cap + files_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(f"Switched to {collection.upper()}! 🔄")


# ─────────────────────────────────────────────
# ❌ CLOSE & PAGE INFO
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^close_data$"))
async def close_cb(bot, query):
    await query.message.delete()


@Client.on_callback_query(filters.regex(r"^pages$"))
async def pages_cb(bot, query):
    await query.answer()


# ─────────────────────────────────────────────
# 🚀 AUTO FILTER CORE - ULTRA FAST
# ─────────────────────────────────────────────
async def auto_filter(client, msg, collection="primary"):
    message = msg
    settings = await get_settings(message.chat.id)

    search = message.text.strip()
    
    # Ultra-fast direct search (NO intermediate message)
    files, next_offset, total = await get_search_results(
        search,
        max_results=MAX_BTN,
        offset=0,
        collection_type=collection
    )

    if not files:
        k = await message.reply(f"❌ I can't find <b>{search}</b>")
        await asyncio.sleep(5)
        await k.delete()
        return

    key = f"{message.chat.id}-{message.id}"
    temp.FILES[key] = files
    BUTTONS[key] = search

    # Build results
    files_text = ""
    for file in files:
        files_text += (
            f"📁 <a href='https://t.me/{temp.U_NAME}"
            f"?start=file_{message.chat.id}_{file['_id']}'>"
            f"[{get_size(file['file_size'])}] {file['file_name']}</a>\n\n"
        )

    total_pages = math.ceil(total / MAX_BTN) if total > 0 else 1

    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total: {total}\n"
        f"📚 Source: {collection.upper()}\n"
        f"📄 Page: 1/{total_pages}</b>\n\n"
    )

    # Build buttons
    buttons = []
    
    # Navigation row
    nav_row = [InlineKeyboardButton(f"📄 1/{total_pages}", callback_data="pages")]
    
    if next_offset:
        nav_row.append(
            InlineKeyboardButton("ɴᴇxᴛ »", callback_data=f"nav_{message.from_user.id}_{key}_{next_offset}_{collection}")
        )
    
    buttons.append(nav_row)

    # Collection row
    coll_row = []
    for coll in ["primary", "cloud", "archive"]:
        emoji = "✅" if coll == collection else "📂"
        coll_row.append(
            InlineKeyboardButton(
                f"{emoji} {coll.upper()[:3]}",
                callback_data=f"coll_{message.from_user.id}_{key}_{coll}"
            )
        )
    buttons.append(coll_row)

    # Close button
    buttons.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_data")])

    # Send instantly
    k = await message.reply(
        cap + files_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )

    # Auto-delete if enabled
    if settings.get("auto_delete"):
        await asyncio.sleep(DELETE_TIME)
        await k.delete()
        try:
            await message.delete()
        except:
            pass
