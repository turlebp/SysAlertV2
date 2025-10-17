"""
Test cryptography utilities
"""
import pytest
from utils.crypto import CryptoManager
import base64
import os


def test_encrypt_decrypt():
    """Test encryption and decryption"""
    master_key = base64.b64encode(os.urandom(32)).decode()
    crypto = CryptoManager(master_key)
    
    plaintext = "192.168.1.100:9876"
    encrypted = crypto.encrypt(plaintext)
    decrypted = crypto.decrypt(encrypted)
    
    assert decrypted == plaintext
    assert encrypted != plaintext.encode()


def test_hash_deterministic():
    """Test hash is deterministic"""
    master_key = base64.b64encode(os.urandom(32)).decode()
    crypto = CryptoManager(master_key)
    
    value = "test_value"
    hash1 = crypto.hash_value(value)
    hash2 = crypto.hash_value(value)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex


def test_different_plaintexts_different_hashes():
    """Test different values produce different hashes"""
    master_key = base64.b64encode(os.urandom(32)).decode()
    crypto = CryptoManager(master_key)
    
    hash1 = crypto.hash_value("value1")
    hash2 = crypto.hash_value("value2")
    
    assert hash1 != hash2


def test_encryption_uses_random_nonce():
    """Test each encryption uses different nonce"""
    master_key = base64.b64encode(os.urandom(32)).decode()
    crypto = CryptoManager(master_key)
    
    plaintext = "same_value"
    encrypted1 = crypto.encrypt(plaintext)
    encrypted2 = crypto.encrypt(plaintext)
    
    # Different ciphertexts due to random nonce
    assert encrypted1 != encrypted2
    
    # But both decrypt to same plaintext
    assert crypto.decrypt(encrypted1) == plaintext
    assert crypto.decrypt(encrypted2) == plaintext


def test_decrypt_wrong_key_fails():
    """Test decryption with wrong key fails"""
    key1 = base64.b64encode(os.urandom(32)).decode()
    key2 = base64.b64encode(os.urandom(32)).decode()
    
    crypto1 = CryptoManager(key1)
    crypto2 = CryptoManager(key2)
    
    encrypted = crypto1.encrypt("secret")
    
    with pytest.raises(Exception):
        crypto2.decrypt(encrypted)