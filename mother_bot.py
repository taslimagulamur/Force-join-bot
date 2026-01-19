#!/usr/bin/env python3

-- coding: utf-8 --

""" 🔥 PREMIUM TELEGRAM FORCE JOIN + CONTENT BOT 🔥 100% FINAL VERSION | TERMUX + RENDER READY Author: Premium Mother Bot System """

import asyncio import logging import json import aiosqlite from datetime import datetime from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ( Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters ) from telegram.constants import ParseMode

================= BASIC CONFIG =================

BOT_TOKEN = "8589887674:AAGZLYVrvpsv8PiH3MMpmApFlUI3YzPtBF4" ADMIN_IDS = [8231476408] DB_NAME = "premium_bot.db"

================= EMOJI =================

E = { "ok": "✅", "no": "❌", "warn": "⚠️", "fire": "🔥", "admin": "👑", "user": "👤", "channel": "📢", "video": "🎥", "photo": "🖼️", "broadcast": "📣", "back": "🔙", "add": "➕", "list": "📋", "stats": "📊", "lock": "🔒", "unlock": "🔓" }

================= UTIL =================

def is_admin(uid: int): return uid in ADMIN_IDS

================= DATABASE =================

async def init_db(): async with aiosqlite.connect(DB_NAME) as db: await db.execute(""" CREATE TABLE IF NOT EXISTS users ( user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, joined_at TEXT, blocked INTEGER DEFAULT 0 )""")

await db.execute("""
    CREATE TABLE IF NOT EXISTS force_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_username TEXT
    )""")

    await db.execute("""
    CREATE TABLE IF NOT EXISTS contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        text TEXT
    )""")

    await db.commit()

async def add_user(user): async with aiosqlite.connect(DB_NAME) as db: await db.execute( "INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, 0)", (user.id, user.username, user.first_name, datetime.now().isoformat()) ) await db.commit()

async def get_channels(): async with aiosqlite.connect(DB_NAME) as db: async with db.execute("SELECT channel_username FROM force_channels") as c: return await c.fetchall()

================= FORCE JOIN CHECK =================

async def check_join(app, uid): channels = await get_channels() for ch in channels: try: member = await app.bot.get_chat_member(ch[0], uid) if member.status in ["left", "kicked"]: return False except: return False return True

================= USER START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): user = update.effective_user await add_user(user)

joined = await check_join(context.application, user.id)
if not joined:
    buttons = []
    channels = await get_channels()
    for ch in channels:
        buttons.append([
            InlineKeyboardButton(f"{E['channel']} Join {ch[0]}", url=f"https://t.me/{ch[0].replace('@','')}")
        ])
    buttons.append([
        InlineKeyboardButton(f"{E['ok']} Verify", callback_data="verify")
    ])

    await update.message.reply_text(
        f"{E['lock']} আগে চ্যানেল জয়েন করুন",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return

await main_menu(update, context)

================= VERIFY =================

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE): q = update.callback_query await q.answer()

if await check_join(context.application, q.from_user.id):
    await main_menu(q, context, edit=True)
else:
    await q.edit_message_text(f"{E['warn']} এখনো জয়েন করেননি")

================= MAIN MENU =================

async def main_menu(target, context, edit=False): text = f""" {E['fire']} Premium Content Bot

{E['video']} Videos {E['photo']} Photos """ buttons = [ [InlineKeyboardButton(f"{E['video']} Videos", callback_data="videos")], [InlineKeyboardButton(f"{E['photo']} Photos", callback_data="photos")] ]

if edit:
    await target.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
else:
    await target.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

================= CONTENT =================

async def show_content(update: Update, context: ContextTypes.DEFAULT_TYPE, ctype): q = update.callback_query await q.answer()

async with aiosqlite.connect(DB_NAME) as db:
    async with db.execute("SELECT text FROM contents WHERE type=?", (ctype,)) as c:
        rows = await c.fetchall()

if not rows:
    await q.edit_message_text("Empty")
    return

msg = "\n\n".join(r[0] for r in rows)
await q.edit_message_text(msg)

================= ADMIN PANEL =================

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): return

text = f"""

{E['admin']} Admin Panel

{E['add']} Add Channel {E['add']} Add Content {E['broadcast']} Broadcast """ buttons = [ [InlineKeyboardButton("Add Channel", callback_data="add_ch")], [InlineKeyboardButton("Add Content", callback_data="add_ct")], [InlineKeyboardButton("Broadcast", callback_data="broadcast")] ]

await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

================= ADMIN ACTIONS =================

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE): q = update.callback_query await q.answer()

if q.data == "add_ch":
    context.user_data['step'] = 'add_ch'
    await q.edit_message_text("Send channel username like @channel")

elif q.data == "add_ct":
    context.user_data['step'] = 'add_ct'
    await q.edit_message_text("Send content text")

elif q.data == "broadcast":
    context.user_data['step'] = 'broadcast'
    await q.edit_message_text("Send broadcast message")

================= ADMIN TEXT =================

async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE): if not is_admin(update.effective_user.id): return

step = context.user_data.get('step')
txt = update.message.text

async with aiosqlite.connect(DB_NAME) as db:
    if step == 'add_ch':
        await db.execute("INSERT INTO force_channels (channel_username) VALUES (?)", (txt,))
        await update.message.reply_text("Channel added")

    elif step == 'add_ct':
        await db.execute("INSERT INTO contents (type, text) VALUES (?, ?)", ('video', txt))
        await update.message.reply_text("Content added")

    elif step == 'broadcast':
        async with db.execute("SELECT user_id FROM users") as c:
            users = await c.fetchall()
        for u in users:
            try:
                await context.bot.send_message(u[0], txt)
            except:
                pass
        await update.message.reply_text("Broadcast done")

    await db.commit()
context.user_data.clear()

================= MAIN =================

async def main(): await init_db() app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(verify, pattern="verify"))
app.add_handler(CallbackQueryHandler(lambda u,c: show_content(u,c,'video'), pattern="videos"))
app.add_handler(CallbackQueryHandler(lambda u,c: show_content(u,c,'photo'), pattern="photos"))
app.add_handler(CallbackQueryHandler(admin_actions))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))

print("🔥 Premium Bot Running")
await app.run_polling()

if name == "main": logging.basicConfig(level=logging.INFO) asyncio.run(main())
