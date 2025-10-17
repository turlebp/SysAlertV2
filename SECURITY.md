# Security Architecture

## Threat Model

### Protected Assets
- User chat IDs and target configurations
- Monitored IP addresses and ports
- Benchmark target preferences
- Historical monitoring data

### Threats Mitigated
- ✅ Database compromise (encryption at rest)
- ✅ Log file exposure (no plaintext secrets)
- ✅ Unauthorized access (admin whitelist)
- ✅ Privilege escalation (non-root containers)
- ✅ Data exfiltration (encrypted storage)

## Cryptographic Design

### Encryption (AES-GCM)
- **Algorithm**: AES-256-GCM
- **Key Derivation**: PBKDF2-HMAC-SHA256 (480,000 iterations)
- **IV**: Random 12 bytes per operation
- **Authentication**: Built-in AEAD tag

### Hashing (HMAC-SHA256)
- **Purpose**: Deterministic fingerprints for indexing
- **Key**: Separate HMAC key derived from master key
- **Output**: Hex-encoded SHA256 digest

### Key Storage
- **Master Key**: Environment variable only (never in DB)
- **Derived Keys**: Generated at runtime via KDF
- **Rotation**: Supported via `rotate_keys.py` script

## Security Features

### Input Validation
- IP address format verification (IPv4/IPv6)
- Port range validation (1-65535)
- Target name sanitization
- Command argument bounds checking

### Access Control
- Admin-only subscription management
- Per-user data isolation
- Chat ID validation on all operations
- API key authentication for scripts

### Container Security
- Non-root user (uid 1000)
- Read-only root filesystem where possible
- No unnecessary capabilities
- Private network isolation

### Rate Limiting
- Per-chat message rate limit (1 msg/sec)
- Global concurrent check limit (50 default)
- Exponential backoff on failures
- Queue overflow protection

## Operational Security

### Secrets Management
```bash
# NEVER commit secrets to git
# Store in environment variables or secret managers
export MASTER_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export TELEGRAM_TOKEN="your_bot_token"
```

### Key Rotation
```bash
# Generate new key
export NEW_MASTER_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Rotate all encrypted data
python scripts/rotate_keys.py --old-key "$MASTER_KEY" --new-key "$NEW_MASTER_KEY"

# Update environment
export MASTER_KEY="$NEW_MASTER_KEY"
```

### Audit Logging
All sensitive operations logged:
- User data access/modification
- Target addition/removal
- Key rotation events
- Admin actions

### Secure Defaults
- Encryption enabled by default
- No auto-subscribe (admin approval required)
- Minimal logging (no plaintext sensitive data)
- Secure random for all crypto operations

## Compliance

### Data Protection
- GDPR-compliant data deletion (`/delete_account`)
- Minimal data retention
- User-controlled data access
- Audit trail for data operations

### Best Practices
- Principle of least privilege
- Defense in depth
- Secure by default
- Fail securely

## Reporting Vulnerabilities

Email: security@example.com (replace with actual contact)

**DO NOT** open public issues for security vulnerabilities.