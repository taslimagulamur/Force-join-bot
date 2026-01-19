#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔥 MOTHER BOT - Complete System in One File 🔥
Run: python mother_bot.py
For Termux: python mother_bot.py
"""

import asyncio
import logging
import aiosqlite
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

# ===== CONFIGURATION =====
MASTER_BOT_TOKEN = "8589887674:AAGZLYVrvpsv8PiH3MMpmApFlUI3YzPtBF4"  # Replace with your bot token
ADMIN_IDS = []  # Add admin user IDs like [8231476408, 987654321]

# EMOJIS
EMOJIS = {
    "heart": "💖", "flower": "🌸", "fire": "🔥", "sparkle": "✨",
    "video": "🎬", "photo": "🖼️", "envelope": "💌", "star": "💫",
    "warning": "⚠️", "check": "✅", "cross": "❌", "home": "🏠",
    "refresh": "🔄", "next": "⏭️", "previous": "⏮️", "watch": "▶️",
    "like": "💖", "share": "📤", "fullscreen": "🔍", "admin": "👑",
    "user": "👤", "bot": "🤖", "channel": "📢", "settings": "⚙️",
    "back": "🔙", "save": "💾", "delete": "🗑️", "edit": "✏️",
    "add": "➕", "list": "📋", "stats": "📊", "lock": "🔒",
    "unlock": "🔓", "camera": "📸", "play": "🎥", "send": "📨",
    "users": "👥", "broadcast": "📢", "database": "🗄️"
}

# Database path
DB_PATH = "mother_bot.db"

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS

# ===== DATABASE FUNCTIONS =====
async def init_db():
    """Initialize database"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Users table
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            is_blocked INTEGER DEFAULT 0,
            joined_channels TEXT DEFAULT '[]'
        )''')
        
        # Welcome messages
        await db.execute('''CREATE TABLE IF NOT EXISTS welcome_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_text TEXT,
            photo_url TEXT,
            order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Force channels
        await db.execute('''CREATE TABLE IF NOT EXISTS force_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE,
            channel_name TEXT,
            channel_link TEXT,
            is_required INTEGER DEFAULT 1,
            auto_join INTEGER DEFAULT 1,
            order_num INTEGER DEFAULT 0
        )''')
        
        # Videos
        await db.execute('''CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT,
            thumbnail_url TEXT,
            category TEXT,
            order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            likes INTEGER DEFAULT 0,
            views INTEGER DEFAULT 0
        )''')
        
        # Photos
        await db.execute('''CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_url TEXT,
            caption TEXT,
            gallery_id INTEGER DEFAULT 1,
            order_num INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Child bots
        await db.execute('''CREATE TABLE IF NOT EXISTS child_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_token TEXT UNIQUE,
            bot_name TEXT,
            bot_username TEXT,
            is_active INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_count INTEGER DEFAULT 0
        )''')
        
        # Posts for multi-channel
        await db.execute('''CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            photo_url TEXT,
            button_text TEXT,
            button_url TEXT,
            channels TEXT,
            scheduled_time TIMESTAMP,
            is_posted INTEGER DEFAULT 0,
            posted_at TIMESTAMP
        )''')
        
        # User video history
        await db.execute('''CREATE TABLE IF NOT EXISTS user_video_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            video_id INTEGER,
            watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            liked INTEGER DEFAULT 0,
            FOREIGN KEY (video_id) REFERENCES videos (id)
        )''')
        
        await db.commit()

async def get_user(user_id: int):
    """Get user from database"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
    return None

async def add_user(user_id: int, username: str, first_name: str):
    """Add new user to database"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, first_name, last_active) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, datetime.now())
        )
        await db.commit()

async def update_user_channels(user_id: int, channels: list):
    """Update user's joined channels"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET joined_channels = ? WHERE user_id = ?",
            (json.dumps(channels), user_id)
        )
        await db.commit()

async def get_welcome_messages():
    """Get all welcome messages"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM welcome_messages WHERE is_active = 1 ORDER BY order_num") as cursor:
            rows = await cursor.fetchall()
            if rows:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    return []

async def get_force_channels():
    """Get all force channels"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM force_channels ORDER BY order_num") as cursor:
            rows = await cursor.fetchall()
            if rows:
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
    return []

async def get_videos(page: int = 1, per_page: int = 6):
    """Get videos with pagination"""
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM videos WHERE is_active = 1 ORDER BY order_num LIMIT ? OFFSET ?",
            (per_page, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            if rows:
                columns = [description[0] for description in cursor.description]
                videos = [dict(zip(columns, row)) for row in rows]
            else:
                videos = []
        
        async with db.execute("SELECT COUNT(*) FROM videos WHERE is_active = 1") as cursor:
            total = (await cursor.fetchone())[0]
        
        return videos, total

async def get_photos(page: int = 1, per_page: int = 4):
    """Get photos with pagination"""
    offset = (page - 1) * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM photos WHERE is_active = 1 ORDER BY order_num LIMIT ? OFFSET ?",
            (per_page, offset)
        ) as cursor:
            rows = await cursor.fetchall()
            if rows:
                columns = [description[0] for description in cursor.description]
                photos = [dict(zip(columns, row)) for row in rows]
            else:
                photos = []
        
        async with db.execute("SELECT COUNT(*) FROM photos WHERE is_active = 1") as cursor:
            total = (await cursor.fetchone())[0]
        
        return photos, total

# ===== UTILITY FUNCTIONS =====
def create_keyboard(buttons: list, buttons_per_row: int = 2):
    """Create inline keyboard with specified buttons per row"""
    keyboard = []
    row = []
    for i, button in enumerate(buttons):
        row.append(button)
        if len(row) == buttons_per_row or i == len(buttons) - 1:
            keyboard.append(row)
            row = []
    return InlineKeyboardMarkup(keyboard)

def format_welcome_message(user_name: str):
    """Format welcome message with emojis"""
    return f"""{EMOJIS['heart']}{EMOJIS['flower']} হ্যালো {user_name}! {EMOJIS['flower']}{EMOJIS['heart']}

{EMOJIS['fire']} স্বাগতম আমাদের {EMOJIS['envelope']} Exclusive Video & Photo Hub {EMOJIS['envelope']}-এ! {EMOJIS['fire']}

{EMOJIS['sparkle']} এখানে তুমি ভিডিও, ছবি এবং মজার কনটেন্ট দেখতে পারবে! {EMOJIS['sparkle']}

{EMOJIS['warning']} সব কনটেন্ট দেখতে **Force Channels join** করতে হবে! {EMOJIS['star']}{EMOJIS['sparkle']}"""

async def check_user_joined_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Check if user has joined all force channels"""
    try:
        channels = await get_force_channels()
        required_channels = [c for c in channels if c.get('is_required', 1) == 1]
        
        user = await get_user(user_id)
        if user and user.get('joined_channels'):
            joined_channels = json.loads(user['joined_channels'])
        else:
            joined_channels = []
        
        missing_channels = []
        for channel in required_channels:
            channel_id = channel.get('channel_id', '')
            if channel_id not in joined_channels:
                try:
                    member = await context.bot.get_chat_member(channel_id, user_id)
                    if member.status not in ['left', 'kicked']:
                        joined_channels.append(channel_id)
                    else:
                        missing_channels.append(channel)
                except Exception as e:
                    logging.error(f"Error checking channel {channel_id}: {e}")
                    missing_channels.append(channel)
        
        # Update user's joined channels
        await update_user_channels(user_id, joined_channels)
        
        return missing_channels
    except Exception as e:
        logging.error(f"Error checking channels: {e}")
        return []

# ===== USER PANEL FUNCTIONS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    await add_user(user.id, user.username, user.first_name)
    
    # Welcome message
    welcome_msg = format_welcome_message(user.first_name)
    
    # Get welcome messages from DB
    welcome_messages = await get_welcome_messages()
    if welcome_messages:
        random_msg = welcome_messages[0]
        welcome_msg = random_msg['message_text'].replace("{user_name}", user.first_name)
    
    # Create buttons
    channels = await get_force_channels()
    buttons = []
    for channel in channels[:4]:
        channel_name = channel.get('channel_name', 'Channel')
        channel_link = channel.get('channel_link', '')
        channel_id = channel.get('channel_id', '')
        
        if not channel_link and channel_id:
            channel_link = f"https://t.me/{channel_id.replace('@', '')}"
        
        buttons.append(InlineKeyboardButton(
            f"{EMOJIS['envelope']} {channel_name}",
            url=channel_link
        ))
    
    # Add Verify button
    buttons.append(InlineKeyboardButton(
        f"{EMOJIS['refresh']} ভেরিফাই জয়েনড",
        callback_data="user_verify_joined"
    ))
    
    keyboard = create_keyboard(buttons)
    
    # Send message
    if welcome_messages and welcome_messages[0].get('photo_url'):
        try:
            await update.message.reply_photo(
                photo=welcome_messages[0]['photo_url'],
                caption=welcome_msg,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
            return
        except Exception as e:
            logging.error(f"Error sending photo: {e}")
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = f"""{EMOJIS['heart']} **Mother Bot Help** {EMOJIS['heart']}

{EMOJIS['check']} **বট ব্যবহার করার নিয়ম:**
1. /start - বট শুরু করুন
2. সব চ্যানেল জয়িন করুন
3. ভেরিফাই বাটনে ক্লিক করুন
4. ভিডিও/ফটো সেকশন আনলক হবে

{EMOJIS['warning']} **প্রয়োজনীয়:**
• সব Force Channel জয়িন করতে হবে
• ভিডিও দেখার জন্য ইন্টারনেট লাগবে

{EMOJIS['admin']} **এডমিন কমান্ড:**
• /admin - এডমিন প্যানেল

{EMOJIS['star']} **সাপোর্ট:** @YourSupportChannel"""
    
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def user_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user panel button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data == "user_verify_joined":
        # Check if user joined all channels
        missing_channels = await check_user_joined_channels(user_id, context)
        
        if missing_channels:
            # User hasn't joined all channels
            message = f"{EMOJIS['warning']} হেই {query.from_user.first_name}! {EMOJIS['warning']}\n\n"
            message += f"{EMOJIS['cross']} তুমি সব Force Channels join করোনি!\n\n"
            message += f"{EMOJIS['warning']} **Missing Channels:**\n"
            
            buttons = []
            for channel in missing_channels:
                channel_name = channel.get('channel_name', 'Unknown')
                message += f"• {channel_name}\n"
                
                channel_link = channel.get('channel_link', '')
                channel_id = channel.get('channel_id', '')
                if not channel_link and channel_id:
                    channel_link = f"https://t.me/{channel_id.replace('@', '')}"
                
                buttons.append(InlineKeyboardButton(
                    f"{EMOJIS['check']} জয়িন {channel_name}",
                    url=channel_link
                ))
            
            buttons.append(InlineKeyboardButton(
                f"{EMOJIS['refresh']} আবার চেক করুন",
                callback_data="user_verify_joined"
            ))
            buttons.append(InlineKeyboardButton(
                f"{EMOJIS['home']} হোম",
                callback_data="user_home"
            ))
            
            keyboard = create_keyboard(buttons)
            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # User joined all channels - Show main menu
            await show_main_menu(query)
    
    elif data == "user_home":
        await show_main_menu(query)
    
    elif data == "user_videos":
        await show_video_section(query, page=1)
    
    elif data == "user_photos":
        await show_photo_section(query, page=1)
    
    elif data.startswith("user_video_page_"):
        page = int(data.split("_")[-1])
        await show_video_section(query, page)
    
    elif data.startswith("user_photo_page_"):
        page = int(data.split("_")[-1])
        await show_photo_section(query, page)
    
    elif data.startswith("user_watch_video_"):
        video_id = int(data.split("_")[-1])
        await show_video_player(query, video_id)
    
    else:
        await query.answer("এই ফিচারটি শীঘ্রই আসছে!", show_alert=True)

async def show_main_menu(query):
    """Show main menu after verification"""
    menu_text = f"""{EMOJIS['star']}{EMOJIS['heart']} **মেনু সিলেক্ট করুন** {EMOJIS['heart']}{EMOJIS['star']}

{EMOJIS['check']} সব চ্যানেল সাকসেসফুলি জয়িন করা হয়েছে!

{EMOJIS['video']} **ভিডিও সেকশন:** এক্সক্লুসিভ ভিডিও কালেকশন
{EMOJIS['photo']} **ফটো সেকশন:** প্রিমিয়াম ফটো গ্যালারি

{EMOJIS['fire']} নির্বাচন করুন যা দেখতে চান:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['video']} ভিডিও সেকশন", callback_data="user_videos"),
        InlineKeyboardButton(f"{EMOJIS['photo']} ফটো সেকশন", callback_data="user_photos"),
        InlineKeyboardButton(f"{EMOJIS['refresh']} রিফ্রেশ", callback_data="user_verify_joined"),
        InlineKeyboardButton(f"{EMOJIS['home']} হোম", callback_data="user_home")
    ]
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        menu_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_video_section(query, page: int = 1):
    """Show video section"""
    videos, total = await get_videos(page)
    total_pages = max(1, (total + 5) // 6)
    
    if not videos:
        await query.edit_message_text(
            f"{EMOJIS['warning']} কোনো ভিডিও পাওয়া যায়নি! এডমিন ভিডিও যোগ করুন।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"{EMOJIS['home']} হোম", callback_data="user_home")
            ]])
        )
        return
    
    message = f"""{EMOJIS['video']} **ভিডিও সেকশন** {EMOJIS['video']}

{EMOJIS['sparkle']} পেজ {page}/{total_pages}
{EMOJIS['fire']} মোট ভিডিও: {total}

{EMOJIS['star']} নির্বাচন করুন:"""
    
    buttons = []
    for video in videos:
        title = video.get('title', 'No Title')
        short_title = title[:15] + "..." if len(title) > 15 else title
        buttons.append(InlineKeyboardButton(
            f"{EMOJIS['play']} {short_title}",
            callback_data=f"user_watch_video_{video['id']}"
        ))
    
    # Navigation buttons
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(
            f"{EMOJIS['previous']} আগের পেজ",
            callback_data=f"user_video_page_{page-1}"
        ))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton(
            f"{EMOJIS['next']} পরের পেজ",
            callback_data=f"user_video_page_{page+1}"
        ))
    
    if nav_buttons:
        buttons.extend(nav_buttons)
    
    buttons.append(InlineKeyboardButton(
        f"{EMOJIS['home']} হোম",
        callback_data="user_home"
    ))
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_video_player(query, video_id: int):
    """Show video player"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM videos WHERE id = ?", (video_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                video = dict(zip(columns, row))
            else:
                video = None
    
    if not video:
        await query.answer("ভিডিওটি পাওয়া যায়নি!", show_alert=True)
        return
    
    title = video.get('title', 'No Title')
    category = video.get('category', 'সাধারণ')
    likes = video.get('likes', 0)
    views = video.get('views', 0)
    url = video.get('url', '#')
    
    message = f"""{EMOJIS['video']} **{title}** {EMOJIS['video']}

{EMOJIS['star']} ক্যাটাগরি: {category}
{EMOJIS['like']} লাইক: {likes}
{EMOJIS['eye']} ভিউ: {views}

{EMOJIS['sparkle']} ভিডিওটি দেখতে নিচের বাটনে ক্লিক করুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['watch']} ওয়াচ ভিডিও", url=url),
        InlineKeyboardButton(f"{EMOJIS['like']} লাইক", callback_data=f"user_like_video_{video_id}"),
        InlineKeyboardButton(f"{EMOJIS['share']} শেয়ার", callback_data=f"user_share_video_{video_id}"),
        InlineKeyboardButton(f"{EMOJIS['previous']} আগের ভিডিও", callback_data=f"user_prev_video_{video_id}"),
        InlineKeyboardButton(f"{EMOJIS['next']} পরের ভিডিও", callback_data=f"user_next_video_{video_id}"),
        InlineKeyboardButton(f"{EMOJIS['video']} ভিডিও লিস্ট", callback_data="user_videos"),
        InlineKeyboardButton(f"{EMOJIS['home']} হোম", callback_data="user_home")
    ]
    
    keyboard = create_keyboard(buttons)
    
    thumbnail_url = video.get('thumbnail_url')
    if thumbnail_url:
        try:
            await query.edit_message_media(
                InputMediaPhoto(
                    media=thumbnail_url,
                    caption=message,
                    parse_mode=ParseMode.MARKDOWN
                ),
                reply_markup=keyboard
            )
            return
        except Exception as e:
            logging.error(f"Error setting photo: {e}")
    
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_photo_section(query, page: int = 1):
    """Show photo section"""
    photos, total = await get_photos(page)
    total_pages = max(1, (total + 3) // 4)
    
    if not photos:
        await query.edit_message_text(
            f"{EMOJIS['warning']} কোনো ফটো পাওয়া যায়নি! এডমিন ফটো যোগ করুন।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f"{EMOJIS['home']} হোম", callback_data="user_home")
            ]])
        )
        return
    
    # Show first photo of the page
    first_photo = photos[0]
    photo_url = first_photo.get('photo_url', '')
    caption = first_photo.get('caption', 'ফটো ভিউয়ার')
    
    message = f"""{EMOJIS['photo']} **ফটো গ্যালারি** {EMOJIS['photo']}

{EMOJIS['sparkle']} পেজ {page}/{total_pages}
{EMOJIS['camera']} মোট ফটো: {total}

{EMOJIS['star']} {caption}"""
    
    buttons = []
    
    # Navigation for current photo
    current_index = (page - 1) * 4
    if current_index > 0:
        buttons.append(InlineKeyboardButton(
            f"{EMOJIS['previous']} আগের ফটো",
            callback_data=f"user_view_photo_{photos[0]['id']-1}"
        ))
    
    if current_index + len(photos) < total:
        buttons.append(InlineKeyboardButton(
            f"{EMOJIS['next']} পরের ফটো",
            callback_data=f"user_view_photo_{photos[0]['id']+1}"
        ))
    
    # Page navigation
    if page > 1:
        buttons.append(InlineKeyboardButton(
            f"{EMOJIS['previous']} আগের পেজ",
            callback_data=f"user_photo_page_{page-1}"
        ))
    
    if page < total_pages:
        buttons.append(InlineKeyboardButton(
            f"{EMOJIS['next']} পরের পেজ",
            callback_data=f"user_photo_page_{page+1}"
        ))
    
    # Action buttons
    buttons.append(InlineKeyboardButton(
        f"{EMOJIS['fullscreen']} ফুলস্ক্রিন",
        callback_data=f"user_fullscreen_photo_{first_photo['id']}"
    ))
    buttons.append(InlineKeyboardButton(
        f"{EMOJIS['share']} শেয়ার",
        callback_data=f"user_share_photo_{first_photo['id']}"
    ))
    buttons.append(InlineKeyboardButton(
        f"{EMOJIS['photo']} ফটো লিস্ট",
        callback_data="user_photos"
    ))
    buttons.append(InlineKeyboardButton(
        f"{EMOJIS['home']} হোম",
        callback_data="user_home"
    ))
    
    keyboard = create_keyboard(buttons)
    
    try:
        await query.edit_message_media(
            InputMediaPhoto(
                media=photo_url,
                caption=message,
                parse_mode=ParseMode.MARKDOWN
            ),
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Error editing photo message: {e}")
        await query.edit_message_text(
            message,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

# ===== ADMIN PANEL FUNCTIONS =====
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text(
            f"{EMOJIS['warning']} আপনাকে অনুমতি নেই! {EMOJIS['warning']}"
        )
        return
    
    admin_text = f"""{EMOJIS['admin']} **এডমিন প্যানেল** {EMOJIS['admin']}

{EMOJIS['star']} হ্যালো {user.first_name}! 
{EMOJIS['sparkle']} Mother Bot এডমিন কন্ট্রোল সেন্টারে স্বাগতম!

{EMOJIS['settings']} **ম্যানেজমেন্ট অপশনস:**"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['envelope']} ওয়েলকাম মেসেজ", callback_data="admin_welcome"),
        InlineKeyboardButton(f"{EMOJIS['channel']} ফোর্স চ্যানেল", callback_data="admin_channels"),
        InlineKeyboardButton(f"{EMOJIS['video']} ভিডিও ম্যানেজ", callback_data="admin_videos"),
        InlineKeyboardButton(f"{EMOJIS['photo']} ফটো ম্যানেজ", callback_data="admin_photos"),
        InlineKeyboardButton(f"{EMOJIS['bot']} চাইল্ড বটস", callback_data="admin_child_bots"),
        InlineKeyboardButton(f"{EMOJIS['send']} মাল্টি পোস্ট", callback_data="admin_multi_post"),
        InlineKeyboardButton(f"{EMOJIS['users']} ইউজার ম্যানেজ", callback_data="admin_users"),
        InlineKeyboardButton(f"{EMOJIS['stats']} স্ট্যাটিসটিক্স", callback_data="admin_stats"),
        InlineKeyboardButton(f"{EMOJIS['database']} ব্যাকআপ", callback_data="admin_backup"),
        InlineKeyboardButton(f"{EMOJIS['home']} ইউজার ভিউ", callback_data="user_home")
    ]
    
    keyboard = create_keyboard(buttons, 2)
    
    await update.message.reply_text(
        admin_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text(
            f"{EMOJIS['warning']} অনুমতি নেই! {EMOJIS['warning']}"
        )
        return
    
    data = query.data
    
    if data == "admin_welcome":
        await show_welcome_management(query)
    
    elif data == "admin_channels":
        await show_channel_management(query)
    
    elif data == "admin_videos":
        await show_video_management(query)
    
    elif data == "admin_photos":
        await show_photo_management(query)
    
    elif data == "admin_child_bots":
        await show_child_bots_management(query)
    
    elif data == "admin_multi_post":
        await start_multi_post(query, context)
    
    elif data == "admin_users":
        await show_user_management(query)
    
    elif data == "admin_stats":
        await show_statistics(query)
    
    elif data == "admin_backup":
        await backup_database(query)
    
    elif data == "admin_back":
        await admin_panel_callback(query)
    
    else:
        await query.answer("এই ফিচারটি শীঘ্রই আসছে!", show_alert=True)

async def show_welcome_management(query):
    """Show welcome message management"""
    welcome_messages = await get_welcome_messages()
    
    message = f"""{EMOJIS['envelope']} **ওয়েলকাম মেসেজ ম্যানেজমেন্ট** {EMOJIS['envelope']}

{EMOJIS['list']} মোট ওয়েলকাম মেসেজ: {len(welcome_messages)}
{EMOJIS['star']} নির্বাচন করুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['add']} নতুন মেসেজ", callback_data="admin_add_welcome"),
        InlineKeyboardButton(f"{EMOJIS['edit']} এডিট মেসেজ", callback_data="admin_edit_welcome"),
        InlineKeyboardButton(f"{EMOJIS['delete']} ডিলিট মেসেজ", callback_data="admin_delete_welcome"),
        InlineKeyboardButton(f"{EMOJIS['list']} ভিউ মেসেজ", callback_data="admin_view_welcome"),
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_channel_management(query):
    """Show force channel management"""
    channels = await get_force_channels()
    
    message = f"""{EMOJIS['channel']} **ফোর্স চ্যানেল ম্যানেজমেন্ট** {EMOJIS['channel']}

{EMOJIS['list']} মোট চ্যানেল: {len(channels)}
{EMOJIS['star']} নির্বাচন করুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['add']} চ্যানেল যোগ", callback_data="admin_add_channel"),
        InlineKeyboardButton(f"{EMOJIS['edit']} চ্যানেল এডিট", callback_data="admin_edit_channel"),
        InlineKeyboardButton(f"{EMOJIS['delete']} চ্যানেল ডিলিট", callback_data="admin_delete_channel"),
        InlineKeyboardButton(f"{EMOJIS['list']} সব চ্যানেল", callback_data="admin_list_channels"),
        InlineKeyboardButton(f"{EMOJIS['users']} ইউজার স্ট্যাটাস", callback_data="admin_channel_stats"),
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_video_management(query):
    """Show video management"""
    videos, total = await get_videos(1, 100)
    
    message = f"""{EMOJIS['video']} **ভিডিও ম্যানেজমেন্ট** {EMOJIS['video']}

{EMOJIS['list']} মোট ভিডিও: {total}
{EMOJIS['star']} নির্বাচন করুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['add']} ভিডিও যোগ", callback_data="admin_add_video"),
        InlineKeyboardButton(f"{EMOJIS['edit']} ভিডিও এডিট", callback_data="admin_edit_video"),
        InlineKeyboardButton(f"{EMOJIS['delete']} ভিডিও ডিলিট", callback_data="admin_delete_video"),
        InlineKeyboardButton(f"{EMOJIS['list']} সব ভিডিও", callback_data="admin_list_videos"),
        InlineKeyboardButton(f"{EMOJIS['settings']} রিঅর্ডার", callback_data="admin_reorder_videos"),
        InlineKeyboardButton(f"{EMOJIS['stats']} ভিডিও স্ট্যাটস", callback_data="admin_video_stats"),
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_photo_management(query):
    """Show photo management"""
    photos, total = await get_photos(1, 100)
    
    message = f"""{EMOJIS['photo']} **ফটো ম্যানেজমেন্ট** {EMOJIS['photo']}

{EMOJIS['list']} মোট ফটো: {total}
{EMOJIS['star']} নির্বাচন করুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['add']} ফটো যোগ", callback_data="admin_add_photo"),
        InlineKeyboardButton(f"{EMOJIS['edit']} ফটো এডিট", callback_data="admin_edit_photo"),
        InlineKeyboardButton(f"{EMOJIS['delete']} ফটো ডিলিট", callback_data="admin_delete_photo"),
        InlineKeyboardButton(f"{EMOJIS['list']} সব ফটো", callback_data="admin_list_photos"),
        InlineKeyboardButton(f"{EMOJIS['settings']} গ্যালারি ম্যানেজ", callback_data="admin_manage_gallery"),
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_child_bots_management(query):
    """Show child bots management"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM child_bots") as cursor:
            total = (await cursor.fetchone())[0] or 0
        
        async with db.execute("SELECT COUNT(*) FROM child_bots WHERE is_active = 1") as cursor:
            active = (await cursor.fetchone())[0] or 0
    
    message = f"""{EMOJIS['bot']} **চাইল্ড বটস ম্যানেজমেন্ট** {EMOJIS['bot']}

{EMOJIS['list']} মোট বটস: {total}
{EMOJIS['check']} অ্যাক্টিভ বটস: {active}
{EMOJIS['cross']} ইনঅ্যাক্টিভ বটস: {total - active}

{EMOJIS['star']} নির্বাচন করুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['add']} বট যোগ", callback_data="admin_add_bot"),
        InlineKeyboardButton(f"{EMOJIS['edit']} বট এডিট", callback_data="admin_edit_bot"),
        InlineKeyboardButton(f"{EMOJIS['delete']} বট ডিলিট", callback_data="admin_delete_bot"),
        InlineKeyboardButton(f"{EMOJIS['list']} সব বটস", callback_data="admin_list_bots"),
        InlineKeyboardButton(f"{EMOJIS['broadcast']} ব্রডকাস্ট", callback_data="admin_broadcast"),
        InlineKeyboardButton(f"{EMOJIS['send']} ফরওয়ার্ড", callback_data="admin_forward"),
        InlineKeyboardButton(f"{EMOJIS['stats']} নেটওয়ার্ক স্ট্যাটস", callback_data="admin_network_stats"),
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def start_multi_post(query, context):
    """Start multi-channel post creation"""
    context.user_data['multi_post_step'] = 'title'
    
    message = f"""{EMOJIS['send']} **মাল্টি-চ্যানেল পোস্ট** {EMOJIS['send']}

{EMOJIS['star']} ধাপ ১/৫: পোস্ট টাইটেল দিন
{EMOJIS['sparkle']} একটি আকর্ষণীয় টাইটেল লিখুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['back']} ক্যান্সেল", callback_data="admin_back")
    ]
    
    keyboard = InlineKeyboardMarkup([buttons])
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_user_management(query):
    """Show user management"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total = (await cursor.fetchone())[0] or 0
        
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1") as cursor:
            blocked = (await cursor.fetchone())[0] or 0
    
    message = f"""{EMOJIS['users']} **ইউজার ম্যানেজমেন্ট** {EMOJIS['users']}

{EMOJIS['list']} মোট ইউজার: {total}
{EMOJIS['check']} অ্যাক্টিভ ইউজার: {total - blocked}
{EMOJIS['cross']} ব্লকড ইউজার: {blocked}

{EMOJIS['star']} নির্বাচন করুন:"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['list']} সব ইউজার", callback_data="admin_list_users"),
        InlineKeyboardButton(f"{EMOJIS['lock']} ইউজার ব্লক", callback_data="admin_block_user"),
        InlineKeyboardButton(f"{EMOJIS['unlock']} ইউজার আনব্লক", callback_data="admin_unblock_user"),
        InlineKeyboardButton(f"{EMOJIS['delete']} ইউজার ডিলিট", callback_data="admin_delete_user"),
        InlineKeyboardButton(f"{EMOJIS['stats']} ডিটেইলড স্ট্যাটস", callback_data="admin_user_stats"),
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = create_keyboard(buttons)
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def show_statistics(query):
    """Show bot statistics"""
    async with aiosqlite.connect(DB_PATH) as db:
        # User stats
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            total_users = (await cursor.fetchone())[0] or 0
        
        async with db.execute("SELECT COUNT(DISTINCT user_id) FROM user_video_history") as cursor:
            active_users = (await cursor.fetchone())[0] or 0
        
        # Video stats
        async with db.execute("SELECT COUNT(*) FROM videos") as cursor:
            total_videos = (await cursor.fetchone())[0] or 0
        
        async with db.execute("SELECT SUM(views) FROM videos") as cursor:
            total_views_result = await cursor.fetchone()
            total_views = total_views_result[0] if total_views_result and total_views_result[0] else 0
        
        # Photo stats
        async with db.execute("SELECT COUNT(*) FROM photos") as cursor:
            total_photos = (await cursor.fetchone())[0] or 0
        
        # Channel stats
        async with db.execute("SELECT COUNT(*) FROM force_channels") as cursor:
            total_channels = (await cursor.fetchone())[0] or 0
    
    avg_views = total_views // total_videos if total_videos > 0 else 0
    
    message = f"""{EMOJIS['stats']} **বট স্ট্যাটিসটিক্স** {EMOJIS['stats']}

{EMOJIS['users']} **ইউজার স্ট্যাটস:**
• মোট ইউজার: {total_users}
• অ্যাক্টিভ ইউজার: {active_users}
• ইনঅ্যাক্টিভ: {total_users - active_users}

{EMOJIS['video']} **ভিডিও স্ট্যাটস:**
• মোট ভিডিও: {total_videos}
• মোট ভিউ: {total_views}
• গড় ভিউ: {avg_views}

{EMOJIS['photo']} **ফটো স্ট্যাটস:**
• মোট ফটো: {total_photos}

{EMOJIS['channel']} **চ্যানেল স্ট্যাটস:**
• ফোর্স চ্যানেল: {total_channels}

{EMOJIS['star']} **সিস্টেম স্ট্যাটস:**
• ডেটাবেজ সাইজ: {os.path.getsize(DB_PATH) // 1024 if os.path.exists(DB_PATH) else 0} KB
• আপটাইম: সক্রিয়"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['refresh']} রিফ্রেশ", callback_data="admin_stats"),
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = InlineKeyboardMarkup([buttons])
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def backup_database(query):
    """Backup database"""
    import shutil
    from datetime import datetime
    
    backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    # Simple backup by copying file
    try:
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup_file)
            file_size = os.path.getsize(backup_file) // 1024
            success = True
        else:
            success = False
            file_size = 0
    except Exception as e:
        success = False
        file_size = 0
        logging.error(f"Backup error: {e}")
    
    if success:
        message = f"""{EMOJIS['database']} **ডেটাবেজ ব্যাকআপ** {EMOJIS['database']}

{EMOJIS['check']} ব্যাকআপ সফল!
{EMOJIS['star']} ফাইল: `{backup_file}`
{EMOJIS['sparkle']} সাইজ: {file_size} KB

{EMOJIS['warning']} ফাইলটি ডাউনলোড করে নিরাপদ স্থানে রাখুন।"""
    else:
        message = f"""{EMOJIS['warning']} **ব্যাকআপ ব্যর্থ!** {EMOJIS['warning']}

{EMOJIS['cross']} ডেটাবেজ ফাইল তৈরি হয়নি।
{EMOJIS['star']} প্রথমে বট চালু করুন এবং কিছু ইউজার যোগ করুন।"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['back']} ব্যাক", callback_data="admin_back")
    ]
    
    keyboard = InlineKeyboardMarkup([buttons])
    await query.edit_message_text(
        message,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_panel_callback(query):
    """Return to admin panel"""
    user = query.from_user
    
    admin_text = f"""{EMOJIS['admin']} **এডমিন প্যানেল** {EMOJIS['admin']}

{EMOJIS['star']} হ্যালো {user.first_name}! 
{EMOJIS['sparkle']} Mother Bot এডমিন কন্ট্রোল সেন্টারে স্বাগতম!"""
    
    buttons = [
        InlineKeyboardButton(f"{EMOJIS['envelope']} ওয়েলকাম মেসেজ", callback_data="admin_welcome"),
        InlineKeyboardButton(f"{EMOJIS['channel']} ফোর্স চ্যানেল", callback_data="admin_channels"),
        InlineKeyboardButton(f"{EMOJIS['video']} ভিডিও ম্যানেজ", callback_data="admin_videos"),
        InlineKeyboardButton(f"{EMOJIS['photo']} ফটো ম্যানেজ", callback_data="admin_photos"),
        InlineKeyboardButton(f"{EMOJIS['bot']} চাইল্ড বটস", callback_data="admin_child_bots"),
        InlineKeyboardButton(f"{EMOJIS['send']} মাল্টি পোস্ট", callback_data="admin_multi_post"),
        InlineKeyboardButton(f"{EMOJIS['users']} ইউজার ম্যানেজ", callback_data="admin_users"),
        InlineKeyboardButton(f"{EMOJIS['stats']} স্ট্যাটিসটিক্স", callback_data="admin_stats"),
        InlineKeyboardButton(f"{EMOJIS['database']} ব্যাকআপ", callback_data="admin_backup"),
        InlineKeyboardButton(f"{EMOJIS['home']} ইউজার ভিউ", callback_data="user_home")
    ]
    
    keyboard = create_keyboard(buttons, 2)
    await query.edit_message_text(
        admin_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin messages for multi-step processes"""
    user = update.effective_user
    if not is_admin(user.id):
        return
    
    if 'multi_post_step' in context.user_data:
        step = context.user_data['multi_post_step']
        
        if step == 'title':
            context.user_data['post_title'] = update.message.text
            context.user_data['multi_post_step'] = 'photo'
            
            await update.message.reply_text(
                f"{EMOJIS['star']} ধাপ ২/৫: এখন একটি ফটো পাঠান\n"
                f"{EMOJIS['sparkle']} PNG বা JPG ফরম্যাটে ফটো পাঠান:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"{EMOJIS['back']} ক্যান্সেল", callback_data="admin_back")
                ]])
            )
        
        elif step == 'photo':
            if update.message.photo:
                photo = update.message.photo[-1]
                context.user_data['post_photo'] = photo.file_id
                context.user_data['multi_post_step'] = 'button_text'
                
                await update.message.reply_text(
                    f"{EMOJIS['star']} ধাপ ৩/৫: বাটন টেক্সট দিন\n"
                    f"{EMOJIS['sparkle']} উদাহরণ: 'ডাউনলোড করুন' বা 'ভিজিট ওয়েবসাইট':",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"{EMOJIS['back']} ক্যান্সেল", callback_data="admin_back")
                    ]])
                )
            else:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} একটি ফটো পাঠান!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(f"{EMOJIS['back']} ক্যান্সেল", callback_data="admin_back")
                    ]])
                )

# ===== MAIN FUNCTION =====
async def main():
    """Main function to start the bot"""
    # Initialize database
    await init_db()
    
    # Create application
    application = Application.builder().token(MASTER_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Add callback query handlers
    application.add_handler(CallbackQueryHandler(user_button_handler, pattern="^user_"))
    application.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^admin_"))
    
    # Add message handler for admin
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_admin_message
    ))
    
    # Start the bot
    print(f"{EMOJIS['bot']} Mother Bot Starting...")
    print(f"{EMOJIS['star']} Bot Token: {MASTER_BOT_TOKEN[:10]}...")
    print(f"{EMOJIS['check']} Database initialized: {DB_PATH}")
    print(f"{EMOJIS['fire']} Admin IDs: {ADMIN_IDS}")
    
    # Run the bot
    await application.run_polling()

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Check for bot token
    if MASTER_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"{EMOJIS['warning']} Error: Please set your bot token in MASTER_BOT_TOKEN variable!")
        print(f"{EMOJIS['star']} Get token from @BotFather")
        print(f"{EMOJIS['check']} Edit line 15: MASTER_BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'")
        exit(1)
    
    if not ADMIN_IDS:
        print(f"{EMOJIS['warning']} Warning: ADMIN_IDS is empty! Add your user ID.")
        print(f"{EMOJIS['star']} Get your ID from @userinfobot")
        print(f"{EMOJIS['check']} Edit line 16: ADMIN_IDS = [123456789]  # Your user ID")
        print(f"{EMOJIS['warning']} Continuing without admin panel...")
    
    print(f"{EMOJIS['heart']} Mother Bot - Complete System")
    print(f"{EMOJIS['flower']} Running on Termux...")
    print(f"{EMOJIS['fire']} Press Ctrl+C to stop")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{EMOJIS['warning']} Bot stopped by user")
