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

    # Direct search without "Searching..." message
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

    # Direct search without "Searching..." message
    await auto_filter(client, message, collection="primary")


# ─────────────────────────────────────────────
# 🔁 NEXT/PREV PAGE
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^navigate_"))
async def navigate_page(bot, query):
    _, req, key, offset, collection = query.data.split("_", 4)

    if int(req) != query.from_user.id:
        return await query.answer("Not for you!", show_alert=True)

    try:
        offset = int(offset)
    except Exception:
        offset = 0

    search = BUTTONS.get(key)
    if not search:
        return await query.answer("Search expired!", show_alert=True)

    files, n_offset, p_offset, total = await get_search_results(
        search, offset=offset, collection=collection
    )
    
    if not files:
        return await query.answer("No results found!", show_alert=True)

    temp.FILES[key] = files

    # Build results text
    files_text = ""
    for file in files:
        files_text += (
            f"📁 <a href='https://t.me/{temp.U_NAME}"
            f"?start=file_{query.message.chat.id}_{file['_id']}'>"
            f"[{get_size(file['file_size'])}] {file['file_name']}</a>\n\n"
        )

    current_page = (offset // MAX_BTN) + 1
    total_pages = math.ceil(total / MAX_BTN) if total else 1

    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total Files: {total}\n"
        f"📚 Collection: {collection.upper()}\n"
        f"📄 Page: {current_page} / {total_pages}</b>\n\n"
    )

    # Build navigation buttons
    nav_btns = []
    
    # Prev and Next buttons
    page_nav = []
    if p_offset is not None:
        page_nav.append(
            InlineKeyboardButton(
                "« ᴘʀᴇᴠ",
                callback_data=f"navigate_{req}_{key}_{p_offset}_{collection}"
            )
        )
    
    page_nav.append(
        InlineKeyboardButton(
            f"📄 {current_page}/{total_pages}",
            callback_data="pages"
        )
    )
    
    if n_offset is not None:
        page_nav.append(
            InlineKeyboardButton(
                "ɴᴇxᴛ »",
                callback_data=f"navigate_{req}_{key}_{n_offset}_{collection}"
            )
        )
    
    if page_nav:
        nav_btns.append(page_nav)

    # Collection selection buttons
    collection_btns = []
    for coll in ["primary", "cloud", "archives"]:
        btn_text = f"{'✅' if coll == collection else '📂'} {coll.upper()}"
        collection_btns.append(
            InlineKeyboardButton(
                btn_text,
                callback_data=f"collection_{req}_{key}_{coll}"
            )
        )
    nav_btns.append(collection_btns)

    # Close button
    nav_btns.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_data")])

    await query.message.edit_text(
        cap + files_text,
        reply_markup=InlineKeyboardMarkup(nav_btns),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer()


# ─────────────────────────────────────────────
# 🗂️ COLLECTION SWITCH
# ─────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^collection_"))
async def switch_collection(bot, query):
    _, req, key, collection = query.data.split("_", 3)

    if int(req) != query.from_user.id:
        return await query.answer("Not for you!", show_alert=True)

    search = BUTTONS.get(key)
    if not search:
        return await query.answer("Search expired!", show_alert=True)

    # Search from beginning of new collection
    files, n_offset, p_offset, total = await get_search_results(
        search, offset=0, collection=collection
    )
    
    if not files:
        return await query.answer(f"No results in {collection.upper()}!", show_alert=True)

    temp.FILES[key] = files

    # Build results text
    files_text = ""
    for file in files:
        files_text += (
            f"📁 <a href='https://t.me/{temp.U_NAME}"
            f"?start=file_{query.message.chat.id}_{file['_id']}'>"
            f"[{get_size(file['file_size'])}] {file['file_name']}</a>\n\n"
        )

    total_pages = math.ceil(total / MAX_BTN) if total else 1

    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total Files: {total}\n"
        f"📚 Collection: {collection.upper()}\n"
        f"📄 Page: 1 / {total_pages}</b>\n\n"
    )

    # Build navigation buttons
    nav_btns = []
    
    # Prev and Next buttons
    page_nav = []
    page_nav.append(
        InlineKeyboardButton(
            f"📄 1/{total_pages}",
            callback_data="pages"
        )
    )
    
    if n_offset is not None:
        page_nav.append(
            InlineKeyboardButton(
                "ɴᴇxᴛ »",
                callback_data=f"navigate_{req}_{key}_{n_offset}_{collection}"
            )
        )
    
    if page_nav:
        nav_btns.append(page_nav)

    # Collection selection buttons
    collection_btns = []
    for coll in ["primary", "cloud", "archives"]:
        btn_text = f"{'✅' if coll == collection else '📂'} {coll.upper()}"
        collection_btns.append(
            InlineKeyboardButton(
                btn_text,
                callback_data=f"collection_{req}_{key}_{coll}"
            )
        )
    nav_btns.append(collection_btns)

    # Close button
    nav_btns.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_data")])

    await query.message.edit_text(
        cap + files_text,
        reply_markup=InlineKeyboardMarkup(nav_btns),
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )
    await query.answer(f"Switched to {collection.upper()} collection! 🔄")


# ─────────────────────────────────────────────
# ❌ CLOSE
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
    
    # Ultra-fast search - no intermediate message
    files, n_offset, p_offset, total = await get_search_results(
        search, offset=0, collection=collection
    )

    if not files:
        # Send and auto-delete "not found" message
        k = await message.reply(f"❌ I can't find <b>{search}</b>")
        await asyncio.sleep(5)
        await k.delete()
        return

    key = f"{message.chat.id}-{message.id}"
    temp.FILES[key] = files
    BUTTONS[key] = search

    # Build results text
    files_text = ""
    for file in files:
        files_text += (
            f"📁 <a href='https://t.me/{temp.U_NAME}"
            f"?start=file_{message.chat.id}_{file['_id']}'>"
            f"[{get_size(file['file_size'])}] {file['file_name']}</a>\n\n"
        )

    total_pages = math.ceil(total / MAX_BTN) if total else 1

    cap = (
        f"<b>👑 Search: {search}\n"
        f"🎬 Total Files: {total}\n"
        f"📚 Collection: {collection.upper()}\n"
        f"📄 Page: 1 / {total_pages}</b>\n\n"
    )

    # Build navigation buttons
    nav_btns = []
    
    # Prev and Next buttons
    page_nav = []
    page_nav.append(
        InlineKeyboardButton(
            f"📄 1/{total_pages}",
            callback_data="pages"
        )
    )
    
    if n_offset is not None:
        page_nav.append(
            InlineKeyboardButton(
                "ɴᴇxᴛ »",
                callback_data=f"navigate_{message.from_user.id}_{key}_{n_offset}_{collection}"
            )
        )
    
    if page_nav:
        nav_btns.append(page_nav)

    # Collection selection buttons
    collection_btns = []
    for coll in ["primary", "cloud", "archives"]:
        btn_text = f"{'✅' if coll == collection else '📂'} {coll.upper()}"
        collection_btns.append(
            InlineKeyboardButton(
                btn_text,
                callback_data=f"collection_{message.from_user.id}_{key}_{coll}"
            )
        )
    nav_btns.append(collection_btns)

    # Close button
    nav_btns.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_data")])

    # Send result directly
    k = await message.reply(
        cap + files_text,
        reply_markup=InlineKeyboardMarkup(nav_btns),
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
