"""
Test RSS/Atom feed generation.

Tests the feed builder infrastructure directly without starting the full API.
Verifies feed generation, GUID format, XML structure, and content accuracy.

Responsibility: Feed system validation
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from src.db.session import Database
from src.feeds import (
    LatestBillsFeedBuilder,
    BillsByTagFeedBuilder,
    AllEntitiesFeedBuilder,
    FeedFormat
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_latest_bills_feed():
    """Test latest bills feed generation."""
    logger.info("=" * 80)
    logger.info("Testing Latest Bills Feed")
    logger.info("=" * 80)
    
    db = Database()
    await db.initialize()
    
    try:
        async with db.session() as session:
            # Test RSS format
            logger.info("\n📰 Generating RSS feed...")
            builder = await LatestBillsFeedBuilder.from_materialized_view(
                session=session,
                feed_url="http://localhost:8000/api/v1/ca/feeds/bills/latest.rss",
                limit=10
            )
            
            rss_xml = builder.generate(FeedFormat.RSS)
            logger.info(f"✅ RSS feed generated: {len(rss_xml)} bytes")
            
            # Verify RSS structure
            assert '<?xml version' in rss_xml, "RSS must have XML declaration"
            assert '<rss version="2.0"' in rss_xml, "RSS must have version 2.0"
            assert '<channel>' in rss_xml, "RSS must have channel element"
            assert '<title>TrueCivic - Latest Bills</title>' in rss_xml, "RSS must have correct title"
            assert '<item>' in rss_xml, "RSS must have at least one item"
            assert '<guid' in rss_xml, "RSS items must have GUIDs"
            assert 'ca:bill:' in rss_xml, "GUIDs must follow ca:bill:ID format"
            logger.info("✅ RSS structure validated")
            
            # Test Atom format
            logger.info("\n⚛️  Generating Atom feed...")
            builder_atom = await LatestBillsFeedBuilder.from_materialized_view(
                session=session,
                feed_url="http://localhost:8000/api/v1/ca/feeds/bills/latest.atom",
                limit=10
            )
            
            atom_xml = builder_atom.generate(FeedFormat.ATOM)
            logger.info(f"✅ Atom feed generated: {len(atom_xml)} bytes")
            
            # Verify Atom structure
            assert '<?xml version' in atom_xml, "Atom must have XML declaration"
            assert '<feed xmlns="http://www.w3.org/2005/Atom"' in atom_xml, "Atom must have correct namespace"
            assert '<title>TrueCivic - Latest Bills</title>' in atom_xml, "Atom must have correct title"
            assert '<entry>' in atom_xml, "Atom must have at least one entry"
            assert '<id>' in atom_xml, "Atom entries must have IDs"
            assert 'ca:bill:' in atom_xml, "IDs must follow ca:bill:ID format"
            logger.info("✅ Atom structure validated")
            
            # Count entries in database
            result = await session.execute(
                text("SELECT COUNT(*) FROM mv_feed_bills_latest")
            )
            count = result.scalar()
            logger.info(f"\n📊 Database has {count} bills in mv_feed_bills_latest")
            
            # Verify entry count matches
            rss_item_count = rss_xml.count('<item>')
            atom_entry_count = atom_xml.count('<entry>')
            logger.info(f"📊 RSS has {rss_item_count} items")
            logger.info(f"📊 Atom has {atom_entry_count} entries")
            
            if count > 0:
                assert rss_item_count > 0, "RSS should have items when database has bills"
                assert atom_entry_count > 0, "Atom should have entries when database has bills"
                assert rss_item_count == atom_entry_count, "RSS and Atom should have same entry count"
                logger.info("✅ Entry counts match")
            
            # Show sample GUID
            import re
            guid_match = re.search(r'<guid[^>]*>(ca:bill:[^<]+)</guid>', rss_xml)
            if guid_match:
                logger.info(f"\n🔖 Sample GUID: {guid_match.group(1)}")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ Latest Bills Feed Test: PASSED")
            logger.info("=" * 80)
            
    finally:
        await db.close()


async def test_bills_by_tag_feed():
    """Test tag-filtered bills feed generation."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing Bills by Tag Feed")
    logger.info("=" * 80)
    
    db = Database()
    await db.initialize()
    
    try:
        async with db.session() as session:
            # Find a tag that exists
            result = await session.execute(
                text("""
                    SELECT DISTINCT unnest(tags) as tag 
                    FROM bills 
                    WHERE tags IS NOT NULL 
                    LIMIT 1
                """)
            )
            row = result.fetchone()
            
            if not row:
                logger.warning("⚠️  No tags found in database, skipping tag feed test")
                return
            
            tag = row[0]
            logger.info(f"\n🏷️  Testing with tag: {tag}")
            
            # Generate feed
            builder = await BillsByTagFeedBuilder.from_materialized_view(
                session=session,
                tag=tag,
                feed_url=f"http://localhost:8000/api/v1/ca/feeds/bills/tag/{tag}.rss",
                limit=10
            )
            
            rss_xml = builder.generate(FeedFormat.RSS)
            logger.info(f"✅ Tag feed generated: {len(rss_xml)} bytes")
            
            # Verify structure
            assert '<?xml version' in rss_xml, "RSS must have XML declaration"
            assert f'<title>TrueCivic - Bills Tagged: {tag}</title>' in rss_xml, "Title must include tag"
            assert '<item>' in rss_xml, "RSS must have at least one item"
            logger.info("✅ Tag feed structure validated")
            
            # Count entries
            result = await session.execute(
                text("SELECT COUNT(*) FROM mv_feed_bills_by_tag WHERE tag = :tag"),
                {"tag": tag}
            )
            count = result.scalar()
            logger.info(f"📊 Database has {count} bills with tag '{tag}'")
            
            item_count = rss_xml.count('<item>')
            logger.info(f"📊 RSS has {item_count} items")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ Bills by Tag Feed Test: PASSED")
            logger.info("=" * 80)
            
    finally:
        await db.close()


