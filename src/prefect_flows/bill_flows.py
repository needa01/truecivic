"""
Prefect flows for Parliament Explorer bill ingestion pipeline.

Defines flows for:
- Fetching bills from OpenParliament API
- Enriching bills with LEGISinfo data
- Persisting bills to database
- Monitoring fetch operations

Responsibility: Orchestrate periodic bill data refreshes
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash

from src.services.bill_integration_service import BillIntegrationService
from src.db.session import Database


@task(
    name="fetch_bills",
    description="Fetch bills from OpenParliament and enrich with LEGISinfo",
    retries=3,
    retry_delay_seconds=60,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
async def fetch_bills_task(
    limit: int = 50,
    parliament: Optional[int] = None,
    session: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Fetch bills from OpenParliament, enrich with LEGISinfo, and persist to database.
    
    Args:
        limit: Maximum number of bills to fetch
        parliament: Specific parliament number (None for all)
        session: Specific session number (None for all)
        
    Returns:
        Dictionary with operation statistics
    """
    logger = get_run_logger()
    logger.info(f"Starting bill fetch: limit={limit}, parliament={parliament}, session={session}")
    
    # Initialize database and integration service
    db = Database()
    await db.initialize()
    
    try:
        async with BillIntegrationService(db) as service:
            logger.info(f"Fetching {limit} bills from OpenParliament API...")
            
            result = await service.fetch_and_persist(
                limit=limit,
                parliament=parliament,
                session=session,
            )
            
            logger.info(
                f"Fetch complete: {result['bills_fetched']} bills, "
                f"{result['created']} created, {result['updated']} updated, "
                f"{result['error_count']} errors"
            )
            
            return result
    finally:
        await db.close()


@task(
    name="monitor_fetch_operations",
    description="Monitor fetch operations and report statistics",
    retries=2,
    retry_delay_seconds=30,
)
async def monitor_fetch_operations_task(hours_back: int = 24) -> Dict[str, Any]:
    """
    Monitor fetch operations from the last N hours and report statistics.
    
    Args:
        hours_back: Number of hours to look back
        
    Returns:
        Dictionary with monitoring statistics
    """
    logger = get_run_logger()
    logger.info(f"Monitoring fetch operations for last {hours_back} hours...")
    
    db = Database()
    await db.initialize()
    
    try:
        # Query fetch_logs table for monitoring
        from src.db.repositories.fetch_log_repository import FetchLogRepository
        
        repo = FetchLogRepository(db)
        
        # Get logs from last N hours
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        logs = await repo.get_logs_since(cutoff_time)
        
        # Calculate statistics
        total_operations = len(logs)
        successful = sum(1 for log in logs if log.status == "success")
        failed = sum(1 for log in logs if log.status == "error")
        partial = sum(1 for log in logs if log.status == "partial")
        
        avg_duration = (
            sum(log.duration_seconds for log in logs) / total_operations
            if total_operations > 0
            else 0
        )
        
        stats = {
            "total_operations": total_operations,
            "successful": successful,
            "failed": failed,
            "partial": partial,
            "avg_duration_seconds": round(avg_duration, 2),
            "success_rate": round(successful / total_operations * 100, 2) if total_operations > 0 else 0,
        }
        
        logger.info(f"Monitoring stats: {stats}")
        return stats
        
    finally:
        await db.close()


@flow(
    name="fetch-latest-bills",
    description="Fetch latest bills from OpenParliament and LEGISinfo",
    log_prints=True,
)
async def fetch_latest_bills_flow(limit: int = 50) -> Dict[str, Any]:
    """
    Main flow for fetching latest bills.
    
    This flow:
    1. Fetches bills from OpenParliament API (most recent first)
    2. Enriches with LEGISinfo data (status, summaries, sponsor names)
    3. Upserts into database (creates new, updates existing)
    4. Logs operation for monitoring
    
    Args:
        limit: Maximum number of bills to fetch (default 50)
        
    Returns:
        Operation statistics
    """
    logger = get_run_logger()
    logger.info(f"🏛️ Starting Parliament Explorer bill fetch flow (limit={limit})")
    
    # Fetch bills
    result = await fetch_bills_task(limit=limit)
    
    logger.info(
        f"✅ Flow complete: {result['bills_fetched']} bills processed, "
        f"{result['created']} created, {result['updated']} updated"
    )
    
    return result


@flow(
    name="fetch-parliament-session-bills",
    description="Fetch all bills from a specific parliament and session",
    log_prints=True,
)
async def fetch_parliament_session_bills_flow(
    parliament: int,
    session: int,
    limit: int = 1000,
) -> Dict[str, Any]:
    """
    Backfill flow for fetching all bills from a specific parliament and session.
    
    Args:
        parliament: Parliament number (e.g., 44)
        session: Session number (e.g., 1)
        limit: Maximum number of bills to fetch (default 1000)
        
    Returns:
        Operation statistics
    """
    logger = get_run_logger()
    logger.info(f"🏛️ Backfilling bills for Parliament {parliament}, Session {session}")
    
    # Fetch bills for specific parliament/session
    result = await fetch_bills_task(
        limit=limit,
        parliament=parliament,
        session=session,
    )
    
    logger.info(
        f"✅ Backfill complete for P{parliament}S{session}: "
        f"{result['bills_fetched']} bills processed"
    )
    
    return result


@flow(
    name="monitor-fetch-operations",
    description="Monitor fetch operations and report statistics",
    log_prints=True,
)
async def monitor_fetch_operations_flow(hours_back: int = 24) -> Dict[str, Any]:
    """
    Monitoring flow for fetch operations.
    
    Args:
        hours_back: Number of hours to look back (default 24)
        
    Returns:
        Monitoring statistics
    """
    logger = get_run_logger()
    logger.info(f"📊 Monitoring fetch operations (last {hours_back} hours)")
    
    # Get monitoring stats
    stats = await monitor_fetch_operations_task(hours_back=hours_back)
    
    logger.info(
        f"✅ Monitoring complete: {stats['total_operations']} operations, "
        f"{stats['success_rate']}% success rate"
    )
    
    return stats


if __name__ == "__main__":
    import asyncio
    
    # Test the flow locally
    asyncio.run(fetch_latest_bills_flow(limit=10))
