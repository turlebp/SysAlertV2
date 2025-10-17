# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SysAlert (SysAlert Monitor Bot v2) is a privacy-hardened Telegram monitoring bot with encrypted storage. It monitors TCP endpoints and CPU benchmarks, sending alerts via Telegram when targets fail or performance degrades.

**Key Philosophy**: Privacy by design with AES-GCM encryption at rest, HMAC-SHA256 fingerprints for indexing (no plaintext), and GDPR-compliant data deletion.

## Development Commands

### Installation & Setup
```bash
make install              # Install Python dependencies
python scripts/bootstrap.sh  # Generate master encryption key
make init-db             # Initialize database (creates data/ dir)
```

### Testing & Quality
```bash
make test                # Run full pytest suite
pytest tests/test_crypto.py -v  # Run single test file
pytest tests/test_db.py::TestClass::test_name  # Run single test
make lint                # Run flake8 + mypy
```

### Running the Bot
```bash
make run                 # Run bot locally (development)
make docker-build        # Build Docker image
make docker-run          # Start via docker-compose (production)
make docker-logs         # View container logs
make docker-stop         # Stop containers
```

### Environment Configuration
Required environment variables in `.env`:
- `TELEGRAM_TOKEN` - Telegram bot API token
- `MASTER_KEY` - Base64-encoded encryption master key (generate via bootstrap.sh)
- `ADMIN_USER_IDS` - Comma-separated admin Telegram user IDs
- `DB_URL` - Database URL (default: `sqlite:///./data/bot.db`)

See bot.py:36-60 for all config options.

## Architecture

### Core Data Flow

1. **Bot Startup** (bot.py:124-143)
   - Load config from environment → Initialize DB with CryptoManager → Register handlers → Start background workers

2. **Background Workers** (launched in bot.py:92-100)
   - `monitoring_worker`: Continuous TCP checks on enabled targets (services/monitor.py:38)
   - `benchmark_monitor_loop`: Periodic CPU benchmark polling if enabled (services/benchmark.py:82)

3. **Message Queue** (services/tele_queue.py)
   - All Telegram messages flow through TeleQueue for rate limiting (1 msg/sec per chat by default)
   - Exponential backoff on failures, tracks stats

### Encryption Architecture (utils/crypto.py)

**Critical**: All user targets are encrypted at rest. Never log decrypted values.

- **Master Key**: Base64-encoded, stored in env only (never in DB)
- **Derived Keys**: PBKDF2-HMAC-SHA256 with 480k iterations
  - `enc_key`: For AES-GCM encryption/decryption
  - `hmac_key`: For deterministic fingerprints (enables lookups without decrypting)
- **Encryption Flow**: `plaintext` → AES-GCM(12-byte nonce + ciphertext) → stored as `encrypted_value`
- **Lookup Flow**: `plaintext` → HMAC-SHA256 → hex digest → stored as `fingerprint` (indexed)

### Database Schema (models.py)

**Important relationships**:
- `Customer` (1) ↔ (N) `Target` - Cascade delete on customer removal
- `BenchmarkTarget` - Multiple per chat_id (removed unique constraint for multi-target support)
- All timestamps are Unix epoch integers (not datetime objects)

**Encrypted fields**:
- `Target.encrypted_value` - AES-GCM encrypted "ip:port"
- `Target.fingerprint` - HMAC-SHA256 of "ip:port" (for indexing)
- `BenchmarkTarget.encrypted_value` - AES-GCM encrypted target name
- `BenchmarkTarget.fingerprint` - HMAC-SHA256 of target name

### Command Handlers (commands/handlers.py)

All handlers follow pattern:
1. Check subscription status (`db.is_subscribed`)
2. Validate input (regex for names, ipaddress module for IPs)
3. Perform DB operation (always via `asyncio.to_thread`)
4. Send response via Telegram (direct for immediate, via `tele_queue` for alerts)

**Admin commands**: `/addsub`, `/rmsub`, `/stats` - guarded by `is_admin()` check

### Monitoring Logic (services/monitor.py)

