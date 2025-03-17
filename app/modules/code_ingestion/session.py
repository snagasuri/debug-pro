"""Module for managing debugging sessions and version tracking."""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.schemas.common import CodeSnapshot
from app.schemas.debug import DebuggingSession, DebuggingPayload
from app.modules.code_ingestion.storage import SnapshotStorage
from app.modules.code_ingestion.diff import calculate_diff, serialize_diff
from app.modules.code_ingestion.metadata import extract_file_metadata

class SessionManager:
    """Manages debugging sessions and their version history."""
    
    def __init__(self, storage: Optional[SnapshotStorage] = None):
        """
        Initialize the session manager.
        
        Args:
            storage: Optional SnapshotStorage instance for persistence
        """
        self.storage = storage or SnapshotStorage()
        self._active_sessions: Dict[str, DebuggingSession] = dict()
    
    async def create_session(self, payload: DebuggingPayload) -> DebuggingSession:
        """
        Create a new debugging session from a payload.
        
        Args:
            payload: The DebuggingPayload containing code and context
            
        Returns:
            A new DebuggingSession instance
        """
        session_id = str(uuid.uuid4())
        
        # Process files and extract metadata
        files = {}
        for path, content in payload.codebase.items():
            metadata = extract_file_metadata(path, content)
            files[path] = {
                "path": path,
                "content": content,
                "metadata": metadata
            }
        
        # Create initial snapshot
        snapshot = CodeSnapshot(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            files=files,
            metadata={
                "session_id": session_id,
                "version": 1,
                "context": payload.context,
                "error": payload.error,
                "logs": payload.logs
            }
        )
        
        # Create session
        session = DebuggingSession(
            id=session_id,
            context=payload.context,
            error=payload.error,
            logs=payload.logs,
            snapshot=snapshot,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={
                "version_history": [{
                    "version": 1,
                    "snapshot_id": snapshot.id,
                    "timestamp": datetime.now().isoformat(),
                    "description": "Initial snapshot"
                }]
            }
        )
        
        # Store session and snapshot
        await self.storage.store_debugging_session(session, snapshot)
        self._active_sessions[session_id] = session
        
        return session
    
    async def update_session(
        self,
        session_id: str,
        payload: DebuggingPayload
    ) -> Optional[DebuggingSession]:
        """
        Update an existing debugging session with new changes.
        
        Args:
            session_id: ID of the session to update
            payload: The DebuggingPayload containing updates
            
        Returns:
            The updated DebuggingSession if successful, None if session not found
        """
        # Get existing session
        session = await self.storage.get_debugging_session(session_id)
        if not session:
            return None
        
        # Process updated files
        new_files = {}
        for path, content in payload.codebase.items():
            metadata = extract_file_metadata(path, content)
            new_files[path] = {
                "path": path,
                "content": content,
                "metadata": metadata
            }
        
        # Create new snapshot
        new_snapshot = CodeSnapshot(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            files=new_files,
            metadata={
                "session_id": session_id,
                "version": len(session.metadata["version_history"]) + 1,
                "context": payload.context,
                "error": payload.error,
                "logs": payload.logs
            }
        )
        
        # Calculate diff from previous snapshot
        diff = calculate_diff(session.snapshot, new_snapshot)
        
        # Update session
        session.context = payload.context
        session.error = payload.error
        session.logs = payload.logs
        session.snapshot = new_snapshot
        session.updated_at = datetime.now()
        
        # Update version history
        version_entry = {
            "version": new_snapshot.metadata["version"],
            "snapshot_id": new_snapshot.id,
            "timestamp": datetime.now().isoformat(),
            "description": f"Update with {len(diff.modified)} modified files",
            "diff": serialize_diff(diff)
        }
        session.metadata["version_history"].append(version_entry)
        
        # Store updated session and snapshot
        await self.storage.store_debugging_session(session, new_snapshot)
        self._active_sessions[session_id] = session
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[DebuggingSession]:
        """
        Retrieve a debugging session.
        
        Args:
            session_id: ID of the session to retrieve
            
        Returns:
            The DebuggingSession if found, None otherwise
        """
        # Check active sessions first
        if session_id in self._active_sessions:
            return self._active_sessions[session_id]
        
        # Try to load from storage
        session = await self.storage.get_debugging_session(session_id)
        if session:
            self._active_sessions[session_id] = session
        
        return session
    
    async def get_version_history(
        self,
        session_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get the version history for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            List of version entries if found, None if session not found
        """
        session = await self.get_session(session_id)
        if not session or "version_history" not in session.metadata:
            return None
        
        return session.metadata["version_history"]
    
    async def revert_to_version(
        self,
        session_id: str,
        version: int
    ) -> Optional[DebuggingSession]:
        """
        Revert a session to a specific version.
        
        Args:
            session_id: ID of the session
            version: Version number to revert to
            
        Returns:
            The reverted DebuggingSession if successful, None otherwise
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        
        # Find the target version
        history = session.metadata["version_history"]
        if version < 1 or version > len(history):
            return None
        
        target_version = history[version - 1]
        snapshot = await self.storage.get_snapshot(target_version["snapshot_id"])
        if not snapshot:
            return None
        
        # Create new version entry for the revert
        new_version = {
            "version": len(history) + 1,
            "snapshot_id": snapshot.id,
            "timestamp": datetime.now().isoformat(),
            "description": f"Reverted to version {version}",
            "reverted_from": version
        }
        
        # Update session
        session.snapshot = snapshot
        session.updated_at = datetime.now()
        session.metadata["version_history"].append(new_version)
        
        # Store changes
        await self.storage.store_debugging_session(session, snapshot)
        self._active_sessions[session_id] = session
        
        return session
