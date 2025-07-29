import logging
from telethon import TelegramClient, events
import asyncio
import time
import random
import sqlite3
import os
from dotenv import load_dotenv

# Read AFK reasons from text file
def load_afk_reasons(filepath):
    with open(filepath, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
funny_afk_reasons = load_afk_reasons("funny_afk_reasons.txt")

# Load environment variables from .env
load_dotenv()
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
admins = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
chat_ids = [int(x) for x in os.getenv("CHAT_IDS", "").split(",") if x.strip()]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("afk_bot.log"),
        logging.StreamHandler()
    ]
)

# Initialize the Telegram client
client = TelegramClient('afk_bot', api_id, api_hash).start(bot_token=bot_token)

# Database setup
conn = sqlite3.connect('afk_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Create tables for AFK statuses and special AFK users
cursor.execute('''
CREATE TABLE IF NOT EXISTS afk_users (
    user_id INTEGER PRIMARY KEY,
    timestamp INTEGER,
    reason TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS special_afk_users (
    user_id INTEGER PRIMARY KEY
)
''')
conn.commit()

# Utility functions for database operations
def format_duration(seconds):
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_parts = []
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0 or not time_parts:
        time_parts.append(f"{seconds}s")
    return " ".join(time_parts)

def set_afk(user_id, reason):
    timestamp = int(time.time())
    cursor.execute("REPLACE INTO afk_users (user_id, timestamp, reason) VALUES (?, ?, ?)", (user_id, timestamp, reason))
    conn.commit()

def remove_afk(user_id):
    cursor.execute("DELETE FROM afk_users WHERE user_id = ?", (user_id,))
    conn.commit()

def get_afk(user_id):
    cursor.execute("SELECT timestamp, reason FROM afk_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def is_special_afk(user_id):
    cursor.execute("SELECT 1 FROM special_afk_users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

def toggle_special_afk(user_id):
    cursor.execute("SELECT 1 FROM special_afk_users WHERE user_id = ?", (user_id,))
    if cursor.fetchone():
        cursor.execute("DELETE FROM special_afk_users WHERE user_id = ?", (user_id,))
        conn.commit()
        return False
    else:
        cursor.execute("INSERT INTO special_afk_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return True

@client.on(events.NewMessage())
async def handle_message(event):
    try:
        sender = await event.get_sender()
        sender_id = sender.id
        sender_name = sender.first_name
        message_text = event.raw_text.strip()

        # Ignore messages from bots
        if sender.bot:
            return

        # Simple help command
        if message_text.lower() == "/help":
            help_text = (
                "AFK Bot Commands:\n"
                "/afk [reason] - Set yourself as AFK with an optional reason.\n"
                "brb [reason] - Set yourself as AFK with an optional reason.\n"
                "/safk (admin, reply) - Toggle special AFK mode for a user.\n"
                "/help - Show this help message."
            )
            await event.reply(help_text)
            return
        # Fetch all AFK users
        afk_users = {row[0]: {"time": row[1], "reason": row[2]} for row in cursor.execute("SELECT user_id, timestamp, reason FROM afk_users").fetchall()}

        # Handle /safk command (admin-only)
        if message_text.lower() == "/safk" and sender_id in admins and event.is_reply:
            replied_msg = await event.get_reply_message()
            target_id = replied_msg.sender_id
            if toggle_special_afk(target_id):
                await event.reply(f"User {replied_msg.sender.first_name} now has special AFK mode.")
            else:
                await event.reply(f"User {replied_msg.sender.first_name} no longer has special AFK mode.")
            return

        # Handle AFK and BRB commands
        if message_text.lower().startswith(("/afk", "brb")):
            reason = message_text.split(" ", 1)[1] if " " in message_text else random.choice(funny_afk_reasons)
            set_afk(sender_id, reason)
            await event.reply(f"{sender_name} is AFK\nReason: {reason}\nSince: Just now ??")
            return

        # Check if the sender is AFK and sends a message
        if sender_id in afk_users and not (is_special_afk(sender_id) and message_text.startswith("!")):
            afk_info = afk_users[sender_id]
            duration = format_duration(int(time.time()) - afk_info["time"])
            remove_afk(sender_id)
            await event.reply(f"{sender_name} is now online\nWas AFK for {duration}")
            return

        # Check if this message mentions or replies to any AFK users
        mentioned_afk_users = set()

        if event.is_reply:
            replied_msg = await event.get_reply_message()
            if replied_msg.sender_id in afk_users:
                mentioned_afk_users.add(replied_msg.sender_id)

        for entity in event.message.entities or []:
            if entity.__class__.__name__ == "MessageEntityMentionName" and entity.user_id in afk_users:
                mentioned_afk_users.add(entity.user_id)

        for afk_id in afk_users:
            afk_user = await client.get_entity(afk_id)
            if afk_user.username and f"@{afk_user.username}".lower() in message_text.lower():
                mentioned_afk_users.add(afk_id)

        if mentioned_afk_users:
            afk_messages = []
            for afk_user_id in mentioned_afk_users:
                afk_info = afk_users[afk_user_id]
                afk_user = await client.get_entity(afk_user_id)
                duration = format_duration(int(time.time()) - afk_info["time"])
                reason = afk_info["reason"]
                afk_messages.append(f"{afk_user.first_name} is AFK\nReason: {reason}\nSince: {duration} ??")

            await event.reply("\n\n".join(afk_messages))

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        print(f"Error: {e}")

# Start the client
logging.info("Bot is running...")
client.run_until_disconnected()