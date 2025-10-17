"""
Railway Services Setup Script
Fixes issues found during validation:
1. Enable pgvector extension
2. Run Alembic migrations
3. Create MinIO buckets

Usage:
    python scripts/setup_railway_services.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from typing import List


class ServiceSetup:
    """Setup Railway services"""
    
    def __init__(self):
        self.load_env()
    
    def load_env(self):
        """Load production environment variables"""
        env_file = Path(__file__).parent.parent / ".env.production"
        if not env_file.exists():
            print("⚠️  .env.production not found, using environment variables")
            return
        
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if not value.startswith('${'):
                        os.environ[key] = value
    
    async def enable_pgvector(self) -> bool:
        """Enable pgvector extension on application database"""
        print("\n🔧 Enabling pgvector extension...")
        
        try:
            import asyncpg
            
            db_url = os.getenv("DATABASE_PUBLIC_URL", "")
            if not db_url:
                print("❌ Missing DATABASE_PUBLIC_URL")
                return False
            
            conn = await asyncpg.connect(db_url)
            
            # Check if pgvector is already enabled
            result = await conn.fetchval(
                "SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector';"
            )
            
            if result > 0:
                print("✅ pgvector extension already enabled")
            else:
                # Enable pgvector
                await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print("✅ pgvector extension enabled successfully")
            
            # Verify
            version = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
            )
            print(f"   Version: {version}")
            
            await conn.close()
            return True
            
        except Exception as e:
            print(f"❌ Failed to enable pgvector: {str(e)}")
            return False
    
    async def run_migrations(self) -> bool:
        """Run Alembic migrations"""
        print("\n🔧 Running Alembic migrations...")
        
        try:
            import subprocess
            
            # Set DATABASE_URL for Alembic
            db_url = os.getenv("DATABASE_PUBLIC_URL", "")
            if not db_url:
                print("❌ Missing DATABASE_PUBLIC_URL")
                return False
            
            # Alembic needs psycopg2 format (not asyncpg)
            sync_db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
            os.environ["DATABASE_URL"] = sync_db_url
            
            # Run migrations
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Migrations completed successfully")
                print(result.stdout)
                return True
            else:
                print(f"❌ Migration failed: {result.stderr}")
                return False
            
        except Exception as e:
            print(f"❌ Failed to run migrations: {str(e)}")
            return False
    
    def create_minio_buckets(self) -> bool:
        """Create MinIO buckets"""
        print("\n🔧 Creating MinIO buckets...")
        
        try:
            from minio import Minio
            
            endpoint = os.getenv("MINIO_ENDPOINT", "")
            access_key = os.getenv("MINIO_ACCESS_KEY", "")
            secret_key = os.getenv("MINIO_SECRET_KEY", "")
            secure = os.getenv("MINIO_SECURE", "true").lower() == "true"
            
            if not all([endpoint, access_key, secret_key]):
                print("❌ Missing MINIO credentials")
                return False
            
            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure
            )
            
            # Buckets to create
            buckets = [
                os.getenv("MINIO_BUCKET_RAW", "parl-raw-prod"),
                os.getenv("MINIO_BUCKET_PROCESSED", "parl-processed-prod"),
                os.getenv("MINIO_BUCKET_BACKUPS", "backups-prod")
            ]
            
            created = []
            existing = []
            
            for bucket_name in buckets:
                if client.bucket_exists(bucket_name):
                    existing.append(bucket_name)
                else:
                    client.make_bucket(bucket_name)
                    created.append(bucket_name)
            
            if created:
                print(f"✅ Created buckets: {', '.join(created)}")
            if existing:
                print(f"ℹ️  Already exist: {', '.join(existing)}")
            
            # Verify
            all_buckets = [b.name for b in client.list_buckets()]
            print(f"   Total buckets: {len(all_buckets)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to create buckets: {str(e)}")
            return False
    
    async def verify_application_tables(self) -> bool:
        """Verify application tables were created"""
        print("\n🔍 Verifying application tables...")
        
        try:
            import asyncpg
            
            db_url = os.getenv("DATABASE_PUBLIC_URL", "")
            conn = await asyncpg.connect(db_url)
            
            # Check tables
            tables_query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """
            tables = await conn.fetch(tables_query)
            table_names = [row['table_name'] for row in tables]
            
            expected_tables = ['bills', 'politicians', 'fetch_logs', 'alembic_version']
            found = [t for t in expected_tables if t in table_names]
            missing = [t for t in expected_tables if t not in table_names]
            
            print(f"✅ Found {len(found)} tables: {', '.join(found)}")
            if missing:
                print(f"⚠️  Missing tables: {', '.join(missing)}")
            
            await conn.close()
            return len(missing) == 0
            
        except Exception as e:
            print(f"❌ Failed to verify tables: {str(e)}")
            return False
    
    async def run_setup(self):
        """Run all setup tasks"""
        print("=" * 80)
        print("🚀 Railway Services Setup")
        print("=" * 80)
        
        # Step 1: Enable pgvector
        pgvector_ok = await self.enable_pgvector()
        
        # Step 2: Run migrations
        migrations_ok = await self.run_migrations()
        
        # Step 3: Verify tables
        tables_ok = await self.verify_application_tables()
        
        # Step 4: Create buckets
        buckets_ok = self.create_minio_buckets()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 Setup Summary")
        print("=" * 80)
        print(f"{'✅' if pgvector_ok else '❌'} pgvector extension")
        print(f"{'✅' if migrations_ok else '❌'} Database migrations")
        print(f"{'✅' if tables_ok else '⚠️ '} Application tables")
        print(f"{'✅' if buckets_ok else '❌'} MinIO buckets")
        
        all_ok = pgvector_ok and migrations_ok and tables_ok and buckets_ok
        
        if all_ok:
            print("\n🎉 All services configured successfully!")
            print("\n📝 Next steps:")
            print("1. Run validation again: python scripts/validate_railway_services.py")
            print("2. Deploy Prefect flows: prefect deploy --all")
            print("3. Start worker in Railway")
        else:
            print("\n⚠️  Some services need attention. Review errors above.")
        
        return all_ok


async def main():
    """Main setup function"""
    setup = ServiceSetup()
    success = await setup.run_setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
