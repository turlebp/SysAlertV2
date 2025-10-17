#!/usr/bin/env python3
"""
Key rotation script: Re-encrypt all data with new master key
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from db import DB
from utils.crypto import CryptoManager


def main():
    print("🔄 SysAlert Monitor Bot - Key Rotation")
    print("=" * 50)
    
    old_key = os.getenv("MASTER_KEY")
    if not old_key:
        print("❌ MASTER_KEY not set in .env")
        sys.exit(1)
    
    print("\nCurrent master key loaded from .env")
    print(f"Key preview: {old_key[:20]}...")
    
    new_key = input("\nEnter NEW master key (or press Enter to generate): ").strip()
    
    if not new_key:
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key().decode()
        print(f"\n🔑 Generated new key: {new_key[:20]}...")
    
    print("\n⚠️  WARNING: This will re-encrypt ALL data in the database")
    print("Ensure you have a backup before proceeding!")
    
    confirm = input("\nProceed with key rotation? (yes/no): ")
    if confirm.lower() != "yes":
        print("Aborted")
        sys.exit(0)
    
    # Initialize old and new crypto managers
    old_crypto = CryptoManager(old_key)
    new_crypto = CryptoManager(new_key)
    
    # Initialize database
    db_url = os.getenv("DB_URL", "sqlite:///./data/bot.db")
    print(f"\nConnecting to database: {db_url}")
    
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Target, BenchmarkTarget
    
    engine = create_engine(db_url, future=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Rotate targets
        print("\n📦 Rotating target encryption...")
        targets = session.query(Target).all()
        
        for target in targets:
            try:
                # Decrypt with old key
                plaintext = old_crypto.decrypt(target.encrypted_value)
                
                # Re-encrypt with new key
                target.encrypted_value = new_crypto.encrypt(plaintext)
                target.fingerprint = new_crypto.hash_value(plaintext)
                
                print(f"  ✅ Rotated: {target.name}")
            except Exception as e:
                print(f"  ❌ Failed to rotate target {target.id}: {e}")
                session.rollback()
                sys.exit(1)
        
        # Rotate benchmark targets
        print("\n📊 Rotating benchmark target encryption...")
        benchmarks = session.query(BenchmarkTarget).all()
        
        for bench in benchmarks:
            try:
                plaintext = old_crypto.decrypt(bench.encrypted_value)
                bench.encrypted_value = new_crypto.encrypt(plaintext)
                bench.fingerprint = new_crypto.hash_value(plaintext)
                print(f"  ✅ Rotated: chat_id {bench.chat_id}")
            except Exception as e:
                print(f"  ❌ Failed to rotate benchmark {bench.id}: {e}")
                session.rollback()
                sys.exit(1)
        
        # Commit all changes
        session.commit()
        print("\n✅ All data re-encrypted successfully!")
        
        # Update .env file
        env_file = Path(".env")
        if env_file.exists():
            content = env_file.read_text()
            lines = []
            
            for line in content.split('\n'):
                if line.startswith('MASTER_KEY='):
                    lines.append(f'MASTER_KEY={new_key}')
                else:
                    lines.append(line)
            
            env_file.write_text('\n'.join(lines))
            print("✅ Updated .env with new master key")
        
        print("\n" + "=" * 50)
        print("✅ Key rotation complete!")
        print("\nIMPORTANT:")
        print("1. Restart the bot to use new key")
        print("2. Update any external scripts/configs")
        print("3. Securely store the new key")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Key rotation failed: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()