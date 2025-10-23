"""Test materialized views and full-text search"""
import os
import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv('.env.production')

async def test_views():
    engine = create_async_engine(
        os.getenv('DATABASE_PUBLIC_URL').replace('postgresql://', 'postgresql+asyncpg://')
    )
    
    async with engine.begin() as conn:
        # Test mv_feed_all
        result = await conn.execute(
            text('SELECT COUNT(*) as total, entity_type FROM mv_feed_all GROUP BY entity_type ORDER BY entity_type')
        )
        rows = result.fetchall()
        print('\n📊 Materialized View mv_feed_all:')
        for row in rows:
            print(f'   {row.entity_type}: {row.total} items')
        
        # Test mv_feed_bills_latest
        result2 = await conn.execute(text('SELECT COUNT(*) FROM mv_feed_bills_latest'))
        print(f'\n📊 mv_feed_bills_latest: {result2.scalar()} bills')
        
        # Test mv_feed_bills_by_tag
        result3 = await conn.execute(
            text('SELECT COUNT(*) as cnt, tag FROM mv_feed_bills_by_tag GROUP BY tag ORDER BY cnt DESC LIMIT 5')
        )
        rows3 = result3.fetchall()
        print(f'\n📊 Top 5 tags in mv_feed_bills_by_tag:')
        for row in rows3:
            print(f'   {row.tag}: {row.cnt} bills')
        
        # Test full-text search on bills
        result4 = await conn.execute(
            text("SELECT COUNT(*) FROM bills WHERE search_vector IS NOT NULL")
        )
        print(f'\n🔍 Bills with full-text search: {result4.scalar()}')
        
        # Test full-text search on debates
        result5 = await conn.execute(
            text("SELECT COUNT(*) FROM debates WHERE search_vector IS NOT NULL")
        )
        print(f'🔍 Debates with full-text search: {result5.scalar()}')
        
        # Test full-text search on speeches
        result6 = await conn.execute(
            text("SELECT COUNT(*) FROM speeches WHERE search_vector IS NOT NULL")
        )
        print(f'🔍 Speeches with full-text search: {result6.scalar()}')
    
    await engine.dispose()
    print('\n✅ All views and indexes verified!')

if __name__ == '__main__':
    asyncio.run(test_views())
