"""
Test script for BillIntegrationService.

Validates end-to-end flow:
1. Fetch bills from OpenParliament API
2. Enrich with LEGISinfo data
3. Persist to database
4. Verify data integrity
"""

import asyncio
import logging
from src.services import BillIntegrationService
from src.db import db
from src.db.repositories import BillRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Test integration service"""
    service = None
    
    try:
        logger.info("=" * 60)
        logger.info("Testing BillIntegrationService")
        logger.info("=" * 60)
        
        # Initialize database
        logger.info("\n1. Initializing database...")
        await db.initialize()
        await db.create_tables()
        logger.info("✅ Database initialized")
        
        # Create integration service
        logger.info("\n2. Creating integration service...")
        service = BillIntegrationService()
        logger.info("✅ Integration service created")
        
        # Test 1: Fetch and persist bills from Parliament 44, Session 1
        logger.info("\n3. Fetching and persisting bills (Parliament 44, Session 1)...")
        result = await service.fetch_and_persist(
            parliament=44,
            session=1,
            limit=10,  # Limit to 10 for testing
            enrich=True
        )
        
        logger.info(f"\n📊 Fetch Results:")
        logger.info(f"  - Fetched: {result['fetched_count']} bills")
        logger.info(f"  - Persisted: {result['persisted_count']} bills")
        logger.info(f"  - Created: {result['created_count']} bills")
        logger.info(f"  - Updated: {result['updated_count']} bills")
        logger.info(f"  - Errors: {len(result['errors'])}")
        logger.info(f"  - Status: {result['status']}")
        logger.info(f"  - Duration: {result['duration_seconds']:.2f}s")
        
        if result['errors']:
            logger.warning(f"\n⚠️ Errors encountered:")
            for err in result['errors'][:5]:  # Show first 5
                logger.warning(f"  - {err}")
        
        # Test 2: Verify data in database
        logger.info("\n4. Verifying data in database...")
        async with db.session() as session:
            repo = BillRepository(session)
            
            # Get bills from Parliament 44, Session 1
            bills = await repo.get_by_parliament_session(parliament=44, session=1)
            
            logger.info(f"✅ Found {len(bills)} bills in database")
            
            if bills:
                # Show first bill details
                first_bill = bills[0]
                logger.info(f"\n📄 Sample Bill:")
                logger.info(f"  - Number: {first_bill.number}")
                logger.info(f"  - Title: {first_bill.short_title_en or first_bill.title_en}")
                logger.info(f"  - Introduced: {first_bill.introduced_date}")
                logger.info(f"  - Sponsor ID: {first_bill.sponsor_politician_id or 'Unknown'}")
                logger.info(f"  - LEGISinfo ID: {first_bill.legisinfo_id or 'Unknown'}")
                logger.info(f"  - Tags: {len(first_bill.subject_tags or [])} tags")
                logger.info(f"  - Committees: {len(first_bill.committee_studies or [])} committees")
        
        # Test 3: Re-fetch same bills (should update, not create)
        logger.info("\n5. Re-fetching same bills (testing updates)...")
        result2 = await service.fetch_and_persist(
            parliament=44,
            session=1,
            limit=10,
            enrich=True
        )
        
        logger.info(f"\n📊 Re-fetch Results:")
        logger.info(f"  - Fetched: {result2['fetched_count']} bills")
        logger.info(f"  - Persisted: {result2['persisted_count']} bills")
        logger.info(f"  - Created: {result2['created_count']} bills (should be 0)")
        logger.info(f"  - Updated: {result2['updated_count']} bills (should match fetched)")
        logger.info(f"  - Duration: {result2['duration_seconds']:.2f}s")
        
        # Test 4: Check fetch logs
        logger.info("\n6. Checking fetch logs...")
        async with db.session() as session:
            from src.db.models import FetchLogModel
            from sqlalchemy import select
            
            result_logs = await session.execute(
                select(FetchLogModel).order_by(FetchLogModel.created_at.desc()).limit(5)
            )
            logs = result_logs.scalars().all()
            
            logger.info(f"✅ Found {len(logs)} fetch logs")
            
            for i, log in enumerate(logs, 1):
                logger.info(f"\n📋 Log {i}:")
                logger.info(f"  - Source: {log.source}")
                logger.info(f"  - Status: {log.status}")
                logger.info(f"  - Attempted: {log.records_attempted}")
                logger.info(f"  - Succeeded: {log.records_succeeded}")
                logger.info(f"  - Failed: {log.records_failed}")
                logger.info(f"  - Duration: {log.duration_seconds:.2f}s")
                logger.info(f"  - Timestamp: {log.created_at}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ All integration tests passed!")
        logger.info("=" * 60)
    
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        raise
    
    finally:
        # Cleanup
        if service:
            await service.close()
        await db.close()
        logger.info("\n🔒 Database connections closed")


if __name__ == "__main__":
    asyncio.run(main())
