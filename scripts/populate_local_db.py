"""Populate the PostgreSQL/pgvector database with real bill data for development."""

import asyncio
import sys
import os
from pathlib import Path

from dotenv import load_dotenv

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def load_environment() -> None:
    """Load .env files to configure database credentials."""
    project_root = Path(__file__).parent.parent
    for env_file in (project_root / ".env.local", project_root / ".env"):
        if env_file.exists():
            load_dotenv(env_file, override=False)


load_environment()
os.environ.setdefault('ENVIRONMENT', 'local')
os.environ.pop('DB_DRIVER', None)
os.environ.pop('DB_DATABASE', None)

from src.services.bill_integration_service import BillIntegrationService
from src.db.session import db
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


async def populate_local_database():
    """Fetch real data and populate the configured PostgreSQL database."""
    
    console.print("\n[bold cyan]🏛️  TrueCivic Data Population[/bold cyan]")
    console.print("[dim]Target: PostgreSQL with pgvector[/dim]")
    console.print("[dim]Fetching real data from OpenParliament API...[/dim]\n")
    
    try:
        # Initialize database
        await db.initialize()
        console.print("✅ PostgreSQL connection initialized\n")
        
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
        
        console.print(f"\n[bold green]✅ Database populated successfully![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(populate_local_database())
