"""Manual one-off migration for the `committee_meetings` table.

This script is designed to be run exactly once against the production
Railway database. It performs a defensive set of operations to ensure
that the `committee_meetings` table matches the schema expected by the
Alembic migration `4_committee_meetings` and that the natural-key unique
index is present without duplicate data blocking it.

Steps executed (unless --dry-run is provided):

1. Load production environment variables from `.env.production` so that
   `src.config.settings` resolves the correct database connection.
2. Ensure the `committee_meetings` table exists with the required
   columns and foreign key by creating it if it is missing.
3. Remove duplicate rows that would prevent the natural-key index from
   being created (keeping the earliest record per natural key).
4. Create the supporting indexes, including the
   `uq_committee_meeting_natural_key` unique index, if any are missing.
5. Optionally update the `alembic_version` table to mark
   `4_committee_meetings` as applied when the database is still
   reporting `3_personalization` (to unblock the subsequent
   `5_api_keys` migration).
6. Provide a verification summary of the table state.

Usage:
    python scripts/manual_committee_meetings_migration.py
    python scripts/manual_committee_meetings_migration.py --dry-run
    python scripts/manual_committee_meetings_migration.py --env-file .env.production

The script is idempotent and safe to re-run: every operation uses
`IF NOT EXISTS` guards or only mutates rows that violate the desired
constraints.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

# Optional dependency: python-dotenv. Provide a minimal fallback loader so the
# script can run even if the package is not installed in the execution
# environment (e.g., CI or ad-hoc hosts).
try:  # pragma: no cover - runtime dependency detection
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback loader
    def load_dotenv(path: Path, override: bool = False) -> None:
        if not path.exists():
            return

        logging.warning(
            "python-dotenv is not installed; using a minimal .env loader for %s",
            path,
        )

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if not override and key in os.environ:
                continue

            os.environ[key] = value
from typing import Any

try:  # pragma: no cover - optional runtime dependency
    from sqlalchemy import (
        Column,
        DateTime,
        ForeignKeyConstraint,
        Integer,
        JSON,
        MetaData,
        String,
        Table,
        Text,
        create_engine,
        inspect,
        text,
    )
    from sqlalchemy.engine import Engine
    from sqlalchemy.engine.url import make_url
    from sqlalchemy.exc import SQLAlchemyError
    SQLALCHEMY_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover - degraded mode for dry runs
    Column = DateTime = ForeignKeyConstraint = Integer = JSON = MetaData = String = Table = Text = None  # type: ignore
    create_engine = inspect = text = None  # type: ignore
    Engine = Any  # type: ignore
    make_url = None  # type: ignore

    class SQLAlchemyError(Exception):
        """Fallback SQLAlchemy error placeholder."""

    SQLALCHEMY_AVAILABLE = False

# Ensure project root on PYTHONPATH before importing internal modules
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_environment(env_file: Path) -> None:
    """Load environment variables from the given .env file."""
    if not env_file.exists():
        logging.warning("Environment file %s not found; relying on existing environment", env_file)
        return

    load_dotenv(env_file, override=True)
    logging.info("Loaded environment from %s", env_file)


# Load env immediately so subsequent helpers can read from os.environ.
load_environment(PROJECT_ROOT / ".env.production")


@dataclass
class MigrationResult:
    """Summary of migration actions performed."""

    table_created: bool = False
    duplicates_before: int = 0
    duplicates_removed: int = 0
    indexes_created: List[str] = field(default_factory=list)
    final_revision: Optional[str] = None


def mask_connection_url(url: str) -> str:
    """Mask credentials in a connection URL for logging."""
    if make_url is None:  # Fallback when SQLAlchemy not installed
        if "@" in url:
            return "***@" + url.split("@", 1)[1]
        return url
    try:
        parsed = make_url(url)
        if parsed.password is not None:
            parsed = parsed.set(password="***")
        return str(parsed)
    except Exception:  # pragma: no cover - defensive logging helper
        return url


def resolve_database_url() -> str:
    """Resolve the synchronous database URL from environment variables."""
    url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("DATABASE_URL")
    if url:
        # Ensure synchronous driver for migrations
        url = url.replace("+asyncpg", "+psycopg")
        if "+psycopg" not in url and url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    driver = os.getenv("DB_DRIVER", "postgresql+psycopg")
    driver = driver.replace("+asyncpg", "+psycopg")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT")
    database = os.getenv("DB_DATABASE", "postgres")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")

    auth = ""
    if username:
        auth = username
        if password:
            auth = f"{auth}:{password}"
        auth = f"{auth}@"

    if port:
        host = f"{host}:{port}"

    return f"{driver}://{auth}{host}/{database}"


def create_engine_from_settings() -> Any:
    """Create a SQLAlchemy engine using the synchronous connection string."""
    if not SQLALCHEMY_AVAILABLE:
        raise RuntimeError(
            "SQLAlchemy is not installed. Install project requirements before running the manual migration."
        )
    url = resolve_database_url()
    if not url:
        raise RuntimeError("Database connection string could not be resolved from settings")

    logging.info("Connecting to %s", mask_connection_url(url))

    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    return engine


def ensure_table_schema(engine: Any) -> bool:
    """Ensure the committee_meetings table exists with the expected schema."""
    if not SQLALCHEMY_AVAILABLE:
        raise RuntimeError("SQLAlchemy is required to manipulate the database schema")
    metadata = MetaData()
    committee_meetings = Table(
        "committee_meetings",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("committee_id", Integer, nullable=False),
        Column("meeting_number", Integer, nullable=False),
        Column("parliament", Integer, nullable=False),
        Column("session", Integer, nullable=False),
        Column("meeting_date", DateTime, nullable=False),
        Column("time_of_day", String(50), nullable=True),
        Column("title_en", Text, nullable=True),
        Column("title_fr", Text, nullable=True),
        Column("meeting_type", String(100), nullable=True),
        Column("room", String(200), nullable=True),
        Column("witnesses", JSON, nullable=True),
        Column("documents", JSON, nullable=True),
        Column("source_url", String(500), nullable=True),
        Column("created_at", DateTime, nullable=False, server_default=text("now()")),
        Column("updated_at", DateTime, nullable=False, server_default=text("now()")),
        ForeignKeyConstraint(
            ["committee_id"],
            ["committees.id"],
            name="fk_committee_meetings_committee",
            ondelete="CASCADE",
        ),
    )

    with engine.begin() as connection:
        inspector = inspect(connection)
        tables = inspector.get_table_names()
        if "committee_meetings" in tables:
            logging.info("Table committee_meetings already present")
            return False

        logging.info("Creating committee_meetings table fresh")
        metadata.create_all(bind=connection, tables=[committee_meetings], checkfirst=True)
        return True


def fetch_duplicate_count(connection) -> int:
    """Return the number of duplicate rows by natural key."""
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT committee_id, meeting_number, parliament, session
                FROM committee_meetings
                GROUP BY committee_id, meeting_number, parliament, session
                HAVING COUNT(*) > 1
            ) dup
            """
        )
    )
    row = result.one()
    return int(row[0])


