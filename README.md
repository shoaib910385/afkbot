# AFK Bot

A simple Telegram bot to manage AFK (Away From Keyboard) statuses for users in any chat.

## Features
- Set yourself as AFK with a reason using `/afk [reason]` or `brb [reason]`
- Automatically removes AFK status when you send a message
- Notifies others when they mention or reply to an AFK user
- Admins can toggle special AFK mode for users(afk wont break if chat starts with !) with `/safk` (by replying to their message)
- `/help` command shows available commands

## Setup
1. Clone the repo:
   - `git clone https://github.com/not-ayan/afkbot afkbot && cd afkbot`
2. Install dependencies:
   - `pip install telethon python-dotenv`
3. Setup the env:
   - `mv sample.env .env`
4. Update the `.env` file with your Telegram API credentials and admin user IDs:
   ```env
   API_ID=your_api_id
   API_HASH=your_api_hash
   BOT_TOKEN=your_bot_token
   ADMINS=123456789,987654321
   ```
5. Add AFK reasons to `funny_afk_reasons.txt` (one per line).
6. Run the bot:
   ```sh
   python afk.py
   ```

## Usage
- `/afk [reason]` — Set yourself as AFK
- `brb [reason]` — Set yourself as AFK
- `/safk` — Admins only, reply to a user to toggle their special AFK mode
- `/help` — Show help message

The bot works in any chat it is added to.
