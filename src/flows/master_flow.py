"""
Master orchestration flow for data ingestion.

Coordinates execution of all adapter flows in the correct sequence.
"""
import asyncio
from datetime import datetime
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.prefect_flows.bill_flows import fetch_bills_flow
from src.flows.vote_flow import fetch_votes_flow, fetch_latest_votes_flow
from src.flows.hansard_flow import fetch_debates_flow, fetch_latest_debates_flow
from src.flows.committee_flow import fetch_committees_flow, fetch_all_committees_flow

logger = logging.getLogger(__name__)


@flow(
    name="ingest_all_data",
    description="Master flow to ingest all parliamentary data",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def ingest_all_data_flow(
    parliament: int = 44,
    session: int = 1,
    full_ingest: bool = False
) -> dict:
    """
    Master orchestration flow to ingest all data types.
    
    Runs all adapters in sequence to populate the database with:
    - Bills
    - Votes
    - Debates/Hansard
    - Committees
    
    Args:
        parliament: Parliament number (default: 44)
        session: Session number (default: 1)
        full_ingest: If True, fetch complete historical data; if False, fetch recent only
        
    Returns:
        Dictionary with results from all flows
    """
    logger = get_run_logger()
    logger.info(f"Starting master data ingestion flow for {parliament}-{session}")
    logger.info(f"Full ingest: {full_ingest}")
    
    start_time = datetime.utcnow()
    results = {}
    
    # Step 1: Fetch Bills
    logger.info("Step 1: Fetching bills...")
    try:
        bills_result = await fetch_bills_flow(parliament, session)
        results["bills"] = bills_result
        logger.info(f"Bills ingestion completed: {bills_result}")
    except Exception as e:
        logger.error(f"Bills ingestion failed: {e}")
        results["bills"] = {"status": "failed", "error": str(e)}
    
    # Step 2: Fetch Votes
    logger.info("Step 2: Fetching votes...")
    try:
        if full_ingest:
            votes_result = await fetch_votes_flow(parliament, session, limit=500)
        else:
            votes_result = await fetch_latest_votes_flow(limit=50)
        results["votes"] = votes_result
        logger.info(f"Votes ingestion completed: {votes_result}")
    except Exception as e:
        logger.error(f"Votes ingestion failed: {e}")
        results["votes"] = {"status": "failed", "error": str(e)}
    
    # Step 3: Fetch Debates
    logger.info("Step 3: Fetching debates...")
    try:
        if full_ingest:
            debates_result = await fetch_debates_flow(parliament, session, limit=500, include_speeches=True)
        else:
            debates_result = await fetch_latest_debates_flow(limit=50)
        results["debates"] = debates_result
        logger.info(f"Debates ingestion completed: {debates_result}")
    except Exception as e:
        logger.error(f"Debates ingestion failed: {e}")
        results["debates"] = {"status": "failed", "error": str(e)}
    
    # Step 4: Fetch Committees
    logger.info("Step 4: Fetching committees...")
    try:
        if full_ingest:
            committees_result = await fetch_committees_flow(parliament, session)
        else:
            committees_result = await fetch_all_committees_flow()
        results["committees"] = committees_result
        logger.info(f"Committees ingestion completed: {committees_result}")
    except Exception as e:
        logger.error(f"Committees ingestion failed: {e}")
        results["committees"] = {"status": "failed", "error": str(e)}
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    # Calculate totals
    total_records = 0
    failed_flows = []
    
    for flow_name, flow_result in results.items():
        if flow_result.get("status") == "failed":
            failed_flows.append(flow_name)
        else:
            # Sum up records from each flow
            for key in ["bills_stored", "votes_stored", "debates_stored", "committees_stored"]:
                if key in flow_result:
                    total_records += flow_result[key]
    
    summary = {
        "status": "completed" if len(failed_flows) == 0 else "partial_failure",
        "parliament": parliament,
        "session": session,
        "full_ingest": full_ingest,
        "duration_seconds": duration,
        "total_records_ingested": total_records,
        "failed_flows": failed_flows,
        "timestamp": end_time.isoformat(),
        "details": results
    }
    
    logger.info(f"Master ingestion flow completed: {summary}")
    return summary


@flow(
    name="incremental_update",
    description="Incremental update flow for latest data",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def incremental_update_flow() -> dict:
    """
    Incremental update flow to fetch only the latest data.
    
    This is designed to be run frequently (e.g., hourly) to keep data up-to-date.
    Fetches only the most recent records instead of full historical data.
    
    Returns:
        Dictionary with results from all flows
    """
    logger = get_run_logger()
    logger.info("Starting incremental update flow")
    
    start_time = datetime.utcnow()
    results = {}
    
    # Fetch latest votes
    logger.info("Fetching latest votes...")
    try:
        votes_result = await fetch_latest_votes_flow(limit=50)
        results["votes"] = votes_result
    except Exception as e:
        logger.error(f"Latest votes fetch failed: {e}")
        results["votes"] = {"status": "failed", "error": str(e)}
    
    # Fetch latest debates
    logger.info("Fetching latest debates...")
    try:
        debates_result = await fetch_latest_debates_flow(limit=50)
        results["debates"] = debates_result
    except Exception as e:
        logger.error(f"Latest debates fetch failed: {e}")
        results["debates"] = {"status": "failed", "error": str(e)}
    
    # Fetch all committees (lightweight)
    logger.info("Fetching committees...")
    try:
        committees_result = await fetch_all_committees_flow()
        results["committees"] = committees_result
    except Exception as e:
        logger.error(f"Committees fetch failed: {e}")
        results["committees"] = {"status": "failed", "error": str(e)}
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    summary = {
        "status": "completed",
        "flow_type": "incremental",
        "duration_seconds": duration,
        "timestamp": end_time.isoformat(),
        "details": results
    }
    
    logger.info(f"Incremental update completed: {summary}")
    return summary


if __name__ == "__main__":
    # Run full ingestion for testing
    asyncio.run(ingest_all_data_flow(parliament=44, session=1, full_ingest=False))
