"""
Run Alembic migrations with Railway production database

Usage:
    python scripts/run_migrations.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env.production
from dotenv import load_dotenv
env_file = Path(__file__).parent.parent / ".env.production"
load_dotenv(env_file)

# Set DB environment variables from DATABASE_PUBLIC_URL
db_url = os.getenv("DATABASE_PUBLIC_URL", "")
if db_url:
    # Parse: postgresql://postgres:password@host:port/database
    from urllib.parse import urlparse
    parsed = urlparse(db_url)
    
    os.environ["DB_DRIVER"] = "postgresql+psycopg2"
    os.environ["DB_HOST"] = parsed.hostname
    os.environ["DB_PORT"] = str(parsed.port)
    os.environ["DB_DATABASE"] = parsed.path.lstrip("/")
    os.environ["DB_USERNAME"] = parsed.username
    os.environ["DB_PASSWORD"] = parsed.password
    
    print(f"🔗 Connecting to: {parsed.hostname}:{parsed.port}/{parsed.path.lstrip('/')}")
else:
    print("❌ DATABASE_PUBLIC_URL not found in .env.production")
    sys.exit(1)

# Now run alembic
from alembic.config import Config
from alembic import command

alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
alembic_cfg.set_main_option("script_location", str(Path(__file__).parent.parent / "alembic"))

print("🚀 Running migrations...")
try:
    command.upgrade(alembic_cfg, "head")
    print("✅ Migrations completed successfully!")
except Exception as e:
    print(f"❌ Migration failed: {str(e)}")
    sys.exit(1)
