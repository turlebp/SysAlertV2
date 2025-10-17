"""
Privacy-safe logging utilities
Never log plaintext sensitive data (targets, IPs, ports, benchmark names)
"""
import hashlib
from typing import Optional


def mask_chat_id(chat_id: int) -> str:
    """
    Mask chat ID for privacy - show only last 4 digits
    Example: 8171181265 -> ****1265
    """
    chat_str = str(chat_id)
    if len(chat_str) <= 4:
        return "****"
    return f"****{chat_str[-4:]}"


def hash_for_log(value: str, prefix: str = "") -> str:
    """
    Create a privacy-safe hash for logging
    Example: "turtlebp" -> "bench:a3f5e9..."
    """
    # Use first 8 chars of SHA256 hash
    h = hashlib.sha256(value.encode()).hexdigest()[:8]
    if prefix:
        return f"{prefix}:{h}"
    return h


def safe_target_log(name: str, ip: str, port: int) -> str:
    """
    Create privacy-safe log entry for target
    Example: "server1" + "192.168.1.1" + 8080 -> "target:7a3e9f2c"
    """
    combined = f"{name}:{ip}:{port}"
    return hash_for_log(combined, "target")


def safe_bench_log(target_name: str, network: str = "mainnet") -> str:
    """
    Create privacy-safe log entry for benchmark target
    Example: "turtlebp" + "mainnet" -> "bench:a3f5e9"
    """
    combined = f"{target_name}:{network}"
    return hash_for_log(combined, "bench")


def safe_ip_log(ip: str) -> str:
    """
    Mask IP address for logging
    Example: "192.168.1.100" -> "192.168.***.***"
    """
    parts = ip.split('.')
    if len(parts) == 4:
        # IPv4
        return f"{parts[0]}.{parts[1]}.***. ***"
    elif ':' in ip:
        # IPv6
        parts = ip.split(':')
        if len(parts) >= 4:
            return f"{parts[0]}:{parts[1]}:***:***"
    return "[IP]"


def redact_sensitive_data(text: str) -> str:
    """
    Redact sensitive data patterns from text
    - IP addresses -> [IP]
    - Port numbers -> [PORT]
    - Chat IDs -> [CHAT_ID]
    """
    import re

    # Redact IPv4 addresses
    text = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', text)

    # Redact IPv6 addresses (simplified)
    text = re.sub(r'[0-9a-fA-F:]{10,}', '[IP]', text)

    # Redact port numbers (standalone numbers 1-65535)
    text = re.sub(r':\d{1,5}\b', ':[PORT]', text)

    # Redact long numeric IDs (likely chat IDs)
    text = re.sub(r'\b\d{8,}\b', '[CHAT_ID]', text)

    return text


# Example usage:
# logger.info(f"Created target: {safe_target_log(name, ip, port)}")
# logger.info(f"Benchmark target added: {safe_bench_log(target_name, network)} for user {mask_chat_id(chat_id)}")
