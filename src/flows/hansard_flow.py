"""
Prefect flow for fetching and storing Hansard debate data.

Orchestrates the Hansard adapter to fetch parliamentary debates and speeches.
"""
import asyncio
from datetime import datetime
from typing import List
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.hansard_adapter import HansardAdapter
from src.db.session import async_session_factory
from src.db.models import DebateModel, SpeechModel
from src.models.adapter_models import DebateData

logger = logging.getLogger(__name__)


@task(name="fetch_debates", retries=2, retry_delay_seconds=30)
async def fetch_debates_task(parliament: int, session: int, limit: int = 500) -> List[DebateData]:
    """
    Fetch debates for a parliament session.
    
    Args:
        parliament: Parliament number
        session: Session number
        limit: Results per page
        
    Returns:
        List of DebateData objects
    """
    logger = get_run_logger()
    logger.info(f"Fetching debates for Parliament {parliament}, Session {session}")
    
    adapter = HansardAdapter()
    debates = await adapter.fetch_debates_for_session(parliament, session, limit)
    
    logger.info(f"Fetched {len(debates)} debates")
    return debates


@task(name="fetch_debate_speeches", retries=2, retry_delay_seconds=30)
async def fetch_debate_speeches_task(debate_id: str, limit: int = 500):
    """
    Fetch speeches for a specific debate.
    
    Args:
        debate_id: Natural debate ID
        limit: Results per page
        
    Returns:
        List of SpeechData objects
    """
    logger = get_run_logger()
    adapter = HansardAdapter()
    speeches = await adapter.fetch_speeches_for_debate(debate_id, limit)
    
    logger.info(f"Fetched {len(speeches)} speeches for debate {debate_id}")
    return speeches


@task(name="store_debates", retries=1)
async def store_debates_task(debates: List[DebateData]) -> int:
    """
    Store debates and speeches in the database.
    
    Args:
        debates: List of DebateData objects
        
    Returns:
        Number of debates stored
    """
    logger = get_run_logger()
    logger.info(f"Storing {len(debates)} debates in database")
    
    stored_count = 0
    
    async with async_session_factory() as session:
        for debate_data in debates:
            try:
                # Check if debate already exists
                existing = await session.get(DebateModel, (debate_data.debate_id, "ca-federal"))
                
                if existing:
                    # Update existing debate
                    existing.parliament = debate_data.parliament
                    existing.session = debate_data.session
                    existing.debate_number = debate_data.debate_number
                    existing.chamber = debate_data.chamber
                    existing.debate_date = debate_data.debate_date
                    existing.topic_en = debate_data.topic_en
                    existing.topic_fr = debate_data.topic_fr
                    existing.debate_type = debate_data.debate_type
                    existing.updated_at = datetime.utcnow()
                    
                    debate_model = existing
                else:
                    # Create new debate
                    debate_model = DebateModel(
                        natural_id=debate_data.debate_id,
                        jurisdiction="ca-federal",
                        parliament=debate_data.parliament,
                        session=debate_data.session,
                        debate_number=debate_data.debate_number,
                        chamber=debate_data.chamber,
                        debate_date=debate_data.debate_date,
                        topic_en=debate_data.topic_en,
                        topic_fr=debate_data.topic_fr,
                        debate_type=debate_data.debate_type
                    )
                    session.add(debate_model)
                
                # Store speeches if present
                if debate_data.speeches:
                    for speech_data in debate_data.speeches:
                        # Check if speech exists
                        speech_natural_id = f"{debate_data.debate_id}-speech-{speech_data.speech_id}"
                        existing_speech = await session.get(SpeechModel, (speech_natural_id, "ca-federal"))
                        
                        if existing_speech:
                            # Update existing speech
                            existing_speech.politician_id = speech_data.politician_id
                            existing_speech.content_en = speech_data.content_en
                            existing_speech.content_fr = speech_data.content_fr
                            existing_speech.speech_time = speech_data.speech_time
                            existing_speech.speaker_name = speech_data.speaker_name
                            existing_speech.speaker_role = speech_data.speaker_role
                            existing_speech.sequence = speech_data.sequence
                            existing_speech.updated_at = datetime.utcnow()
                        else:
                            # Create new speech
                            speech_model = SpeechModel(
                                natural_id=speech_natural_id,
                                jurisdiction="ca-federal",
                                debate_id=debate_data.debate_id,
                                politician_id=speech_data.politician_id,
                                content_en=speech_data.content_en,
                                content_fr=speech_data.content_fr,
                                speech_time=speech_data.speech_time,
                                speaker_name=speech_data.speaker_name,
                                speaker_role=speech_data.speaker_role,
                                sequence=speech_data.sequence
                            )
                            session.add(speech_model)
                
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing debate {debate_data.debate_id}: {e}")
        
        await session.commit()
    
    logger.info(f"Stored {stored_count} debates")
    return stored_count


@flow(
    name="fetch_debates",
    description="Fetch and store Hansard debate data",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_debates_flow(
    parliament: int = 44,
    session: int = 1,
    limit: int = 500,
    include_speeches: bool = False
) -> dict:
    """
    Main flow to fetch and store debate data.
    
    Args:
        parliament: Parliament number (default: 44)
        session: Session number (default: 1)
        limit: Results per page (default: 500)
        include_speeches: Whether to fetch individual speeches (default: False)
        
    Returns:
        Dictionary with flow results
    """
    logger = get_run_logger()
    logger.info(f"Starting debate fetch flow for {parliament}-{session}")
    
    start_time = datetime.utcnow()
    
    # Fetch debates
    debates = await fetch_debates_task(parliament, session, limit)
    
    # Optionally fetch speeches
    if include_speeches and debates:
        logger.info(f"Fetching speeches for {len(debates)} debates")
        for debate in debates:
            speeches = await fetch_debate_speeches_task(debate.debate_id, limit=500)
            debate.speeches = speeches
    
    # Store debates
    stored_count = await store_debates_task(debates)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "parliament": parliament,
        "session": session,
        "debates_fetched": len(debates),
        "debates_stored": stored_count,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger.info(f"Debate fetch flow completed: {result}")
    return result


@flow(
    name="fetch_latest_debates",
    description="Fetch and store latest parliamentary debates",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_latest_debates_flow(limit: int = 50) -> dict:
    """
    Fetch and store the most recent debates.
    
    Args:
        limit: Maximum number of debates to fetch (default: 50)
        
    Returns:
        Dictionary with flow results
    """
    logger = get_run_logger()
    logger.info(f"Starting latest debates fetch flow (limit: {limit})")
    
    start_time = datetime.utcnow()
    
    # Fetch latest debates
    adapter = HansardAdapter()
    debates = await adapter.fetch_latest_debates(limit)
    
    # Store debates
    stored_count = await store_debates_task(debates)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "debates_fetched": len(debates),
        "debates_stored": stored_count,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger.info(f"Latest debates fetch flow completed: {result}")
    return result


if __name__ == "__main__":
    # Run the flow for testing
    asyncio.run(fetch_debates_flow(parliament=44, session=1, limit=100))
