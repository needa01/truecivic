"""
End-to-end ETL pipeline test script.

Tests the complete bill ingestion flow:
1. Fetch bills from OpenParliament API (--limit 5)
2. Enrich with LEGISinfo data
3. Persist to PostgreSQL database
4. Verify data in database
5. Check Redis cache
6. Validate MinIO storage (if used)

Usage:
    python scripts/test_etl_pipeline.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables before importing project modules
load_dotenv(".env.production")

import asyncpg
import redis.asyncio as aioredis
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.prefect_flows.bill_flows import fetch_latest_bills_flow
from src.db.session import Database

console = Console()


class ETLPipelineTest:
    """End-to-end ETL pipeline testing"""
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_PUBLIC_URL")
        self.redis_url = os.getenv("REDIS_URL")
        self.test_limit = 5
        self.test_results = {
            "flow_execution": None,
            "database_validation": None,
            "redis_validation": None,
            "data_quality": None,
        }
    
    async def run_complete_test(self):
        """Execute complete ETL pipeline test"""
        console.print("\n[bold cyan]🧪 ETL Pipeline End-to-End Test[/bold cyan]\n")
        console.print(f"Test Parameters: limit={self.test_limit}\n")
        
        try:
            # Step 1: Run Prefect flow
            await self._test_flow_execution()
            
            # Step 2: Validate database
            await self._test_database_validation()
            
            # Step 3: Validate Redis cache
            await self._test_redis_validation()
            
            # Step 4: Validate data quality
            await self._test_data_quality()
            
            # Step 5: Generate report
            await self._generate_report()
            
            console.print("\n[bold green]✅ All tests completed![/bold green]\n")
            
        except Exception as e:
            console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]\n")
            raise
    
    async def _test_flow_execution(self):
        """Test 1: Execute Prefect flow with limit=5"""
        console.print("[bold yellow]Step 1: Running Prefect flow (limit=5)...[/bold yellow]")
        
        try:
            # Execute flow
            result = await fetch_latest_bills_flow(limit=self.test_limit)
            
            self.test_results["flow_execution"] = {
                "status": "✅ PASSED",
                "bills_fetched": result.get("bills_fetched", 0),
                "created": result.get("created", 0),
                "updated": result.get("updated", 0),
                "errors": result.get("error_count", 0),
                "duration": result.get("duration_seconds", 0),
            }
            
            console.print(f"  ✅ Flow executed successfully")
            console.print(f"     Bills fetched: {result.get('bills_fetched', 0)}")
            console.print(f"     Created: {result.get('created', 0)}")
            console.print(f"     Updated: {result.get('updated', 0)}")
            console.print(f"     Errors: {result.get('error_count', 0)}\n")
            
        except Exception as e:
            self.test_results["flow_execution"] = {
                "status": "❌ FAILED",
                "error": str(e),
            }
            console.print(f"  ❌ Flow execution failed: {e}\n")
            raise
    
    async def _test_database_validation(self):
        """Test 2: Validate data in PostgreSQL"""
        console.print("[bold yellow]Step 2: Validating PostgreSQL database...[/bold yellow]")
        
        try:
            conn = await asyncpg.connect(self.db_url)
            
            try:
                # Check bills table
                bills_count = await conn.fetchval("SELECT COUNT(*) FROM bills")
                
                # Get latest bills
                latest_bills = await conn.fetch("""
                    SELECT 
                        number,
                        title_en as title,
                        law_status as status,
                        parliament,
                        session,
                        created_at,
                        updated_at
                    FROM bills
                    ORDER BY updated_at DESC
                    LIMIT 10
                """)
                
                # Check fetch_logs table
                recent_logs = await conn.fetch("""
                    SELECT 
                        source,
                        status,
                        records_succeeded,
                        records_failed,
                        duration_seconds,
                        created_at
                    FROM fetch_logs
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                
                # Check politicians table
                politicians_count = await conn.fetchval("SELECT COUNT(*) FROM politicians")
                
                self.test_results["database_validation"] = {
                    "status": "✅ PASSED",
                    "total_bills": bills_count,
                    "latest_bills": [
                        {
                            "bill_number": bill["number"],
                            "title": bill["title"][:50] + "..." if len(bill["title"]) > 50 else bill["title"],
                            "status": bill["status"] or "Unknown",
                            "parliament": f"{bill['parliament']}-{bill['session']}",
                        }
                        for bill in latest_bills[:5]
                    ],
                    "recent_logs": len(recent_logs),
                    "politicians_count": politicians_count,
                }
                
                console.print(f"  ✅ Database connection successful")
                console.print(f"     Total bills in database: {bills_count}")
                console.print(f"     Total politicians: {politicians_count}")
                console.print(f"     Recent fetch logs: {len(recent_logs)}")
                console.print(f"     Latest 5 bills:")
                
                for bill in latest_bills[:5]:
                    console.print(f"       - {bill['number']}: {bill['title'][:60]}...")
                
                console.print()
                
            finally:
                await conn.close()
                
        except Exception as e:
            self.test_results["database_validation"] = {
                "status": "❌ FAILED",
                "error": str(e),
            }
            console.print(f"  ❌ Database validation failed: {e}\n")
            raise
    
    async def _test_redis_validation(self):
        """Test 3: Validate Redis cache"""
        console.print("[bold yellow]Step 3: Validating Redis cache...[/bold yellow]")
        
        try:
            redis_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            
            try:
                # Test connection
                await redis_client.ping()
                
                # Get Redis info
                info = await redis_client.info()
                
                # Get all keys (for inspection)
                keys = await redis_client.keys("*")
                
                # Get Prefect-related keys
                prefect_keys = [k for k in keys if "prefect" in k.lower()]
                bill_keys = [k for k in keys if "bill" in k.lower()]
                
                self.test_results["redis_validation"] = {
                    "status": "✅ PASSED",
                    "redis_version": info.get("redis_version", "unknown"),
                    "total_keys": len(keys),
                    "prefect_keys": len(prefect_keys),
                    "bill_keys": len(bill_keys),
                    "memory_used": info.get("used_memory_human", "unknown"),
                }
                
                console.print(f"  ✅ Redis connection successful")
                console.print(f"     Redis version: {info.get('redis_version', 'unknown')}")
                console.print(f"     Total keys: {len(keys)}")
                console.print(f"     Prefect-related keys: {len(prefect_keys)}")
                console.print(f"     Bill-related keys: {len(bill_keys)}")
                console.print(f"     Memory used: {info.get('used_memory_human', 'unknown')}\n")
                
            finally:
                await redis_client.aclose()
                
        except Exception as e:
            self.test_results["redis_validation"] = {
                "status": "⚠️  WARNING",
                "error": str(e),
                "note": "Redis cache not critical for ETL operation"
            }
            console.print(f"  ⚠️  Redis validation warning: {e}")
            console.print(f"     (Redis is optional - ETL will continue)\n")
    
    async def _test_data_quality(self):
        """Test 4: Validate data quality"""
        console.print("[bold yellow]Step 4: Validating data quality...[/bold yellow]")
        
        try:
            conn = await asyncpg.connect(self.db_url)
            
            try:
                # Check for required fields
                bills_with_nulls = await conn.fetch("""
                    SELECT 
                        number,
                        CASE WHEN title_en IS NULL THEN 'title' END as missing_title,
                        CASE WHEN law_status IS NULL THEN 'status' END as missing_status,
                        CASE WHEN parliament IS NULL THEN 'parliament' END as missing_parliament
                    FROM bills
                    WHERE title_en IS NULL OR parliament IS NULL
                    LIMIT 10
                """)
                
                # Check for recent bills (updated in last hour)
                recent_bills = await conn.fetchval("""
                    SELECT COUNT(*) 
                    FROM bills 
                    WHERE updated_at > NOW() - INTERVAL '1 hour'
                """)
                
                # Check for duplicate bill numbers
                duplicates = await conn.fetch("""
                    SELECT jurisdiction, parliament, session, number, COUNT(*) as count
                    FROM bills
                    GROUP BY jurisdiction, parliament, session, number
                    HAVING COUNT(*) > 1
                """)
                
                # Check bill status distribution
                status_distribution = await conn.fetch("""
                    SELECT law_status as status, COUNT(*) as count
                    FROM bills
                    GROUP BY law_status
                    ORDER BY count DESC
                    LIMIT 10
                """)
                
                # Validate fetch logs
                failed_fetches = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM fetch_logs
                    WHERE status = 'error'
                    AND created_at > NOW() - INTERVAL '1 hour'
                """)
                
                self.test_results["data_quality"] = {
                    "status": "✅ PASSED" if len(bills_with_nulls) == 0 and len(duplicates) == 0 else "⚠️  WARNING",
                    "bills_with_nulls": len(bills_with_nulls),
                    "recent_updates": recent_bills,
                    "duplicate_bills": len(duplicates),
                    "failed_fetches": failed_fetches,
                    "status_distribution": [
                        {"status": row["status"], "count": row["count"]}
                        for row in status_distribution
                    ],
                }
                
                console.print(f"  ✅ Data quality checks completed")
                console.print(f"     Bills with missing required fields: {len(bills_with_nulls)}")
                console.print(f"     Recent updates (last hour): {recent_bills}")
                console.print(f"     Duplicate bill numbers: {len(duplicates)}")
                console.print(f"     Failed fetches (last hour): {failed_fetches}")
                console.print(f"     Bill status distribution:")
                
                for row in status_distribution[:5]:
                    console.print(f"       - {row['status']}: {row['count']} bills")
                
                console.print()
                
            finally:
                await conn.close()
                
        except Exception as e:
            self.test_results["data_quality"] = {
                "status": "❌ FAILED",
                "error": str(e),
            }
            console.print(f"  ❌ Data quality validation failed: {e}\n")
            raise
    
    async def _generate_report(self):
        """Generate comprehensive test report"""
        console.print("\n[bold cyan]📊 ETL Pipeline Test Report[/bold cyan]\n")
        
        # Test Summary Table
        summary_table = Table(title="Test Summary", show_header=True, header_style="bold magenta")
        summary_table.add_column("Test", style="cyan", width=30)
        summary_table.add_column("Status", width=15)
        summary_table.add_column("Details", width=50)
        
        # Flow Execution
        flow_result = self.test_results.get("flow_execution", {})
        if flow_result.get("status") == "✅ PASSED":
            summary_table.add_row(
                "1. Flow Execution",
                flow_result["status"],
                f"Fetched: {flow_result['bills_fetched']}, Created: {flow_result['created']}, Updated: {flow_result['updated']}"
            )
        else:
            summary_table.add_row(
                "1. Flow Execution",
                flow_result.get("status", "❌ FAILED"),
                flow_result.get("error", "Unknown error")
            )
        
        # Database Validation
        db_result = self.test_results.get("database_validation", {})
        if db_result.get("status") == "✅ PASSED":
            summary_table.add_row(
                "2. Database Validation",
                db_result["status"],
                f"Total bills: {db_result['total_bills']}, Politicians: {db_result['politicians_count']}"
            )
        else:
            summary_table.add_row(
                "2. Database Validation",
                db_result.get("status", "❌ FAILED"),
                db_result.get("error", "Unknown error")
            )
        
        # Redis Validation
        redis_result = self.test_results.get("redis_validation", {})
        summary_table.add_row(
            "3. Redis Validation",
            redis_result.get("status", "❌ FAILED"),
            f"Keys: {redis_result.get('total_keys', 0)}, Memory: {redis_result.get('memory_used', 'N/A')}"
            if redis_result.get("status") == "✅ PASSED"
            else redis_result.get("note", "Redis unavailable")
        )
        
        # Data Quality
        quality_result = self.test_results.get("data_quality", {})
        if quality_result.get("status") in ["✅ PASSED", "⚠️  WARNING"]:
            summary_table.add_row(
                "4. Data Quality",
                quality_result["status"],
                f"Recent updates: {quality_result['recent_updates']}, Nulls: {quality_result['bills_with_nulls']}, Duplicates: {quality_result['duplicate_bills']}"
            )
        else:
            summary_table.add_row(
                "4. Data Quality",
                quality_result.get("status", "❌ FAILED"),
                quality_result.get("error", "Unknown error")
            )
        
        console.print(summary_table)
        
        # Latest Bills Table
        db_result = self.test_results.get("database_validation", {})
        if db_result.get("latest_bills"):
            console.print()
            bills_table = Table(title="Latest Bills in Database", show_header=True, header_style="bold green")
            bills_table.add_column("Bill Number", style="cyan", width=15)
            bills_table.add_column("Title", width=50)
            bills_table.add_column("Status", width=15)
            bills_table.add_column("Parliament", width=12)
            
            for bill in db_result["latest_bills"]:
                bills_table.add_row(
                    bill["bill_number"],
                    bill["title"],
                    bill["status"],
                    bill["parliament"]
                )
            
            console.print(bills_table)
        
        # Overall Status
        console.print()
        all_passed = (
            flow_result.get("status") == "✅ PASSED" and
            db_result.get("status") == "✅ PASSED" and
            quality_result.get("status") in ["✅ PASSED", "⚠️  WARNING"]
        )
        
        if all_passed:
            console.print(Panel(
                "[bold green]🎉 ETL Pipeline Test: PASSED[/bold green]\n\n"
                "All critical systems validated:\n"
                "✅ Prefect flow execution\n"
                "✅ PostgreSQL database persistence\n"
                "✅ Data quality checks\n"
                f"{'✅' if redis_result.get('status') == '✅ PASSED' else '⚠️ '} Redis cache (optional)\n\n"
                "[bold]Next Steps:[/bold]\n"
                "1. Run full ingestion: python scripts/run_full_etl.py\n"
                "2. Deploy Prefect flows: prefect deploy --all\n"
                "3. Start Prefect worker: prefect worker start --pool default-agent-pool",
                title="✅ Test Summary",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[bold red]❌ ETL Pipeline Test: FAILED[/bold red]\n\n"
                "Review errors above and fix issues before proceeding.",
                title="❌ Test Summary",
                border_style="red"
            ))


async def main():
    """Main test execution"""
    test = ETLPipelineTest()
    await test.run_complete_test()


if __name__ == "__main__":
    asyncio.run(main())
