"""
Prefect flow for fetching committee and committee meeting data.

Orchestrates committee data fetching and storage.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.adapters.openparliament_committees import OpenParliamentCommitteeAdapter
from src.db.session import async_session_factory
from src.db.repositories.committee_repository import CommitteeRepository

logger = logging.getLogger(__name__)


@task(name="fetch_committees", retries=2, retry_delay_seconds=30)
async def fetch_committees_task(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch all parliamentary committees.
    
    Args:
        limit: Maximum committees to fetch
        
    Returns:
        List of committee dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info("Fetching all committees")
    
    adapter = OpenParliamentCommitteeAdapter()
    response = await adapter.fetch_committees(limit=limit)
    
    if response.errors:
        logger_task.error(f"Errors fetching committees: {response.errors}")
    
    logger_task.info(f"Fetched {response.total_fetched} committees")
    return response.records


@task(name="fetch_committee_meetings", retries=2, retry_delay_seconds=30)
async def fetch_committee_meetings_task(
    committee_code: str,
    limit: int = 50,
    parliament: int = None,
    session: int = None
) -> List[Dict[str, Any]]:
    """
    Fetch meetings for a specific committee.
    
    Args:
        committee_code: Committee acronym
        limit: Maximum meetings to fetch
        parliament: Filter by parliament number
        session: Filter by session number
        
    Returns:
        List of meeting dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching meetings for committee: {committee_code}")
    
    adapter = OpenParliamentCommitteeAdapter()
    response = await adapter.fetch_committee_meetings(
        committee_acronym=committee_code,
        limit=limit,
        parliament=parliament,
        session=session
    )
    
    if response.errors:
        logger_task.error(f"Errors fetching meetings: {response.errors}")
    
    logger_task.info(
        f"Fetched {response.total_fetched} meetings for {committee_code}"
    )
    return response.records


@task(name="fetch_meeting_details", retries=2, retry_delay_seconds=30)
async def fetch_meeting_details_task(meeting_id: int) -> Dict[str, Any]:
    """
    Fetch detailed meeting information including witnesses.
    
    Args:
        meeting_id: Meeting ID
        
    Returns:
        Meeting details dictionary
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching meeting details: {meeting_id}")
    
    adapter = OpenParliamentCommitteeAdapter()
    response = await adapter.fetch_meeting_details(meeting_id)
    
    if response.errors:
        logger_task.error(f"Errors fetching meeting details: {response.errors}")
        return {}
    
    if response.records:
        return response.records[0]
    return {}


@task(name="store_committees", retries=1)
async def store_committees_task(
    committees_data: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Store committees in database using batch upsert.
    
    Args:
        committees_data: List of committee dictionaries
        
    Returns:
        Dict with count of stored committees
    """
    logger_task = get_run_logger()
    logger_task.info(f"Storing {len(committees_data)} committees")
    
    if not committees_data:
        return {"stored": 0}
    
    async with async_session_factory() as session:
        committee_repo = CommitteeRepository(session)
        
        # Use batch upsert
        stored_committees = await committee_repo.upsert_many(committees_data)
        await session.commit()
        
        logger_task.info(f"Stored {len(stored_committees)} committees")
        
        return {"stored": len(stored_committees)}


