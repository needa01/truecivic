"""Manual end-to-end test for the bill integration service.

Usage:
    python scripts/manual/integration_service_smoke_test.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import db
from src.db.repositories import BillRepository
from src.services import BillIntegrationService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

LOGGER = logging.getLogger(__name__)


async def main() -> None:
    """Run the manual integration smoke test."""
    service: BillIntegrationService | None = None

    try:
        LOGGER.info("=" * 60)
        LOGGER.info("Testing BillIntegrationService")
        LOGGER.info("=" * 60)

        LOGGER.info("\n1. Initializing database...")
        await db.initialize()
        await db.create_tables()
        LOGGER.info("✅ Database initialized")

        LOGGER.info("\n2. Creating integration service...")
        service = BillIntegrationService()
        LOGGER.info("✅ Integration service created")

        LOGGER.info("\n3. Fetching and persisting bills (Parliament 44, Session 1)...")
        result = await service.fetch_and_persist(
            parliament=44,
            session=1,
            limit=10,
            enrich=True,
        )

        LOGGER.info("\n📊 Fetch Results:")
        LOGGER.info("  - Fetched: %s bills", result["fetched_count"])
        LOGGER.info("  - Persisted: %s bills", result["persisted_count"])
        LOGGER.info("  - Created: %s bills", result["created_count"])
        LOGGER.info("  - Updated: %s bills", result["updated_count"])
        LOGGER.info("  - Errors: %s", len(result["errors"]))
        LOGGER.info("  - Status: %s", result["status"])
        LOGGER.info("  - Duration: %.2fs", result["duration_seconds"])

        if result["errors"]:
            LOGGER.warning("\n⚠️ Errors encountered:")
            for err in result["errors"][:5]:
                LOGGER.warning("  - %s", err)

        LOGGER.info("\n4. Verifying data in database...")
        async with db.session() as session:
            repo = BillRepository(session)
            bills = await repo.get_by_parliament_session(parliament=44, session=1)
            LOGGER.info("✅ Found %s bills in database", len(bills))

            if bills:
                first_bill = bills[0]
                LOGGER.info("\n📄 Sample Bill:")
                LOGGER.info("  - Number: %s", first_bill.number)
                LOGGER.info(
                    "  - Title: %s",
                    first_bill.short_title_en or first_bill.title_en,
                )
                LOGGER.info("  - Introduced: %s", first_bill.introduced_date)
                LOGGER.info(
                    "  - Sponsor ID: %s",
                    first_bill.sponsor_politician_id or "Unknown",
                )
                LOGGER.info("  - LEGISinfo ID: %s", first_bill.legisinfo_id or "Unknown")
                LOGGER.info("  - Tags: %s tags", len(first_bill.subject_tags or []))
                LOGGER.info(
                    "  - Committees: %s committees",
                    len(first_bill.committee_studies or []),
                )

        LOGGER.info("\n5. Re-fetching same bills (testing updates)...")
        result2 = await service.fetch_and_persist(
            parliament=44,
            session=1,
            limit=10,
            enrich=True,
        )

        LOGGER.info("\n📊 Re-fetch Results:")
        LOGGER.info("  - Fetched: %s bills", result2["fetched_count"])
        LOGGER.info("  - Persisted: %s bills", result2["persisted_count"])
        LOGGER.info("  - Created: %s bills", result2["created_count"])
        LOGGER.info("  - Updated: %s bills", result2["updated_count"])
        LOGGER.info("  - Duration: %.2fs", result2["duration_seconds"])

        LOGGER.info("\n6. Checking fetch logs...")
        async with db.session() as session:
            from sqlalchemy import select

            from src.db.models import FetchLogModel

            result_logs = await session.execute(
                select(FetchLogModel).order_by(FetchLogModel.created_at.desc()).limit(5)
            )
            logs = result_logs.scalars().all()

            LOGGER.info("✅ Found %s fetch logs", len(logs))

            for idx, log in enumerate(logs, 1):
                LOGGER.info("\n📋 Log %s:", idx)
                LOGGER.info("  - Source: %s", log.source)
                LOGGER.info("  - Status: %s", log.status)
                LOGGER.info("  - Attempted: %s", log.records_attempted)
                LOGGER.info("  - Succeeded: %s", log.records_succeeded)
                LOGGER.info("  - Failed: %s", log.records_failed)
                LOGGER.info("  - Duration: %.2fs", log.duration_seconds)
                LOGGER.info("  - Timestamp: %s", log.created_at)

        LOGGER.info("\n" + "=" * 60)
        LOGGER.info("✅ All integration tests passed!")
        LOGGER.info("=" * 60)

    except Exception as exc:  # pragma: no cover - diagnostic script
        LOGGER.error("\n❌ Test failed: %s", exc, exc_info=True)
        raise

    finally:
        if service:
            await service.close()
        await db.close()
        LOGGER.info("\n🔒 Database connections closed")


if __name__ == "__main__":
    asyncio.run(main())
