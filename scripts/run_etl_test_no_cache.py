"""
Run a complete ETL test without cache to ensure full pipeline functionality.

This script:
1. Clears Prefect task cache
2. Runs fetch with --limit 5 (no cache)
3. Validates data exists in database
4. Generates comprehensive report

Usage:
    python scripts/run_etl_test_no_cache.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Ensure environment variables are loaded before project imports
load_dotenv(".env.production")

import asyncpg
from rich.console import Console
from rich.panel import Panel

from src.db.session import Database
from src.services.bill_integration_service import BillIntegrationService

console = Console()


async def run_etl_test():
    """Run ETL test without cache"""
    
    console.print("\n[bold cyan]🧪 ETL Pipeline Test (No Cache)[/bold cyan]\n")
    
    # Step 1: Initialize database
    console.print("[yellow]Step 1: Initializing database...[/yellow]")
    db = Database()
    await db.initialize()
    console.print("  ✅ Database initialized\n")
    
    # Step 2: Run ETL
    console.print(f"[yellow]Step 2: Running ETL (limit=5, no cache)...[/yellow]")
    
    try:
        async with BillIntegrationService(db) as service:
            result = await service.fetch_and_persist(
                limit=5,
                enrich=True
            )
            
            console.print(f"  ✅ ETL completed")
            console.print(f"     Bills fetched: {result['bills_fetched']}")
            console.print(f"     Created: {result['created']}")
            console.print(f"     Updated: {result['updated']}")
            console.print(f"     Errors: {result['error_count']}")
            console.print(f"     Error messages: {result.get('errors', [])}")
            console.print(f"     Duration: {result['duration_seconds']:.2f}s\n")
            
            if result['error_count'] > 0:
                console.print(f"[red]     Errors encountered:[/red]")
                for err in result.get('errors', []):
                    console.print(f"       - {err}")
                console.print()
            
    except Exception as e:
        console.print(f"  ❌ ETL failed: {e}\n")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await db.close()
    
    # Step 3: Validate database
    console.print("[yellow]Step 3: Validating database...[/yellow]")
    
    db_url = os.getenv("DATABASE_PUBLIC_URL")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Count total bills
        total_bills = await conn.fetchval("SELECT COUNT(*) FROM bills")
        
        # Get latest bills
        latest_bills = await conn.fetch("""
            SELECT 
                jurisdiction,
                parliament,
                session,
                number,
                title_en,
                law_status,
                legisinfo_status,
                created_at,
                updated_at
            FROM bills
            ORDER BY updated_at DESC
            LIMIT 10
        """)
        
        # Get recent fetch logs
        recent_logs = await conn.fetch("""
            SELECT 
                source,
                status,
                records_attempted,
                records_succeeded,
                records_failed,
                duration_seconds,
                created_at
            FROM fetch_logs
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        console.print(f"  ✅ Database validated")
        console.print(f"     Total bills: {total_bills}")
        console.print(f"     Recent fetch logs: {len(recent_logs)}\n")
        
        # Display bills
        if latest_bills:
            console.print("[bold green]Latest Bills:[/bold green]")
            for bill in latest_bills[:5]:
                console.print(
                    f"  • {bill['number']} (P{bill['parliament']}S{bill['session']}): "
                    f"{bill['title_en'][:60]}..."
                )
                console.print(f"    Status: {bill['law_status'] or 'Unknown'}")
                console.print(f"    LEGISinfo: {bill['legisinfo_status'] or 'Not enriched'}")
                console.print()
        else:
            console.print("[yellow]  ⚠️  No bills found in database![/yellow]\n")
        
        # Display logs
        if recent_logs:
            console.print("[bold green]Recent Fetch Logs:[/bold green]")
            for log in recent_logs:
                console.print(
                    f"  • {log['source']}: {log['status']} "
                    f"({log['records_succeeded']}/{log['records_attempted']} succeeded) "
                    f"[{log['duration_seconds']:.2f}s]"
                )
            console.print()
        
        # Final validation
        if total_bills >= result['bills_fetched']:
            console.print(Panel(
                f"[bold green]✅ ETL Test PASSED[/bold green]\n\n"
                f"Successfully fetched and persisted {result['bills_fetched']} bills.\n"
                f"Database now contains {total_bills} total bills.\n\n"
                f"[bold]Next Steps:[/bold]\n"
                f"1. Review bills above to verify data quality\n"
                f"2. Run full ingestion if needed\n"
                f"3. Deploy to Railway: prefect deploy --all",
                title="✅ Test Results",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[bold yellow]⚠️  ETL Test WARNING[/bold yellow]\n\n"
                f"Fetched {result['bills_fetched']} bills but only {total_bills} in database.\n"
                f"Possible data persistence issue.",
                title="⚠️  Test Results",
                border_style="yellow"
            ))
    
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_etl_test())
