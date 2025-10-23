"""Inspect the latest bills feed output and cache setup.

Loads production-style environment variables, initializes the async
PostgreSQL connection, and prints a short preview of the generated feed
so manual debugging remains easy when adjusting feed builders.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env.production")
os.environ.setdefault("PYTHONPATH", str(PROJECT_ROOT))

from src.db.session import Database
from src.feeds.bill_feeds import FeedFormat, LatestBillsFeedBuilder


async def preview_feed(limit: int = 3) -> None:
    """Generate a preview of the latest bills feed and print a snippet."""
    database = Database()
    await database.initialize()
    try:
        async with database.session() as session:
            builder = await LatestBillsFeedBuilder.from_materialized_view(
                session=session,
                feed_url="http://localhost/feed",
                limit=limit,
            )

            rss_xml = builder.generate(FeedFormat.RSS)
            print(rss_xml[:400])
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(preview_feed())
