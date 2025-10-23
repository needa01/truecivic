"""
Validate backfill results by summarizing key table counts.

Usage:
    python scripts/validate_backfill_results.py --window-minutes 90
"""

from __future__ import annotations

import argparse
import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import asyncpg
from dotenv import load_dotenv

# MARK: configuration helpers
ROOT_DIR = Path(__file__).resolve().parents[1]


def load_environment(env: str | None) -> None:
    """Load environment variables, defaulting to production."""
    env = (env or "production").lower()
    candidates = {
        "production": [ROOT_DIR / ".env.production"],
        "local": [ROOT_DIR / ".env.local", ROOT_DIR / ".env"],
    }

    for path in candidates.get(env, []) + [ROOT_DIR / ".env"]:
        if path.exists():
            load_dotenv(path, override=True)
            return

    load_dotenv(override=True)


async def connect_with_fallback() -> asyncpg.Connection:
    """Connect to the database, preferring private URLs over public ones."""

    candidate_names: List[str] = [
        "DATABASE_URL",
        "DATABASE_POOLING_URL",
        "DATABASE_PUBLIC_URL",
    ]

    candidates: List[Tuple[str, str]] = []
    for name in candidate_names:
        value = os.environ.get(name)
        if value:
            candidates.append((name, value))

    if not candidates:
        raise RuntimeError(
            "No database connection string found. Set DATABASE_URL or DATABASE_PUBLIC_URL."
        )

    errors: List[Tuple[str, Exception]] = []
    for name, dsn in candidates:
        try:
            connection = await asyncpg.connect(dsn=dsn)
            print(f"Connected using {name}.")
            return connection
        except Exception as exc:  # noqa: PERF203 - deliberate broad catch to capture connection reasons
            errors.append((name, exc))

    formatted_errors = "\n".join(
        f" - {name}: {type(error).__name__}: {error}" for name, error in errors
    )
    raise RuntimeError(
        "Failed to connect using available database URLs:\n" f"{formatted_errors}"
    )


# MARK: validation logic
async def summarize(window_minutes: int, environment: str | None) -> None:
    load_environment(environment)

    window_start = datetime.now(UTC) - timedelta(minutes=window_minutes)
    window_value = window_start.replace(tzinfo=None)

    queries: Dict[str, Tuple[str, str]] = {
        "debates": (
            "SELECT COUNT(*) FROM debates",
            "SELECT COUNT(*) FROM debates WHERE created_at >= $1",
        ),
        "speeches": (
            "SELECT COUNT(*) FROM speeches",
            "SELECT COUNT(*) FROM speeches WHERE created_at >= $1",
        ),
        "documents (speech)": (
            "SELECT COUNT(*) FROM documents WHERE entity_type = 'speech'",
            "SELECT COUNT(*) FROM documents WHERE entity_type = 'speech' AND created_at >= $1",
        ),
        "embeddings": (
            "SELECT COUNT(*) FROM embeddings",
            "SELECT COUNT(*) FROM embeddings WHERE created_at >= $1",
        ),
    }

    connection = await connect_with_fallback()

    print(f"Validation window start (UTC): {window_start.isoformat()}\n")

    for label, (total_sql, window_sql) in queries.items():
        total = await connection.fetchval(total_sql)
        recent = await connection.fetchval(window_sql, window_value)
        print(f"{label:<22} total={total:>8}  recent={recent:>6}")

    print("\nSample recent debates:")
    rows = await connection.fetch(
        """
        SELECT hansard_id, document_url, sitting_date, created_at
        FROM debates
        WHERE created_at >= $1
        ORDER BY created_at DESC
        LIMIT 5
        """,
        window_value,
    )
    if not rows:
        print(" (no debates created in the selected window)")
    else:
        for row in rows:
            created = row["created_at"].isoformat() if row["created_at"] else "unknown"
            sitting = row["sitting_date"].isoformat() if row["sitting_date"] else "unknown"
            doc = row["document_url"] or "<no document>"
            print(f" - hansard_id={row['hansard_id']} (sitting={sitting}, created={created})")
            print(f"   document: {doc}")

    await connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate backfill results")
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=90,
        help="How far back (in minutes) to consider records as recent",
    )
    parser.add_argument(
        "--env",
        default="production",
        choices=("production", "local"),
        help="Environment configuration to load",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(summarize(args.window_minutes, args.env))


if __name__ == "__main__":
    main()
