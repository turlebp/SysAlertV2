"""
Security utilities for input validation and sanitization
"""
import re
import html
from typing import Optional


# Strict validation patterns
TARGET_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,32}$')
DOMAIN_PATTERN = re.compile(
    r'^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
    r'(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
)

# Dangerous characters that could be used for injection or confusion
FORBIDDEN_CHARS = ['<', '>', '"', "'", '`', '\n', '\r', '\0']


def sanitize_target_name(name: str) -> Optional[str]:
    """
    Sanitize and validate target name.
    Returns sanitized name or None if invalid.
    """
    if not name or len(name) > 32:
        return None

    # Remove whitespace
    name = name.strip()

    # Check for forbidden characters
    if any(char in name for char in FORBIDDEN_CHARS):
        return None

    # Validate against pattern
    if not TARGET_NAME_PATTERN.match(name):
        return None

    return name


def sanitize_for_display(text: str, max_length: int = 200) -> str:
    """
    Sanitize text for safe display in Telegram messages.
    Escapes HTML entities and truncates long text.
    """
    if not text:
        return ""

    # Escape HTML entities
    text = html.escape(text)

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text


def validate_domain(domain: str) -> bool:
    """
    Validate domain name format.
    Returns True if valid, False otherwise.
    """
    if not domain or len(domain) > 253:
        return False

    return bool(DOMAIN_PATTERN.match(domain))


def validate_port(port: int) -> bool:
    """
    Validate port number is in valid range.
    """
    return 1 <= port <= 65535


def is_safe_interval(interval: int, min_interval: int = 20, max_interval: int = 86400) -> bool:
    """
    Validate check interval is within safe bounds.
    """
    return min_interval <= interval <= max_interval
