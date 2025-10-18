"""
Prefect flow for fetching and storing vote data.

Orchestrates the vote adapter to fetch parliamentary votes and vote records.
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy import select

from src.adapters.vote_adapter import VoteAdapter
from src.db.session import async_session_factory
from src.db.models import BillModel, VoteModel, VoteRecordModel
from src.models.adapter_models import VoteData

logger = logging.getLogger(__name__)


@task(name="fetch_votes", retries=2, retry_delay_seconds=30)
async def fetch_votes_task(
    parliament: int,
    session: int,
    limit: int = 500,
    include_ballots: bool = True,
) -> List[VoteData]:
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
    try:
        votes = await adapter.fetch_votes_for_session(
            parliament,
            session,
            limit,
            include_ballots=include_ballots,
        )
    finally:
        await adapter.close()
    
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
    try:
        vote = await adapter.fetch_vote_detail(vote_url)
        if vote:
            logger.info(f"Fetched vote {vote.vote_number} with {len(vote.vote_records)} ballots")
        return vote
    finally:
        await adapter.close()


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
    bill_cache: Dict[Tuple[int, int, str], Optional[int]] = {}

    async with async_session_factory() as session:
        for vote_data in votes:
            try:
                stmt = select(VoteModel).where(
                    VoteModel.jurisdiction == "ca-federal",
                    VoteModel.vote_id == vote_data.vote_id
                )
                existing_result = await session.execute(stmt)
                vote_model = existing_result.scalar_one_or_none()

                if vote_model:
                    vote_model.parliament = vote_data.parliament
                    vote_model.session = vote_data.session
                    vote_model.vote_number = vote_data.vote_number
                    vote_model.chamber = vote_data.chamber
                    vote_model.vote_date = vote_data.vote_date or vote_model.vote_date
                    vote_model.vote_description_en = vote_data.vote_description_en
                    vote_model.vote_description_fr = vote_data.vote_description_fr
                    vote_model.result = vote_data.result
                    vote_model.yeas = vote_data.yeas
                    vote_model.nays = vote_data.nays
                    vote_model.abstentions = vote_data.abstentions
                    vote_model.updated_at = datetime.utcnow()
                else:
                    vote_model = VoteModel(
                        jurisdiction="ca-federal",
                        vote_id=vote_data.vote_id,
                        parliament=vote_data.parliament,
                        session=vote_data.session,
                        vote_number=vote_data.vote_number,
                        chamber=vote_data.chamber,
                        vote_date=vote_data.vote_date or datetime.utcnow(),
                        vote_description_en=vote_data.vote_description_en,
                        vote_description_fr=vote_data.vote_description_fr,
                        result=vote_data.result,
                        yeas=vote_data.yeas,
                        nays=vote_data.nays,
                        abstentions=vote_data.abstentions
                    )
                    session.add(vote_model)
                    await session.flush()

                if vote_data.bill_number:
                    bill_key = (
                        vote_data.parliament,
                        vote_data.session,
                        vote_data.bill_number,
                    )
                    if bill_key not in bill_cache:
                        bill_stmt = select(BillModel.id).where(
                            BillModel.jurisdiction == "ca-federal",
                            BillModel.parliament == vote_data.parliament,
                            BillModel.session == vote_data.session,
                            BillModel.number == vote_data.bill_number,
                        )
                        bill_result = await session.execute(bill_stmt)
                        bill_cache[bill_key] = bill_result.scalar_one_or_none()

                    vote_model.bill_id = bill_cache[bill_key]
                else:
                    vote_model.bill_id = None

                if vote_model.id is None:
                    await session.flush()

                if vote_data.vote_records:
                    existing_records_result = await session.execute(
                        select(VoteRecordModel).where(
                            VoteRecordModel.vote_id == vote_model.id
                        )
                    )
                    existing_records = {
                        record.politician_id: record
                        for record in existing_records_result.scalars()
                    }
                    synced_politicians: Set[int] = set()

                    for record_data in vote_data.vote_records:
                        if record_data.politician_id is None:
                            continue

                        synced_politicians.add(record_data.politician_id)
                        existing_record = existing_records.get(
                            record_data.politician_id
                        )

                        if existing_record:
                            existing_record.vote_position = record_data.vote_position
                        else:
                            session.add(
                                VoteRecordModel(
                                    vote_id=vote_model.id,
                                    politician_id=record_data.politician_id,
                                    vote_position=record_data.vote_position,
                                )
                            )

                    for politician_id, record in existing_records.items():
                        if politician_id not in synced_politicians:
                            await session.delete(record)

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
    votes = await fetch_votes_task(parliament, session, limit, include_ballots)
    
    # Optionally fetch ballot details
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
    try:
        votes = await adapter.fetch_latest_votes(limit)
    finally:
        await adapter.close()
    
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
