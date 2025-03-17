"""Comprehensive tests for the code ingestion module."""

import pytest
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from app.schemas.debug import DebuggingPayload, DebuggingSession
from app.schemas.common import CodeFile, CodeSnapshot
from app.modules.code_ingestion.storage import SnapshotStorage
from app.modules.code_ingestion.snapshot import CodeIngestionManager

@pytest.fixture
async def storage(redis_clean, supabase_clean):
    """Fixture for SnapshotStorage instance."""
    return SnapshotStorage()

@pytest.fixture
async def manager(redis_clean, supabase_clean):
    """Fixture for CodeIngestionManager instance."""
    return CodeIngestionManager()

@pytest.fixture
def complex_codebase() -> Dict[str, str]:
    """Fixture for a complex codebase with multiple file types and structures."""
    return {
        # TypeScript files
        "src/services/auth/login.ts": """
            import { User } from '../../types';
            import { db } from '../../db';
            import { validateInput } from '../../utils';
            
            export async function login(email: string, password: string): Promise<User> {
                validateInput({ email, password });
                const user = await db.users.findOne({ email });
                if (!user) throw new Error('User not found');
                return user;
            }
        """,
        "src/services/auth/register.ts": """
            import { User } from '../../types';
            import { db } from '../../db';
            import { validateInput, hashPassword } from '../../utils';
            
            export async function register(email: string, password: string): Promise<User> {
                validateInput({ email, password });
                const hashedPassword = await hashPassword(password);
                return await db.users.create({ email, password: hashedPassword });
            }
        """,
        # Configuration files
        "config/database.json": """
            {
                "host": "localhost",
                "port": 5432,
                "database": "myapp",
                "user": "postgres"
            }
        """,
        # Python backend files
        "backend/app.py": """
            from flask import Flask, jsonify
            from database import db
            
            app = Flask(__name__)
            
            @app.route('/api/health')
            def health_check():
                return jsonify({"status": "healthy"})
            
            if __name__ == '__main__':
                app.run(debug=True)
        """,
        # React component
        "frontend/components/LoginForm.tsx": """
            import React, { useState } from 'react';
            import { login } from '../../services/auth';
            
            export const LoginForm: React.FC = () => {
                const [email, setEmail] = useState('');
                const [password, setPassword] = useState('');
                
                const handleSubmit = async (e: React.FormEvent) => {
                    e.preventDefault();
                    try {
                        await login(email, password);
                    } catch (error) {
                        console.error('Login failed:', error);
                    }
                };
                
                return (
                    <form onSubmit={handleSubmit}>
                        <input type="email" value={email} onChange={e => setEmail(e.target.value)} />
                        <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
                        <button type="submit">Login</button>
                    </form>
                );
            };
        """
    }

@pytest.fixture
def sample_error_payload(complex_codebase):
    """Fixture for a sample debugging payload with a complex error scenario."""
    return DebuggingPayload(
        context="Production error in user authentication flow",
        error="TypeError: Cannot read properties of undefined (reading 'password')",
        logs="""
        Error: Cannot read properties of undefined (reading 'password')
            at Object.login [as handler] (/app/src/services/auth/login.ts:7:21)
            at processTicksAndRejections (node:internal/process/task_queues:95:5)
            at async /app/frontend/components/LoginForm.tsx:12:25
        
        Additional context:
        - User IP: 192.168.1.100
        - Timestamp: 2025-03-16T23:15:00Z
        - Browser: Chrome 120.0.0
        - Platform: macOS
        """,
        codebase=complex_codebase
    )

@pytest.mark.asyncio
async def test_large_codebase_ingestion(storage, sample_error_payload):
    """Test ingesting and retrieving a large codebase with multiple file types."""
    # Create initial snapshot
    files = {
        path: CodeFile(path=path, content=content)
        for path, content in sample_error_payload.codebase.items()
    }
    
    snapshot = CodeSnapshot(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        files=files,
        metadata={
            "context": sample_error_payload.context,
            "error": sample_error_payload.error,
            "logs": sample_error_payload.logs,
            "environment": {
                "node_version": "18.15.0",
                "npm_version": "9.5.0",
                "platform": "darwin",
                "arch": "arm64"
            }
        }
    )
    
    # Store snapshot
    await storage.store_snapshot(snapshot)
    
    # Retrieve and verify
    retrieved = await storage.get_snapshot(snapshot.id)
    assert retrieved is not None
    assert retrieved.id == snapshot.id
    assert len(retrieved.files) == len(sample_error_payload.codebase)
    assert retrieved.metadata["environment"]["node_version"] == "18.15.0"
    
    # Verify specific file contents
    assert "login" in retrieved.files["src/services/auth/login.ts"].content
    assert "Flask" in retrieved.files["backend/app.py"].content
    assert "useState" in retrieved.files["frontend/components/LoginForm.tsx"].content

