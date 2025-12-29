import re
import time
import asyncio
from hydrogram import Client, filters, enums
from hydrogram.errors import FloodWait
from info import ADMINS, INDEX_EXTENSIONS
from database.ia_filterdb import save_file
from hydrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import temp, get_readable_time

lock = asyncio.Lock()

@Client.on_callback_query(filters.regex(r'^index'))
async def index_files(bot, query):
    data_parts = query.data.split("#")
    ident = data_parts[1]
    
    if ident == 'yes':
        # Show collection selection buttons
        chat = data_parts[2]
        lst_msg_id = data_parts[3]
        skip = data_parts[4]
        
        buttons = [
            [
                InlineKeyboardButton('✅ PRIMARY', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#primary'),
                InlineKeyboardButton('📂 CLOUD', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#cloud')
            ],
            [
                InlineKeyboardButton('📦 ARCHIVES', callback_data=f'index#start#{chat}#{lst_msg_id}#{skip}#archive')
            ],
            [
                InlineKeyboardButton('❌ CANCEL', callback_data='close_data')
            ]
        ]
        await query.message.edit(
            "🗂️ <b>Select Collection to Index:</b>\n\n"
            "• <b>PRIMARY</b> - Main database\n"
            "• <b>CLOUD</b> - Cloud storage\n"
            "• <b>ARCHIVES</b> - Archive storage",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif ident == 'start':
        # Start indexing with selected collection
        chat = data_parts[2]
        lst_msg_id = data_parts[3]
        skip = data_parts[4]
        collection = data_parts[5]
        
        msg = query.message
        await msg.edit(f"Starting Indexing to <b>{collection.upper()}</b> collection...")
        
        try:
            chat = int(chat)
        except:
            chat = chat
        
        await index_files_to_db(int(lst_msg_id), chat, msg, bot, int(skip), collection)
    
    elif ident == 'cancel':
        temp.CANCEL = True
        await query.message.edit("Trying to cancel Indexing...")


@Client.on_message(filters.command('index') & filters.private & filters.user(ADMINS))
async def send_for_index(bot, message):
    if lock.locked():
        return await message.reply('Wait until previous process complete.')
    
    i = await message.reply("Forward last message or send last message link.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await i.delete()
    
    if msg.text and msg.text.startswith("https://t.me"):
        try:
            msg_link = msg.text.split("/")
            last_msg_id = int(msg_link[-1])
            chat_id = msg_link[-2]
            if chat_id.isnumeric():
                chat_id = int(("-100" + chat_id))
        except:
            await message.reply('Invalid message link!')
            return
    elif msg.forward_from_chat and msg.forward_from_chat.type == enums.ChatType.CHANNEL:
        last_msg_id = msg.forward_from_message_id
        chat_id = msg.forward_from_chat.username or msg.forward_from_chat.id
    else:
        await message.reply('This is not forwarded message or link.')
        return
    
    try:
        chat = await bot.get_chat(chat_id)
    except Exception as e:
        return await message.reply(f'Errors - {e}')

    if chat.type != enums.ChatType.CHANNEL:
        return await message.reply("I can index only channels.")

    s = await message.reply("Send skip message number.")
    msg = await bot.listen(chat_id=message.chat.id, user_id=message.from_user.id)
    await s.delete()
    
    try:
        skip = int(msg.text)
    except:
        return await message.reply("Number is invalid.")

    buttons = [[
        InlineKeyboardButton('YES', callback_data=f'index#yes#{chat_id}#{last_msg_id}#{skip}')
    ],[
        InlineKeyboardButton('CLOSE', callback_data='close_data'),
    ]]
    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply(
        f'Do you want to index <b>{chat.title}</b> channel?\n'
        f'Total Messages: <code>{last_msg_id}</code>\n'
        f'Skip: <code>{skip}</code>', 
        reply_markup=reply_markup
    )


async def index_files_to_db(lst_msg_id, chat, msg, bot, skip, collection_type="primary"):
    start_time = time.time()
    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0
    badfiles = 0
    current = skip
    
    async with lock:
        try:
            async for message in bot.iter_messages(chat, lst_msg_id, skip):
                time_taken = get_readable_time(time.time()-start_time)
                
                if temp.CANCEL:
                    temp.CANCEL = False
                    await msg.edit(
                        f"<b>✅ Successfully Cancelled!</b>\n"
                        f"📚 Collection: <code>{collection_type.upper()}</code>\n"
                        f"⏱ Completed in: <code>{time_taken}</code>\n\n"
                        f"📁 Saved Files: <code>{total_files}</code>\n"
                        f"🔄 Duplicates: <code>{duplicate}</code>\n"
                        f"🗑 Deleted: <code>{deleted}</code>\n"
                        f"❌ No Media: <code>{no_media + unsupported}</code>\n"
                        f"⚠️ Unsupported: <code>{unsupported}</code>\n"
                        f"❗ Errors: <code>{errors}</code>\n"
                        f"🚫 Bad Files: <code>{badfiles}</code>"
                    )
                    return
                
                current += 1
                
                if current % 30 == 0:
                    btn = [[
                        InlineKeyboardButton('CANCEL', callback_data=f'index#cancel#{chat}#{lst_msg_id}#{skip}')
                    ]]
                    try:
                        await msg.edit_text(
                            text=f"<b>📊 Indexing Progress</b>\n"
                            f"📚 Collection: <code>{collection_type.upper()}</code>\n"
                            f"⏱ Time: <code>{time_taken}</code>\n\n"
                            f"📨 Total Received: <code>{current}</code>\n"
                            f"📁 Saved: <code>{total_files}</code>\n"
                            f"🔄 Duplicates: <code>{duplicate}</code>\n"
                            f"🗑 Deleted: <code>{deleted}</code>\n"
                            f"❌ No Media: <code>{no_media + unsupported}</code>\n"
                            f"⚠️ Unsupported: <code>{unsupported}</code>\n"
                            f"❗ Errors: <code>{errors}</code>\n"
                            f"🚫 Bad Files: <code>{badfiles}</code>", 
                            reply_markup=InlineKeyboardMarkup(btn)
                        )
                    except FloodWait as e:
                        await asyncio.sleep(e.value)
                    except Exception:
                        pass
                
                if message.empty:
                    deleted += 1
                    continue
                elif not message.media:
                    no_media += 1
                    continue
                elif message.media not in [enums.MessageMediaType.VIDEO, enums.MessageMediaType.DOCUMENT]:
                    unsupported += 1
                    continue
                
                media = getattr(message, message.media.value, None)
                if not media:
                    unsupported += 1
                    continue
                elif not (str(media.file_name).lower()).endswith(tuple(INDEX_EXTENSIONS)):
                    unsupported += 1
                    continue
                
                media.caption = message.caption
                file_name = re.sub(r"@\w+|(_|\-|\.|\+)", " ", str(media.file_name))
                
                # Save to selected collection
                sts = await save_file(media, collection_type=collection_type)
                
                if sts == 'suc':
                    total_files += 1
                elif sts == 'dup':
                    duplicate += 1
                elif sts == 'err':
                    errors += 1
                    
        except Exception as e:
            await msg.reply(f'Index canceled due to Error - {e}')
        else:
            time_taken = get_readable_time(time.time()-start_time)
            await msg.edit(
                f'<b>✅ Successfully Indexed!</b>\n'
                f'📚 Collection: <code>{collection_type.upper()}</code>\n'
                f'⏱ Completed in: <code>{time_taken}</code>\n\n'
                f'📁 Saved Files: <code>{total_files}</code>\n'
                f'🔄 Duplicates: <code>{duplicate}</code>\n'
                f'🗑 Deleted: <code>{deleted}</code>\n'
                f'❌ No Media: <code>{no_media + unsupported}</code>\n'
                f'⚠️ Unsupported: <code>{unsupported}</code>\n'
                f'❗ Errors: <code>{errors}</code>\n'
                f'🚫 Bad Files: <code>{badfiles}</code>'
            )
