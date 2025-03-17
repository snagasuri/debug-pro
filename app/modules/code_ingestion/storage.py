"""Module for efficient storage and caching of code snapshots using Supabase and Redis."""

import json
from typing import Dict, Optional, Any
from datetime import datetime

from app.schemas.common import CodeFile, CodeSnapshot
from app.schemas.debug import DebuggingSession
from app.modules.code_ingestion.diff import serialize_diff, deserialize_diff
from app.core.redis_client import redis_client
from app.utils.supabase import snapshot_storage, session_storage
from app.utils.json_utils import json_dumps, json_loads

class SnapshotStorage:
    """Manages storage and caching of code snapshots using Supabase and Redis."""
    
    def __init__(self):
        """Initialize storage manager with Redis and Supabase."""
        self.redis = redis_client
        self.snapshot_storage = snapshot_storage
        self.session_storage = session_storage
    
    async def store_snapshot(self, snapshot: CodeSnapshot) -> None:
        """Store a snapshot using tiered storage (Redis + Supabase)."""
        # Prepare snapshot data
        snapshot_data = snapshot.dict()
        
        # Store full snapshot in Supabase
        await self.snapshot_storage.upload_file(
            f"{snapshot.id}.json",
            json_dumps(snapshot_data).encode(),
            metadata={
                "timestamp": snapshot.timestamp.isoformat(),
                "file_count": len(snapshot.files)
            }
        )
        
        # Cache metadata and small files in Redis
        snapshot_key = self.redis.get_cache_key("snapshot", snapshot.id)
        await self.redis.set_hash_cache(snapshot_key, {
            "id": snapshot.id,
            "timestamp": snapshot.timestamp.isoformat(),
            "file_count": str(len(snapshot.files)),
            "metadata": json_dumps(snapshot.metadata or {})
        })
        
        # Cache individual files if they're small enough
        for path, file in snapshot.files.items():
            content_size = len(str(file.content).encode())
            if content_size < 512 * 1024:  # 512KB limit
                file_key = self.redis.get_cache_key("file", f"{snapshot.id}:{path}")
                await self.redis.set_hash_cache(file_key, {
                    "path": path,
                    "content": str(file.content),
                    "metadata": json_dumps(file.metadata or {})
                })
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[CodeSnapshot]:
        """Retrieve a snapshot using tiered storage."""
        # Get snapshot data from Supabase first
        result = await self.snapshot_storage.download_file(
            f"{snapshot_id}.json",
            include_metadata=True
        )
        
        if not result:
            return None
            
        snapshot_data = json_loads(result["data"].decode())
        
        # Try Redis cache for individual files
        snapshot_key = self.redis.get_cache_key("snapshot", snapshot_id)
        cached_metadata = await self.redis.get_hash_cache(snapshot_key)
        
        if cached_metadata:  # Redis client now returns None for non-existent keys
            files = {}
            
            # Try to get files from Redis
            for path in snapshot_data["files"].keys():
                file_key = self.redis.get_cache_key("file", f"{snapshot_id}:{path}")
                file_data = await self.redis.get_hash_cache(file_key)
                if file_data and file_data.get("content"):  # Only use cache if it has content
                    content = file_data["content"]
                    if isinstance(content, (dict, list)):
                        content = json.dumps(content)
                    content_size = len(content.encode())
                    if content_size < 512 * 1024:  # Only use cached files under 512KB
                        files[path] = CodeFile(
                            path=path,
                            content=content,
                            metadata=json_loads(file_data["metadata"]) if isinstance(file_data["metadata"], str) else file_data.get("metadata", {})
                        )
                    else:
                        # Use file from Supabase data for large files
                        file_data = snapshot_data["files"][path]
                        content = file_data["content"]
                        if isinstance(content, (dict, list)):
                            content = json.dumps(content)
                        files[path] = CodeFile(
                            path=path,
                            content=content,
                            metadata=file_data.get("metadata", {})
                        )
                else:
                    # Use file from Supabase data for non-cached files
                    file_data = snapshot_data["files"][path]
                    content = file_data["content"]
                    if isinstance(content, (dict, list)):
                        content = json.dumps(content)
                    files[path] = CodeFile(
                        path=path,
                        content=content,
                        metadata=file_data.get("metadata", {})
                    )
            
            # Return snapshot with mix of cached and non-cached files
            metadata = json_loads(cached_metadata["metadata"]) if isinstance(cached_metadata["metadata"], str) else cached_metadata.get("metadata", {})
            return CodeSnapshot(
                id=snapshot_id,
                timestamp=datetime.fromisoformat(cached_metadata["timestamp"]),
                files=files,
                metadata=metadata
            )
        
        # If no Redis cache, create snapshot from Supabase data
        # Convert file contents to strings if they're dicts/lists
        for path, file_data in snapshot_data["files"].items():
            if isinstance(file_data["content"], (dict, list)):
                snapshot_data["files"][path]["content"] = str(file_data["content"])
        
        snapshot = CodeSnapshot(**snapshot_data)
        
        # Cache in Redis for next time
        await self.store_snapshot(snapshot)
        
        return snapshot
    
    async def store_debugging_session(
        self,
        session: DebuggingSession,
        snapshot: CodeSnapshot
    ) -> None:
        """Store a debugging session and its associated snapshot."""
        # Store the snapshot first
        await self.store_snapshot(snapshot)
        
        # Prepare session data
        session_data = session.dict()
        session_data["snapshot_id"] = snapshot.id
        
        # Store in Supabase
        await self.session_storage.upload_file(
            f"{session.id}.json",
            json_dumps(session_data).encode(),
            metadata={
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "snapshot_id": snapshot.id
            }
        )
        
        # Cache session metadata in Redis
        session_key = self.redis.get_cache_key("session", session.id)
        await self.redis.set_hash_cache(session_key, {
            "id": session.id,
            "snapshot_id": snapshot.id,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "context": session.context,
            "error": session.error,
            "logs": session.logs
        })
    
    async def get_debugging_session(
        self,
        session_id: str
    ) -> Optional[DebuggingSession]:
        """Retrieve a debugging session and its snapshot."""
        # Check Redis cache first
        session_key = self.redis.get_cache_key("session", session_id)
        cached_metadata = await self.redis.get_hash_cache(session_key)
        
        if cached_metadata and cached_metadata.get("id"):  # Only use cache if it exists and has data
            # Get snapshot using cached metadata
            snapshot = await self.get_snapshot(cached_metadata["snapshot_id"])
            if snapshot:
                return DebuggingSession(
                    id=session_id,
                    snapshot=snapshot,
                    created_at=datetime.fromisoformat(cached_metadata["created_at"]),
                    updated_at=datetime.fromisoformat(cached_metadata["updated_at"]),
                    context=cached_metadata["context"],
                    error=cached_metadata["error"],
                    logs=cached_metadata["logs"]
                )
        
        # Fallback to Supabase
        result = await self.session_storage.download_file(
            f"{session_id}.json",
            include_metadata=True
        )
        
        if result:
            session_data = json_loads(result["data"].decode())
            snapshot = await self.get_snapshot(session_data["snapshot_id"])
            if snapshot:
                session = DebuggingSession(**session_data)
                session.snapshot = snapshot
                
                # Cache in Redis for next time
                await self.store_debugging_session(session, snapshot)
                
                return session
        
        return None
    
    async def store_diff(
        self,
        base_id: str,
        target_id: str,
        diff: Dict[str, Any]
    ) -> None:
        """Store a diff between two snapshots in Redis."""
        diff_key = self.redis.get_cache_key("diff", f"{base_id}:{target_id}")
        await self.redis.set_cache(diff_key, diff)
    
    async def get_diff(
        self,
        base_id: str,
        target_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a stored diff from Redis."""
        diff_key = self.redis.get_cache_key("diff", f"{base_id}:{target_id}")
        result = await self.redis.get_cache(diff_key)
        return result if result and len(result) > 0 else None
