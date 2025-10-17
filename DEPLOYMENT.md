# SysAlert Deployment Guide

Simple guide to get SysAlert running - a Telegram monitoring bot with encryption.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 minutes)](#quick-start-5-minutes)
3. [Production with Docker](#production-with-docker)
4. [Configuration](#configuration)
5. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python**: 3.11 or higher
- **Docker** (optional, for production)
- **Internet**: For Telegram API access
- **Free space**: 1GB minimum

### Get Telegram Bot Credentials

1. Open Telegram → Message `@BotFather`
2. Send `/newbot` → Follow prompts → Save your **bot token**
3. Message `@userinfobot` → Save your **user ID** (for admin access)

---

## Quick Start (5 minutes)

```bash
# 1. Clone and setup
git clone https://github.com/yourusername/SysAlert.git
cd SysAlert

# 2. Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# 3. Setup configuration
cp .env.example .env

# 4. Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 5. Edit .env with your values:
# - TELEGRAM_TOKEN (from @BotFather)
# - MASTER_KEY (from command above)
# - ADMIN_USER_IDS (your Telegram user ID)
nano .env

# 6. Initialize database
mkdir -p data
python3 -c "from db import DB; import os; from dotenv import load_dotenv; load_dotenv(); DB(os.getenv('DB_URL', 'sqlite:///./data/bot.db'), os.getenv('MASTER_KEY'))"

# 7. Run the bot
python3 bot.py
```

**Test it**: Send `/start` to your bot on Telegram!

---

## Production with Docker

### Setup

```bash
# Install Docker (if not already installed)
sudo apt update && sudo apt install docker.io docker-compose

# Setup configuration
cp .env.example .env

# Generate encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit .env with your values
nano .env

# Secure permissions
chmod 600 .env
mkdir -p data && chmod 700 data
```

### Run

```bash
# Build and start
docker-compose build
docker-compose up -d

# Check logs
docker-compose logs -f bot

# Stop
docker-compose down
```

---

## Configuration

### Required Settings (in `.env`)

```bash
TELEGRAM_TOKEN=your_bot_token
MASTER_KEY=your_encryption_key
ADMIN_USER_IDS=your_telegram_id
```

### Optional Settings

```bash
# Monitoring
MAX_CONCURRENT_CHECKS=50
MIN_INTERVAL_SECONDS=20
DEFAULT_INTERVAL_SECONDS=60
CONNECTION_TIMEOUT=10
FAILURE_THRESHOLD=3

# Database (default is fine)
DB_URL=sqlite:///./data/bot.db

# Logging
LOG_LEVEL=INFO
```

See `.env.example` for all available options.

---

## Troubleshooting

### Bot doesn't start

```bash
# Check if dependencies are installed
pip install -r requirements.txt

# Verify Python version (must be 3.11+)
python3 --version

# Check for errors in logs
python3 bot.py  # Run in foreground to see errors
```

### "TELEGRAM_TOKEN is required"

```bash
# Verify .env file exists
cat .env

# Make sure you have a valid token from @BotFather
```

### "MASTER_KEY is required"

```bash
# Generate a new key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add it to .env
echo "MASTER_KEY=YOUR_KEY_HERE" >> .env
```

### "Database is locked"

```bash
# Check if another instance is running
ps aux | grep bot.py

# Kill any running instances
pkill -f bot.py

# Start again
python3 bot.py
```

### Bot doesn't respond on Telegram

```bash
# Check if bot is running
ps aux | grep bot.py

# Verify token is correct
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Restart the bot
pkill -f bot.py
python3 bot.py
```

### Docker container keeps restarting

```bash
# Check container logs
docker-compose logs bot

# Stop and check .env
docker-compose down
cat .env  # Verify all required variables

# Try running again
docker-compose up -d
```

---

## Getting Help

1. **Check the logs** first
2. **Verify all required environment variables** are set in `.env`
3. **Test your Telegram token**: `curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe`
4. **Check internet connectivity**: `ping api.telegram.org`

For more information, see `README.md` and `SECURITY.md`.
