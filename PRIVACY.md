# Privacy Policy & Data Handling

## Data We Collect

### Required Data
- **Telegram Chat ID**: Used to identify your account
- **User Messages**: Command inputs for bot operation

### Optional Data (User-Configured)
- **Monitoring Targets**: IP addresses and ports you want to monitor
- **Benchmark Preferences**: CPU benchmark target names
- **Target Aliases**: Custom names for your targets

## How Data Is Stored

### Encryption at Rest
All sensitive data is encrypted using AES-256-GCM:

- **Monitoring Targets**: IP:port combinations encrypted before storage
- **Benchmark Targets**: User preferences encrypted
- **Historical Data**: Target names encrypted in logs

### Indexing
For efficient lookups without storing plaintext:

- **HMAC Fingerprints**: Deterministic hashes of encrypted data
- **No Reverse Lookup**: Fingerprints cannot be reversed to plaintext
- **Collision Resistant**: SHA256-based hashing

### Example Storage
```python
# User adds target: 192.168.1.100:9876
# Stored as:
{
    "encrypted_value": "gAAAABj...",  # AES-GCM encrypted
    "fingerprint": "a3f5c9...",       # HMAC-SHA256 hash
    "chat_id": 123456789              # User identifier
}
```

## Data Access

### Who Can Access Your Data
- **You**: Full access to your own encrypted data
- **Admins**: Can manage subscriptions, NOT read encrypted targets
- **System**: Automated monitoring checks (decryption happens in memory only)

### What We NEVER Store
- ❌ Plaintext IP addresses in database
- ❌ Plaintext port numbers in database
- ❌ Decrypted data in logs
- ❌ Master encryption key in database
- ❌ Historical plaintext target data

## Data Retention

### Active Users
- Encrypted targets: Retained while account active
- Check history: Last 10,000 records per user
- Audit logs: Last 90 days

### Deleted Accounts
- All user data deleted within 24 hours of `/delete_account` confirmation
- Backups purged within 30 days
- Audit log entry for deletion retained (chat ID only, no target data)

## Data Security

### Encryption Details
- **Algorithm**: AES-256-GCM (AEAD)
- **Key Derivation**: PBKDF2-HMAC-SHA256, 480k iterations
- **IV**: Random 12 bytes per encryption
- **Authentication**: Built-in AEAD tag prevents tampering

### Key Management
- Master key stored in environment variable only
- Never written to disk or logs
- Key rotation supported (see SECURITY.md)
- Derived keys generated at runtime

### Access Controls
- Non-root Docker containers
- Database access limited to bot process
- No external API exposure
- Admin commands require user ID whitelist

## Your Rights

### Data Access
Use `/status` command to view all your monitored targets (encrypted display).

### Data Export
Currently manual via admin request. Contact admin with your chat ID.

### Data Deletion
1. Send `/delete_account` command
2. Receive confirmation token
3. Send `/confirm_delete <token>` within 10 minutes
4. All data deleted immediately

### Data Portability
Encrypted backups available on request. Master key required to decrypt.

## Third-Party Services

### Telegram
- Bot communicates via Telegram Bot API
- Subject to Telegram's privacy policy
- No data shared with Telegram beyond necessary API calls

### Benchmark Services
- CPU benchmark checks query external APIs
- Only benchmark target names sent (e.g., "turtle")
- No personally identifiable information transmitted

## Changes to Privacy Policy

- Version: 2.0
- Last Updated: 2025-01-15
- Changes: Initial privacy-hardened release
- Notification: Users notified via bot broadcast for major changes

## Contact

Privacy questions: privacy@example.com (replace with actual)

Data deletion requests: Send `/delete_account` command in bot
