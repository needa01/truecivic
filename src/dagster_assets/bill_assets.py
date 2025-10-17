"""
Dagster assets for Parliament Explorer bill ingestion pipeline.

Defines scheduled assets for:
- Fetching bills from OpenParliament API
- Enriching bills with LEGISinfo data
- Persisting bills to database
- Monitoring fetch operations

Responsibility: Orchestrate periodic bill data refreshes
"""

from datetime import datetime
from typing import Dict, Any

from dagster import (
    asset,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    Output,
    AssetKey,
    DailyPartitionsDefinition,
)

from src.services.bill_integration_service import BillIntegrationService
from src.db.session import Database


# Daily partitions for tracking fetch operations
daily_partitions = DailyPartitionsDefinition(start_date="2025-01-01")


@asset(
    name="fetch_latest_bills",
    group_name="bills",
    compute_kind="python",
    description="Fetch and persist latest bills from OpenParliament API with LEGISinfo enrichment",
)
async def fetch_latest_bills(context: AssetExecutionContext) -> MaterializeResult:
    """
    Fetch latest bills from OpenParliament, enrich with LEGISinfo, and persist to database.
    
    This asset runs periodically to keep bill data up-to-date. It:
    1. Fetches bills from OpenParliament API (most recent first)
    2. Enriches with LEGISinfo data (status, summaries, sponsor names)
    3. Upserts into database (creates new, updates existing)
    4. Logs operation for monitoring
    
    Args:
        context: Dagster execution context for logging and metadata
        
    Returns:
        MaterializeResult with operation statistics
    """
    context.log.info("Starting bill fetch operation...")
    
    # Initialize database and integration service
    db = Database()
    await db.initialize()
    
    try:
        async with BillIntegrationService(db) as service:
            # Fetch bills with limit (configurable via config)
            limit = context.op_config.get("limit", 50)
            context.log.info(f"Fetching {limit} bills from OpenParliament API...")
            
            result = await service.fetch_and_persist(
                limit=limit,
                parliament=None,  # All parliaments
                session=None,     # All sessions
            )
            
            context.log.info(
                f"Fetch complete: {result['bills_fetched']} bills, "
                f"{result['created']} created, {result['updated']} updated"
            )
            
            # Return materialization with metadata
            return MaterializeResult(
                metadata={
                    "bills_fetched": MetadataValue.int(result["bills_fetched"]),
                    "bills_created": MetadataValue.int(result["created"]),
                    "bills_updated": MetadataValue.int(result["updated"]),
                    "error_count": MetadataValue.int(result["error_count"]),
                    "duration_seconds": MetadataValue.float(result["duration_seconds"]),
                    "fetch_timestamp": MetadataValue.timestamp(datetime.utcnow()),
                }
            )
    finally:
        await db.close()


