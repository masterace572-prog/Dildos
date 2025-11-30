# GitHub UDP Bot

Deploy directly on GitHub and control via Telegram!

## Setup Instructions:

1. **Create GitHub Secrets:**
   - `BOT_TOKEN`: Your Telegram bot token from @BotFather
   - `NGROK_AUTH`: Your ngrok auth token from https://dashboard.ngrok.com/

2. **Update AUTHORIZED_USERS:**
   - In `bot_server.py`, replace `[123456789]` with your Telegram user ID
   - Get your ID from @userinfobot on Telegram

3. **Start the Bot:**
   - Go to Actions → "Telegram Bot Server" → Run workflow
   - The bot will start and show the public URL

## Usage:
- `/start` - Show help
- `/attack IP PORT TIME THREADS` - Start attack
- `/stop` - Stop attack
- `/status` - Check status
- `/stats` - Show statistics

## Features:
- 🚀 Runs directly on GitHub Actions
- 📱 Controlled via Telegram
- ⚡ Multi-threaded UDP floods
- 📊 Real-time statistics
- 🔒 User authorization
