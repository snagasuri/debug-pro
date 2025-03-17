"""Setup database tables and functions using Supabase client."""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()  # Load .env.local by default
if os.getenv("TEST_MODE"):
    load_dotenv(".env.test")

def setup_database():
    """Setup database tables and functions."""
    try:
        # Initialize Supabase client with service role key
        supabase: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        )
        
        print("Setting up database...")
        
        # Read SQL commands
        with open(os.path.join(os.path.dirname(__file__), 'setup.sql'), 'r') as f:
            sql = f.read()
            
        # Split SQL into individual commands
        commands = sql.split(';')
        
        # Execute each command separately
        for command in commands:
            command = command.strip()
            if command:  # Skip empty commands
                try:
                    result = supabase.postgrest.schema('public').execute(command)
                    print(f"Executed command successfully")
                except Exception as e:
                    print(f"Error executing command: {e}")
                    raise
                    
        print("Database setup completed successfully")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        raise

if __name__ == "__main__":
    setup_database()
