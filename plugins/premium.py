import os
import qrcode
import random
import asyncio
from datetime import datetime, timedelta
from hydrogram import Client, filters, enums
from hydrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from hydrogram.errors import ListenerTimeout
from database.users_chats_db import db
from info import (
    IS_PREMIUM, 
    PRE_DAY_AMOUNT, 
    RECEIPT_SEND_USERNAME, 
    UPI_ID, 
    UPI_NAME, 
    ADMINS,
    PICS
)

# Global variable for trial status (default OFF)
TRIAL_ENABLED = False
from Script import script
from utils import is_premium, temp
import random


@Client.on_message(filters.command('myplan') & filters.private)
async def myplan(client: Client, message: Message):
    """Check user's current premium plan"""
    global TRIAL_ENABLED
    
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled by admin')
    
    mp = db.get_plan(message.from_user.id)
    
    if not await is_premium(message.from_user.id, client):
        btn = []
        
        # Only show trial button if enabled
        if TRIAL_ENABLED:
            btn.append([
                InlineKeyboardButton('Activate Trial', callback_data='activate_trial'),
                InlineKeyboardButton('Activate Plan', callback_data='activate_plan')
            ])
        else:
            btn.append([
                InlineKeyboardButton('Activate Plan', callback_data='activate_plan')
            ])
        
        return await message.reply(
            'You dont have any premium plan, please use /plan to activate plan', 
            reply_markup=InlineKeyboardMarkup(btn)
        )
    
    await message.reply(
        f"You activated {mp['plan']} plan\nExpire: {mp['expire'].strftime('%Y.%m.%d %H:%M:%S')}"
    )


@Client.on_message(filters.command('plan') & filters.private)
async def plan(client: Client, message: Message):
    """Show premium plans and activation options"""
    global TRIAL_ENABLED
    
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled by admin')
    
    btn = []
    
    # Only show trial button if enabled
    if TRIAL_ENABLED:
        btn.append([InlineKeyboardButton('Activate Trial', callback_data='activate_trial')])
    
    btn.append([InlineKeyboardButton('Activate Plan', callback_data='activate_plan')])
    
    await message.reply(
        script.PLAN_TXT.format(PRE_DAY_AMOUNT, RECEIPT_SEND_USERNAME), 
        reply_markup=InlineKeyboardMarkup(btn)
    )


@Client.on_message(filters.command('add_prm') & filters.user(ADMINS))
async def add_premium(bot: Client, message: Message):
    """Admin command to add premium to users"""
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    
    try:
        _, user_id, d = message.text.split(' ')
    except:
        return await message.reply('Usage: /add_prm user_id 1d')
    
    try:
        d = int(d[:-1])
    except:
        return await message.reply('Not valid days, use: 1d, 7d, 30d, 365d, etc...')
    
    try:
        user = await bot.get_users(user_id)
    except Exception as e:
        return await message.reply(f'Error: {e}')
    
    if user.id in ADMINS:
        return await message.reply('ADMINS is already premium')
    
    if not await is_premium(user.id, bot):
        mp = db.get_plan(user.id)
        ex = datetime.now() + timedelta(days=d)
        mp['expire'] = ex
        mp['plan'] = f'{d} days'
        mp['premium'] = True
        db.update_plan(user.id, mp)
        
        await message.reply(
            f"Given premium to {user.mention}\nExpire: {ex.strftime('%Y.%m.%d %H:%M:%S')}"
        )
        
        try:
            await bot.send_message(
                user.id, 
                f"Your now premium user\nExpire: {ex.strftime('%Y.%m.%d %H:%M:%S')}"
            )
        except:
            pass
    else:
        await message.reply(f"{user.mention} is already premium user")


@Client.on_message(filters.command('rm_prm') & filters.user(ADMINS))
async def remove_premium(bot: Client, message: Message):
    """Admin command to remove premium from users"""
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    
    try:
        _, user_id = message.text.split(' ')
    except:
        return await message.reply('Usage: /rm_prm user_id')
    
    try:
        user = await bot.get_users(user_id)
    except Exception as e:
        return await message.reply(f'Error: {e}')
    
    if user.id in ADMINS:
        return await message.reply('ADMINS is already premium')
    
    if not await is_premium(user.id, bot):
        await message.reply(f"{user.mention} is not premium user")
    else:
        mp = db.get_plan(user.id)
        mp['expire'] = ''
        mp['plan'] = ''
        mp['premium'] = False
        db.update_plan(user.id, mp)
        
        await message.reply(f"{user.mention} is no longer premium user")
        
        try:
            await bot.send_message(user.id, "Your premium plan was removed by admin")
        except:
            pass


