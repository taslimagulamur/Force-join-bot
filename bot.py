import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
import json
import os

# ================= CONFIG =================
BOT_TOKEN = "8589887674:AAGZLYVrvpsv8PiH3MMpmApFlUI3YzPtBF4"  # আপনার Bot Token
ADMINS = [8231476408]  # আপনার Telegram ID
DATA_FILE = "data.json"

# Welcome Media
WELCOME_PHOTO_URL = "https://i.ibb.co/your-image.jpg"  # আপনার welcome photo / GIF / video
WELCOME_SOUND_URL = "https://www.example.com/welcome.mp3"  # Optional welcome sound

# Admin Message for Verified Users
ADMIN_VERIFIED_MSG = "🎉✅ আপনি সব চ্যানেল join করেছেন। এখন বট ব্যবহার করতে পারবেন! ❤️"

# Inline Buttons for welcome (Multiple links)
WELCOME_BUTTONS = [
    {"text": "📢 Join Our Channel", "url": "https://t.me/YourChannel"},
    {"text": "🌐 Visit Website", "url": "https://example.com"},
    {"text": "📜 Rules", "url": "https://t.me/YourRulesChannel"}
]
# =========================================

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- Data Load / Save ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"channels": [], "force": True, "users": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ---------- Helpers ----------
def is_admin(uid):
    return uid in ADMINS

def check_join(uid):
    """Check if user joined all channels"""
    if not data["force"]:
        return True
    for ch in data["channels"]:
        try:
            member = bot.get_chat_member(ch, uid)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ---------- Start / Welcome ----------
@bot.message_handler(commands=["start"])
def start(message):
    uid = message.from_user.id
    chat_id = message.chat.id

    # Save user
    if uid not in data["users"]:
        data["users"].append(uid)
        save_data(data)

    # Inline Buttons (2 row)
    markup = InlineKeyboardMarkup(row_width=1)
    for btn in WELCOME_BUTTONS:
        markup.add(InlineKeyboardButton(btn["text"], url=btn["url"]))

    # Force Join check
    if check_join(uid):
        bot.send_message(chat_id, ADMIN_VERIFIED_MSG, reply_markup=markup)
    else:
        welcome_text = (
            "💖✨ স্বাগতম প্রিয় বন্ধু! ✨💖\n\n"
            "🌟 আমি তোমাকে আমাদের প্রিমিয়াম বটের জগতে স্বাগত জানাচ্ছি! 🌟\n"
            "🥰 Force Join সব চ্যানেল করতে হবে, তারপর বট ব্যবহার করতে পারবেন! 😎🎉\n\n"
            "✅ নিচের বাটন ক্লিক করে চ্যানেল Join & Verify করুন 🚀"
        )
        bot.send_photo(chat_id, WELCOME_PHOTO_URL, caption=welcome_text, reply_markup=markup)
        # Optional Welcome Sound
        # bot.send_audio(chat_id, WELCOME_SOUND_URL)

# ---------- Admin Panel ----------
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("➕ Add Channel", "➖ Remove Channel")
    kb.row("✅ Force ON", "❌ Force OFF")
    kb.row("📣 Broadcast", "👥 Total Users")
    kb.row("📄 Channel List", "✏️ Set Admin Verified Message")
    bot.send_message(message.chat.id, "👑 Admin Panel Opened", reply_markup=kb)

# ---------- Admin Buttons ----------
@bot.message_handler(func=lambda m: m.text == "➕ Add Channel")
def add_channel(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id, "Channel username / ID দিন (@ সহ বা -1001234567890 for private):")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):
    ch = message.text.strip()
    if ch not in data["channels"]:
        data["channels"].append(ch)
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Added: {ch}")

@bot.message_handler(func=lambda m: m.text == "➖ Remove Channel")
def remove_channel(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id, "Remove করতে channel username / ID দিন:")
    bot.register_next_step_handler(msg, del_channel)

def del_channel(message):
    ch = message.text.strip()
    if ch in data["channels"]:
        data["channels"].remove(ch)
        save_data(data)
        bot.send_message(message.chat.id, f"❌ Removed: {ch}")

@bot.message_handler(func=lambda m: m.text == "✅ Force ON")
def force_on(message):
    if not is_admin(message.from_user.id):
        return
    data["force"] = True
    save_data(data)
    bot.send_message(message.chat.id, "✅ Force Join ENABLED")

@bot.message_handler(func=lambda m: m.text == "❌ Force OFF")
def force_off(message):
    if not is_admin(message.from_user.id):
        return
    data["force"] = False
    save_data(data)
    bot.send_message(message.chat.id, "❌ Force Join DISABLED")

@bot.message_handler(func=lambda m: m.text == "👥 Total Users")
def total_users(message):
    if not is_admin(message.from_user.id):
        return
    bot.send_message(message.chat.id, f"👥 Total Users: {len(data['users'])}")

@bot.message_handler(func=lambda m: m.text == "📄 Channel List")
def channel_list(message):
    if not is_admin(message.from_user.id):
        return
    if not data["channels"]:
        bot.send_message(message.chat.id, "No channels added.")
    else:
        bot.send_message(message.chat.id, "📄 Channels:\n" + "\n".join(data["channels"]))

@bot.message_handler(func=lambda m: m.text == "✏️ Set Admin Verified Message")
def set_verified_message(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id, "Send new Verified Message (with emojis, text, etc.):")
    bot.register_next_step_handler(msg, save_verified_message)

def save_verified_message(message):
    global ADMIN_VERIFIED_MSG
    ADMIN_VERIFIED_MSG = message.text
    bot.send_message(message.chat.id, f"✅ Admin Verified Message Updated!")

@bot.message_handler(func=lambda m: m.text == "📣 Broadcast")
def broadcast(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id, "Broadcast message লিখুন:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    count = 0
    for uid in data["users"]:
        try:
            bot.send_message(uid, message.text)
            count += 1
        except:
            pass
    bot.send_message(message.chat.id, f"✅ Sent to {count} users")

# ---------- Run Bot ----------
bot.infinity_polling()
