"""Initialize local SQLite database with schema from Alembic migrations."""
import os
import sys
from pathlib import Path
import asyncio

# Force local environment BEFORE any imports
os.environ['ENVIRONMENT'] = 'local'
os.environ['DB_DRIVER'] = 'sqlite+aiosqlite'
os.environ['DB_DATABASE'] = 'parliament_explorer_local.db'

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command
from src.config import settings


async def init_local_database():
    """Initialize local SQLite database with Alembic migrations."""
    print("🏛️  TrueCivic Local Database Initialization")
    print("=" * 60)
    
    # Get database path
    db_path = Path(project_root) / 'parliament_explorer_local.db'
    print(f"\n📍 Database Path: {db_path}")
    print(f"📍 Connection String: {settings.db.sync_connection_string}")
    
    # Remove existing database if it exists
    if db_path.exists():
        print(f"🗑️  Removing existing database...")
        db_path.unlink()
    
    # Create Alembic config
    alembic_ini = project_root / 'alembic.ini'
    if not alembic_ini.exists():
        print(f"❌ Error: alembic.ini not found at {alembic_ini}")
        return False
    
    print(f"\n📝 Running Alembic migrations...")
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option('script_location', str(project_root / 'alembic'))
    
    # Note: alembic/env.py will use settings.db.sync_connection_string
    # which is already configured via environment variables above
    
    try:
        # Upgrade to head (run all migrations)
        command.upgrade(alembic_cfg, "head")
        print(f"\n✅ Database schema created successfully!")
        
        # Verify tables were created
        from sqlalchemy import create_engine, inspect
        engine = create_engine(settings.db.sync_connection_string)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n📊 Created Tables ({len(tables)}):")
        for table in sorted(tables):
            print(f"  ✓ {table}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(init_local_database())
    sys.exit(0 if success else 1)
