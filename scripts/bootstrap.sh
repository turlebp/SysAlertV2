#!/usr/bin/env python3
"""
Bootstrap script: Generate master key and initialize database
"""
import os
import sys
from pathlib import Path
from cryptography.fernet import Fernet

def main():
    print("🔐 SysAlert Monitor Bot - Bootstrap")
    print("=" * 50)
    
    env_file = Path(".env")
    
    # Check if .env exists
    if not env_file.exists():
        print("❌ .env file not found")
        print("Please copy .env.example to .env first:")
        print("  cp .env.example .env")
        sys.exit(1)
    
    # Read .env
    env_content = env_file.read_text()
    
    # Check if MASTER_KEY already set
    if "MASTER_KEY=" in env_content and not env_content.split("MASTER_KEY=")[1].startswith("your_"):
        print("⚠️  MASTER_KEY already set in .env")
response = input("Generate new key? (yes/no): ")
if response.lower() != "yes":
print("Aborted")
sys.exit(0)
