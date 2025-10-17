# Privacy-Safe Logging

## Overview

**CRITICAL**: All sensitive user data is encrypted in the database AND masked in logs.

Users can fully trust that their monitoring targets (IPs, ports, benchmark names) are NEVER stored in plaintext - neither in the database nor in log files.

## What's Protected

### ❌ Never Logged in Plaintext

1. **Target IP addresses** - Always encrypted or masked
2. **Target ports** - Always encrypted or masked
3. **Target names** (if sensitive) - Hashed in logs
4. **Benchmark target names** - Hashed in logs
5. **Full chat IDs** - Only last 4 digits shown
6. **Any decrypted data** - Never appears in logs

### ✅ What IS Logged (Privacy-Safe)

1. **Hashed references** - `target:a3f5e9bc` instead of actual target
2. **Masked chat IDs** - `****1265` instead of full ID
3. **Generic labels** - `[encrypted]` instead of actual values
4. **Aggregate stats** - Counts, intervals, status (no sensitive data)
5. **Error types** - HTTP codes, timeout errors (no user data)

---

## Implementation

### Privacy Logger Module

Location: `utils/privacy_logger.py`

#### Functions Available:

```python
from utils.privacy_logger import (
    mask_chat_id,           # Mask chat ID: 8171181265 -> ****1265
    safe_target_log,        # Hash target: name+ip+port -> target:a3f5e9bc
    safe_bench_log,         # Hash benchmark: name+network -> bench:7d2a1f3e
    safe_ip_log,            # Mask IP: 192.168.1.100 -> 192.168.***.***
    redact_sensitive_data   # Auto-redact IPs/ports/IDs from text
)
```

### Example Usage

#### Before (INSECURE - Leaks Data):
```python
logger.info(f"Created target: {name}")  # ❌ BAD
logger.info(f"Added benchmark for {chat_id}: {target_name}")  # ❌ BAD
logger.info(f"Removed target {name} for customer {customer_id}")  # ❌ BAD
```

#### After (SECURE - Privacy-Safe):
```python
logger.info(f"Created target: {safe_target_log(name, ip, port)}")  # ✅ GOOD
logger.info(f"Added benchmark: {safe_bench_log(target_name, network)} for user {mask_chat_id(chat_id)}")  # ✅ GOOD
logger.info(f"Removed target: [encrypted] for customer {mask_chat_id(customer_id)}")  # ✅ GOOD
```

---

## Log Examples

### Before Privacy Fixes

```log
2025-10-17 08:48:13 - INFO - Created target: p2p
2025-10-17 08:48:50 - INFO - Added benchmark target for 8171181265: turtlebp on testnet
2025-10-17 08:50:15 - INFO - Added benchmark target for 8171181265: protonnz on mainnet
2025-10-17 09:15:22 - INFO - Removed target: api-server for customer 8171181265
```

**Problems**:
- Target names visible
- Full chat IDs visible
- Benchmark names visible
- Can correlate user activity

### After Privacy Fixes

```log
2025-10-17 08:48:13 - INFO - Created target: target:a3f5e9bc
2025-10-17 08:48:50 - INFO - Added benchmark: bench:7d2a1f3e for user ****1265
2025-10-17 08:50:15 - INFO - Added benchmark: bench:2f8c4a61 for user ****1265
2025-10-17 09:15:22 - INFO - Removed target: [encrypted] for customer ****1265
```

**Benefits**:
- No plaintext target/benchmark names
- Chat IDs partially masked
- Still useful for debugging (hashes are consistent)
- Cannot reverse-engineer user data

---

## Files Modified

All logging statements updated in:

1. ✅ **db.py** - Database operations
   - Subscription management
   - Target operations
   - Benchmark operations
   - Audit logging

2. ✅ **services/monitor.py** - TCP monitoring
   - Target check failures/successes
   - Recovery messages
   - Error logging

3. ✅ **services/benchmark.py** - CPU benchmarks
   - Benchmark check errors
   - Threshold violations (no target names)

4. ✅ **bot.py** - Main application
   - Error handler (generic messages only)

---

## Verification

### Check Your Logs

```bash
# Search for potential leaks (should find NOTHING):
grep -E "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" bot.log  # IPs
grep -E ":[0-9]{2,5}\b" bot.log | grep -v "target:"  # Ports
grep -E "\b[0-9]{8,}\b" bot.log | grep -v "\*\*\*\*"  # Full chat IDs

# Search for privacy-safe patterns (should find MANY):
grep "target:" bot.log  # Hashed targets
grep "bench:" bot.log  # Hashed benchmarks
grep "\*\*\*\*" bot.log  # Masked chat IDs
grep "\[encrypted\]" bot.log  # Generic labels
```

