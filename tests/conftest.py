"""Pytest configuration and fixtures for testing."""

import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Set test mode and load test environment variables
os.environ["TEST_MODE"] = "true"
load_dotenv(".env.test", override=True)

# Import after environment is configured
from app.core.redis_client import redis_client
from app.utils.supabase import (
    get_supabase_admin_client,
    get_supabase_client,
    snapshot_storage,
    session_storage
)
from app.db.migrations.init_storage import create_storage_buckets, create_tables

@pytest.fixture
def supabase_admin_client():
    """Get a fresh Supabase admin client for each test."""
    return get_supabase_admin_client()

@pytest.fixture
def supabase_client():
    """Get a fresh Supabase client for each test."""
    return get_supabase_client()

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Global test setup/teardown for Redis and Supabase."""
    # Initialize storage and tables
    create_storage_buckets()
    create_tables()
    
    yield

@pytest.fixture
async def redis_clean():
    """Fixture to clean Redis before each test."""
    await redis_client.flushdb()

@pytest.fixture
async def supabase_clean():
    """Fixture to clean Supabase storage before each test."""
    # Clean snapshots bucket
    files = snapshot_storage.client.storage.from_("snapshots").list()
    if files:
        snapshot_storage.client.storage.from_("snapshots").remove(
            [f["name"] for f in files]
        )
    
    # Clean sessions bucket
    files = session_storage.client.storage.from_("sessions").list()
    if files:
        session_storage.client.storage.from_("sessions").remove(
            [f["name"] for f in files]
        )
