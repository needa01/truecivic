"""
Migration runner with better error handling and logging.

Runs Alembic migrations with:
- Timeout handling
- Better error messages
- Idempotency (safe to run multiple times)
- Connection pooling optimizations

Usage:
    python scripts/run_migrations.py
"""

import sys
import os
import logging
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from src.config import settings


def check_database_connection() -> bool:
    """
    Test connection to database before running migrations.
    
    Returns:
        True if connection succeeds, False otherwise
    """
    try:
        from sqlalchemy import create_engine, text
        
        logger.info(f"Testing database connection to: {settings.db.sync_connection_string[:50]}...")
        
        # Use connection pool with optimized settings for migrations
        engine = create_engine(
            settings.db.sync_connection_string,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,  # Verify connections before using
            connect_args={"connect_timeout": 10},
            echo=False
        )
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False


def get_current_migration() -> str:
    """
    Get the current migration revision from the database.
    
    Returns:
        Current revision ID or "None" if no migrations applied
    """
    try:
        from sqlalchemy import create_engine, text
        
        engine = create_engine(
            settings.db.sync_connection_string,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True
        )
        
        with engine.connect() as conn:
            # Check if alembic_version table exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'alembic_version')"
            ))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("No migration history found - will start from initial migration")
                return "None"
            
            # Get current revision
            result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"))
            revision = result.scalar()
            logger.info(f"Current migration: {revision}")
            return revision
            
    except Exception as e:
        logger.warning(f"Could not determine current migration: {str(e)}")
        return "Unknown"


def run_migrations() -> int:
    """
    Run Alembic migrations with proper error handling.
    
    Returns:
        0 if successful, non-zero on error
    """
    try:
        logger.info("=" * 70)
        logger.info("Starting Database Migrations")
        logger.info("=" * 70)
        
        # Check database connection first
        if not check_database_connection():
            logger.error("Cannot proceed - database connection failed")
            return 1
        
        # Get current migration state
        current_revision = get_current_migration()
        logger.info(f"Database state before migrations: {current_revision}")
        
        # Set environment variables for Alembic
        os.environ["PYTHONUNBUFFERED"] = "1"
        
        # Run migrations with timeout
        logger.info("Running: alembic upgrade head")
        logger.info("(This may take a few minutes on first run...)")
        
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=project_root,
            timeout=300,  # 5 minute timeout
            capture_output=False,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Migration failed with return code: {result.returncode}")
            return result.returncode
        
        # Verify migrations completed
        new_revision = get_current_migration()
        logger.info(f"Database state after migrations: {new_revision}")
        
        logger.info("=" * 70)
        logger.info("✅ Migrations completed successfully")
        logger.info("=" * 70)
        
        return 0
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Migration timed out after 5 minutes")
        logger.error("This usually means:")
        logger.error("  1. Database is slow or overloaded")
        logger.error("  2. There's a lock on tables from another process")
        logger.error("  3. The migration is doing heavy work (creating indexes on large tables)")
        return 1
        
    except Exception as e:
        logger.error(f"❌ Migration failed with error: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = run_migrations()
    sys.exit(exit_code)

