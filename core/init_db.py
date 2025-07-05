#!/usr/bin/env python3
"""
Database initialization script.
Run this to create all database tables.
"""

import sys
import os
from pathlib import Path

# Add the core directory to the Python path
core_dir = Path(__file__).parent
sys.path.insert(0, str(core_dir))

# Ensure we can find the local.env file
if not os.getenv("ENV_FILE"):
    env_file = core_dir.parent / "local.env"
    if env_file.exists():
        os.environ["ENV_FILE"] = str(env_file)

def main():
    """Initialize the database schema."""
    try:
        from configs.database import init_db
        
        print("🗃️  Initializing database schema...")
        print(f"📁 Working directory: {os.getcwd()}")
        print(f"📄 Environment file: {os.getenv('ENV_FILE', 'Not set')}")
        
        # Test database connection first
        print("🔌 Testing database connection...")
        from configs.database import engine
        from sqlmodel import text
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
        
        # Initialize the database
        init_db()
        
        print("✅ Database schema created successfully!")
        print("🎉 Database initialization complete!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        print(f"📊 Error type: {type(e).__name__}")
        
        # Print more detailed error info for debugging
        import traceback
        print("\n📋 Full error traceback:")
        traceback.print_exc()
        
        sys.exit(1)

if __name__ == "__main__":
    main() 