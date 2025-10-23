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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.hansard_adapter import HansardAdapter
from src.db.session import async_session_factory
from src.db.models import DebateModel, SpeechModel
from src.models.adapter_models import DebateData, SpeechData

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
                existing_stmt = select(DebateModel).where(
                    DebateModel.jurisdiction == "ca-federal",
                    DebateModel.hansard_id == debate_data.debate_id,
                )
                result = await session.execute(existing_stmt)
                debate_model = result.scalar_one_or_none()

                sitting_date = debate_data.debate_date or datetime.utcnow()
                chamber = debate_data.chamber or "House"

                if debate_model:
                    debate_model.parliament = debate_data.parliament
                    debate_model.session = debate_data.session
                    debate_model.sitting_date = sitting_date
                    debate_model.chamber = chamber
                    debate_model.debate_type = debate_data.debate_type
                    debate_model.document_url = getattr(debate_data, "document_url", None)
                    debate_model.updated_at = datetime.utcnow()
                else:
                    debate_model = DebateModel(
                        jurisdiction="ca-federal",
                        hansard_id=debate_data.debate_id,
                        parliament=debate_data.parliament,
                        session=debate_data.session,
                        sitting_date=sitting_date,
                        chamber=chamber,
                        debate_type=debate_data.debate_type,
                        document_url=getattr(debate_data, "document_url", None),
                    )
                    session.add(debate_model)
                    await session.flush()

                if debate_data.speeches:
                    await _sync_speeches(session, debate_model.id, debate_data.speeches)

                stored_count += 1

            except Exception as exc:
                logger.error("Error storing debate %s: %s", debate_data.debate_id, exc)

        await session.commit()
    
    logger.info(f"Stored {stored_count} debates")
    return stored_count


async def _sync_speeches(
    session: AsyncSession,
    debate_db_id: int,
    speeches: List[SpeechData],
) -> None:
    """Upsert speeches for a debate while pruning removed entries."""

    if not speeches:
        return

    existing_result = await session.execute(
        select(SpeechModel).where(SpeechModel.debate_id == debate_db_id)
    )
    existing_by_sequence = {
        speech.sequence: speech for speech in existing_result.scalars()
    }

    processed_sequences = set()

    for speech_data in speeches:
        sequence = speech_data.sequence or 0
        if sequence <= 0:
            continue

        text_content = speech_data.content_en or speech_data.content_fr
        if not text_content:
            continue

        language = None
        if speech_data.content_en and not speech_data.content_fr:
            language = "en"
        elif speech_data.content_fr and not speech_data.content_en:
            language = "fr"

        timestamp = (
            speech_data.speech_time.isoformat()
            if isinstance(speech_data.speech_time, datetime)
            else None
        )

        existing_speech = existing_by_sequence.get(sequence)
        if existing_speech:
            existing_speech.politician_id = speech_data.politician_id
            existing_speech.speaker_name = speech_data.speaker_name or existing_speech.speaker_name
            existing_speech.language = language
            existing_speech.text_content = text_content
            existing_speech.timestamp_start = timestamp
        else:
            session.add(
                SpeechModel(
                    debate_id=debate_db_id,
                    politician_id=speech_data.politician_id,
                    speaker_name=speech_data.speaker_name or "Unknown speaker",
                    sequence=sequence,
                    language=language,
                    text_content=text_content,
                    timestamp_start=timestamp,
                    timestamp_end=None,
                )
            )

        processed_sequences.add(sequence)

    # Remove speeches no longer present
    for sequence, existing_speech in existing_by_sequence.items():
        if sequence not in processed_sequences:
            await session.delete(existing_speech)

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
