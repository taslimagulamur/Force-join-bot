"""
================================================================================
MOTHER BOT - FULL ADMIN CONTROL MULTI-BOT SYSTEM
VERSION: v2.0 (Enterprise Edition)
AUTHOR: AI DEVELOPER
================================================================================
"""

import os
import sys
import json
import sqlite3
import logging
import threading
import asyncio
import datetime
import hashlib
import secrets
import time
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
import psutil

# Telegram imports
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, InputMediaVideo, BotCommand,
    Message, User, Chat
)
from telegram.constants import ParseMode
from telegram.helpers import mention_html
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler,
    filters, ApplicationBuilder, CallbackContext,
    CallbackContext
)

# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================

class Config:
    # Bot Configuration
    MOTHER_BOT_TOKEN = "7959770637:AAE9lr18A3J5JoC-Cwxuv-0mXH6dUB9jy60"
    ADMIN_IDS = {8013042180}
    DB_NAME = "mother_bot.db"
    BACKUP_DIR = "backups"
    LOG_FILE = "mother_bot.log"
    
    # System Constants
    DEFAULT_AUTO_DELETE = 45
    MAX_MESSAGE_LENGTH = 4000
    FLOOD_LIMIT = 3
    SESSION_TIMEOUT = 300
    PAGINATION_LIMIT = 6
    
    # Conversation States
    STATE_WELCOME_MSG = 1
    STATE_WELCOME_PHOTO = 2
    STATE_CHANNEL_ADD = 3
    STATE_CHANNEL_EDIT = 4
    STATE_VIDEO_ADD = 5
    STATE_VIDEO_EDIT = 6
    STATE_PHOTO_ADD = 7
    STATE_PHOTO_EDIT = 8
    STATE_POST_TITLE = 9
    STATE_POST_PHOTO = 10
    STATE_POST_BUTTON = 11
    STATE_POST_CHANNELS = 12
    STATE_POST_CONFIRM = 13
    STATE_BOT_ADD = 14
    STATE_BROADCAST = 15
    STATE_USER_MANAGE = 16
    
    # Emojis for Hot Bangla Style
    EMOJIS = {
        "heart": "💖",
        "flower": "🌸",
        "fire": "🔥",
        "sparkle": "✨",
        "video": "🎬",
        "photo": "🖼️",
        "love": "💌",
        "star": "💫",
        "lock": "🔒",
        "unlock": "🔓",
        "check": "✅",
        "cross": "❌",
        "warning": "⚠️",
        "home": "🏠",
        "refresh": "🔄",
        "next": "⏭️",
        "prev": "⏮️",
        "play": "▶️",
        "like": "💖",
        "share": "💌",
        "eye": "👁️",
        "gear": "⚙️",
        "users": "👥",
        "crown": "👑",
        "chart": "📊",
        "back": "🔙",
        "trash": "🗑️",
        "plus": "➕",
        "minus": "➖",
        "edit": "✏️",
        "camera": "📸",
        "tv": "📺",
        "bell": "🔔"
    }

# ==============================================================================
# 📝 ADVANCED LOGGING
# ==============================================================================