def remove_duplicates(connection) -> int:
    """Remove duplicate committee meetings, retaining the oldest record per key."""
    result = connection.execute(
        text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY committee_id, meeting_number, parliament, session
                        ORDER BY created_at ASC, id ASC
                    ) AS row_rank
                FROM committee_meetings
            )
            DELETE FROM committee_meetings
            WHERE id IN (
                SELECT id FROM ranked WHERE row_rank > 1
            )
            """
        )
    )
    # rowcount may be -1 for some dialects; coerce to int defensively
    deleted = result.rowcount if result.rowcount is not None and result.rowcount >= 0 else 0
    return int(deleted)


INDEX_STATEMENTS: Iterable[tuple[str, str]] = (
    (
        "idx_committee_meetings_committee",
        "CREATE INDEX IF NOT EXISTS idx_committee_meetings_committee ON committee_meetings (committee_id)",
    ),
    (
        "idx_committee_meetings_date",
        "CREATE INDEX IF NOT EXISTS idx_committee_meetings_date ON committee_meetings (meeting_date)",
    ),
    (
        "idx_committee_meetings_parliament_session",
        "CREATE INDEX IF NOT EXISTS idx_committee_meetings_parliament_session ON committee_meetings (parliament, session)",
    ),
    (
        "idx_committee_meetings_committee_date",
        "CREATE INDEX IF NOT EXISTS idx_committee_meetings_committee_date ON committee_meetings (committee_id, meeting_date)",
    ),
    (
        "uq_committee_meeting_natural_key",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_committee_meeting_natural_key ON committee_meetings (committee_id, meeting_number, parliament, session)",
    ),
)


def ensure_indexes(connection) -> List[str]:
    """Ensure all supporting indexes exist, returning the names verified."""
    ensured: List[str] = []
    for index_name, statement in INDEX_STATEMENTS:
        connection.execute(text(statement))
        ensured.append(index_name)
    logging.info("Ensured committee_meetings indexes are present")
    return ensured


def ensure_revision_flag(connection) -> Optional[str]:
    """Ensure alembic_version reflects at least 4_committee_meetings."""
    try:
        rows = connection.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    except SQLAlchemyError:
        logging.warning("alembic_version table not found; skipping revision update")
        return None

    if not rows:
        logging.info("alembic_version table empty; inserting 4_committee_meetings")
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES (:rev)"), {"rev": "4_committee_meetings"})
        return "4_committee_meetings"

    if len(rows) > 1:
        logging.warning("Multiple alembic_version rows detected; leaving unchanged")
        return rows[-1][0]

    current = rows[0][0]
    logging.info("Current alembic revision: %s", current)

    if current == "3_personalization":
        logging.info("Updating alembic_version to 4_committee_meetings")
        connection.execute(text("UPDATE alembic_version SET version_num = :rev"), {"rev": "4_committee_meetings"})
        return "4_committee_meetings"

    return current


def run_manual_migration(dry_run: bool) -> MigrationResult:
    """Execute the manual migration pipeline."""
    result = MigrationResult()
    database_url = resolve_database_url()

    if dry_run:
        logging.info("Dry run requested; no changes will be applied.")
        # Just display the connection string for confirmation
        logging.info("Target database: %s", mask_connection_url(database_url))
        return result

    if not SQLALCHEMY_AVAILABLE:
        raise RuntimeError(
            "SQLAlchemy is not installed in the current environment. Install requirements.txt before executing."
        )

    engine = create_engine_from_settings()

    # Step 1: ensure table exists
    table_created = ensure_table_schema(engine)
    result.table_created = table_created

    with engine.begin() as connection:
        # Step 2: check duplicates
        duplicates_before = fetch_duplicate_count(connection)
        result.duplicates_before = duplicates_before
        if duplicates_before > 0:
            logging.info("Found %s duplicate natural keys; cleaning up", duplicates_before)
            removed = remove_duplicates(connection)
            logging.info("Removed %s duplicate rows", removed)
            result.duplicates_removed = removed
        else:
            logging.info("No duplicate committee meeting rows detected")

        # Step 3: ensure indexes (always attempt to create to guarantee presence)
        created = ensure_indexes(connection)
        result.indexes_created = created

        # Step 4: ensure revision flag
        revision = ensure_revision_flag(connection)
        result.final_revision = revision

    # Verification: duplicates after clean-up
    with engine.begin() as connection:
        remaining_duplicates = fetch_duplicate_count(connection)
        if remaining_duplicates > 0:
            logging.warning("Duplicates remain after cleanup (%s keys)", remaining_duplicates)
        else:
            logging.info("Verification: no duplicate keys remain")

    return result


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True,
    )


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual one-off committee meetings migration")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load configuration and print actions without mutating the database",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=PROJECT_ROOT / ".env.production",
        help="Path to the environment file to load (default: .env.production)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )
    args = parser.parse_args(argv)

    # Reload environment if a different path is provided via CLI
    if args.env_file != PROJECT_ROOT / ".env.production":
        load_environment(args.env_file)

    return args


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    try:
        result = run_manual_migration(dry_run=args.dry_run)
    except Exception as exc:  # pragma: no cover - top-level safety
        logging.error("Manual migration failed: %s", exc, exc_info=True)
        return 1

    if args.dry_run:
        logging.info("Dry run completed – no changes applied.")
        return 0

    logging.info("Migration summary: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