@Client.on_message(filters.command('prm_list') & filters.user(ADMINS))
async def premium_list(bot: Client, message: Message):
    """Admin command to list all premium users"""
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    
    tx = await message.reply('Getting list of premium users')
    pr = [i['id'] for i in db.get_premium_users() if i['status']['premium']]
    t = 'premium users saved in database are:\n\n'
    
    for p in pr:
        try:
            u = await bot.get_users(p)
            t += f"{u.mention} : {p}\n"
        except:
            t += f"{p}\n"
    
    await tx.edit_text(t)


@Client.on_message(filters.command('trial_on') & filters.user(ADMINS))
async def trial_on(bot: Client, message: Message):
    """Admin command to enable trial feature"""
    global TRIAL_ENABLED
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    
    TRIAL_ENABLED = True
    await message.reply('✅ Trial feature has been enabled!\nUsers can now activate 1 hour free trial.')


@Client.on_message(filters.command('trial_off') & filters.user(ADMINS))
async def trial_off(bot: Client, message: Message):
    """Admin command to disable trial feature"""
    global TRIAL_ENABLED
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    
    TRIAL_ENABLED = False
    await message.reply('❌ Trial feature has been disabled!\nUsers cannot activate trial now.')


@Client.on_message(filters.command('trial_status') & filters.user(ADMINS))
async def trial_status(bot: Client, message: Message):
    """Admin command to check trial feature status"""
    if not IS_PREMIUM:
        return await message.reply('Premium feature was disabled')
    
    status = "✅ Enabled" if TRIAL_ENABLED else "❌ Disabled"
    await message.reply(f'Trial Feature Status: {status}')


