"""Verify that the PostgreSQL/pgvector database contains expected seed data."""

import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).parent.parent


def load_environment(files: Iterable[Path]) -> None:
    for env_file in files:
        if env_file.exists():
            load_dotenv(env_file, override=False)


load_environment((PROJECT_ROOT / ".env.local", PROJECT_ROOT / ".env"))
os.environ.setdefault("ENVIRONMENT", "local")

from src.config import settings


def fetch_scalar(connection, query: str) -> int:
    result = connection.execute(text(query))
    value = result.scalar()
    return int(value or 0)


def main() -> int:
    try:
        engine = create_engine(settings.db.sync_connection_string)
    except ValueError as exc:
        print(f"❌ Configuration error: {exc}")
        return 1

    with engine.connect() as connection:
        print("🏛️  TrueCivic Data Snapshot (PostgreSQL + pgvector)")
        print("=" * 70)

        totals = {
            "bills": fetch_scalar(connection, "SELECT COUNT(*) FROM bills"),
            "politicians": fetch_scalar(connection, "SELECT COUNT(*) FROM politicians"),
            "votes": fetch_scalar(connection, "SELECT COUNT(*) FROM votes"),
            "debates": fetch_scalar(connection, "SELECT COUNT(*) FROM debates"),
            "committees": fetch_scalar(connection, "SELECT COUNT(*) FROM committees"),
        }

        print("\n� Totals:")
        for table, count in totals.items():
            print(f"  • {table}: {count}")

        sample_query = text("""
            SELECT number, title_en
            FROM bills
            ORDER BY created_at DESC
            LIMIT 5
        """)
        rows = connection.execute(sample_query).fetchall()

        print("\n📋 Latest bills:")
        for number, title in rows:
            snippet = (title or "").strip()
            snippet = snippet[:80] + ("..." if len(snippet) > 80 else "")
            print(f"  • {number}: {snippet}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
