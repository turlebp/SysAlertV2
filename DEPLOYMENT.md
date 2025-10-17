# SysAlert Deployment Guide

Complete step-by-step guide to deploy SysAlert - a privacy-hardened Telegram monitoring bot with encrypted storage.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Development Setup](#development-setup)
4. [Production Deployment](#production-deployment)
5. [Configuration Reference](#configuration-reference)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)
8. [Security Checklist](#security-checklist)
9. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows (WSL2)
- **Python**: 3.11 or higher
- **RAM**: Minimum 512MB, recommended 1GB+
- **Disk**: 1GB free space minimum
- **Network**: Internet access for Telegram API

### Required Tools

```bash
# Check Python version (must be 3.11+)
python3 --version

# Install pip if not present
sudo apt update
sudo apt install python3-pip python3-venv

# For production (Docker)
sudo apt install docker.io docker-compose

# Optional: git
sudo apt install git
```

### Telegram Setup

1. **Create a Telegram Bot**:
   ```
   1. Open Telegram and message @BotFather
   2. Send /newbot
   3. Follow prompts to choose name and username
   4. Save the bot token (looks like: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)
   ```

2. **Get Your Chat ID**:
   ```
   1. Message @userinfobot on Telegram
   2. Save your user ID (this will be your admin ID)
   ```

---

## Quick Start

For the impatient - get running in 5 minutes:

```bash
# 1. Clone repository
git clone https://github.com/yourusername/SysAlert.git
cd SysAlert

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env

# 5. Generate master encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 6. Edit .env with your credentials
nano .env
# Add: TELEGRAM_TOKEN, MASTER_KEY, ADMIN_USER_IDS

# 7. Initialize database
mkdir -p data
python3 -c "from db import DB; import os; from dotenv import load_dotenv; load_dotenv(); DB(os.getenv('DB_URL', 'sqlite:///./data/bot.db'), os.getenv('MASTER_KEY'))"

# 8. Run bot
python3 bot.py
```

**Test it**: Send `/start` to your bot on Telegram!

---

## Development Setup

### Step 1: Clone Repository

```bash
# Via HTTPS
git clone https://github.com/yourusername/SysAlert.git
cd SysAlert

# OR via SSH
git clone git@github.com:yourusername/SysAlert.git
cd SysAlert
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/macOS
# OR
.venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

**Expected packages**:
- python-telegram-bot >= 20.7
- aiohttp >= 3.9.0
- SQLAlchemy >= 2.0.0
- cryptography >= 41.0.0
- pytest >= 7.4.0

### Step 4: Configure Environment

```bash
# Copy template
cp .env.example .env

# Generate master encryption key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy the output (e.g., "qFqaPvj7C0EoeRsGMxWRx59UgOQO4IeR/abFQxY8XHI=")

# Edit configuration
nano .env  # or use your favorite editor
```

**Required settings in `.env`**:

```bash
# Telegram Configuration
TELEGRAM_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_USER_IDS=YOUR_TELEGRAM_USER_ID

# Encryption (use generated key above)
MASTER_KEY=YOUR_GENERATED_KEY_HERE

# Database (default is fine for development)
DB_URL=sqlite:///./data/bot.db
```

**Optional settings** (keep defaults for now):

```bash
# Monitoring
MAX_CONCURRENT_CHECKS=50
MIN_INTERVAL_SECONDS=20
DEFAULT_INTERVAL_SECONDS=60
CONNECTION_TIMEOUT=10
FAILURE_THRESHOLD=3

# Security
MAX_FAILED_ADMIN_ATTEMPTS=5
ADMIN_BAN_DURATION=3600

# Logging
LOG_LEVEL=INFO
```

### Step 5: Initialize Database

```bash
# Create data directory
mkdir -p data

# Initialize database with encryption
python3 -c "
from db import DB
import os
from dotenv import load_dotenv

load_dotenv()
db = DB(os.getenv('DB_URL', 'sqlite:///./data/bot.db'), os.getenv('MASTER_KEY'))
print('✅ Database initialized successfully!')
"
```

**Verify**:
```bash
ls -lh data/
# Should see: bot.db, bot.db-shm, bot.db-wal

sqlite3 data/bot.db ".tables"
# Should see: audit_logs, benchmark_targets, customers, history, subscriptions, targets
```

### Step 6: Run Tests

```bash
# Run all tests
make test

# OR manually
pytest -v

# Run specific test
pytest tests/test_crypto.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

**Expected output**: All tests should pass ✅

### Step 7: Run Bot (Development)

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run bot
python3 bot.py

# OR using make
make run
```

**Expected output**:
```
2025-01-15 10:30:00 - SysAlertBot - INFO - Starting SysAlert Monitor Bot v2.0
2025-01-15 10:30:00 - SysAlertBot.db - INFO - Database initialized: sqlite:///./data/bot.db
2025-01-15 10:30:01 - SysAlertBot - INFO - Bot initialized successfully
2025-01-15 10:30:01 - SysAlertBot - INFO - Bot polling started
```

### Step 8: Test Your Bot

1. **Open Telegram** and find your bot
2. **Send `/start`** - Should get welcome message
3. **Send `/whoami`** - Should show your info
4. **Add subscription** (as admin):
   ```
   /addsub YOUR_CHAT_ID
   ```
5. **Add a test target**:
   ```
   /addtarget test-server 8.8.8.8 53
   ```
6. **Check status**:
   ```
   /status
   ```

---

## Production Deployment

### Option 1: Docker (Recommended)

#### Step 1: Install Docker

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
# Log out and back in for this to take effect
```

#### Step 2: Configure Environment

```bash
# Copy template
cp .env.example .env

# Generate master key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Edit configuration
nano .env
```

**Production `.env` example**:

```bash
# Telegram
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_USER_IDS=123456789

# Encryption
MASTER_KEY=qFqaPvj7C0EoeRsGMxWRx59UgOQO4IeR/abFQxY8XHI=

# Database
DB_URL=sqlite:///./data/bot.db

# Monitoring (production values)
MAX_CONCURRENT_CHECKS=100
MIN_INTERVAL_SECONDS=60
DEFAULT_INTERVAL_SECONDS=300
CONNECTION_TIMEOUT=10
FAILURE_THRESHOLD=3

# Security (strict)
MAX_FAILED_ADMIN_ATTEMPTS=5
ADMIN_BAN_DURATION=3600

# Logging (less verbose in production)
LOG_LEVEL=WARNING

# Bot Branding
BOT_NAME=SysAlert
```

#### Step 3: Set File Permissions

```bash
# Secure the .env file
chmod 600 .env

# Create data directory with correct permissions
mkdir -p data
chmod 700 data
```

#### Step 4: Build Docker Image

```bash
# Build image
docker-compose build

# OR using make
make docker-build
```

**Verify**:
```bash
docker images | grep sysalert
# Should see: sysalert image
```

#### Step 5: Start Container

```bash
# Start in background
docker-compose up -d

# OR using make
make docker-run

# Check logs
docker-compose logs -f bot
```

**Expected output**:
```
bot_1  | 2025-01-15 10:30:00 - SysAlertBot - INFO - Starting SysAlert Monitor Bot v2.0
bot_1  | 2025-01-15 10:30:01 - SysAlertBot - INFO - Bot polling started
```

#### Step 6: Verify Container is Running

```bash
# Check status
docker-compose ps

# Should show:
# Name         State    Ports
# sysalert_bot_1   Up

# Check resource usage
docker stats sysalert_bot_1 --no-stream
```

#### Step 7: Test Production Bot

Same as development testing - send `/start` to your bot on Telegram.

### Option 2: Systemd Service (Alternative)

For running directly on the host (without Docker):

#### Step 1: Create Service File

```bash
sudo nano /etc/systemd/system/sysalert.service
```

**Content**:

```ini
[Unit]
Description=SysAlert Telegram Monitoring Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/path/to/SysAlert
Environment="PATH=/path/to/SysAlert/.venv/bin"
ExecStart=/path/to/SysAlert/.venv/bin/python3 /path/to/SysAlert/bot.py
Restart=always
RestartSec=10

# Security
PrivateTmp=yes
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
```

**Replace**:
- `YOUR_USERNAME` with your Linux username
- `/path/to/SysAlert` with actual path

#### Step 2: Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable sysalert

# Start service
sudo systemctl start sysalert

# Check status
sudo systemctl status sysalert

# View logs
sudo journalctl -u sysalert -f
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_TOKEN` | ✅ Yes | - | Bot token from @BotFather |
| `MASTER_KEY` | ✅ Yes | - | Base64 encryption key |
| `ADMIN_USER_IDS` | ✅ Yes | - | Comma-separated admin IDs |
| `DB_URL` | No | `sqlite:///./data/bot.db` | Database connection string |
| `MAX_CONCURRENT_CHECKS` | No | `50` | Max simultaneous TCP checks |
| `MIN_INTERVAL_SECONDS` | No | `20` | Minimum check interval |
| `DEFAULT_INTERVAL_SECONDS` | No | `60` | Default check interval |
| `CONNECTION_TIMEOUT` | No | `10` | TCP connection timeout (seconds) |
| `FAILURE_THRESHOLD` | No | `3` | Failures before alert |
| `MAX_TARGETS_PER_USER` | No | `10` | Max targets per user |
| `MAX_BENCH_TARGETS_PER_USER` | No | `5` | Max benchmark targets per user |
| `TELE_WORKERS` | No | `3` | Telegram queue workers |
| `PER_CHAT_RATE_SECONDS` | No | `1.0` | Message rate limit per chat |
| `MAX_FAILED_ADMIN_ATTEMPTS` | No | `5` | Failed admin attempts before ban |
| `ADMIN_BAN_DURATION` | No | `3600` | Ban duration in seconds |
| `CPU_BENCH_ENABLED` | No | `true` | Enable CPU benchmark monitoring |
| `CPU_BENCH_THRESHOLD_SECONDS` | No | `0.35` | Benchmark alert threshold |
| `CPU_BENCH_INTERVAL` | No | `300` | Benchmark check interval |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `BOT_NAME` | No | `SysAlert` | Bot branding name |

### Database Options

**SQLite (Default - Good for single instance)**:
```bash
DB_URL=sqlite:///./data/bot.db
```

**PostgreSQL (Recommended for production with multiple instances)**:
```bash
DB_URL=postgresql://username:password@localhost:5432/sysalert
```

---

## Testing

### Unit Tests

```bash
# All tests
make test

# Specific test file
pytest tests/test_crypto.py -v

# Specific test function
pytest tests/test_db.py::test_add_subscription -v

# With coverage
pytest --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Integration Tests

```bash
# Test bot commands manually
# 1. Start bot in one terminal
python3 bot.py

# 2. In Telegram, test:
/start
/whoami
/help
/addsub YOUR_CHAT_ID  # Admin only
/addtarget test 8.8.8.8 53
/status
/check test
```

### Load Testing

```bash
# Test with multiple targets
# Create 10 test targets
for i in {1..10}; do
  # In Telegram:
  /addtarget test$i 8.8.8.8 53
done

# Monitor logs
tail -f bot.log

# Check resource usage
top -p $(pgrep -f bot.py)
```

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'telegram'"

**Problem**: Dependencies not installed

**Solution**:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

#### 2. "TELEGRAM_TOKEN is required"

**Problem**: Missing or incorrect `.env` file

**Solution**:
```bash
# Check .env exists
ls -la .env

# Verify content
cat .env | grep TELEGRAM_TOKEN

# If missing, copy template
cp .env.example .env
nano .env
```

---

#### 3. "MASTER_KEY is required"

**Problem**: Encryption key not set

**Solution**:
```bash
# Generate new key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
echo "MASTER_KEY=YOUR_KEY_HERE" >> .env
```

---

#### 4. "Database is locked"

**Problem**: SQLite concurrent access issue

**Solution**:
```bash
# Check if multiple instances are running
ps aux | grep bot.py

# Kill duplicates
pkill -f bot.py

# Restart
python3 bot.py
```

---

#### 5. Bot doesn't respond on Telegram

**Problem**: Various causes

**Solution**:
```bash
# Check bot is running
ps aux | grep bot.py

# Check logs for errors
tail -100 bot.log

# Verify token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# Check network
ping api.telegram.org

# Restart bot
pkill -f bot.py
python3 bot.py
```

---

#### 6. Docker container keeps restarting

**Problem**: Configuration or runtime error

**Solution**:
```bash
# Check container logs
docker-compose logs bot

# Check specific error
docker-compose logs bot | grep ERROR

# Stop container
docker-compose down

# Fix issue in .env, then restart
docker-compose up -d
```

---

### Logs Location

| Deployment | Log Location |
|------------|--------------|
| Development | `./bot.log` |
| Docker | `docker-compose logs -f bot` |
| Systemd | `sudo journalctl -u sysalert -f` |

### Debug Mode

Enable detailed logging:

```bash
# In .env
LOG_LEVEL=DEBUG

# Restart bot
```

---

## Security Checklist

Before deploying to production, verify:

### Pre-Deployment

- [ ] Generated unique `MASTER_KEY` (not example value)
- [ ] Generated unique `TELEGRAM_TOKEN` from @BotFather
- [ ] Set correct `ADMIN_USER_IDS`
- [ ] `.env` file has correct permissions (`chmod 600 .env`)
- [ ] `.env` is NOT committed to git (`git check-ignore .env` shows it)
- [ ] Reviewed and adjusted rate limits
- [ ] Set `LOG_LEVEL=WARNING` for production
- [ ] Database directory has correct permissions (`chmod 700 data/`)

### Post-Deployment

- [ ] Bot responds to `/start` command
- [ ] Admin commands work (`/addsub`, `/stats`)
- [ ] Non-admin cannot access admin commands
- [ ] Monitoring targets work (`/addtarget`, `/status`)
- [ ] Logs don't contain plaintext sensitive data
- [ ] Backups are configured (see Maintenance section)
- [ ] Firewall rules are set (if applicable)

### Ongoing

- [ ] Review audit logs monthly (`SELECT * FROM audit_logs`)
- [ ] Rotate `MASTER_KEY` every 90 days (use `rotate_keys.py`)
- [ ] Update dependencies (`pip install --upgrade -r requirements.txt`)
- [ ] Monitor disk usage (`df -h data/`)
- [ ] Review failed admin attempts (`grep "failed_admin_attempt" bot.log`)

**For detailed security information**, see:
- `SECURITY_HARDENING.md` - Complete security guide
- `PRIVACY_LOGGING.md` - Privacy protection details
- `SECURITY_QUICK_REFERENCE.md` - Quick security commands

---

## Maintenance

### Backups

#### Manual Backup

```bash
# Backup with timestamp
tar czf backup_$(date +%Y%m%d_%H%M%S).tar.gz data/ .env

# Encrypted backup
tar czf - data/ .env | gpg -c > backup_$(date +%Y%m%d).tar.gz.gpg
```

#### Automated Backup (Cron)

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/SysAlert && tar czf backup_$(date +\%Y\%m\%d).tar.gz data/ .env && find . -name "backup_*.tar.gz" -mtime +7 -delete
```

#### Restore from Backup

```bash
# Stop bot
docker-compose down
# OR
pkill -f bot.py

# Extract backup
tar xzf backup_20250115.tar.gz

# Verify database
sqlite3 data/bot.db "PRAGMA integrity_check;"

# Start bot
docker-compose up -d
# OR
python3 bot.py
```

---

### Updates

#### Update Dependencies

```bash
# Activate virtual environment
source .venv/bin/activate

# Update all packages
pip install --upgrade -r requirements.txt

# Test after update
make test
```

#### Update Bot Code

```bash
# Stop bot
docker-compose down

# Pull latest code
git pull origin main

# Rebuild (if using Docker)
docker-compose build

# Run tests
make test

# Start bot
docker-compose up -d

# Monitor logs
docker-compose logs -f bot
```

---

### Key Rotation

Rotate encryption keys every 90 days:

```bash
# 1. Generate new key
export NEW_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# 2. Stop bot
docker-compose down

# 3. Backup database
cp -r data/ data_backup_$(date +%Y%m%d)/

# 4. Rotate keys
python3 rotate_keys.py

# 5. Update .env
sed -i "s/MASTER_KEY=.*/MASTER_KEY=$NEW_MASTER_KEY/" .env

# 6. Start bot
docker-compose up -d

# 7. Verify
docker-compose logs -f bot | grep "initialized"
```

---

### Monitoring

#### Check Bot Health

```bash
# Is bot running?
docker-compose ps
# OR
ps aux | grep bot.py

# Check resource usage
docker stats sysalert_bot_1 --no-stream

# Check database size
du -h data/bot.db

# Check log size
du -h bot.log
```

#### Monitor Metrics (Admin Command)

In Telegram, send:
```
/stats
```

Shows:
- Active subscriptions
- Total targets
- Queue statistics
- Message send/fail counts

---

### Log Rotation

Prevent log files from growing too large:

```bash
# Install logrotate
sudo apt install logrotate

# Create config
sudo nano /etc/logrotate.d/sysalert
```

**Content**:
```
/path/to/SysAlert/bot.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 your_username your_group
}
```

**Test**:
```bash
sudo logrotate -f /etc/logrotate.d/sysalert
```

---

## Scaling

### Horizontal Scaling

For high availability or load distribution:

1. **Use PostgreSQL** instead of SQLite:
   ```bash
   DB_URL=postgresql://user:pass@db-server:5432/sysalert
   ```

2. **Deploy multiple instances** behind a load balancer

3. **Share database** across instances

4. **Consider Redis** for distributed rate limiting

---

## Support

### Documentation

- **README.md** - Project overview
- **SECURITY.md** - Security policy
- **CLAUDE.md** - Development guide
- **PRIVACY_LOGGING.md** - Privacy documentation

### Getting Help

1. **Check logs** first:
   ```bash
   tail -100 bot.log | grep ERROR
   ```

2. **Search issues**: [GitHub Issues](https://github.com/yourusername/SysAlert/issues)

3. **Create issue**: Include:
   - SysAlert version
   - Python version
   - OS details
   - Error logs (redact sensitive data!)
   - Steps to reproduce

### Contributing

See `CONTRIBUTING.md` (if exists) for contribution guidelines.

---

## License

MIT License - See `LICENSE` file

---

**Deployed successfully?** 🎉

Test your bot: Send `/start` on Telegram!

**Questions?** Open an issue on GitHub.

**Star the repo** ⭐ if this helped you!