@task(name="store_meetings", retries=1)
async def store_meetings_task(
    meetings_data: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Store committee meetings in database.
    
    Note: This requires a CommitteeMeetingRepository which we'll create separately.
    For now, this is a placeholder.
    
    Args:
        meetings_data: List of meeting dictionaries
        
    Returns:
        Dict with count of stored meetings
    """
    logger_task = get_run_logger()
    logger_task.info(f"Storing {len(meetings_data)} meetings (placeholder)")
    
    # TODO: Implement CommitteeMeetingRepository
    # async with async_session_factory() as session:
    #     meeting_repo = CommitteeMeetingRepository(session)
    #     stored_meetings = await meeting_repo.upsert_many(meetings_data)
    #     await session.commit()
    
    return {"stored": 0, "note": "CommitteeMeetingRepository not yet implemented"}


@flow(
    name="fetch_all_committees",
    description="Fetch and store all parliamentary committees",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_all_committees_flow(limit: int = 100) -> Dict[str, Any]:
    """
    Main flow to fetch and store all committees.
    
    Args:
        limit: Maximum committees to fetch (default: 100)
        
    Returns:
        Dictionary with flow results
    """
    logger_flow = get_run_logger()
    logger_flow.info("Starting fetch all committees flow")
    
    start_time = datetime.utcnow()
    
    # Step 1: Fetch committees
    committees_data = await fetch_committees_task(limit)
    
    if not committees_data:
        return {
            "status": "no_data",
            "committees_fetched": 0,
            "committees_stored": 0
        }
    
    # Step 2: Store committees
    store_result = await store_committees_task(committees_data)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "committees_fetched": len(committees_data),
        "committees_stored": store_result.get("stored", 0),
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger_flow.info(f"Fetch all committees flow completed: {result}")
    return result


@flow(
    name="fetch_committee_meetings_flow",
    description="Fetch and store meetings for specific committees",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_committee_meetings_flow(
    committee_codes: List[str],
    limit_per_committee: int = 50,
    parliament: int = 44,
    session: int = 1
) -> Dict[str, Any]:
    """
    Flow to fetch meetings for multiple committees.
    
    Args:
        committee_codes: List of committee acronyms (e.g., ['HUMA', 'FINA'])
        limit_per_committee: Max meetings per committee
        parliament: Parliament number
        session: Session number
        
    Returns:
        Dictionary with flow results
    """
    logger_flow = get_run_logger()
    logger_flow.info(f"Starting fetch meetings flow for {len(committee_codes)} committees")
    
    start_time = datetime.utcnow()
    
    all_meetings = []
    
    # Fetch meetings for each committee
    for committee_code in committee_codes:
        meetings_data = await fetch_committee_meetings_task(
            committee_code=committee_code,
            limit=limit_per_committee,
            parliament=parliament,
            session=session
        )
        all_meetings.extend(meetings_data)
    
    # Store meetings
    store_result = await store_meetings_task(all_meetings)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "committees_processed": len(committee_codes),
        "meetings_fetched": len(all_meetings),
        "meetings_stored": store_result.get("stored", 0),
        "note": store_result.get("note", ""),
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger_flow.info(f"Fetch committee meetings flow completed: {result}")
    return result


@flow(
    name="fetch_all_committees_daily",
    description="Daily flow to fetch all committees",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_all_committees_daily_flow() -> Dict[str, Any]:
    """
    Daily scheduled flow to fetch all committees.
    
    Returns:
        Dictionary with flow results
    """
    logger_flow = get_run_logger()
    logger_flow.info("Starting daily committees fetch")
    
    return await fetch_all_committees_flow(limit=100)


@flow(
    name="fetch_top_committees_meetings_daily",
    description="Daily flow to fetch meetings for major committees",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_top_committees_meetings_daily_flow() -> Dict[str, Any]:
    """
    Daily scheduled flow to fetch meetings for top committees.
    
    Returns:
        Dictionary with flow results
    """
    logger_flow = get_run_logger()
    logger_flow.info("Starting daily top committees meetings fetch")
    
    # List of major committees to track
    top_committees = [
        "HUMA",  # Human Resources
        "FINA",  # Finance
        "JUST",  # Justice
        "ENVI",  # Environment
        "HESA",  # Health
        "NDDN",  # National Defence
        "ETHI",  # Ethics
        "PROC",  # Procedure
        "TRAN",  # Transport
        "AGRI"   # Agriculture
    ]
    
    return await fetch_committee_meetings_flow(
        committee_codes=top_committees,
        limit_per_committee=20,
        parliament=44,
        session=1
    )


if __name__ == "__main__":
    # Test the flow
    asyncio.run(fetch_all_committees_flow(limit=20))
