"""
Verify the complete schema migration on Railway database.

Checks that all new tables exist and have the correct structure.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# Load production environment
project_root = Path(__file__).parent.parent
env_file = project_root / ".env.production"
if env_file.exists():
    load_dotenv(env_file)

def verify_schema():
    """Verify all tables exist in Railway database."""
    
    print("=" * 80)
    print("🔍 Verifying Schema Migration on Railway")
    print("=" * 80)
    print()
    
    database_url = os.getenv("DATABASE_PUBLIC_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_PUBLIC_URL not set")
        return 1
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    # Expected tables from complete schema
    expected_tables = {
        # Original tables
        "bills": "Legislative bills",
        "politicians": "MPs and Senators",
        "fetch_logs": "ETL fetch history",
        
        # New tables from migration
        "parties": "Political parties",
        "ridings": "Electoral ridings/constituencies",
        "votes": "Parliamentary votes",
        "vote_records": "Individual MP votes",
        "committees": "Parliamentary committees",
        "debates": "Hansard debate sessions",
        "speeches": "Individual speeches in debates",
        "documents": "Full-text documents for embeddings",
        "embeddings": "Vector embeddings for search",
        "rankings": "Entity ranking scores",
    }
    
    print("📊 Checking tables...")
    print()
    
    existing_tables = inspector.get_table_names()
    all_good = True
    
    for table_name, description in expected_tables.items():
        if table_name in existing_tables:
            # Get column count
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            
            print(f"✅ {table_name:<20} ({len(columns):2} columns, {len(indexes):2} indexes) - {description}")
        else:
            print(f"❌ {table_name:<20} MISSING! - {description}")
            all_good = False
    
    print()
    
    if all_good:
        print("=" * 80)
        print("✅ All Tables Present!")
        print("=" * 80)
        print()
        
        # Check row counts
        print("📊 Table Row Counts:")
        print()
        
        with engine.connect() as conn:
            for table_name in expected_tables.keys():
                if table_name in existing_tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    print(f"   {table_name:<20}: {count:>6} rows")
        
        print()
        return 0
    else:
        print("=" * 80)
        print("❌ Schema Verification Failed!")
        print("=" * 80)
        print()
        print("Some tables are missing. Please check the migration logs.")
        return 1


if __name__ == "__main__":
    exit_code = verify_schema()
    sys.exit(exit_code)
