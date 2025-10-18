"""
Fetch REAL data and store in LOCAL SQLite database.

This script:
1. Uses LOCAL SQLite database (not PostgreSQL)
2. Fetches REAL data from OpenParliament API
3. Stores everything locally for frontend development

Responsibility: Local data population for development
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force LOCAL environment with SQLite
os.environ['ENVIRONMENT'] = 'local'
os.environ['DB_DRIVER'] = 'sqlite+aiosqlite'
os.environ['DB_DATABASE'] = 'parliament_explorer_local.db'

from src.services.bill_integration_service import BillIntegrationService
from src.db.session import db
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


async def populate_local_database():
    """Fetch real data and populate local SQLite database."""
    
    console.print("\n[bold cyan]🏛️  TrueCivic Local Data Population[/bold cyan]")
    console.print("[dim]Fetching REAL data from OpenParliament API...[/dim]\n")
    
    try:
        # Initialize database
        await db.initialize()
        console.print("✅ Local SQLite database initialized\n")
        
        # Create service
        service = BillIntegrationService(database=db)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Fetch Bills - Parliament 44, Session 1 (current)
            task1 = progress.add_task("Fetching bills from Parliament 44...", total=None)
            result = await service.fetch_and_persist(
                parliament=44,
                session=1,
                limit=100,  # Get 100 real bills
                enrich=True
            )
            progress.update(task1, completed=True)
            
            console.print(f"\n[green]✅ Bills fetched and stored locally:[/green]")
            console.print(f"   • Fetched: {result['bills_fetched']}")
            console.print(f"   • Created: {result['created']}")
            console.print(f"   • Updated: {result['updated']}")
            console.print(f"   • Errors: {result['error_count']}")
            console.print(f"   • Duration: {result['duration_seconds']:.2f}s")
        
        # TODO: Add politicians, votes, debates when services are ready
        console.print("\n[yellow]⚠️  Note: Politicians, Votes, and Debates services not yet implemented[/yellow]")
        console.print("[dim]   These will be added once integration services are created[/dim]")
        
        console.print(f"\n[bold green]✅ Local database populated successfully![/bold green]")
        console.print(f"[dim]Database location: {Path('parliament_explorer_local.db').absolute()}[/dim]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(populate_local_database())
