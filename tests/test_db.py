"""
Test database operations
"""
import pytest


def test_add_subscription(temp_db):
    """Test adding subscription"""
    temp_db.add_subscription(12345)
    assert temp_db.is_subscribed(12345)


def test_subscription_idempotent(temp_db):
    """Test adding same subscription twice"""
    temp_db.add_subscription(12345)
    temp_db.add_subscription(12345)
    assert temp_db.is_subscribed(12345)


def test_encrypted_target_storage(temp_db):
    """Test target encryption and decryption"""
    temp_db.add_subscription(12345)
    customer = temp_db.create_customer(12345)
    
    # Add encrypted target
    target = temp_db.upsert_target(customer.id, "test_server", "192.168.1.100", 9876)
    
    assert target.name == "test_server"
    assert target.encrypted_value is not None
    assert target.fingerprint is not None
    
    # Decrypt
    ip, port = temp_db.get_target_decrypted(target)
    assert ip == "192.168.1.100"
    assert port == 9876


def test_benchmark_target_encryption(temp_db):
    """Test benchmark target encryption"""
    temp_db.add_subscription(12345)
    
    # Set benchmark target
    temp_db.set_benchmark_target(12345, "turtle")
    
    # Retrieve and decrypt
    target_name = temp_db.get_benchmark_target(12345)
    assert target_name == "turtle"


def test_delete_user_data(temp_db):
    """Test GDPR-compliant data deletion"""
    temp_db.add_subscription(12345)
    customer = temp_db.create_customer(12345)
    temp_db.upsert_target(customer.id, "server1", "10.0.0.1", 80)
    temp_db.set_benchmark_target(12345, "turtle")
    
    # Delete all data
    temp_db.delete_user_data(12345)
    
    # Verify deletion
    assert not temp_db.is_subscribed(12345)
    assert temp_db.get_customer_by_chat(12345) is None
    assert temp_db.get_benchmark_target(12345) is None


def test_fingerprint_uniqueness(temp_db):
    """Test fingerprints are unique for different values"""
    temp_db.add_subscription(12345)
    customer = temp_db.create_customer(12345)
    
    target1 = temp_db.upsert_target(customer.id, "srv1", "10.0.0.1", 80)
    target2 = temp_db.upsert_target(customer.id, "srv2", "10.0.0.2", 80)
    
    assert target1.fingerprint != target2.fingerprint