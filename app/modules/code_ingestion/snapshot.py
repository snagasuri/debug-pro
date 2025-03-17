"""Main module for code ingestion and snapshot management."""

import os
from typing import Dict, Optional, Any, Tuple, List
from datetime import datetime

from app.schemas.common import CodeFile, CodeSnapshot
from app.schemas.debug import DebuggingPayload, DebuggingSession
from app.modules.code_ingestion.diff import calculate_diff, apply_diff
from app.modules.code_ingestion.metadata import extract_file_metadata
from app.modules.code_ingestion.storage import SnapshotStorage
from app.modules.code_ingestion.session import SessionManager

class CodeIngestionManager:
    """Manages code ingestion, snapshots, and debugging sessions."""
    
    def __init__(self):
        """Initialize the code ingestion manager."""
        self.storage = SnapshotStorage()
        self.session_manager = SessionManager(storage=self.storage)
        
        # File filtering configuration
        self.ignore_patterns = [
            ".git",
            "node_modules",
            "__pycache__",
            ".docker",
            ".venv",
            ".env",
            ".DS_Store",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            "*.so",
            "*.dylib",
            "*.dll",
            "*.log",
            "*.tmp"
        ]
    
    def is_valid_file(self, file_path: str) -> bool:
        """
        Check if a file should be ingested based on ignore patterns.
        
        Args:
            file_path: Path of the file to check
            
        Returns:
            True if the file should be ingested, False otherwise
        """
        from fnmatch import fnmatch
        
        # Normalize path for consistent matching
        normalized_path = file_path.replace('\\', '/')
        
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if fnmatch(normalized_path, pattern):
                    return False
            elif normalized_path.startswith(pattern) or f"/{pattern}" in normalized_path:
                return False
        return True
    
    async def process_debugging_payload(
        self,
        payload: DebuggingPayload
    ) -> Tuple[CodeSnapshot, Dict[str, Any]]:
        """
        Process an incoming debugging payload.
        
        Args:
            payload: The DebuggingPayload containing code and context
            
        Returns:
            A tuple of (CodeSnapshot, metadata)
        """
        try:
            # Filter and process files
            valid_files: Dict[str, CodeFile] = {}
            for file_path, content in payload.codebase.items():
                if not self.is_valid_file(file_path):
                    continue
                
                # Extract metadata including language detection and complexity metrics
                metadata = extract_file_metadata(file_path, content)
                
                valid_files[file_path] = CodeFile(
                    path=file_path,
                    content=content,
                    metadata=metadata
                )
            
            if payload.session_id:
                # Update existing session
                session = await self.session_manager.update_session(
                    payload.session_id,
                    payload
                )
                if not session:
                    raise ValueError(f"Session {payload.session_id} not found")
                return session.snapshot, session.metadata
            else:
                # Create new session
                session = await self.session_manager.create_session(payload)
                return session.snapshot, session.metadata
            
        except Exception as e:
            raise Exception(f"Error processing debugging payload: {str(e)}")
    
    async def get_session_history(
        self,
        session_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get the version history for a debugging session.
        
        Args:
            session_id: ID of the debugging session
            
        Returns:
            List of version history entries if found, None otherwise
        """
        return await self.session_manager.get_version_history(session_id)
    
    async def revert_session(
        self,
        session_id: str,
        version: int
    ) -> Optional[DebuggingSession]:
        """
        Revert a debugging session to a specific version.
        
        Args:
            session_id: ID of the debugging session
            version: Version number to revert to
            
        Returns:
            The reverted DebuggingSession if successful, None otherwise
        """
        return await self.session_manager.revert_to_version(session_id, version)
    
    async def cleanup(self) -> None:
        """Clean up expired cache entries and temporary files."""
        await self.storage.cleanup_expired_cache()
