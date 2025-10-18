"""
Apply schema migration to Railway production database.

This script applies the complete schema migration (votes, debates, committees, etc.)
to the Railway PostgreSQL database.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load production environment
env_file = project_root / ".env.production"
if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print(f"⚠️  Warning: {env_file} not found, using system environment")

from alembic import command
from alembic.config import Config


def apply_railway_migration():
    """Apply pending migrations to Railway database."""
    
    print("=" * 80)
    print("🚀 Applying Schema Migration to Railway Database")
    print("=" * 80)
    print()
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_PUBLIC_URL")
    
    if not database_url:
        print("❌ ERROR: DATABASE_PUBLIC_URL not set in environment")
        print("   Please set DATABASE_PUBLIC_URL in .env.production")
        return 1
    
    if "railway" not in database_url.lower() and "rlwy" not in database_url.lower():
        print("⚠️  WARNING: DATABASE_PUBLIC_URL doesn't appear to be a Railway database")
        print(f"   URL: {database_url}")
        response = input("   Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            print("   Aborted.")
            return 1
    
    print(f"📊 Target Database: {database_url.split('@')[1] if '@' in database_url else 'Railway'}")
    print()
    
    # Configure Alembic
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    
    try:
        # Show current version
        print("📋 Checking current migration version...")
        from alembic.script import ScriptDirectory
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import create_engine
        
        engine = create_engine(database_url)
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_rev = context.get_current_revision()
            print(f"   Current revision: {current_rev or 'None (empty database)'}")
        
        # Show available migrations
        script = ScriptDirectory.from_config(alembic_cfg)
        print()
        print("📦 Available migrations:")
        for revision in script.walk_revisions():
            marker = "✅" if revision.revision == current_rev else "⏳"
            print(f"   {marker} {revision.revision}: {revision.doc}")
        
        print()
        print("🔄 Applying pending migrations...")
        print()
        
        # Apply migrations
        command.upgrade(alembic_cfg, "head")
        
        print()
        print("=" * 80)
        print("✅ Migration Completed Successfully!")
        print("=" * 80)
        print()
        
        # Show final state
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            final_rev = context.get_current_revision()
            print(f"📊 Final revision: {final_rev}")
        
        print()
        print("📋 New tables created:")
        print("   ✅ parties")
        print("   ✅ ridings")
        print("   ✅ votes")
        print("   ✅ vote_records")
        print("   ✅ committees")
        print("   ✅ debates")
        print("   ✅ speeches")
        print("   ✅ documents")
        print("   ✅ embeddings")
        print("   ✅ rankings")
        print()
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Migration Failed!")
        print("=" * 80)
        print()
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = apply_railway_migration()
    sys.exit(exit_code)
