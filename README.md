

# 🚨 SysAlert Monitor Bot v2

**Your intelligent Telegram monitoring companion** for production systems — built with enterprise-grade encryption, personalized benchmarks, and flexible target management.

> **🎉 What's New:** We've added more commands to give you even greater control over your monitoring setup! Check out the expanded command list below to see what's now available.
> 

---

## What Makes This Different?

**Built for privacy-conscious teams.** Every target you monitor is encrypted at rest using AES-GCM encryption with HMAC-SHA256 fingerprints. No plaintext storage. Ever.

**Personalized to your needs.** Set custom benchmark targets for each chat ID, track historical performance, and get alerts that matter to you.

**Deploy with confidence.** Production-ready architecture with comprehensive testing, CI/CD pipelines, and security hardening built in from day one.

---

## Key Capabilities

🔐 **Privacy by Design** — All monitoring targets encrypted with AES-GCM, indexed via HMAC fingerprints instead of plaintext

🎯 **Per-User Benchmarks** — Define custom performance baselines that adapt to your infrastructure

🔄 **Cryptographic Key Rotation** — Built-in support for rotating encryption keys without downtime

🚀 **Zero-Friction Deployment** — Docker and docker-compose configurations with non-root containers ready to go

🧪 **Production Hardened** — Complete test coverage, CI/CD integration, and comprehensive audit logging

🔒 **Security First** — Input validation, rate limiting, and least-privilege access controls throughout

📊 **Smart Monitoring** — TCP connectivity checks, CPU benchmarking, and historical trend analysis

---

## Get Started in 5 Minutes

See the [Deployment Guide](DEPLOYMENT.md)
**That's it!** Your bot is now running and ready to accept commands.

---

## Technical Architecture

Built on modern, battle-tested technologies:

- **Language**: Python 3.11+ with async/await patterns
- **Bot Framework**: python-telegram-bot (fully async)
- **Database**: SQLAlchemy ORM with Alembic migrations
- **Encryption**: AES-GCM authenticated encryption with HMAC-SHA256
- **Container**: Docker with non-root user security
- **Testing**: pytest with asyncio support

---

## Dive Deeper

Want to understand the security model or deploy to production? Check out our comprehensive guides:

- [SECURITY.md](http://SECURITY.md) — Security architecture, threat model, and best practices
- [PRIVACY.md](http://PRIVACY.md) — Data handling policies and encryption implementation details

---

## How to Use It

### For All Users

**Getting oriented:**

- `/start` — Get a friendly welcome and overview
- `/whoami` — Check your chat ID and subscription status

If you're not hosting this bot yourself,then you can chat us at `https://t.me/trutle_sleep` to add your chat id into susbcriber with zero complexity and zero hidden fees.

**Managing your monitoring:**

- `/setbench <target>` — Set your benchmark target (try `turtle` or `chainblock`)
- `/addtarget <spec> [as <alias>]` — Add a new monitoring target with optional friendly name
- `/get cpu` — View your current benchmark score
- `/get <target>` — Check the status of a specific target
- `/status` — See all your active monitoring targets at a glance
- `/history` — Review recent check results
- `/listbench` — List all available benchmark targets

![command list](commands list.png)

**Privacy controls:**

- `/delete_account` — Permanently delete all your data (no questions asked)

### For Administrators

**Subscription management:**

- `/addsub <chat_id>` — Grant monitoring access to a new user
- `/rmsub <chat_id>` — Revoke access for a user
- `/stats` — View bot-wide usage statistics

---

## Your Privacy Matters

We've architected this bot with privacy as the foundation, not an afterthought:

✅ **Encrypted at rest** — All targets use AES-GCM authenticated encryption

✅ **Private indexing** — HMAC fingerprints mean no plaintext data in lookups

✅ **Key rotation ready** — Rotate encryption keys via CLI without service interruption

✅ **Right to deletion** — Users can request complete data deletion anytime

✅ **Container security** — Non-root Docker containers limit privilege escalation

✅ **Audit trail** — Every operation logged for security review

✅ **Clean logs** — Zero sensitive data in plaintext logs

**Want the full technical breakdown?** Read our [PRIVACY.md](http://PRIVACY.md) documentation.

---

## License

Released under the MIT License — see the LICENSE file for complete terms.

---

