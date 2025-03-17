"""Initialize Supabase storage buckets and database tables."""

import asyncio
import os
from app.utils.supabase import (
    supabase_admin_client,
    snapshot_storage,
    session_storage
)

def create_storage_buckets():
    """Create required storage buckets if they don't exist."""
    try:
        print("Creating storage buckets...")
        snapshot_storage.ensure_bucket_exists()
        session_storage.ensure_bucket_exists()
        print("Storage buckets created successfully")
    except Exception as e:
        print(f"Error creating storage buckets: {e}")
        raise

def create_tables():
    """Create required database tables if they don't exist."""
    try:
        print("Creating database tables...")
        
        # Read table creation SQL
        tables_path = os.path.join(os.path.dirname(__file__), 'create_tables.sql')
        with open(tables_path, 'r') as f:
            sql = f.read()
        
        # Execute SQL using database function
        supabase_admin_client.rpc(
            'create_tables',
            {
                'sql_commands': sql
            }
        ).execute()
        
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")
        raise

def main():
    """Run all initialization tasks."""
    try:
        create_storage_buckets()
        create_tables()
        print("Initialization completed successfully")
    except Exception as e:
        print(f"Initialization failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
