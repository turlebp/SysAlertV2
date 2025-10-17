"""
Pytest configuration and fixtures
"""
import pytest
import tempfile
from pathlib import Path
import base64
import os
from db import DB


@pytest.fixture
def master_key():
    """Generate test master key"""
    # Generate 32 random bytes and encode as base64
    return base64.b64encode(os.urandom(32)).decode()


@pytest.fixture
def temp_db(master_key):
    """Create temporary test database"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = DB(f"sqlite:///{db_path}", master_key)
        yield db


@pytest.fixture
def sample_config():
    """Sample configuration"""
    return {
        "max_concurrent_checks": 50,
        "min_interval_seconds": 20,
        "connection_timeout": 5,
        "cpu_benchmark": {
            "enabled": False,
            "url": "",
            "threshold_seconds": 0.35,
            "poll_interval_seconds": 300
        }
    }