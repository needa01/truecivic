"""
Enhanced Prefect flow for fetching votes with individual MP voting records.

Orchestrates vote data fetching and storage including individual ballot records.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Tuple
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.adapters.openparliament_votes import OpenParliamentVotesAdapter
from src.db.session import async_session_factory
from src.db.repositories.vote_repository import VoteRepository, VoteRecordRepository
from src.db.models import PoliticianModel

logger = logging.getLogger(__name__)


@task(name="fetch_votes_batch", retries=2, retry_delay_seconds=30)
async def fetch_votes_batch_task(
    parliament: int, 
    session: int, 
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch votes for a parliament session.
    
    Args:
        parliament: Parliament number
        session: Session number
        limit: Maximum votes to fetch
        
    Returns:
        List of vote dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching votes for Parliament {parliament}, Session {session}")
    
    adapter = OpenParliamentVotesAdapter()
    response = await adapter.fetch_votes(
        limit=limit,
        parliament=parliament,
        session=session
    )
    
    if response.errors:
        logger_task.error(f"Errors fetching votes: {response.errors}")
    
    logger_task.info(f"Fetched {response.total_fetched} votes")
    return response.records


@task(name="fetch_vote_records_for_vote", retries=2, retry_delay_seconds=30)
async def fetch_vote_records_task(vote_id: str) -> List[Dict[str, Any]]:
    """
    Fetch individual MP voting records for a specific vote.
    
    Args:
        vote_id: Vote identifier (e.g., '44-1-123')
        
    Returns:
        List of vote record dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching vote records for: {vote_id}")
    
    adapter = OpenParliamentVotesAdapter()
    response = await adapter.fetch_vote_by_id(vote_id)
    
    if response.errors:
        logger_task.error(f"Errors fetching vote records: {response.errors}")
        return []
    
    # Extract MP votes from the response
    if response.records and len(response.records) > 0:
        vote_data = response.records[0]
        mp_votes = vote_data.get("mp_votes", [])
        logger_task.info(f"Fetched {len(mp_votes)} vote records for {vote_id}")
        return mp_votes
    
    return []


