"""Tests for the code ingestion module."""

import pytest
import json
import uuid
from datetime import datetime
from app.schemas.debug import DebuggingPayload
from app.schemas.common import CodeFile, CodeSnapshot
from app.modules.code_ingestion.storage import SnapshotStorage
from app.modules.code_ingestion.snapshot import CodeIngestionManager
from app.core.redis_client import redis_client

@pytest.fixture
async def storage(redis_clean, supabase_clean):
    """Fixture for SnapshotStorage instance."""
    return SnapshotStorage()

@pytest.fixture
async def manager(redis_clean, supabase_clean):
    """Fixture for CodeIngestionManager instance."""
    return CodeIngestionManager()

@pytest.fixture
def sample_payload():
    """Fixture for a sample debugging payload."""
    return DebuggingPayload(
        context="Testing error in user authentication",
        error="TypeError: Cannot read property 'id' of undefined",
        logs="Error occurred in /auth/login.ts:25\nStack trace: ...",
        codebase={
            "auth/login.ts": """
            export async function login(email: string, password: string) {
                const user = await db.users.findOne({ email });
                return user.id;  // Error: user might be undefined
            }
            """,
            "auth/types.ts": """
            export interface User {
                id: string;
                email: string;
                password: string;
            }
            """
        }
    )

@pytest.mark.asyncio
async def test_store_and_retrieve_snapshot(storage, sample_payload):
    """Test storing and retrieving a snapshot."""
    # Create a snapshot
    files = {
        path: CodeFile(path=path, content=content)
        for path, content in sample_payload.codebase.items()
    }
    
    snapshot = CodeSnapshot(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        files=files,
        metadata={
            "context": sample_payload.context,
            "error": sample_payload.error,
            "logs": sample_payload.logs
        }
    )
    
    # Store the snapshot
    await storage.store_snapshot(snapshot)
    
    # Retrieve the snapshot
    retrieved = await storage.get_snapshot(snapshot.id)
    
    assert retrieved is not None
    assert retrieved.id == snapshot.id
    assert len(retrieved.files) == len(snapshot.files)
    assert retrieved.metadata["context"] == sample_payload.context

@pytest.mark.asyncio
async def test_redis_caching(storage, sample_payload):
    """Test Redis caching for snapshots."""
    # Create a snapshot
    files = {
        path: CodeFile(path=path, content=content)
        for path, content in sample_payload.codebase.items()
    }
    
    snapshot = CodeSnapshot(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        files=files,
        metadata={
            "context": sample_payload.context,
            "error": sample_payload.error,
            "logs": sample_payload.logs
        }
    )
    
    # Store the snapshot
    await storage.store_snapshot(snapshot)
    
    # First retrieval should cache in Redis
    retrieved1 = await storage.get_snapshot(snapshot.id)
    assert retrieved1 is not None
    
    # Second retrieval should come from Redis cache
    retrieved2 = await storage.get_snapshot(snapshot.id)
    assert retrieved2 is not None
    assert retrieved2.id == retrieved1.id
    assert len(retrieved2.files) == len(retrieved1.files)

@pytest.mark.asyncio
async def test_diff_storage(storage):
    """Test storing and retrieving diffs."""
    base_id = str(uuid.uuid4())
    target_id = str(uuid.uuid4())
    diff_data = {
        "added": {"new_file.ts": "new content"},
        "modified": {"existing.ts": "updated content"},
        "deleted": ["removed.ts"]
    }
    
    # Store diff
    await storage.store_diff(base_id, target_id, diff_data)
    
    # Retrieve diff
    retrieved_diff = await storage.get_diff(base_id, target_id)
    
    assert retrieved_diff is not None
    assert retrieved_diff["added"] == diff_data["added"]
    assert retrieved_diff["modified"] == diff_data["modified"]
    assert retrieved_diff["deleted"] == diff_data["deleted"]
