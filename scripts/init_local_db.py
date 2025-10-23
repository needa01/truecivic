"""Initialize the PostgreSQL/pgvector database using Alembic migrations."""

import os
import sys
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, inspect


PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_environment(files: Iterable[Path]) -> None:
    """Load environment variables from .env files if present."""
    for env_file in files:
        if env_file.exists():
            load_dotenv(env_file, override=False)


# Ensure baseline environment before importing settings
load_environment((PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env"))
os.environ.setdefault("ENVIRONMENT", "local")

from src.config import settings


def _mask_connection(url: str) -> str:
    """Mask connection string credentials for safe logging."""
    if "@" not in url:
        return url
    prefix, suffix = url.split("@", 1)
    if ":" in prefix:
        prefix = prefix.split(":", 1)[0]
    return f"{prefix}:***@{suffix}"


def run_migrations() -> bool:
    """Execute Alembic migrations against the configured PostgreSQL database."""
    print("🏛️  TrueCivic Database Initialization (PostgreSQL + pgvector)")
    print("=" * 70)

    try:
        connection_string = settings.db.sync_connection_string
    except ValueError as exc:
        print(f"❌ Configuration error: {exc}")
        print("Ensure DB_* environment variables or DATABASE_URL point to PostgreSQL with pgvector enabled.")
        return False

    print(f"\n🔗 Connection: {_mask_connection(connection_string)}")

    alembic_ini = PROJECT_ROOT / "alembic.ini"
    if not alembic_ini.exists():
        print(f"❌ Error: alembic.ini not found at {alembic_ini}")
        return False

    print("\n📝 Running Alembic migrations...")
    alembic_cfg = Config(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:  # pragma: no cover - CLI feedback path
        print(f"\n❌ Migration failed: {exc}")
        import traceback
        traceback.print_exc()
        return False

    # Verify tables
    engine = create_engine(connection_string)
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())

    print("\n✅ Database schema is up to date.")
    print(f"📊 Tables provisioned ({len(tables)}):")
    for table in tables:
        print(f"  • {table}")

    return True


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
