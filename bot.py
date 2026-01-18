import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from motor.motor_asyncio import AsyncIOMotorClient
from flask import Flask
from threading import Thread

# --- RENDER PORT BINDING & KEEP ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running 24/7! 🔥"

def run():
    # Render takes port from environment or defaults to 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- CONFIGURATION (Apnar deya Details) ---
API_ID = 33970225
API_HASH = "1ccfef47fd720a822c6c7978ba1902f5"
BOT_TOKEN = "8589887674:AAGZLYVrvpsv8PiH3MMpmApFlUI3YzPtBF4"
ADMIN_ID = 8231476408
MONGO_URL = os.environ.get("MONGO_URL")

# --- BOT & DB SETUP ---
bot = Client("HotPremiumBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db_client = AsyncIOMotorClient(MONGO_URL)
db = db_client["HotPhotoBot"]
folders_col = db["folders"]
config_col = db["config"]

# --- UTILS (Force Join Check) ---
async def is_subscribed(user_id):
    data = await config_col.find_one({"id": "force_join"})
    channels = data["channels"] if data else []
    if not channels: return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]:
                return False
        except Exception:
            return False
    return True

# --- USER INTERFACE (Hot Bangla Style) ---
@bot.on_message(filters.command("start"))
async def start(client, message):
    user = message.from_user
    subscribed = await is_subscribed(user.id)
    
    if not subscribed:
        data = await config_col.find_one({"id": "force_join"})
        channels = data["channels"] if data else []
        btns = [[InlineKeyboardButton("📢 Join Now 🔞", url=f"https://t.me/{ch.replace('@','')}")] for ch in channels]
        btns.append([InlineKeyboardButton("✅ Verify & Start 💋", callback_data="verify")])
        
        return await message.reply_text(
            f"👋 **Hey Shona {user.mention}!!** 💋\n\n"
            "🔞 **Secret Gallery**-te dhukte niche deya channel join koro shona!", 
            reply_markup=InlineKeyboardMarkup(btns)
        )

    folders = await folders_col.find().to_list(100)
    if not folders:
        return await message.reply_text(f"🔥 **Hey {user.first_name}!**\n\n😔 *Admin ekhono kono folder upload koreni!*")
    
    btn = [[InlineKeyboardButton(f"📁 {f['name']} (Click koro) 🔥", callback_data=f"open_{f['name']}_0")] for f in folders]
    await message.reply_text(
        f"🌟 **Hello Jan {user.first_name}!** 🌟\n\n"
        "📸 **Nicher folder theke gorom collection browse koro:** 👇",
        reply_markup=InlineKeyboardMarkup(btn)
    )

@bot.on_callback_query(filters.regex("verify"))
async def verify_cb(client, cb: CallbackQuery):
    if await is_subscribed(cb.from_user.id):
        await cb.answer("✅ Verified Success! Enjoy koro shona. 💋", show_alert=True)
        await start(client, cb.message)
        await cb.message.delete()
    else:
        await cb.answer("❌ Uff! Age join koro tarpore verify click koro! 🔞", show_alert=True)

# --- PHOTO VIEWER (NEXT/PREV) ---
@bot.on_callback_query(filters.regex(r"^open_(.*)_(.*)"))
async def view_photos(client, cb: CallbackQuery):
    _, f_name, idx = cb.data.split("_")
    idx = int(idx)
    folder = await folders_col.find_one({"name": f_name})
    photos = folder["photos"]
    total = len(photos)
    
    btns = []
    nav = []
    if idx > 0: nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"open_{f_name}_{idx-1}"))
    if idx < total - 1: nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"open_{f_name}_{idx+1}"))
    
    if nav: btns.append(nav)
    btns.append([InlineKeyboardButton("🏠 Main Menu 🔥", callback_data="home")])
    
    try:
        await cb.message.edit_media(
            media=InputMediaPhoto(photos[idx], caption=f"📁 **Folder:** {f_name}\n🖼 **Photo:** {idx+1}/{total}"), 
            reply_markup=InlineKeyboardMarkup(btns)
        )
    except:
        await cb.message.reply_photo(
            photo=photos[idx],
            caption=f"📁 **Folder:** {f_name}\n🖼 **Photo:** {idx+1}/{total}",
            reply_markup=InlineKeyboardMarkup(btns)
        )
        await cb.message.delete()

@bot.on_callback_query(filters.regex("home"))
async def home_cb(client, cb: CallbackQuery):
    await start(client, cb.message)
    await cb.message.delete()

# --- ADMIN PANEL ---
@bot.on_message(filters.command("add_folder") & filters.user(ADMIN_ID))
async def add_folder(c, m):
    try:
        name = m.text.split(" ", 1)[1]
        await folders_col.insert_one({"name": name, "photos": []})
        await m.reply(f"✅ Folder '**{name}**' ready! 🔞")
    except: await m.reply("Usage: `/add_folder Name`")

@bot.on_message(filters.command("add_photos") & filters.user(ADMIN_ID))
async def add_photos(c, m):
    try:
        parts = m.text.split()
        f_name = parts[1]
        links = parts[2:]
        await folders_col.update_one({"name": f_name}, {"$push": {"photos": {"$each": links}}})
        await m.reply(f"✅ Photo add hoyeche! 🔥")
    except: await m.reply("Usage: `/add_photos FolderName Link1 Link2`")

@bot.on_message(filters.command("add_force") & filters.user(ADMIN_ID))
async def add_force(c, m):
    try:
        ch = m.text.split(" ", 1)[1]
        await config_col.update_one({"id": "force_join"}, {"$addToSet": {"channels": ch}}, upsert=True)
        await m.reply(f"✅ Channel {ch} Force Join-e add hoyeche! 🛡️")
    except: await m.reply("Usage: `/add_force @channel`")

if __name__ == "__main__":
    keep_alive()
    print("Bot is Starting... Hot Mode On! 🔥")
    bot.run()
