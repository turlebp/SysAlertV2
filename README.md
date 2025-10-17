# SysAlert Monitor Bot v2

Production-grade Telegram monitoring bot with privacy-hardened encrypted storage, per-user benchmarks, and flexible target management.

## Features

- 🔐 **Privacy by Design**: AES-GCM encrypted targets, HMAC-SHA256 fingerprints
- 🎯 **Per-User Benchmarks**: Custom benchmark targets per chat ID
- 🔄 **Key Rotation**: Built-in cryptographic key rotation support
- 🚀 **Easy Deployment**: Docker + docker-compose with non-root containers
- 🧪 **Production Ready**: Comprehensive tests, CI/CD, audit logging
- 🔒 **Security Hardened**: Input validation, rate limits, least privilege
- 📊 **Monitoring**: TCP checks, CPU benchmarks, historical tracking

## Quick Start
```bash
# 1. Clone and install
git clone <repo>
cd sysalert-monitor-bot
make install

# 2. Configure
cp .env.example .env
# Edit .env with your TELEGRAM_TOKEN, ADMIN_USER_IDS, etc.

# 3. Generate master key
python scripts/bootstrap.sh

# 4. Initialize database
make init-db

# 5. Run tests
make test

# 6. Start bot
docker-compose up -d
```

## Architecture

- **Language**: Python 3.11+ (async)
- **Bot Framework**: python-telegram-bot (async)
- **Database**: SQLAlchemy + Alembic
- **Encryption**: AES-GCM + HMAC-SHA256
- **Container**: Docker (non-root user)
- **Tests**: pytest + pytest-asyncio

## Documentation

- [SECURITY.md](SECURITY.md) - Security architecture and practices
- [PRIVACY.md](PRIVACY.md) - Data handling and encryption details
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment steps

## Commands

### User Commands
- `/start` - Welcome message
- `/whoami` - Show chat ID and status
- `/setbench <target>` - Set benchmark target (e.g., `turtle`, `chainblock`)
- `/addtarget <spec> [as <alias>]` - Add monitoring target
- `/get cpu` - Show benchmark score
- `/get <target>` - Show target status
- `/delete_account` - Delete all your data
- `/status` - View all targets
- `/history` - Recent check history

### Admin Commands
- `/addsub <chat_id>` - Add subscription
- `/rmsub <chat_id>` - Remove subscription
- `/stats` - Bot statistics

## Privacy & Security

✅ All targets encrypted at rest (AES-GCM)  
✅ HMAC fingerprints for lookups (no plaintext indexing)  
✅ Key rotation support via CLI  
✅ User data deletion on request  
✅ Non-root Docker containers  
✅ Audit logging for all operations  
✅ No plaintext logging of sensitive data  

See [PRIVACY.md](PRIVACY.md) for full details.

## License

MIT License - See LICENSE file