"""
Simple test script that bypasses Prefect caching and directly tests the database pipeline
"""
import os
import asyncio
from pathlib import Path
import sys
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv('.env.production')


async def test_direct_ingestion():
    """Test direct ingestion without Prefect"""
    print("\n" + "="*80)
    print("🧪 DIRECT DATABASE INGESTION TEST (No Prefect)")
    print("="*80)
    
    from src.services.bill_integration_service import BillIntegrationService
    from src.db.session import Database
    
    db = Database()
    await db.initialize()
    
    print(f"\n✅ Database initialized")
    print(f"   Connection: {db.engine.url}")
    
    try:
        async with BillIntegrationService(db) as service:
            print(f"\n🔄 Fetching 5 bills from OpenParliament...")
            
            result = await service.fetch_and_persist(
                limit=5,
                parliament=None,
                session=None,
                enrich=True
            )
            
            print(f"\n✅ Fetch complete!")
            print(f"   Status: {result.get('status')}")
            print(f"   Bills fetched: {result.get('bills_fetched', 0)}")
            print(f"   Created: {result.get('created', 0)}")
            print(f"   Updated: {result.get('updated', 0)}")
            print(f"   Errors: {result.get('error_count', 0)}")
            
            if result.get('errors'):
                print(f"\n⚠️  Errors encountered:")
                for error in result['errors'][:5]:
                    print(f"      - {error}")
    
    finally:
        await db.close()


async def verify_data():
    """Verify data was actually written"""
    print("\n" + "="*80)
    print("📊 VERIFYING DATA IN DATABASE")
    print("="*80)
    
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    try:
        async with engine.begin() as conn:
            # Check bills
            result = await conn.execute(text("SELECT COUNT(*) FROM bills"))
            bills_count = result.scalar()
            print(f"\n   Bills in database: {bills_count}")
            
            if bills_count > 0:
                # Get sample
                result = await conn.execute(text("""
                    SELECT number, title_en, law_status, introduced_date
                    FROM bills 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """))
                print(f"\n   📋 Sample bills:")
                for row in result.fetchall():
                    print(f"      {row.number}: {row.title_en[:60]}...")
                    print(f"         Status: {row.law_status}, Date: {row.introduced_date}")
            
            # Check search vectors
            result = await conn.execute(text("SELECT COUNT(*) FROM bills WHERE search_vector IS NOT NULL"))
            indexed_count = result.scalar()
            print(f"\n   Bills with search_vector: {indexed_count}")
            
            return bills_count > 0
    
    finally:
        await engine.dispose()


async def test_materialized_views():
    """Test materialized views after refresh"""
    print("\n" + "="*80)
    print("🔄 TESTING MATERIALIZED VIEWS")
    print("="*80)
    
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    try:
        # Refresh views in one transaction
        async with engine.begin() as conn:
            print("\n   Refreshing materialized views...")
            await conn.execute(text("REFRESH MATERIALIZED VIEW mv_feed_all"))
            await conn.execute(text("REFRESH MATERIALIZED VIEW mv_feed_bills_latest"))
            await conn.execute(text("REFRESH MATERIALIZED VIEW mv_feed_bills_by_tag"))
            print("   ✅ Views refreshed")
        
        # Query views in separate transaction
        async with engine.begin() as conn:
            # Check mv_feed_all
            result = await conn.execute(text("""
                SELECT COUNT(*) as total, entity_type 
                FROM mv_feed_all 
                GROUP BY entity_type
            """))
            rows = result.fetchall()
            if rows:
                print(f"\n   📊 mv_feed_all:")
                for row in rows:
                    print(f"      {row.entity_type}: {row.total} items")
            else:
                print(f"\n   ⚠️  mv_feed_all is empty")
            
            # Check mv_feed_bills_latest
            result = await conn.execute(text("SELECT COUNT(*) FROM mv_feed_bills_latest"))
            count = result.scalar()
            print(f"\n   📊 mv_feed_bills_latest: {count} bills")
            
            if count > 0:
                result = await conn.execute(text("""
                    SELECT number, title_en 
                    FROM mv_feed_bills_latest 
                    LIMIT 3
                """))
                print(f"      Sample:")
                for row in result.fetchall():
                    print(f"         {row.number}: {row.title_en[:50]}...")
    
    finally:
        await engine.dispose()


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🚀 TRUECIVIC DIRECT PIPELINE TEST")
    print("="*80)
    print("\nThis bypasses Prefect caching and tests database directly.\n")
    
    # Step 1: Direct ingestion
    await test_direct_ingestion()
    
    # Step 2: Verify data
    has_data = await verify_data()
    
    # Step 3: Test views (if we have data)
    if has_data:
        await test_materialized_views()
    else:
        print("\n⚠️  No data found - skipping materialized view tests")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    asyncio.run(main())