@pytest.mark.asyncio
async def test_debugging_session_with_multiple_snapshots(storage, sample_error_payload):
    """Test creating a debugging session with multiple snapshots representing code changes."""
    # Create initial snapshot
    initial_files = {
        path: CodeFile(path=path, content=content)
        for path, content in sample_error_payload.codebase.items()
    }
    
    initial_snapshot = CodeSnapshot(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        files=initial_files,
        metadata={"version": "1.0.0"}
    )
    
    # Create modified snapshot (simulating a fix)
    modified_files = initial_files.copy()
    modified_files["src/services/auth/login.ts"] = CodeFile(
        path="src/services/auth/login.ts",
        content="""
            import { User } from '../../types';
            import { db } from '../../db';
            import { validateInput } from '../../utils';
            
            export async function login(email: string, password: string): Promise<User> {
                validateInput({ email, password });
                const user = await db.users.findOne({ email });
                if (!user) throw new Error('User not found');
                if (!user.password) throw new Error('Invalid user data');
                return user;
            }
        """
    )
    
    modified_snapshot = CodeSnapshot(
        id=str(uuid.uuid4()),
        timestamp=datetime.now() + timedelta(minutes=30),
        files=modified_files,
        metadata={"version": "1.0.1"}
    )
    
    # Create debugging session
    session = DebuggingSession(
            id=str(uuid.uuid4()),
            context=sample_error_payload.context,
            error=sample_error_payload.error,
            logs=sample_error_payload.logs,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            snapshot_id=initial_snapshot.id,
            snapshot=initial_snapshot  # Add the snapshot field
        )
    
    # Store everything
    await storage.store_snapshot(initial_snapshot)
    await storage.store_snapshot(modified_snapshot)
    await storage.store_debugging_session(session, initial_snapshot)
    
    # Store diff between snapshots
    diff_data = {
        "modified": {
            "src/services/auth/login.ts": {
                "added_lines": [9],
                "removed_lines": [],
                "changes": [
                    {
                        "line": 9,
                        "content": "                if (!user.password) throw new Error('Invalid user data');"
                    }
                ]
            }
        }
    }
    await storage.store_diff(initial_snapshot.id, modified_snapshot.id, diff_data)
    
    # Retrieve and verify session
    retrieved_session = await storage.get_debugging_session(session.id)
    assert retrieved_session is not None
    assert retrieved_session.context == sample_error_payload.context
    assert retrieved_session.error == sample_error_payload.error
    
    # Verify diff
    retrieved_diff = await storage.get_diff(initial_snapshot.id, modified_snapshot.id)
    assert retrieved_diff is not None
    assert "src/services/auth/login.ts" in retrieved_diff["modified"]
    assert len(retrieved_diff["modified"]["src/services/auth/login.ts"]["changes"]) == 1

@pytest.mark.asyncio
async def test_redis_caching_with_large_files(storage, sample_error_payload):
    """Test Redis caching behavior with files of varying sizes."""
    # Create a snapshot with a mix of small and large files
    large_content = "x" * (1024 * 1024)  # 1MB content
    files = {
        "small_file.ts": CodeFile(
            path="small_file.ts",
            content="console.log('small file');"
        ),
        "large_file.txt": CodeFile(
            path="large_file.txt",
            content=large_content
        )
    }
    
    snapshot = CodeSnapshot(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        files=files,
        metadata={"file_sizes": {"small_file.ts": 24, "large_file.txt": len(large_content)}}
    )
    
    # Store snapshot
    await storage.store_snapshot(snapshot)
    
    # First retrieval (should cache small file in Redis)
    retrieved1 = await storage.get_snapshot(snapshot.id)
    assert retrieved1 is not None
    
    # Verify small file is in Redis cache
    small_file_key = storage.redis.get_cache_key("file", f"{snapshot.id}:small_file.ts")
    cached_small_file = await storage.redis.get_hash_cache(small_file_key)
    assert cached_small_file is not None
    
    # Verify large file is not in Redis cache
    large_file_key = storage.redis.get_cache_key("file", f"{snapshot.id}:large_file.txt")
    cached_large_file = await storage.redis.get_hash_cache(large_file_key)
    assert cached_large_file is None
    
    # Second retrieval (should use cache for small file)
    retrieved2 = await storage.get_snapshot(snapshot.id)
    assert retrieved2 is not None
    assert retrieved2.files["small_file.ts"].content == "console.log('small file');"
    assert retrieved2.files["large_file.txt"].content == large_content