@asset(
    name="fetch_parliament_session_bills",
    group_name="bills",
    compute_kind="python",
    description="Fetch all bills from a specific parliament and session",
)
async def fetch_parliament_session_bills(
    context: AssetExecutionContext,
) -> MaterializeResult:
    """
    Fetch all bills from a specific parliament and session.
    
    This asset is useful for:
    - Backfilling historical data
    - Refreshing specific parliament sessions
    - Initial data load
    
    Configure parliament and session via op_config:
    ```
    run_config = {
        "ops": {
            "fetch_parliament_session_bills": {
                "config": {
                    "parliament": 44,
                    "session": 1,
                    "limit": 1000
                }
            }
        }
    }
    ```
    
    Args:
        context: Dagster execution context for logging and metadata
        
    Returns:
        MaterializeResult with operation statistics
    """
    # Get parliament and session from config
    parliament = context.op_config.get("parliament")
    session = context.op_config.get("session")
    limit = context.op_config.get("limit", 1000)
    
    if not parliament or not session:
        raise ValueError(
            "Must provide 'parliament' and 'session' in op_config. "
            "Example: {'parliament': 44, 'session': 1}"
        )
    
    context.log.info(
        f"Starting fetch for Parliament {parliament}, Session {session} "
        f"(limit: {limit})..."
    )
    
    # Initialize database and integration service
    db = Database()
    await db.initialize()
    
    try:
        async with BillIntegrationService(db) as service:
            result = await service.fetch_and_persist(
                limit=limit,
                parliament=parliament,
                session=session,
            )
            
            context.log.info(
                f"Fetch complete for P{parliament}S{session}: "
                f"{result['bills_fetched']} bills, "
                f"{result['created']} created, {result['updated']} updated"
            )
            
            # Return materialization with metadata
            return MaterializeResult(
                metadata={
                    "parliament": MetadataValue.int(parliament),
                    "session": MetadataValue.int(session),
                    "bills_fetched": MetadataValue.int(result["bills_fetched"]),
                    "bills_created": MetadataValue.int(result["created"]),
                    "bills_updated": MetadataValue.int(result["updated"]),
                    "error_count": MetadataValue.int(result["error_count"]),
                    "duration_seconds": MetadataValue.float(result["duration_seconds"]),
                    "fetch_timestamp": MetadataValue.timestamp(datetime.utcnow()),
                }
            )
    finally:
        await db.close()


@asset(
    name="monitor_fetch_operations",
    group_name="monitoring",
    compute_kind="python",
    description="Monitor recent fetch operations and report statistics",
)
async def monitor_fetch_operations(
    context: AssetExecutionContext,
) -> MaterializeResult:
    """
    Monitor recent fetch operations and report statistics.
    
    This asset queries the fetch_logs table to provide insights into:
    - Recent fetch success/failure rates
    - Average fetch durations
    - Error patterns
    - Data freshness
    
    Args:
        context: Dagster execution context for logging and metadata
        
    Returns:
        MaterializeResult with monitoring statistics
    """
    from src.db.repositories.fetch_log_repository import FetchLogRepository
    from datetime import timedelta
    
    context.log.info("Monitoring fetch operations...")
    
    # Initialize database
    db = Database()
    await db.initialize()
    
    try:
        async with db.session() as session:
            repo = FetchLogRepository(session)
            
            # Get recent logs (last 24 hours)
            hours_back = context.op_config.get("hours_back", 24)
            since = datetime.utcnow() - timedelta(hours=hours_back)
            
            # Query logs
            from sqlalchemy import select, func
            from src.db.models import FetchLogModel
            
            # Count by status
            result = await session.execute(
                select(
                    FetchLogModel.status,
                    func.count(FetchLogModel.id).label("count"),
                    func.avg(FetchLogModel.duration_seconds).label("avg_duration"),
                    func.sum(FetchLogModel.records_succeeded).label("total_succeeded"),
                    func.sum(FetchLogModel.records_failed).label("total_failed"),
                )
                .where(FetchLogModel.created_at >= since)
                .group_by(FetchLogModel.status)
            )
            
            stats = result.all()
            
            # Build metadata
            metadata = {
                "hours_monitored": MetadataValue.int(hours_back),
                "monitoring_timestamp": MetadataValue.timestamp(datetime.utcnow()),
            }
            
            for stat in stats:
                prefix = f"{stat.status}_"
                metadata[f"{prefix}count"] = MetadataValue.int(stat.count)
                metadata[f"{prefix}avg_duration"] = MetadataValue.float(
                    round(stat.avg_duration, 2) if stat.avg_duration else 0
                )
                metadata[f"{prefix}total_succeeded"] = MetadataValue.int(
                    stat.total_succeeded or 0
                )
                metadata[f"{prefix}total_failed"] = MetadataValue.int(
                    stat.total_failed or 0
                )
            
            context.log.info(f"Monitoring complete: {len(stats)} status groups found")
            
            return MaterializeResult(metadata=metadata)
    finally:
        await db.close()
