"""
Quick verification script to check database tables.

Responsibility: Database verification
"""

import asyncio
from sqlalchemy import inspect
from src.db.session import get_async_engine


async def verify_tables():
    """Verify all tables exist in database."""
    engine = get_async_engine()
    
    async with engine.connect() as conn:
        # Run sync inspection in async context
        tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        
        print("✅ Database tables:")
        for table in sorted(tables):
            print(f"   - {table}")
        
        print(f"\n📊 Total tables: {len(tables)}")
        
        # Expected tables
        expected = [
            'alembic_version', 'bills', 'politicians', 'fetch_logs',
            'parties', 'ridings', 'votes', 'vote_records',
            'committees', 'debates', 'speeches', 'documents',
            'embeddings', 'rankings'
        ]
        
        missing = set(expected) - set(tables)
        if missing:
            print(f"\n⚠️  Missing tables: {missing}")
        else:
            print("\n✅ All expected tables present!")


if __name__ == "__main__":
    asyncio.run(verify_tables())
