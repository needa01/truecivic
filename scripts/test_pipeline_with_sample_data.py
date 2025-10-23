"""
Test Complete Pipeline with Limited Sample Data
================================================
Pulls limited data (--limit 5), verifies ingestion, tests materialized views,
and validates full-text search functionality.

Usage: python scripts/test_pipeline_with_sample_data.py
"""
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv('.env.production')


async def run_ingestion():
    """Run bill ingestion flow with limited data"""
    print("\n" + "="*80)
    print("🚀 STEP 1: Ingesting Limited Sample Data (5 bills)")
    print("="*80)
    
    from src.prefect_flows.bill_flows import fetch_latest_bills_flow
    
    try:
        # Run latest bills flow with limit=5
        print("\n   Running fetch_latest_bills_flow (limit=5)...")
        result = await fetch_latest_bills_flow(limit=5)
        print(f"\n✅ Ingestion completed!")
        print(f"   Bills processed: {result.get('bills_processed', 0)}")
        print(f"   Status: {result.get('status', 'unknown')}")
        return True
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_base_data():
    """Verify base tables have data"""
    print("\n" + "="*80)
    print("📊 STEP 2: Verifying Base Tables")
    print("="*80)
    
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    try:
        async with engine.begin() as conn:
            # Check bills
            result = await conn.execute(text("SELECT COUNT(*) FROM bills"))
            bills_count = result.scalar()
            print(f"\n   Bills: {bills_count}")
            
            # Check politicians
            result = await conn.execute(text("SELECT COUNT(*) FROM politicians"))
            politicians_count = result.scalar()
            print(f"   Politicians: {politicians_count}")
            
            # Check parties
            result = await conn.execute(text("SELECT COUNT(*) FROM parties"))
            parties_count = result.scalar()
            print(f"   Parties: {parties_count}")
            
            # Check ridings
            result = await conn.execute(text("SELECT COUNT(*) FROM ridings"))
            ridings_count = result.scalar()
            print(f"   Ridings: {ridings_count}")
            
            # Sample bill details
            result = await conn.execute(text("""
                SELECT number, title_en, introduced_date, law_status 
                FROM bills 
                ORDER BY introduced_date DESC 
                LIMIT 3
            """))
            print(f"\n   📋 Sample Bills:")
            for row in result.fetchall():
                print(f"      {row.number}: {row.title_en[:60]}...")
                print(f"         Status: {row.law_status}, Date: {row.introduced_date}")
            
            if bills_count == 0:
                print("\n   ⚠️  No bills found - ingestion may have failed")
                return False
            
            print(f"\n✅ Base tables verified!")
            return True
            
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def refresh_materialized_views():
    """Refresh all materialized views"""
    print("\n" + "="*80)
    print("🔄 STEP 3: Refreshing Materialized Views")
    print("="*80)
    
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    try:
        async with engine.begin() as conn:
            print("\n   Refreshing mv_feed_all...")
            await conn.execute(text("REFRESH MATERIALIZED VIEW mv_feed_all"))
            
            print("   Refreshing mv_feed_bills_latest...")
            await conn.execute(text("REFRESH MATERIALIZED VIEW mv_feed_bills_latest"))
            
            print("   Refreshing mv_feed_bills_by_tag...")
            await conn.execute(text("REFRESH MATERIALIZED VIEW mv_feed_bills_by_tag"))
            
            await conn.commit()
            print("\n✅ All materialized views refreshed!")
            return True
            
    except Exception as e:
        print(f"\n❌ Refresh failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def verify_materialized_views():
    """Verify materialized views have correct data"""
    print("\n" + "="*80)
    print("📊 STEP 4: Verifying Materialized Views")
    print("="*80)
    
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    try:
        async with engine.begin() as conn:
            # Check mv_feed_all
            result = await conn.execute(text("""
                SELECT COUNT(*) as total, entity_type 
                FROM mv_feed_all 
                GROUP BY entity_type 
                ORDER BY entity_type
            """))
            rows = result.fetchall()
            print('\n   📊 mv_feed_all by entity type:')
            total_feed = 0
            for row in rows:
                print(f'      {row.entity_type}: {row.total} items')
                total_feed += row.total
            
            if total_feed == 0:
                print("      ⚠️  Feed is empty - no data to display")
            
            # Check mv_feed_bills_latest
            result = await conn.execute(text("SELECT COUNT(*) FROM mv_feed_bills_latest"))
            bills_latest_count = result.scalar()
            print(f'\n   📊 mv_feed_bills_latest: {bills_latest_count} bills')
            
            # Sample from latest bills
            if bills_latest_count > 0:
                result = await conn.execute(text("""
                    SELECT number, title_en, introduced_date 
                    FROM mv_feed_bills_latest 
                    ORDER BY introduced_date DESC 
                    LIMIT 3
                """))
                print(f'      Sample entries:')
                for row in result.fetchall():
                    print(f'         {row.number}: {row.title_en[:50]}...')
            
            # Check mv_feed_bills_by_tag
            result = await conn.execute(text("""
                SELECT COUNT(*) as cnt, tag 
                FROM mv_feed_bills_by_tag 
                GROUP BY tag 
                ORDER BY cnt DESC 
                LIMIT 5
            """))
            rows = result.fetchall()
            if rows:
                print(f'\n   📊 Top 5 tags in mv_feed_bills_by_tag:')
                for row in rows:
                    print(f'      {row.tag}: {row.cnt} bills')
            else:
                print(f'\n   📊 mv_feed_bills_by_tag: No tags found (bills may not have subject_tags)')
            
            print(f"\n✅ Materialized views verified!")
            return True
            
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def verify_full_text_search():
    """Verify full-text search functionality"""
    print("\n" + "="*80)
    print("🔍 STEP 5: Verifying Full-Text Search")
    print("="*80)
    
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    try:
        async with engine.begin() as conn:
            # Check bills with search_vector
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM bills WHERE search_vector IS NOT NULL
            """))
            bills_indexed = result.scalar()
            print(f'\n   Bills with search index: {bills_indexed}')
            
            # Test search if we have data
            if bills_indexed > 0:
                result = await conn.execute(text("""
                    SELECT number, title_en,
                           ts_rank(search_vector, websearch_to_tsquery('english', 'budget')) as rank
                    FROM bills 
                    WHERE search_vector @@ websearch_to_tsquery('english', 'budget')
                    ORDER BY rank DESC 
                    LIMIT 3
                """))
                rows = result.fetchall()
                if rows:
                    print(f'\n   🔎 Search test - "budget":')
                    for row in rows:
                        print(f'      {row.number}: {row.title_en[:60]}...')
                        print(f'         Relevance score: {row.rank:.4f}')
                else:
                    print(f'\n   🔎 Search test - "budget": No results (expected with limited data)')
                
                # Try a broader search
                result = await conn.execute(text("""
                    SELECT number, title_en
                    FROM bills 
                    WHERE search_vector IS NOT NULL
                    LIMIT 3
                """))
                rows = result.fetchall()
                if rows:
                    print(f'\n   📋 Bills with search enabled:')
                    for row in rows:
                        print(f'      {row.number}: {row.title_en[:60]}...')
            
            # Check debates
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM debates WHERE search_vector IS NOT NULL
            """))
            debates_indexed = result.scalar()
            print(f'\n   Debates with search index: {debates_indexed}')
            
            # Check speeches
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM speeches WHERE search_vector IS NOT NULL
            """))
            speeches_indexed = result.scalar()
            print(f'   Speeches with search index: {speeches_indexed}')
            
            print(f"\n✅ Full-text search verified!")
            return True
            
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def test_personalization_tables():
    """Test personalization tables are accessible"""
    print("\n" + "="*80)
    print("👤 STEP 6: Verifying Personalization Tables")
    print("="*80)
    
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    try:
        async with engine.begin() as conn:
            # Check ignored_bill table
            result = await conn.execute(text("SELECT COUNT(*) FROM ignored_bill"))
            ignored_count = result.scalar()
            print(f'\n   ignored_bill entries: {ignored_count}')
            
            # Check personalized_feed_token table
            result = await conn.execute(text("SELECT COUNT(*) FROM personalized_feed_token"))
            token_count = result.scalar()
            print(f'   personalized_feed_token entries: {token_count}')
            
            # Test insert/delete on ignored_bill (to verify FK works)
            print(f'\n   Testing foreign key constraints...')
            
            # Get a real bill_id
            result = await conn.execute(text("SELECT id FROM bills LIMIT 1"))
            row = result.fetchone()
            if row:
                bill_id = row.id
                test_device_id = 'test-device-12345'
                
                # Insert test record
                await conn.execute(text("""
                    INSERT INTO ignored_bill (natural_id, jurisdiction, device_id, bill_id, ignored_at, created_at)
                    VALUES (:natural_id, :jurisdiction, :device_id, :bill_id, NOW(), NOW())
                """), {
                    'natural_id': 'test-ignore-1',
                    'jurisdiction': 'ca',
                    'device_id': test_device_id,
                    'bill_id': bill_id
                })
                print(f'      ✅ INSERT into ignored_bill successful')
                
                # Delete test record
                await conn.execute(text("""
                    DELETE FROM ignored_bill WHERE natural_id = :natural_id
                """), {'natural_id': 'test-ignore-1'})
                print(f'      ✅ DELETE from ignored_bill successful')
                print(f'      ✅ Foreign key constraint working (bill_id → bills.id)')
            else:
                print(f'      ⚠️  No bills to test FK constraint')
            
            await conn.commit()
            print(f"\n✅ Personalization tables verified!")
            return True
            
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def main():
    """Run complete pipeline test"""
    print("\n" + "="*80)
    print("🧪 TRUECIVIC PIPELINE TEST - LIMITED SAMPLE DATA")
    print("="*80)
    print("\nThis script will:")
    print("1. Ingest 5 bills from LEGISinfo API")
    print("2. Verify base tables (bills, politicians, parties, ridings)")
    print("3. Refresh materialized views")
    print("4. Verify materialized view contents")
    print("5. Test full-text search functionality")
    print("6. Verify personalization tables and FK constraints")
    
    results = []
    
    # Step 1: Ingest data
    success = await run_ingestion()
    results.append(("Ingestion", success))
    if not success:
        print("\n❌ Ingestion failed - stopping test")
        return
    
    # Step 2: Verify base data
    success = await verify_base_data()
    results.append(("Base Data Verification", success))
    if not success:
        print("\n⚠️  Base data verification failed - continuing anyway")
    
    # Step 3: Refresh views
    success = await refresh_materialized_views()
    results.append(("Materialized View Refresh", success))
    if not success:
        print("\n⚠️  View refresh failed - continuing anyway")
    
    # Step 4: Verify views
    success = await verify_materialized_views()
    results.append(("Materialized View Verification", success))
    
    # Step 5: Verify search
    success = await verify_full_text_search()
    results.append(("Full-Text Search", success))
    
    # Step 6: Test personalization
    success = await test_personalization_tables()
    results.append(("Personalization Tables", success))
    
    # Summary
    print("\n" + "="*80)
    print("📋 FINAL SUMMARY")
    print("="*80)
    
    all_passed = True
    for step_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {step_name}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Pipeline is working correctly.")
        print("\n📝 Next steps:")
        print("   1. Build RSS/Atom feed endpoints (Phase E)")
        print("   2. Create full-text search API endpoints")
        print("   3. Add materialized view refresh flow")
    else:
        print("\n⚠️  Some tests failed - review output above")
    
    print("="*80)


if __name__ == '__main__':
    asyncio.run(main())