@Client.on_callback_query(filters.regex(r'^activate_trial


@Client.on_callback_query(filters.regex(r'^activate_plan$'))
async def activate_plan_callback(client: Client, query: CallbackQuery):
    """Callback handler for premium plan activation"""
    q = await query.message.edit('How many days you need premium plan?\nSend days as number')
    
    try:
        msg = await client.listen(
            chat_id=query.message.chat.id, 
            user_id=query.from_user.id,
            timeout=300
        )
    except ListenerTimeout:
        await q.delete()
        return await query.message.reply('Timeout! Please try again using /plan')
    
    try:
        d = int(msg.text)
    except:
        await q.delete()
        return await query.message.reply('Invalid number\nIf you want 7 days then send 7 only')
    
    transaction_note = f'{d} days premium plan for {query.from_user.id}'
    amount = d * PRE_DAY_AMOUNT
    upi_uri = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR&tn={transaction_note}"
    
    # Generate QR code
    qr = qrcode.make(upi_uri)
    p = f"upi_qr_{query.from_user.id}.png"
    qr.save(p)
    
    await q.delete()
    await query.message.reply_photo(
        p, 
        caption=f"{d} days premium plan amount is {amount} INR\n"
                f"Scan this QR in your UPI support platform and pay that amount (This is dynamic QR)\n\n"
                f"Send your receipt as photo in here (timeout in 10 mins)\n\n"
                f"Support: {RECEIPT_SEND_USERNAME}"
    )
    
    os.remove(p)
    
    try:
        msg = await client.listen(
            chat_id=query.message.chat.id, 
            user_id=query.from_user.id, 
            timeout=600
        )
    except ListenerTimeout:
        await q.delete()
        return await query.message.reply(f'Your time is over, send your receipt to: {RECEIPT_SEND_USERNAME}')
    
    if msg.photo:
        await q.delete()
        await query.message.reply(
            f'Your receipt was sent, wait some time\nSupport: {RECEIPT_SEND_USERNAME}'
        )
        await client.send_photo(RECEIPT_SEND_USERNAME, msg.photo.file_id, transaction_note)
    else:
        await q.delete()
        await query.message.reply(f"Not valid photo, send your receipt to: {RECEIPT_SEND_USERNAME}")


# Additional utility functions for premium checks

async def check_premium_expired():
    """Background task to check and update expired premium users"""
    while True:
        try:
            premium_users = db.get_premium_users()
            current_time = datetime.now()
            
            for user in premium_users:
                if user['status']['premium']:
                    user_plan = db.get_plan(user['id'])
                    if user_plan['expire'] and current_time > user_plan['expire']:
                        # Expire the premium
                        user_plan['premium'] = False
                        user_plan['plan'] = ''
                        db.update_plan(user['id'], user_plan)
            
            # Check every hour
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Error in check_premium_expired: {e}")
            await asyncio.sleep(3600)


def get_premium_button():
    """Get standard premium button"""
    return InlineKeyboardButton('🤑 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")


def premium_required(func):
    """Decorator to check if user has premium access"""
    async def wrapper(client: Client, message: Message):
        if not await is_premium(message.from_user.id, client):
            btn = [[get_premium_button()]]
            return await message.reply(
                'This feature is only available for premium users!\nUse /plan to activate premium.',
                reply_markup=InlineKeyboardMarkup(btn)
            )
        return await func(client, message)
    return wrapper
))
async def activate_trial_callback(client: Client, query: CallbackQuery):
    """Callback handler for trial activation"""
    global TRIAL_ENABLED
    
    if not TRIAL_ENABLED:
        return await query.answer(
            'Trial feature is currently disabled by admin!', 
            show_alert=True
        )
    
    mp = db.get_plan(query.from_user.id)
    
    if mp['trial']:
        return await query.message.edit('You already used trial, use /plan to activate plan')
    
    ex = datetime.now() + timedelta(hours=1)
    mp['expire'] = ex
    mp['trial'] = True
    mp['plan'] = '1 hour'
    mp['premium'] = True
    db.update_plan(query.from_user.id, mp)
    
    await query.message.edit(
        f"Congratulations! Your activated trial for 1 hour\nExpire: {ex.strftime('%Y.%m.%d %H:%M:%S')}"
    )


@Client.on_callback_query(filters.regex(r'^activate_plan$'))
async def activate_plan_callback(client: Client, query: CallbackQuery):
    """Callback handler for premium plan activation"""
    q = await query.message.edit('How many days you need premium plan?\nSend days as number')
    
    try:
        msg = await client.listen(
            chat_id=query.message.chat.id, 
            user_id=query.from_user.id,
            timeout=300
        )
    except ListenerTimeout:
        await q.delete()
        return await query.message.reply('Timeout! Please try again using /plan')
    
    try:
        d = int(msg.text)
    except:
        await q.delete()
        return await query.message.reply('Invalid number\nIf you want 7 days then send 7 only')
    
    transaction_note = f'{d} days premium plan for {query.from_user.id}'
    amount = d * PRE_DAY_AMOUNT
    upi_uri = f"upi://pay?pa={UPI_ID}&pn={UPI_NAME}&am={amount}&cu=INR&tn={transaction_note}"
    
    # Generate QR code
    qr = qrcode.make(upi_uri)
    p = f"upi_qr_{query.from_user.id}.png"
    qr.save(p)
    
    await q.delete()
    await query.message.reply_photo(
        p, 
        caption=f"{d} days premium plan amount is {amount} INR\n"
                f"Scan this QR in your UPI support platform and pay that amount (This is dynamic QR)\n\n"
                f"Send your receipt as photo in here (timeout in 10 mins)\n\n"
                f"Support: {RECEIPT_SEND_USERNAME}"
    )
    
    os.remove(p)
    
    try:
        msg = await client.listen(
            chat_id=query.message.chat.id, 
            user_id=query.from_user.id, 
            timeout=600
        )
    except ListenerTimeout:
        await q.delete()
        return await query.message.reply(f'Your time is over, send your receipt to: {RECEIPT_SEND_USERNAME}')
    
    if msg.photo:
        await q.delete()
        await query.message.reply(
            f'Your receipt was sent, wait some time\nSupport: {RECEIPT_SEND_USERNAME}'
        )
        await client.send_photo(RECEIPT_SEND_USERNAME, msg.photo.file_id, transaction_note)
    else:
        await q.delete()
        await query.message.reply(f"Not valid photo, send your receipt to: {RECEIPT_SEND_USERNAME}")


# Additional utility functions for premium checks

async def check_premium_expired():
    """Background task to check and update expired premium users"""
    while True:
        try:
            premium_users = db.get_premium_users()
            current_time = datetime.now()
            
            for user in premium_users:
                if user['status']['premium']:
                    user_plan = db.get_plan(user['id'])
                    if user_plan['expire'] and current_time > user_plan['expire']:
                        # Expire the premium
                        user_plan['premium'] = False
                        user_plan['plan'] = ''
                        db.update_plan(user['id'], user_plan)
            
            # Check every hour
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Error in check_premium_expired: {e}")
            await asyncio.sleep(3600)


def get_premium_button():
    """Get standard premium button"""
    return InlineKeyboardButton('🤑 Buy Premium', url=f"https://t.me/{temp.U_NAME}?start=premium")


def premium_required(func):
    """Decorator to check if user has premium access"""
    async def wrapper(client: Client, message: Message):
        if not await is_premium(message.from_user.id, client):
            btn = [[get_premium_button()]]
            return await message.reply(
                'This feature is only available for premium users!\nUse /plan to activate premium.',
                reply_markup=InlineKeyboardMarkup(btn)
            )
        return await func(client, message)
    return wrapper