class BotLogger:
    def __init__(self):
        self.logger = logging.getLogger("MotherBot")
        self.setup_logging()
        
    def setup_logging(self):
        # Create handlers
        console_handler = logging.StreamHandler(sys.stdout)
        file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # Set formatters
        console_handler.setFormatter(simple_formatter)
        file_handler.setFormatter(detailed_formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.setLevel(logging.INFO)
        
        self.logger.info("=" * 60)
        self.logger.info("MOTHER BOT v2.0 STARTING...")
        self.logger.info("=" * 60)
    
    def get_logger(self):
        return self.logger

logger = BotLogger().get_logger()

# ==============================================================================
# 🗄️ DATABASE MANAGER
# ==============================================================================

class DatabaseManager:
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.db_path = Config.DB_NAME
        self.backup_dir = Config.BACKUP_DIR
        self.setup_directories()
        self.connection_pool = {}
        self.init_database()
        self._initialized = True
        
    def setup_directories(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        
    def get_connection(self, thread_id=None):
        if thread_id is None:
            thread_id = threading.get_ident()
            
        with self._lock:
            if thread_id not in self.connection_pool:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30
                )
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA foreign_keys=ON")
                self.connection_pool[thread_id] = conn
                
            return self.connection_pool[thread_id]
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_blocked BOOLEAN DEFAULT 0,
                joined_channels TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            )
        ''')
        
        # Welcome messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS welcome_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT NOT NULL,
                photo_url TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                display_order INTEGER DEFAULT 0
            )
        ''')
        
        # Force channels table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS force_channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT NOT NULL,
                channel_link TEXT NOT NULL,
                auto_join BOOLEAN DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Videos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                video_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnail_url TEXT,
                category TEXT,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0
            )
        ''')
        
        # Photos table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS photos (
                photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gallery_id TEXT,
                photo_url TEXT NOT NULL,
                caption TEXT,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Child bots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS child_bots (
                bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_token TEXT UNIQUE NOT NULL,
                bot_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME,
                total_users INTEGER DEFAULT 0
            )
        ''')
        
        # Multi-channel posts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_posts (
                post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                photo_url TEXT,
                button_text TEXT,
                button_link TEXT,
                channels TEXT,  -- JSON array of channel IDs
                scheduled_time DATETIME,
                is_posted BOOLEAN DEFAULT 0,
                posted_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User video history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_video_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                video_id INTEGER,
                watched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                liked BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (video_id) REFERENCES videos(video_id)
            )
        ''')
        
        # Admin logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(last_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_videos_order ON videos(display_order)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_photos_gallery ON photos(gallery_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_scheduled ON channel_posts(scheduled_time)')
        
        conn.commit()
        self.initialize_defaults()
        logger.info("Database initialized successfully")
    
    def initialize_defaults(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Add default welcome message if none exists
        cursor.execute("SELECT COUNT(*) FROM welcome_messages")
        if cursor.fetchone()[0] == 0:
            default_message = '''{heart}{flower} হ্যালো [User]! {flower}{heart}
{fire} স্বাগতম আমাদের {love} Exclusive Video & Photo Hub {love}-এ! {fire}
{sparkle} এখানে তুমি ভিডিও, ছবি এবং মজার কনটেন্ট দেখতে পারবে! {sparkle}
{warning} সব কনটেন্ট দেখতে **Force Channels join** করতে হবে! {star}{star}'''
            
            cursor.execute(
                "INSERT INTO welcome_messages (message_text, display_order) VALUES (?, ?)",
                (default_message, 1)
            )
        
        conn.commit()
    
    # ===== USER MANAGEMENT =====
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                last_active = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name, last_name))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False
    
    def get_user(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        columns = [desc[0] for desc in cursor.description]
        row = cursor.fetchone()
        
        if row:
            user_dict = dict(zip(columns, row))
            # Parse joined_channels JSON
            if user_dict.get('joined_channels'):
                user_dict['joined_channels'] = json.loads(user_dict['joined_channels'])
            else:
                user_dict['joined_channels'] = []
            return user_dict
        return None
    
    def update_user_channels(self, user_id: int, channel_id: str, joined: bool):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT joined_channels FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            
            if result:
                channels = json.loads(result[0]) if result[0] else []
                
                if joined and channel_id not in channels:
                    channels.append(channel_id)
                elif not joined and channel_id in channels:
                    channels.remove(channel_id)
                
                cursor.execute(
                    "UPDATE users SET joined_channels = ? WHERE user_id = ?",
                    (json.dumps(channels), user_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating user channels: {e}")
        
        return False
    
    def get_all_users(self, active_only: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT user_id, first_name, username, join_date 
                FROM users WHERE is_blocked = 0 
                ORDER BY last_active DESC
            ''')
        else:
            cursor.execute("SELECT user_id, first_name, username, join_date FROM users")
        
        return [{
            'user_id': row[0],
            'first_name': row[1],
            'username': row[2],
            'join_date': row[3]
        } for row in cursor.fetchall()]
    
    def block_user(self, user_id: int, admin_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
            
            cursor.execute(
                "INSERT INTO admin_logs (admin_id, action, details) VALUES (?, ?, ?)",
                (admin_id, 'block_user', f'Blocked user {user_id}')
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error blocking user: {e}")
            return False
    
    def unblock_user(self, user_id: int, admin_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
            
            cursor.execute(
                "INSERT INTO admin_logs (admin_id, action, details) VALUES (?, ?, ?)",
                (admin_id, 'unblock_user', f'Unblocked user {user_id}')
            )
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error unblocking user: {e}")
            return False
    
    # ===== WELCOME MESSAGES =====
    def add_welcome_message(self, message_text: str, photo_url: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO welcome_messages (message_text, photo_url)
                VALUES (?, ?)
            ''', (message_text, photo_url))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding welcome message: {e}")
            return None
    
    def get_welcome_messages(self, active_only: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT message_id, message_text, photo_url, display_order
                FROM welcome_messages 
                WHERE is_active = 1
                ORDER BY display_order, created_at
            ''')
        else:
            cursor.execute('''
                SELECT message_id, message_text, photo_url, display_order, is_active
                FROM welcome_messages 
                ORDER BY display_order, created_at
            ''')
        
        return [{
            'message_id': row[0],
            'message_text': row[1],
            'photo_url': row[2],
            'display_order': row[3],
            'is_active': row[4] if len(row) > 4 else True
        } for row in cursor.fetchall()]
    
    def get_random_welcome_message(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT message_text, photo_url 
            FROM welcome_messages 
            WHERE is_active = 1 
            ORDER BY RANDOM() 
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        if row:
            return {'message_text': row[0], 'photo_url': row[1]}
        return None
    
    def update_welcome_message(self, message_id: int, message_text: str = None, photo_url: str = None, is_active: bool = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            updates = []
            params = []
            
            if message_text is not None:
                updates.append("message_text = ?")
                params.append(message_text)
            
            if photo_url is not None:
                updates.append("photo_url = ?")
                params.append(photo_url)
            
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(is_active)
            
            if updates:
                params.append(message_id)
                query = f"UPDATE welcome_messages SET {', '.join(updates)} WHERE message_id = ?"
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating welcome message: {e}")
        
        return False
    
    def delete_welcome_message(self, message_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM welcome_messages WHERE message_id = ?", (message_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting welcome message: {e}")
            return False
    
    # ===== FORCE CHANNELS =====
    def add_force_channel(self, channel_id: str, channel_name: str, channel_link: str, auto_join: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO force_channels (channel_id, channel_name, channel_link, auto_join)
                VALUES (?, ?, ?, ?)
            ''', (channel_id, channel_name, channel_link, auto_join))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding force channel: {e}")
            return False
    
    def get_force_channels(self, active_only: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT channel_id, channel_name, channel_link, auto_join
                FROM force_channels 
                WHERE is_active = 1
                ORDER BY created_at
            ''')
        else:
            cursor.execute('SELECT channel_id, channel_name, channel_link, auto_join FROM force_channels')
        
        return [{
            'channel_id': row[0],
            'channel_name': row[1],
            'channel_link': row[2],
            'auto_join': bool(row[3])
        } for row in cursor.fetchall()]
    
    def update_force_channel(self, channel_id: str, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            updates = []
            params = []
            
            for key, value in kwargs.items():
                if key in ['channel_name', 'channel_link', 'auto_join', 'is_active']:
                    updates.append(f"{key} = ?")
                    params.append(value)
            
            if updates:
                params.append(channel_id)
                query = f"UPDATE force_channels SET {', '.join(updates)} WHERE channel_id = ?"
                cursor.execute(query, params)
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating force channel: {e}")
        
        return False
    
    def delete_force_channel(self, channel_id: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM force_channels WHERE channel_id = ?", (channel_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting force channel: {e}")
            return False
    
    # ===== VIDEO MANAGEMENT =====
    def add_video(self, title: str, url: str, thumbnail_url: str = None, category: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get max display order
            cursor.execute("SELECT COALESCE(MAX(display_order), 0) FROM videos")
            max_order = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO videos (title, url, thumbnail_url, category, display_order)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, url, thumbnail_url, category, max_order + 1))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding video: {e}")
            return None
    
    def get_videos(self, active_only: bool = True, limit: int = None, offset: int = 0):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT video_id, title, url, thumbnail_url, category, display_order, view_count, like_count
            FROM videos 
            WHERE is_active = 1 
            ORDER BY display_order, created_at
        ''' if active_only else '''
            SELECT video_id, title, url, thumbnail_url, category, display_order, view_count, like_count, is_active
            FROM videos 
            ORDER BY display_order, created_at
        '''
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query)
        
        videos = []
        for row in cursor.fetchall():
            video = {
                'video_id': row[0],
                'title': row[1],
                'url': row[2],
                'thumbnail_url': row[3],
                'category': row[4],
                'display_order': row[5],
                'view_count': row[6],
                'like_count': row[7]
            }
            if not active_only:
                video['is_active'] = row[8]
            videos.append(video)
        
        return videos
    
    def get_video_count(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM videos WHERE is_active = 1")
        return cursor.fetchone()[0]
    
    def get_video_by_id(self, video_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT video_id, title, url, thumbnail_url, category, view_count, like_count
            FROM videos WHERE video_id = ? AND is_active = 1
        ''', (video_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'video_id': row[0],
                'title': row[1],
                'url': row[2],
                'thumbnail_url': row[3],
                'category': row[4],
                'view_count': row[5],
                'like_count': row[6]
            }
        return None
    
    def increment_video_view(self, video_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE videos SET view_count = view_count + 1 WHERE video_id = ?", (video_id,))
            conn.commit()
            return True
        except:
            return False
    
    def increment_video_like(self, video_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE videos SET like_count = like_count + 1 WHERE video_id = ?", (video_id,))
            conn.commit()
            return True
        except:
            return False
    
    # ===== PHOTO MANAGEMENT =====
    def add_photo(self, photo_url: str, gallery_id: str = None, caption: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get max display order for gallery
            cursor.execute(
                "SELECT COALESCE(MAX(display_order), 0) FROM photos WHERE gallery_id = ?",
                (gallery_id or 'default',)
            )
            max_order = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO photos (gallery_id, photo_url, caption, display_order)
                VALUES (?, ?, ?, ?)
            ''', (gallery_id or 'default', photo_url, caption, max_order + 1))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding photo: {e}")
            return None
    
    def get_photos(self, gallery_id: str = None, limit: int = None, offset: int = 0):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT photo_id, photo_url, caption, display_order
            FROM photos 
            WHERE is_active = 1 
        '''
        
        params = []
        if gallery_id:
            query += " AND gallery_id = ?"
            params.append(gallery_id)
        
        query += " ORDER BY display_order, created_at"
        
        if limit:
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query, params)
        
        return [{
            'photo_id': row[0],
            'photo_url': row[1],
            'caption': row[2],
            'display_order': row[3]
        } for row in cursor.fetchall()]
    
    def get_photo_count(self, gallery_id: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM photos WHERE is_active = 1"
        params = []
        
        if gallery_id:
            query += " AND gallery_id = ?"
            params.append(gallery_id)
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]
    
    # ===== CHILD BOTS =====
    def add_child_bot(self, bot_token: str, bot_name: str = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO child_bots (bot_token, bot_name)
                VALUES (?, ?)
            ''', (bot_token, bot_name))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding child bot: {e}")
            return None
    
    def get_child_bots(self, active_only: bool = True):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT bot_id, bot_token, bot_name, is_active, last_active, total_users
                FROM child_bots 
                WHERE is_active = 1
                ORDER BY created_at
            ''')
        else:
            cursor.execute('''
                SELECT bot_id, bot_token, bot_name, is_active, last_active, total_users
                FROM child_bots 
                ORDER BY created_at
            ''')
        
        return [{
            'bot_id': row[0],
            'bot_token': row[1],
            'bot_name': row[2],
            'is_active': bool(row[3]),
            'last_active': row[4],
            'total_users': row[5]
        } for row in cursor.fetchall()]
    
    # ===== CHANNEL POSTS =====
    def add_channel_post(self, title: str, photo_url: str = None, button_text: str = None, 
                        button_link: str = None, channels: List[str] = None, scheduled_time: datetime = None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            channels_json = json.dumps(channels) if channels else '[]'
            
            cursor.execute('''
                INSERT INTO channel_posts (title, photo_url, button_text, button_link, channels, scheduled_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (title, photo_url, button_text, button_link, channels_json, scheduled_time))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding channel post: {e}")
            return None
    
    # ===== STATISTICS =====
    def get_statistics(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # User stats
        cursor.execute("SELECT COUNT(*) FROM users")
        stats['total_users'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE('now')")
        stats['today_users'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 1")
        stats['blocked_users'] = cursor.fetchone()[0]
        
        # Content stats
        cursor.execute("SELECT COUNT(*) FROM welcome_messages WHERE is_active = 1")
        stats['welcome_messages'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM force_channels WHERE is_active = 1")
        stats['force_channels'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM videos WHERE is_active = 1")
        stats['videos'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM photos WHERE is_active = 1")
        stats['photos'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM child_bots WHERE is_active = 1")
        stats['child_bots'] = cursor.fetchone()[0]
        
        # Video view stats
        cursor.execute("SELECT SUM(view_count) FROM videos")
        stats['total_views'] = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(like_count) FROM videos")
        stats['total_likes'] = cursor.fetchone()[0] or 0
        
        return stats

db = DatabaseManager()

# ==============================================================================
# 🎨 UI MANAGER WITH HOT BANGLA STYLE
# ==============================================================================

class UIManager:
    """Hot Bangla Style UI Manager"""
    
    @staticmethod
    def format_message(text: str, user: User = None, **kwargs) -> str:
        """Format message with emojis and user info"""
        # Replace emoji placeholders
        for key, emoji in Config.EMOJIS.items():
            text = text.replace(f"{{{key}}}", emoji)
        
        # Replace [User] placeholder
        if user:
            user_name = user.first_name or "প্রিয়"
            text = text.replace("[User]", user_name)
        
        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        text += f"\n\n⏰ {timestamp}"
        
        return text
    
    @staticmethod
    def create_keyboard(buttons: List[List[Dict]], add_back: bool = False, add_home: bool = False) -> InlineKeyboardMarkup:
        """Create inline keyboard with 2 buttons per row"""
        keyboard = []
        
        for row in buttons:
            if len(row) > 2:
                # Split into multiple rows of 2 buttons each
                for i in range(0, len(row), 2):
                    row_buttons = []
                    for btn in row[i:i+2]:
                        button_text = UIManager.format_message(btn.get('text', ''))
                        row_buttons.append(
                            InlineKeyboardButton(
                                text=button_text,
                                callback_data=btn.get('callback', ''),
                                url=btn.get('url', None)
                            )
                        )
                    if row_buttons:
                        keyboard.append(row_buttons)
            else:
                row_buttons = []
                for btn in row:
                    button_text = UIManager.format_message(btn.get('text', ''))
                    row_buttons.append(
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=btn.get('callback', ''),
                            url=btn.get('url', None)
                        )
                    )
                if row_buttons:
                    keyboard.append(row_buttons)
        
        # Add navigation buttons
        nav_buttons = []
        if add_back:
            nav_buttons.append(InlineKeyboardButton("🔙 Back", callback_data="back"))
        if add_home:
            nav_buttons.append(InlineKeyboardButton("🏠 Home", callback_data="home"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_welcome_keyboard(missing_channels: List[Dict] = None) -> InlineKeyboardMarkup:
        """Get welcome message keyboard"""
        if missing_channels:
            # Show join buttons for missing channels
            buttons = []
            for i in range(0, len(missing_channels), 2):
                row = []
                for channel in missing_channels[i:i+2]:
                    row.append({
                        "text": f"💌 {channel['channel_name']}",
                        "url": channel['channel_link']
                    })
                if row:
                    buttons.append(row)
            
            buttons.append([
                {"text": "🔄 Verify Joined", "callback": "verify_joined"},
                {"text": "🏠 Home", "callback": "home"}
            ])
        else:
            # All channels joined, show content buttons
            buttons = [
                [
                    {"text": "🎬 Video Section", "callback": "video_section"},
                    {"text": "🖼️ Photo Section", "callback": "photo_section"}
                ],
                [
                    {"text": "⚙️ Settings", "callback": "settings"},
                    {"text": "ℹ️ Help", "callback": "help"}
                ]
            ]
        
        return UIManager.create_keyboard(buttons)
    
    @staticmethod
    def get_admin_main_menu() -> InlineKeyboardMarkup:
        """Get admin main menu"""
        buttons = [
            [
                {"text": "💌 Welcome Messages", "callback": "admin_welcome"},
                {"text": "🔗 Force Channels", "callback": "admin_channels"}
            ],
            [
                {"text": "🎬 Video Management", "callback": "admin_videos"},
                {"text": "🖼️ Photo Management", "callback": "admin_photos"}
            ],
            [
                {"text": "📢 Multi-Channel Post", "callback": "admin_post"},
                {"text": "🤖 Child Bots", "callback": "admin_bots"}
            ],
            [
                {"text": "👥 User Management", "callback": "admin_users"},
                {"text": "📊 Statistics", "callback": "admin_stats"}
            ],
            [
                {"text": "⚙️ System Settings", "callback": "admin_system"},
                {"text": "❌ Close", "callback": "close"}
            ]
        ]
        
        return UIManager.create_keyboard(buttons)
    
    @staticmethod
    def get_video_list_keyboard(videos: List[Dict], page: int = 0) -> InlineKeyboardMarkup:
        """Get video list keyboard with pagination"""
        total_videos = len(videos)
        start_idx = page * Config.PAGINATION_LIMIT
        end_idx = start_idx + Config.PAGINATION_LIMIT
        
        buttons = []
        for video in videos[start_idx:end_idx]:
            buttons.append([
                {"text": f"🎥 {video['title'][:20]}", "callback": f"video_{video['video_id']}"}
            ])
        
        # Pagination buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append({"text": "⏮️ Previous", "callback": f"video_page_{page-1}"})
        
        if end_idx < total_videos:
            nav_buttons.append({"text": "⏭️ Next", "callback": f"video_page_{page+1}"})
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([
            {"text": "🏠 Home", "callback": "home"},
            {"text": "🔄 Refresh", "callback": "video_section"}
        ])
        
        return UIManager.create_keyboard(buttons)
    
    @staticmethod
    def get_video_player_keyboard(video_id: int, total_videos: int, current_index: int) -> InlineKeyboardMarkup:
        """Get video player control buttons"""
        buttons = [
            [
                {"text": "▶️ Watch Video", "callback": f"watch_{video_id}"},
                {"text": "💖 Like", "callback": f"like_{video_id}"}
            ],
            [
                {"text": "💌 Share", "callback": f"share_{video_id}"}
            ]
        ]
        
        # Navigation buttons if there are multiple videos
        if total_videos > 1:
            nav_buttons = []
            if current_index > 0:
                nav_buttons.append({"text": "⏮️ Previous", "callback": f"prev_video_{current_index-1}"})
            if current_index < total_videos - 1:
                nav_buttons.append({"text": "⏭️ Next", "callback": f"next_video_{current_index+1}"})
            
            if nav_buttons:
                buttons.insert(1, nav_buttons)
        
        buttons.append([
            {"text": "🏠 Home", "callback": "home"},
            {"text": "🎬 Videos", "callback": "video_section"}
        ])
        
        return UIManager.create_keyboard(buttons)

ui = UIManager()

# ==============================================================================
# 🔐 SECURITY & VERIFICATION MANAGER
# ==============================================================================

class SecurityManager:
    """Handles channel verification and security"""
    
    def __init__(self):
        self.verification_cache = {}
        self.flood_control = {}
    
    async def check_user_membership(self, user_id: int, bot) -> List[Dict]:
        """Check if user has joined all force channels"""
        cache_key = f"membership_{user_id}"
        
        # Check cache first (5 minute cache)
        if cache_key in self.verification_cache:
            cached_time, result = self.verification_cache[cache_key]
            if time.time() - cached_time < 300:
                return result
        
        missing_channels = []
        force_channels = db.get_force_channels()
        
        for channel in force_channels:
            try:
                member = await bot.get_chat_member(
                    chat_id=channel['channel_id'],
                    user_id=user_id
                )
                
                if member.status in ['left', 'kicked', 'banned']:
                    missing_channels.append(channel)
            except Exception as e:
                logger.warning(f"Failed to check channel {channel['channel_id']}: {e}")
                missing_channels.append(channel)
        
        # Update cache
        self.verification_cache[cache_key] = (time.time(), missing_channels)
        
        return missing_channels
    
    def check_flood(self, user_id: int) -> bool:
        """Check if user is flooding"""
        current_time = time.time()
        
        if user_id not in self.flood_control:
            self.flood_control[user_id] = {
                'count': 1,
                'first_time': current_time
            }
            return False
        
        user_data = self.flood_control[user_id]
        
        # Reset if more than 60 seconds passed
        if current_time - user_data['first_time'] > 60:
            user_data['count'] = 1
            user_data['first_time'] = current_time
            return False
        
        user_data['count'] += 1
        
        # Check flood limit
        if user_data['count'] > Config.FLOOD_LIMIT * 60:  # messages per minute
            return True
        
        return False
    
    def clear_user_cache(self, user_id: int):
        """Clear verification cache for user"""
        cache_key = f"membership_{user_id}"
        if cache_key in self.verification_cache:
            del self.verification_cache[cache_key]

security = SecurityManager()

# ==============================================================================
# 🎮 USER PANEL HANDLERS
# ==============================================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Hot Bangla Welcome"""
    user = update.effective_user
    
    # Add user to database
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name or ""
    )
    
    # Check if user is blocked
    user_data = db.get_user(user.id)
    if user_data and user_data.get('is_blocked'):
        await update.message.reply_text(
            "🚫 আপনার অ্যাক্সেস ব্লক করা হয়েছে। অ্যাডমিনের সাথে যোগাযোগ করুন।",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Check flood control
    if security.check_flood(user.id):
        await update.message.reply_text(
            "⚠️ আপনি খুব দ্রুত মেসেজ পাঠাচ্ছেন। দয়া করে কিছুক্ষণ অপেক্ষা করুন।",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Get random welcome message
    welcome_data = db.get_random_welcome_message()
    if not welcome_data:
        welcome_text = f"""💖🌸 হ্যালো {user.first_name}! 🌸💖
🔥 স্বাগতম আমাদের 💌 Exclusive Video & Photo Hub 💌-এ! 🔥
✨ এখানে তুমি ভিডিও, ছবি এবং মজার কনটেন্ট দেখতে পারবে! ✨
⚠️ সব কনটেন্ট দেখতে **Force Channels join** করতে হবে! 💎💫"""
    else:
        welcome_text = ui.format_message(welcome_data['message_text'], user)
    
    # Check channel membership
    missing_channels = await security.check_user_membership(user.id, context.bot)
    
    keyboard = ui.get_welcome_keyboard(missing_channels)
    
    # Send welcome message with photo if available
    if welcome_data and welcome_data.get('photo_url'):
        try:
            await update.message.reply_photo(
                photo=welcome_data['photo_url'],
                caption=welcome_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except:
            await update.message.reply_text(
                welcome_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    else:
        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    data = query.data
    
    # Update user activity
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name or ""
    )
    
    # ===== USER PANEL CALLBACKS =====
    if data == "verify_joined":
        # Clear cache and re-check
        security.clear_user_cache(user.id)
        missing_channels = await security.check_user_membership(user.id, context.bot)
        
        if missing_channels:
            # Show missing channels pop-up
            popup_text = f"""⚠️ হেই {user.first_name}! ⚠️
💔 তুমি সব Force Channels join করোনি!
❌ Missing Channels:"""
            
            for channel in missing_channels:
                popup_text += f"\n• {channel['channel_name']}"
            
            popup_text += "\n💌 Join করো সব Channel তারপর ভিডিও / ছবি দেখো! 💖💫"
            
            # Create buttons for missing channels
            buttons = []
            for i in range(0, len(missing_channels), 2):
                row = []
                for channel in missing_channels[i:i+2]:
                    row.append({
                        "text": f"✅ {channel['channel_name'][:15]}",
                        "url": channel['channel_link']
                    })
                if row:
                    buttons.append(row)
            
            buttons.append([
                {"text": "🔄 Verify Again", "callback": "verify_joined"},
                {"text": "🏠 Home", "callback": "home"}
            ])
            
            keyboard = ui.create_keyboard(buttons)
            
            await query.edit_message_caption(
                caption=popup_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        else:
            # All channels joined - unlock content
            welcome_text = f"""🎉 অভিনন্দন {user.first_name}! 🎉
✅ সব Force Channels join করা হয়েছে!
✨ এখন তুমি ভিডিও এবং ছবি সেকশনে প্রবেশ করতে পারবে! ✨"""
            
            keyboard = ui.get_welcome_keyboard()
            
            await query.edit_message_caption(
                caption=welcome_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    
    elif data == "home":
        # Go back to home/welcome
        welcome_data = db.get_random_welcome_message()
        if welcome_data:
            welcome_text = ui.format_message(welcome_data['message_text'], user)
        else:
            welcome_text = f"💖🌸 হ্যালো {user.first_name}! 🌸💖"
        
        missing_channels = await security.check_user_membership(user.id, context.bot)
        keyboard = ui.get_welcome_keyboard(missing_channels)
        
        try:
            await query.edit_message_caption(
                caption=welcome_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
        except:
            await query.edit_message_text(
                welcome_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    
    elif data == "video_section":
        # Check if all channels joined
        missing_channels = await security.check_user_membership(user.id, context.bot)
        if missing_channels:
            await query.answer("❌ সব চ্যানেল জয়েন করা হয়নি!", show_alert=True)
            return
        
        # Show video section
        videos = db.get_videos()
        
        if not videos:
            text = f"""🎬 ভিডিও সেকশন 🎬
{user.first_name}, এখনো কোন ভিডিও যোগ করা হয়নি!"""
            
            await query.edit_message_caption(
                caption=text,
                reply_markup=ui.create_keyboard([[
                    {"text": "🏠 Home", "callback": "home"}
                ]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        text = f"""🎬 ভিডিও Section খুলে গেছে! 🌟
{user.first_name}, এখানে সব ভিডিও দেখতে পারবে! ✨💖🔥"""
        
        keyboard = ui.get_video_list_keyboard(videos)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data.startswith("video_page_"):
        # Handle video pagination
        page = int(data.replace("video_page_", ""))
        videos = db.get_videos()
        
        text = f"""🎬 ভিডিও Section - Page {page+1} 🌟"""
        
        keyboard = ui.get_video_list_keyboard(videos, page)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data.startswith("video_"):
        # Show individual video
        video_id = int(data.replace("video_", ""))
        video = db.get_video_by_id(video_id)
        
        if not video:
            await query.answer("❌ ভিডিওটি পাওয়া যায়নি!", show_alert=True)
            return
        
        # Increment view count
        db.increment_video_view(video_id)
        
        # Get all videos for navigation
        all_videos = db.get_videos()
        current_index = next((i for i, v in enumerate(all_videos) if v['video_id'] == video_id), 0)
        
        text = f"""📽️ {video['title']}
🌟 Views: {video['view_count']} | Likes: {video['like_count']}
💫 Enjoy the video! ✨"""
        
        keyboard = ui.get_video_player_keyboard(video_id, len(all_videos), current_index)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data.startswith("watch_"):
        video_id = int(data.replace("watch_", ""))
        video = db.get_video_by_id(video_id)
        
        if video:
            await query.answer(f"🎬 ভিডিও লিঙ্ক: {video['url'][:50]}...", show_alert=True)
    
    elif data.startswith("like_"):
        video_id = int(data.replace("like_", ""))
        db.increment_video_like(video_id)
        await query.answer("💖 ভিডিওটি লাইক করা হয়েছে!", show_alert=True)
        
        # Refresh the video info
        video = db.get_video_by_id(video_id)
        all_videos = db.get_videos()
        current_index = next((i for i, v in enumerate(all_videos) if v['video_id'] == video_id), 0)
        
        text = f"""📽️ {video['title']}
🌟 Views: {video['view_count']} | Likes: {video['like_count']}
💫 Enjoy the video! ✨"""
        
        keyboard = ui.get_video_player_keyboard(video_id, len(all_videos), current_index)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data == "photo_section":
        # Check if all channels joined
        missing_channels = await security.check_user_membership(user.id, context.bot)
        if missing_channels:
            await query.answer("❌ সব চ্যানেল জয়েন করা হয়নি!", show_alert=True)
            return
        
        # Show photo section
        photos = db.get_photos()
        
        if not photos:
            text = f"""🖼️ ফটো সেকশন 🖼️
{user.first_name}, এখনো কোন ফটো যোগ করা হয়নি!"""
            
            await query.edit_message_caption(
                caption=text,
                reply_markup=ui.create_keyboard([[
                    {"text": "🏠 Home", "callback": "home"}
                ]]),
                parse_mode=ParseMode.HTML
            )
            return
        
        # Show first photo
        first_photo = photos[0]
        
        text = f"""🖼️ Photo Section খুলে গেছে! 🌹
{user.first_name}, এখানে সব ছবি দেখতে পারবে! 💖✨"""
        
        # Create photo navigation keyboard
        buttons = [
            [
                {"text": "🔍 View Fullscreen", "callback": f"photo_full_{first_photo['photo_id']}"}
            ],
            [
                {"text": "⏮️ Previous", "callback": "photo_prev_0"},
                {"text": "⏭️ Next", "callback": "photo_next_0"}
            ],
            [
                {"text": "💌 Share", "callback": f"photo_share_{first_photo['photo_id']}"},
                {"text": "🏠 Home", "callback": "home"}
            ]
        ]
        
        keyboard = ui.create_keyboard(buttons)
        
        try:
            await query.message.reply_photo(
                photo=first_photo['photo_url'],
                caption=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
            await query.delete_message()
        except:
            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML
            )
    
    # ===== ADMIN PANEL CALLBACKS =====
    elif data == "admin_panel":
        if user.id not in Config.ADMIN_IDS:
            await query.answer("🚫 Admin access only!", show_alert=True)
            return
        
        text = f"""👑 ADMIN PANEL 👑
{user.first_name}, আপনি এখন অ্যাডমিন প্যানেলে আছেন!"""
        
        keyboard = ui.get_admin_main_menu()
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data == "admin_welcome":
        if user.id not in Config.ADMIN_IDS:
            await query.answer("🚫 Admin access only!", show_alert=True)
            return
        
        welcome_messages = db.get_welcome_messages(active_only=False)
        
        text = f"""💌 Welcome Message Management
Total Messages: {len(welcome_messages)}"""
        
        buttons = []
        for msg in welcome_messages:
            status = "✅" if msg['is_active'] else "❌"
            buttons.append([
                {
                    "text": f"{status} Msg {msg['message_id']}",
                    "callback": f"welcome_edit_{msg['message_id']}"
                },
                {
                    "text": f"🗑️ Delete",
                    "callback": f"welcome_delete_{msg['message_id']}"
                }
            ])
        
        buttons.append([
            {"text": "➕ Add New", "callback": "welcome_add"},
            {"text": "🔙 Back", "callback": "admin_panel"}
        ])
        
        keyboard = ui.create_keyboard(buttons)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data == "admin_channels":
        if user.id not in Config.ADMIN_IDS:
            await query.answer("🚫 Admin access only!", show_alert=True)
            return
        
        channels = db.get_force_channels(active_only=False)
        
        text = f"""🔗 Force Channel Management
Total Channels: {len(channels)}"""
        
        buttons = []
        for channel in channels:
            auto_join = "✅" if channel['auto_join'] else "❌"
            buttons.append([
                {
                    "text": f"📢 {channel['channel_name'][:15]}",
                    "callback": f"channel_edit_{channel['channel_id']}"
                },
                {
                    "text": f"{auto_join} Auto",
                    "callback": f"channel_toggle_{channel['channel_id']}"
                }
            ])
        
        buttons.append([
            {"text": "➕ Add Channel", "callback": "channel_add"},
            {"text": "🔙 Back", "callback": "admin_panel"}
        ])
        
        keyboard = ui.create_keyboard(buttons)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data == "admin_videos":
        if user.id not in Config.ADMIN_IDS:
            await query.answer("🚫 Admin access only!", show_alert=True)
            return
        
        videos = db.get_videos(active_only=False)
        
        text = f"""🎬 Video Management
Total Videos: {len(videos)}
Total Views: {sum(v['view_count'] for v in videos)}
Total Likes: {sum(v['like_count'] for v in videos)}"""
        
        buttons = []
        for video in videos:
            status = "✅" if video.get('is_active', True) else "❌"
            buttons.append([
                {
                    "text": f"{status} {video['title'][:15]}",
                    "callback": f"video_edit_{video['video_id']}"
                },
                {
                    "text": f"👁️{video['view_count']}",
                    "callback": f"video_stats_{video['video_id']}"
                }
            ])
        
        buttons.append([
            {"text": "➕ Add Video", "callback": "video_add"},
            {"text": "🔙 Back", "callback": "admin_panel"}
        ])
        
        keyboard = ui.create_keyboard(buttons)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data == "admin_users":
        if user.id not in Config.ADMIN_IDS:
            await query.answer("🚫 Admin access only!", show_alert=True)
            return
        
        users = db.get_all_users()
        
        text = f"""👥 User Management
Total Users: {len(users)}"""
        
        # Show first 10 users with pagination
        page = context.user_data.get('user_page', 0)
        start_idx = page * 5
        end_idx = start_idx + 5
        
        for user_data in users[start_idx:end_idx]:
            text += f"\n👤 {user_data['first_name']} (@{user_data['username'] or 'N/A'})"
        
        buttons = []
        
        # Pagination buttons
        if page > 0:
            buttons.append([{"text": "⏮️ Previous", "callback": f"user_page_{page-1}"}])
        
        if end_idx < len(users):
            buttons.append([{"text": "⏭️ Next", "callback": f"user_page_{page+1}"}])
        
        buttons.append([
            {"text": "📊 Stats", "callback": "admin_stats"},
            {"text": "🔙 Back", "callback": "admin_panel"}
        ])
        
        keyboard = ui.create_keyboard(buttons)
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data == "admin_stats":
        if user.id not in Config.ADMIN_IDS:
            await query.answer("🚫 Admin access only!", show_alert=True)
            return
        
        stats = db.get_statistics()
        
        text = f"""📊 System Statistics

👥 Users:
• Total: {stats['total_users']}
• Today: {stats['today_users']}
• Blocked: {stats['blocked_users']}

📁 Content:
• Welcome Messages: {stats['welcome_messages']}
• Force Channels: {stats['force_channels']}
• Videos: {stats['videos']}
• Photos: {stats['photos']}
• Child Bots: {stats['child_bots']}

🎬 Video Stats:
• Total Views: {stats['total_views']}
• Total Likes: {stats['total_likes']}"""
        
        keyboard = ui.create_keyboard([[
            {"text": "🔄 Refresh", "callback": "admin_stats"},
            {"text": "🔙 Back", "callback": "admin_panel"}
        ]])
        
        await query.edit_message_caption(
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    elif data == "close":
        try:
            await query.delete_message()
        except:
            pass
    
    else:
        await query.answer("❌ Unknown action!")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user = update.effective_user
    
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("🚫 Admin access only!")
        return
    
    text = f"""👑 ADMIN PANEL 👑
{user.first_name}, আপনি এখন অ্যাডমিন প্যানেলে আছেন!"""
    
    keyboard = ui.get_admin_main_menu()
    
    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    user = update.effective_user
    
    if user.id not in Config.ADMIN_IDS:
        await update.message.reply_text("🚫 Admin access only!")
        return
    
    stats = db.get_statistics()
    
    text = f"""📊 Bot Statistics

👥 Users: {stats['total_users']}
🎬 Videos: {stats['videos']}
🖼️ Photos: {stats['photos']}
📺 Total Views: {stats['total_views']}
💖 Total Likes: {stats['total_likes']}"""
    
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML
    )

# ==============================================================================
# 🚀 APPLICATION SETUP
# ==============================================================================

def setup_application():
    """Setup the Telegram application"""
    
    # Create application
    application = ApplicationBuilder() \
        .token(Config.MOTHER_BOT_TOKEN) \
        .connection_pool_size(10) \
        .pool_timeout(30) \
        .build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    return application

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling update: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ একটি ত্রুটি ঘটেছে। দয়া করে পরে চেষ্টা করুন।",
                parse_mode=ParseMode.HTML
            )
    except:
        pass

async def set_bot_commands(application: Application):
    """Set bot commands"""
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("admin", "Admin panel"),
        BotCommand("stats", "View statistics")
    ]
    
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands set successfully")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

def main():
    """Main entry point"""
    logger.info("🚀 Starting Mother Bot v2.0...")
    logger.info("=" * 60)
    
    try:
        # Create and setup application
        application = setup_application()
        
        # Set bot commands
        asyncio.run(set_bot_commands(application))
        
        # Start polling
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
