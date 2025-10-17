"""
Cryptography utilities for encryption and hashing - FIXED
"""
import os
import base64
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class CryptoManager:
    """Handles AES-GCM encryption and HMAC hashing"""
    
    def __init__(self, master_key: str):
        """Initialize with base64-encoded master key"""
        self.master_key_bytes = base64.b64decode(master_key.encode())
        
        # Derive encryption key
        kdf_enc = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"sysalert_enc_salt_v1",
            iterations=480000,
            backend=default_backend()
        )
        self.enc_key = kdf_enc.derive(self.master_key_bytes)
        self.aesgcm = AESGCM(self.enc_key)
        
        # Derive HMAC key
        kdf_hmac = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"sysalert_hmac_salt_v1",
            iterations=480000,
            backend=default_backend()
        )
        self.hmac_key = kdf_hmac.derive(self.master_key_bytes)
    
    def encrypt(self, plaintext: str) -> bytes:
        """Encrypt string using AES-GCM"""
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode(), None)
        return nonce + ciphertext
    
    def decrypt(self, encrypted: bytes) -> str:
        """Decrypt AES-GCM encrypted data"""
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        plaintext_bytes = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode()
    
    def hash_value(self, value: str) -> str:
        """Generate HMAC-SHA256 fingerprint"""
        h = hmac.new(self.hmac_key, value.encode(), hashlib.sha256)
        return h.hexdigest()