async def test_all_entities_feed():
    """Test unified activity feed (all entities)."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing All Entities Feed")
    logger.info("=" * 80)
    
    db = Database()
    await db.initialize()
    
    try:
        async with db.session() as session:
            logger.info("\n🌐 Generating unified activity feed...")
            builder = await AllEntitiesFeedBuilder.from_materialized_view(
                session=session,
                feed_url="http://localhost:8000/api/v1/ca/feeds/all.rss",
                limit=20
            )
            
            rss_xml = builder.generate(FeedFormat.RSS)
            logger.info(f"✅ All entities feed generated: {len(rss_xml)} bytes")
            
            # Verify structure
            assert '<?xml version' in rss_xml, "RSS must have XML declaration"
            assert '<title>TrueCivic - All Parliamentary Activity</title>' in rss_xml, "Title must be correct"
            assert '<item>' in rss_xml or count == 0, "RSS must have items if data exists"
            logger.info("✅ All entities feed structure validated")
            
            # Count entries by type
            result = await session.execute(
                text("SELECT entity_type, COUNT(*) FROM mv_feed_all GROUP BY entity_type")
            )
            
            logger.info("\n📊 Entity counts in mv_feed_all:")
            total = 0
            for row in result:
                entity_type, count = row
                logger.info(f"   {entity_type}: {count}")
                total += count
            
            logger.info(f"   TOTAL: {total}")
            
            item_count = rss_xml.count('<item>')
            logger.info(f"\n📊 RSS has {item_count} items")
            
            if total > 0:
                assert item_count > 0, "RSS should have items when database has entities"
                assert item_count <= 20, "RSS should respect limit parameter"
                logger.info("✅ Entry count validated")
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ All Entities Feed Test: PASSED")
            logger.info("=" * 80)
            
    finally:
        await db.close()


async def test_feed_caching():
    """Test feed caching functionality."""
    logger.info("\n" + "=" * 80)
    logger.info("Testing Feed Caching")
    logger.info("=" * 80)
    
    from src.feeds import feed_cache
    
    # Clear cache first
    feed_cache.cache.clear()
    logger.info("🗑️  Cleared cache")
    
    # Test set and get
    test_key = "test:feed:rss:10"
    test_content = "<rss>test</rss>"
    
    feed_cache.set(test_key, test_content)
    logger.info(f"✅ Set cache key: {test_key}")
    
    cached = feed_cache.get(test_key)
    assert cached == test_content, "Cached content should match"
    logger.info("✅ Retrieved cached content")
    
    # Test expiration (would need to wait 5 minutes in real scenario)
    logger.info(f"📊 Cache size: {len(feed_cache.cache)} items")
    logger.info(f"⏱️  TTL: {feed_cache.ttl} seconds")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Feed Caching Test: PASSED")
    logger.info("=" * 80)


async def main():
    """Run all feed tests."""
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Starting Feed Infrastructure Tests")
    logger.info("=" * 80)
    
    try:
        await test_latest_bills_feed()
        await test_bills_by_tag_feed()
        await test_all_entities_feed()
        await test_feed_caching()
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 ALL FEED TESTS PASSED")
        logger.info("=" * 80)
        logger.info("\nNext steps:")
        logger.info("1. Start API: python -m api.main")
        logger.info("2. Test endpoints:")
        logger.info("   - http://localhost:8000/api/v1/ca/feeds/all.rss")
        logger.info("   - http://localhost:8000/api/v1/ca/feeds/bills/latest.atom")
        logger.info("   - http://localhost:8000/api/v1/ca/feeds/cache/stats")
        logger.info("3. Validate feeds: https://validator.w3.org/feed/")
        
    except Exception as e:
        logger.error(f"\n❌ Test failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
