"""
Prefect flow for fetching and storing vote data.

Orchestrates the vote adapter to fetch parliamentary votes and vote records.
"""
import asyncio
from datetime import datetime
from typing import List
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.vote_adapter import VoteAdapter
from src.db.session import async_session_factory
from src.db.models import VoteModel, VoteRecordModel
from src.models.adapter_models import VoteData

logger = logging.getLogger(__name__)


@task(name="fetch_votes", retries=2, retry_delay_seconds=30)
async def fetch_votes_task(parliament: int, session: int, limit: int = 500) -> List[VoteData]:
    """
    Fetch votes for a parliament session.
    
    Args:
        parliament: Parliament number
        session: Session number
        limit: Results per page
        
    Returns:
        List of VoteData objects
    """
    logger = get_run_logger()
    logger.info(f"Fetching votes for Parliament {parliament}, Session {session}")
    
    adapter = VoteAdapter()
    votes = await adapter.fetch_votes_for_session(parliament, session, limit)
    
    logger.info(f"Fetched {len(votes)} votes")
    return votes


@task(name="fetch_vote_details", retries=2, retry_delay_seconds=30)
async def fetch_vote_details_task(vote_url: str) -> VoteData:
    """
    Fetch detailed vote information including ballots.
    
    Args:
        vote_url: API URL for the vote
        
    Returns:
        VoteData with ballot records
    """
    logger = get_run_logger()
    adapter = VoteAdapter()
    vote = await adapter.fetch_vote_detail(vote_url)
    
    if vote:
        logger.info(f"Fetched vote {vote.vote_number} with {len(vote.vote_records)} ballots")
    
    return vote


@task(name="store_votes", retries=1)
async def store_votes_task(votes: List[VoteData]) -> int:
    """
    Store votes in the database.
    
    Args:
        votes: List of VoteData objects
        
    Returns:
        Number of votes stored
    """
    logger = get_run_logger()
    logger.info(f"Storing {len(votes)} votes in database")
    
    stored_count = 0
    
    async with async_session_factory() as session:
        for vote_data in votes:
            try:
                # Check if vote already exists
                existing = await session.get(VoteModel, (vote_data.vote_id, "ca-federal"))
                
                if existing:
                    # Update existing vote
                    existing.parliament = vote_data.parliament
                    existing.session = vote_data.session
                    existing.vote_number = vote_data.vote_number
                    existing.chamber = vote_data.chamber
                    existing.vote_date = vote_data.vote_date
                    existing.vote_description_en = vote_data.vote_description_en
                    existing.vote_description_fr = vote_data.vote_description_fr
                    existing.bill_number = vote_data.bill_number
                    existing.result = vote_data.result
                    existing.yeas = vote_data.yeas
                    existing.nays = vote_data.nays
                    existing.abstentions = vote_data.abstentions
                    existing.updated_at = datetime.utcnow()
                    
                    vote_model = existing
                else:
                    # Create new vote
                    vote_model = VoteModel(
                        natural_id=vote_data.vote_id,
                        jurisdiction="ca-federal",
                        parliament=vote_data.parliament,
                        session=vote_data.session,
                        vote_number=vote_data.vote_number,
                        chamber=vote_data.chamber,
                        vote_date=vote_data.vote_date,
                        vote_description_en=vote_data.vote_description_en,
                        vote_description_fr=vote_data.vote_description_fr,
                        bill_number=vote_data.bill_number,
                        result=vote_data.result,
                        yeas=vote_data.yeas,
                        nays=vote_data.nays,
                        abstentions=vote_data.abstentions
                    )
                    session.add(vote_model)
                
                # Store vote records if present
                if vote_data.vote_records:
                    for record_data in vote_data.vote_records:
                        # Check if record exists
                        record_id = f"{vote_data.vote_id}-{record_data.politician_id}"
                        existing_record = await session.get(VoteRecordModel, (record_id, "ca-federal"))
                        
                        if not existing_record:
                            record_model = VoteRecordModel(
                                natural_id=record_id,
                                jurisdiction="ca-federal",
                                vote_id=vote_data.vote_id,
                                politician_id=record_data.politician_id,
                                vote_position=record_data.vote_position
                            )
                            session.add(record_model)
                
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing vote {vote_data.vote_id}: {e}")
        
        await session.commit()
    
    logger.info(f"Stored {stored_count} votes")
    return stored_count


@flow(
    name="fetch_votes",
    description="Fetch and store parliamentary vote data",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_votes_flow(
    parliament: int = 44,
    session: int = 1,
    limit: int = 500,
    include_ballots: bool = False
) -> dict:
    """
    Main flow to fetch and store vote data.
    
    Args:
        parliament: Parliament number (default: 44)
        session: Session number (default: 1)
        limit: Results per page (default: 500)
        include_ballots: Whether to fetch individual ballot records (default: False)
        
    Returns:
        Dictionary with flow results
    """
    logger = get_run_logger()
    logger.info(f"Starting vote fetch flow for {parliament}-{session}")
    
    start_time = datetime.utcnow()
    
    # Fetch votes
    votes = await fetch_votes_task(parliament, session, limit)
    
    # Optionally fetch ballot details
    if include_ballots and votes:
        logger.info(f"Fetching ballot details for {len(votes)} votes")
        # Note: This would require vote URLs from the API
        # For now, we'll skip this step
        pass
    
    # Store votes
    stored_count = await store_votes_task(votes)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "parliament": parliament,
        "session": session,
        "votes_fetched": len(votes),
        "votes_stored": stored_count,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger.info(f"Vote fetch flow completed: {result}")
    return result


@flow(
    name="fetch_latest_votes",
    description="Fetch and store latest parliamentary votes",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_latest_votes_flow(limit: int = 50) -> dict:
    """
    Fetch and store the most recent votes.
    
    Args:
        limit: Maximum number of votes to fetch (default: 50)
        
    Returns:
        Dictionary with flow results
    """
    logger = get_run_logger()
    logger.info(f"Starting latest votes fetch flow (limit: {limit})")
    
    start_time = datetime.utcnow()
    
    # Fetch latest votes
    adapter = VoteAdapter()
    votes = await adapter.fetch_latest_votes(limit)
    
    # Store votes
    stored_count = await store_votes_task(votes)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "votes_fetched": len(votes),
        "votes_stored": stored_count,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger.info(f"Latest votes fetch flow completed: {result}")
    return result


if __name__ == "__main__":
    # Run the flow for testing
    asyncio.run(fetch_votes_flow(parliament=44, session=1, limit=100))