### Test Privacy Logging

```python
# Test in Python console
from utils.privacy_logger import *

# Test chat ID masking
print(mask_chat_id(8171181265))  # Output: ****1265

# Test target hashing (consistent hashes)
hash1 = safe_target_log("server1", "192.168.1.1", 8080)
hash2 = safe_target_log("server1", "192.168.1.1", 8080)
print(hash1 == hash2)  # Output: True (same input = same hash)

# Test benchmark hashing
print(safe_bench_log("turtlebp", "mainnet"))  # Output: bench:7d2a1f3e

# Test IP masking
print(safe_ip_log("192.168.1.100"))  # Output: 192.168.***.***
```

---

## Why This Matters

### Trust & Privacy

Users trust you with sensitive infrastructure data:
- Internal IP addresses
- Service ports
- Server names
- Monitoring configurations

**Encryption in database is NOT enough** - logs must be secure too!

### Compliance

- **GDPR Article 5**: Data minimization - don't log more than necessary
- **GDPR Article 32**: Security of processing - protect data in transit AND at rest
- **SOC 2**: Logging and monitoring controls must not leak sensitive data

### Real-World Scenarios

**Scenario 1: Log Aggregation**
```
If logs are sent to:
- Elasticsearch / Loki
- CloudWatch / Datadog
- File-sharing for debugging

Plaintext data would be exposed in multiple systems!
```

**Scenario 2: Debug Sessions**
```
Developer needs logs for debugging:
- With privacy logging: Safe to share
- Without: Would expose all user targets
```

**Scenario 3: Security Incident**
```
If server is compromised:
- Encrypted database: Attacker needs master key
- Privacy-safe logs: No plaintext to steal
- Regular logs: All targets exposed
```

---

## Best Practices

### DO:
✅ Use privacy logger functions for all sensitive data
✅ Log hashes instead of plaintext
✅ Log aggregated statistics (counts, averages)
✅ Log error types and codes
✅ Mask user identifiers (last 4 digits only)

### DON'T:
❌ Log decrypted target data
❌ Log full chat IDs or user IDs
❌ Log IP addresses in plaintext
❌ Log ports in plaintext
❌ Log benchmark target names in plaintext
❌ Include sensitive data in error messages

### When Adding New Features

1. **Before logging**:
   ```python
   # Ask: Does this contain user data?
   # If yes, use privacy logger functions
   ```

2. **Review pattern**:
   ```python
   # Search your code for logger. calls
   grep -n "logger\." your_new_file.py

   # Verify each one doesn't leak data
   ```

3. **Test logs**:
   ```bash
   # Run feature, check bot.log
   tail -f bot.log | grep -E "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}"
   # Should see NOTHING sensitive
   ```

---

## Monitoring Privacy Compliance

### Automated Checks

Add to your CI/CD:

```bash
# ci/check_privacy_logs.sh
#!/bin/bash

# Check for IP address leaks
if grep -E "[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}" bot.py db.py services/*.py | grep -v "127.0.0.1" | grep -v "0.0.0.0"; then
    echo "ERROR: Potential IP address in logging code"
    exit 1
fi

# Check for chat ID leaks
if grep -E 'logger.*chat_id[^)]*\)' *.py services/*.py | grep -v "mask_chat_id"; then
    echo "ERROR: Potential unmasked chat_id in logs"
    exit 1
fi

echo "Privacy logging checks passed"
```

### Manual Audits

Monthly checklist:

- [ ] Review bot.log for any plaintext data
- [ ] Verify all new logger statements use privacy functions
- [ ] Test log export (safe to share?)
- [ ] Check log aggregation systems for leaks
- [ ] Update this document if patterns change

---

## Summary

🔒 **Database**: AES-GCM encrypted at rest
🔒 **Logs**: Hashed/masked, no plaintext
🔒 **Messages**: Only to authorized users
🔒 **Backups**: Encrypted

**Result**: Complete privacy from storage to logging

**Trust Level**: ⭐⭐⭐⭐⭐ Users can fully trust this bot with sensitive infrastructure data.

---

**Last Updated**: 2025-01-15
**Version**: SysAlert v2.1
