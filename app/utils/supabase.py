"""Supabase client configuration and utilities."""

import os
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# Load environment variables
from dotenv import load_dotenv
load_dotenv()  # Load .env.local by default
if os.getenv("TEST_MODE"):
    load_dotenv(".env.test")  # Override with test environment if in test mode

# Configuration
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# Initialize clients
def get_supabase_client():
    """Get configured Supabase client."""
    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
        options=ClientOptions(
            schema="public",
            headers={"X-Client-Info": "deebo-debug-assistant"}
        )
    )

def get_supabase_admin_client():
    """Get configured Supabase admin client."""
    return create_client(
        SUPABASE_URL,
        SUPABASE_SERVICE_ROLE_KEY,
        options=ClientOptions(
            schema="public",
            headers={"X-Client-Info": "deebo-debug-assistant-admin"}
        )
    )

# Create client instances
supabase_client = get_supabase_client()
supabase_admin_client = get_supabase_admin_client()

class SupabaseStorage:
    """Enhanced Supabase Storage operations."""
    
    def __init__(self, bucket: str, client: Optional[Client] = None):
        self.bucket = bucket
        # Use admin client by default for storage operations to bypass RLS
        self.client = client or supabase_admin_client
    
    def ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            # Try to create the bucket, ignore if it already exists
            self.client.storage.create_bucket(
                self.bucket,
                options={"public": False}
            )
        except Exception as e:
            # Ignore if bucket already exists (409 Duplicate)
            if "409" not in str(e):
                raise e
    
    def _generate_content_hash(self, data: bytes) -> str:
        """Generate SHA-256 hash of content."""
        return hashlib.sha256(data).hexdigest()
    
    async def upload_file(
        self,
        path: str,
        data: bytes,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload file with metadata."""
        content_hash = self._generate_content_hash(data)
        
        # Store metadata if provided
        if metadata:
            metadata_path = f"{path}.metadata.json"
            metadata_data = json.dumps({
                "content_hash": content_hash,
                "timestamp": datetime.utcnow().isoformat(),
                **metadata
            }).encode()
            try:
                self.client.storage.from_(self.bucket).upload(
                    metadata_path,
                    metadata_data,
                    {"upsert": "true"}
                )
            except Exception as e:
                if "409" not in str(e):  # Ignore duplicate errors
                    raise
        
        # Upload main file
        try:
            self.client.storage.from_(self.bucket).upload(
                path,
                data,
                {"contentType": "application/json", "upsert": "true"}
            )
        except Exception as e:
            if "409" not in str(e):  # Ignore duplicate errors
                raise
        
        return {
            "key": path,
            "content_hash": content_hash,
            "size": len(data)
        }
    
    async def download_file(
        self,
        path: str,
        include_metadata: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Download file and optionally its metadata."""
        data = self.client.storage.from_(self.bucket).download(path)
        if not data:
            return None
            
        result = {"data": data}
        
        if include_metadata:
            metadata_path = f"{path}.metadata.json"
            metadata_data = self.client.storage.from_(self.bucket).download(
                metadata_path
            )
            if metadata_data:
                result["metadata"] = json.loads(metadata_data.decode())
        
        return result
    
    async def list_files(
        self,
        prefix: Optional[str] = None,
        include_metadata: bool = False
    ) -> List[Dict[str, Any]]:
        """List files with optional metadata."""
        files = self.client.storage.from_(self.bucket).list(prefix or "")
        
        if not include_metadata:
            return files
            
        # Fetch metadata for each file
        enhanced_files = []
        for file in files:
            if not file["name"].endswith(".metadata.json"):
                metadata_path = f"{file['name']}.metadata.json"
                metadata_data = self.client.storage.from_(self.bucket).download(
                    metadata_path
                )
                if metadata_data:
                    file["metadata"] = json.loads(metadata_data.decode())
                enhanced_files.append(file)
        
        return enhanced_files
    
    async def delete_file(self, path: str, delete_metadata: bool = True) -> bool:
        """Delete file and optionally its metadata."""
        self.client.storage.from_(self.bucket).remove([path])
        
        if delete_metadata:
            metadata_path = f"{path}.metadata.json"
            self.client.storage.from_(self.bucket).remove([metadata_path])
        
        return True

# Storage instances for different data types
snapshot_storage = SupabaseStorage("snapshots")
session_storage = SupabaseStorage("sessions")