**Key behavior** (monitoring_worker:38-71):
- Loops every 5 seconds fetching subscriptions
- For each customer, reloads fresh target list from DB
- Skips disabled targets (`target.enabled = False`)
- Creates async task per target with semaphore limiting concurrent checks
- Sends alerts when `consecutive_failures >= failure_threshold`
- Sends recovery message when target recovers (was failing, now success)

**Important**: Always reload customer/target data fresh in loops to catch enabled/disabled state changes.

### Benchmark Monitoring (services/benchmark.py)

Supports multiple benchmark targets per user with network selection (mainnet/testnet).

**Data parsing** (_parse_possible_structures:12-48):
- Handles CSV-like strings: `"target_name,timestamp,value"`
- Handles list of dicts: `[{"name": "...", "data": [[ts, val], ...]}]`
- Handles dict of lists: `{"target_name": [[ts, val], ...]}`
- Returns first match for CSV format, last data point for time series

## Security Best Practices

1. **Never log decrypted target values** - Only log target names or "[encrypted]"
2. **Always encrypt before DB insert** - Use `db.crypto.encrypt()` and `db.crypto.hash_value()`
3. **Validate all user input** - Use `utils/security.py` functions for sanitization
4. **Use asyncio.to_thread for DB calls** - DB operations are synchronous
5. **Audit sensitive actions** - Use `db.audit()` for admin operations
6. **Sanitize error messages** - Global error handler prevents info leakage (bot.py:23-36)
7. **Rate limit admin commands** - Failed attempts tracked, auto-ban after 5 attempts

### New Security Module (utils/security.py)

Always use these functions for input validation:
- `sanitize_target_name(name)` - Validates target names (alphanumeric + dash/underscore, max 32 chars)
- `validate_domain(domain)` - RFC-compliant domain validation
- `validate_port(port)` - Port range check (1-65535)
- `is_safe_interval(interval)` - Check interval bounds (20s - 24h)
- `sanitize_for_display(text)` - HTML escape for safe display in messages

## Common Patterns

### Adding a new command handler
```python
async def newcmd_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    # Always check subscription first
    if not await asyncio.to_thread(db.is_subscribed, chat_id):
        await update.message.reply_text("❌ You're not subscribed")
        return

    # Validate args
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /newcmd <arg>")
        return

    # Perform DB operation in thread
    result = await asyncio.to_thread(db.some_method, chat_id, context.args[0])

    await update.message.reply_text(f"✅ Done: {result}")

# Register in register_handlers()
app.add_handler(CommandHandler("newcmd", newcmd_cmd))
```

### Adding encrypted field to DB
```python
# In models.py
class NewModel(Base):
    encrypted_value = Column(LargeBinary, nullable=False)
    fingerprint = Column(String(64), nullable=False, index=True)

# In db.py
def add_encrypted_item(self, plaintext: str):
    with self.session_scope() as s:
        encrypted = self.crypto.encrypt(plaintext)
        fingerprint = self.crypto.hash_value(plaintext)
        item = NewModel(encrypted_value=encrypted, fingerprint=fingerprint)
        s.add(item)
```

### Sending alerts via queue
```python
# In background worker
alert_msg = f"⚠️ {config['bot_name']} ⚠️\nAlert message here"
await tele_queue.enqueue(chat_id, alert_msg)
```

## Database Migrations

This project uses Alembic for schema migrations:
```bash
alembic revision -m "description"  # Create migration
alembic upgrade head               # Apply migrations
alembic downgrade -1               # Rollback one migration
```

Config: `alembic.ini` (default: `sqlite:///./data/bot.db`)

## Testing

- Tests use pytest with pytest-asyncio (asyncio_mode = auto in pytest.ini)
- Fixtures in tests/conftest.py provide in-memory DB for isolation
- Run tests before commits: `make test && make lint`

## Troubleshooting

**"MASTER_KEY is required"**: Run `python scripts/bootstrap.sh` to generate key, add to `.env`

**Targets not being checked**: Check `target.enabled` status (use `/mode active <target>` to enable)

**Messages not sending**: Check TeleQueue stats via `/stats` (admin command) - look for dropped/failed counts

**Database locked**: SQLite WAL mode enabled (see db.py:43-48), ensure `data/` directory is writable