@task(name="store_votes_batch", retries=1)
async def store_votes_batch_task(votes_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Store votes in database using batch upsert.
    
    Args:
        votes_data: List of vote dictionaries
        
    Returns:
        Dict with counts of created/updated votes
    """
    logger_task = get_run_logger()
    logger_task.info(f"Storing {len(votes_data)} votes")
    
    if not votes_data:
        return {"created": 0, "updated": 0}
    
    async with async_session_factory() as session:
        vote_repo = VoteRepository(session)
        
        # Use batch upsert
        stored_votes = await vote_repo.upsert_many(votes_data)
        await session.commit()
        
        logger_task.info(f"Stored {len(stored_votes)} votes")
        
        return {
            "stored": len(stored_votes),
            "created": len(stored_votes),  # TODO: Track actual creates vs updates
            "updated": 0
        }


@task(name="store_vote_records_batch", retries=1)
async def store_vote_records_batch_task(
    vote_id: str,
    vote_db_id: int,
    records_data: List[Dict[str, Any]]
) -> int:
    """
    Store vote records in database using batch upsert.
    
    Args:
        vote_id: Vote identifier
        vote_db_id: Vote database ID
        records_data: List of vote record dictionaries with politician_id and vote_position
        
    Returns:
        Count of stored records
    """
    logger_task = get_run_logger()
    logger_task.info(f"Storing {len(records_data)} vote records for vote {vote_id}")
    
    if not records_data:
        return 0
    
    async with async_session_factory() as session:
        vote_record_repo = VoteRecordRepository(session)
        
        # Map OpenParliament politician IDs to our database IDs
        records_to_insert = []
        
        for record in records_data:
            op_politician_id = record.get("politician_id")
            if not op_politician_id:
                continue
            
            # Find politician by OpenParliament ID
            # TODO: This requires a mapping table or field in PoliticianModel
            # For now, we'll skip records where we can't find the politician
            # In production, we need a politician_mappings table or openparliament_id field
            
            # Placeholder: assume politician_id maps directly (needs fixing)
            records_to_insert.append({
                "vote_id": vote_db_id,
                "politician_id": op_politician_id,  # TODO: Map to our DB ID
                "vote_position": record.get("vote_position", "Unknown")
            })
        
        if records_to_insert:
            stored_records = await vote_record_repo.upsert_many(records_to_insert)
            await session.commit()
            logger_task.info(f"Stored {len(stored_records)} vote records")
            return len(stored_records)
        
        return 0


@task(name="get_vote_db_id")
async def get_vote_db_id_task(jurisdiction: str, vote_id: str) -> int:
    """
    Get database ID for a vote by its natural key.
    
    Args:
        jurisdiction: Jurisdiction code
        vote_id: Vote identifier
        
    Returns:
        Database ID or None
    """
    async with async_session_factory() as session:
        vote_repo = VoteRepository(session)
        vote = await vote_repo.get_by_vote_id(jurisdiction, vote_id)
        return vote.id if vote else None


@flow(
    name="fetch_votes_with_records",
    description="Fetch votes and individual MP voting records",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_votes_with_records_flow(
    parliament: int = 44,
    session: int = 1,
    limit: int = 100,
    fetch_records: bool = True
) -> Dict[str, Any]:
    """
    Main flow to fetch and store votes with optional individual MP records.
    
    Args:
        parliament: Parliament number (default: 44)
        session: Session number (default: 1)
        limit: Maximum votes to fetch (default: 100)
        fetch_records: Whether to fetch individual MP voting records (default: True)
        
    Returns:
        Dictionary with flow results
    """
    logger_flow = get_run_logger()
    logger_flow.info(f"Starting votes+records flow for {parliament}-{session}")
    
    start_time = datetime.utcnow()
    
    # Step 1: Fetch votes
    votes_data = await fetch_votes_batch_task(parliament, session, limit)
    
    if not votes_data:
        return {
            "status": "no_data",
            "votes_fetched": 0,
            "votes_stored": 0,
            "records_stored": 0
        }
    
    # Step 2: Store votes
    store_result = await store_votes_batch_task(votes_data)
    
    # Step 3: Optionally fetch and store individual MP vote records
    total_records = 0
    if fetch_records:
        logger_flow.info(f"Fetching individual vote records for {len(votes_data)} votes")
        
        for vote_data in votes_data[:10]:  # Limit to first 10 for now (API rate limits)
            vote_id = vote_data.get("vote_id")
            if not vote_id:
                continue
            
            # Get database ID for this vote
            vote_db_id = await get_vote_db_id_task("ca", vote_id)
            if not vote_db_id:
                logger_flow.warning(f"Could not find DB ID for vote {vote_id}")
                continue
            
            # Fetch records for this vote
            records_data = await fetch_vote_records_task(vote_id)
            
            # Store records
            if records_data:
                stored_count = await store_vote_records_batch_task(
                    vote_id, 
                    vote_db_id, 
                    records_data
                )
                total_records += stored_count
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "parliament": parliament,
        "session": session,
        "votes_fetched": len(votes_data),
        "votes_stored": store_result.get("stored", 0),
        "records_stored": total_records,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger_flow.info(f"Votes+records flow completed: {result}")
    return result


@flow(
    name="fetch_latest_votes_hourly",
    description="Hourly flow to fetch latest votes with records",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_latest_votes_hourly_flow(limit: int = 50) -> Dict[str, Any]:
    """
    Hourly scheduled flow to fetch the most recent votes.
    
    Args:
        limit: Maximum votes to fetch (default: 50)
        
    Returns:
        Dictionary with flow results
    """
    logger_flow = get_run_logger()
    logger_flow.info(f"Starting hourly latest votes flow (limit: {limit})")
    
    start_time = datetime.utcnow()
    
    # Fetch latest votes (no filters, just latest)
    adapter = OpenParliamentVotesAdapter()
    response = await adapter.fetch_votes(limit=limit)
    
    if response.errors:
        logger_flow.error(f"Errors fetching votes: {response.errors}")
        return {"status": "error", "errors": response.errors}
    
    votes_data = response.records
    
    # Store votes
    store_result = await store_votes_batch_task(votes_data)
    
    # Fetch records for recent votes (first 20)
    total_records = 0
    for vote_data in votes_data[:20]:
        vote_id = vote_data.get("vote_id")
        if vote_id:
            vote_db_id = await get_vote_db_id_task("ca", vote_id)
            if vote_db_id:
                records_data = await fetch_vote_records_task(vote_id)
                if records_data:
                    stored_count = await store_vote_records_batch_task(
                        vote_id,
                        vote_db_id,
                        records_data
                    )
                    total_records += stored_count
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "votes_fetched": len(votes_data),
        "votes_stored": store_result.get("stored", 0),
        "records_stored": total_records,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger_flow.info(f"Hourly latest votes flow completed: {result}")
    return result


if __name__ == "__main__":
    # Test the flow
    asyncio.run(fetch_votes_with_records_flow(parliament=44, session=1, limit=10))
