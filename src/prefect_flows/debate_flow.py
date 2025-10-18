"""
Prefect flow for fetching debate and speech data.

Orchestrates debate and speech data fetching and storage.

Responsibility: Orchestration of debate data pipeline
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
from src.adapters.openparliament_debates import OpenParliamentDebatesAdapter
from src.db.session import async_session_factory
from src.db.repositories.speech_repository import SpeechRepository
from src.db.models import DebateModel

logger = logging.getLogger(__name__)


@task(name="fetch_debates", retries=2, retry_delay_seconds=30)
async def fetch_debates_task(
    limit: int = 100,
    offset: int = 0,
    parliament: Optional[int] = None,
    session: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetch parliamentary debates.
    
    Args:
        limit: Maximum debates to fetch
        offset: Pagination offset
        parliament: Filter by parliament number
        session: Filter by session number
        
    Returns:
        List of debate dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching debates: limit={limit}, offset={offset}")
    
    adapter = OpenParliamentDebatesAdapter()
    response = await adapter.fetch(
        limit=limit,
        offset=offset,
        parliament=parliament,
        session=session
    )
    
    if response.errors:
        logger_task.error(f"Errors fetching debates: {response.errors}")
    
    records = response.data or []
    logger_task.info(f"Fetched {len(records)} debates")
    return records


@task(name="fetch_debate_speeches", retries=2, retry_delay_seconds=30)
async def fetch_debate_speeches_task(debate_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all speeches for a specific debate.
    
    Args:
        debate_id: Debate identifier from API
        
    Returns:
        List of speech dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching speeches for debate: {debate_id}")
    
    adapter = OpenParliamentDebatesAdapter()
    response = await adapter.fetch_speeches_for_debate(debate_id)
    
    if response.errors:
        logger_task.error(f"Errors fetching speeches: {response.errors}")
    
    records = response.data or []
    logger_task.info(f"Fetched {len(records)} speeches for debate {debate_id}")
    return records


@task(name="fetch_politician_speeches", retries=2, retry_delay_seconds=30)
async def fetch_politician_speeches_task(
    politician_id: int,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Fetch recent speeches by a politician.
    
    Args:
        politician_id: Politician database ID
        limit: Maximum speeches to fetch
        
    Returns:
        List of speech dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching speeches for politician: {politician_id}")
    
    adapter = OpenParliamentDebatesAdapter()
    response = await adapter.fetch_speeches_for_politician(
        politician_id=politician_id,
        limit=limit
    )
    
    if response.errors:
        logger_task.error(f"Errors fetching speeches: {response.errors}")
    
    records = response.data or []
    logger_task.info(f"Fetched {len(records)} speeches for politician")
    return records


@task(name="store_debates", retries=1)
async def store_debates_task(debates_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Store fetched debates in database.
    
    Note: DebateRepository implementation expected to exist.
    For now, this is a placeholder - actual storage implemented after DB layer created.
    
    Args:
        debates_data: List of debate dictionaries
        
    Returns:
        Dictionary with counts
    """
    logger_task = get_run_logger()
    
    if not debates_data:
        logger_task.info("No debates to store")
        return {"stored": 0}
    
    logger_task.info(f"Storing {len(debates_data)} debates")
    
    try:
        # TODO: Implement DebateRepository and integrate here
        logger_task.info(f"✅ Stored {len(debates_data)} debates (placeholder)")
        return {"stored": len(debates_data)}
    except Exception as e:
        logger_task.error(f"Error storing debates: {e}", exc_info=True)
        return {"stored": 0, "error": str(e)}


@task(name="store_speeches", retries=1)
async def store_speeches_task(speeches_data: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Store fetched speeches in database.
    
    Args:
        speeches_data: List of speech dictionaries
        
    Returns:
        Dictionary with count of stored speeches
    """
    logger_task = get_run_logger()
    
    if not speeches_data:
        logger_task.info("No speeches to store")
        return {"stored": 0}
    
    logger_task.info(f"Storing {len(speeches_data)} speeches")
    
    try:
        async with async_session_factory() as session:
            speech_repo = SpeechRepository(session)
            stored_speeches = await speech_repo.upsert_many(speeches_data)
            await session.commit()
            
            logger_task.info(f"✅ Stored {len(stored_speeches)} speeches")
            return {"stored": len(stored_speeches)}
    except Exception as e:
        logger_task.error(f"Error storing speeches: {e}", exc_info=True)
        await session.rollback()
        return {"stored": 0, "error": str(e)}


@task(name="fetch_debates_batch_with_speeches", retries=1)
async def fetch_debates_batch_with_speeches_task(
    limit: int = 20,
    parliament: int = None,
    session: int = None
) -> Dict[str, Any]:
    """
    Fetch debates and then fetch speeches for each debate.
    
    Orchestrates multiple speech fetches for a batch of debates.
    
    Args:
        limit: Number of debates to fetch
        parliament: Filter by parliament
        session: Filter by session
        
    Returns:
        Dictionary with results
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching {limit} debates with speeches")
    
    # Fetch debates first
    debates = await fetch_debates_task(
        limit=limit,
        parliament=parliament,
        session=session
    )
    
    if not debates:
        logger_task.warning("No debates fetched")
        return {"debates": 0, "speeches": 0}
    
    logger_task.info(f"Processing {len(debates)} debates for speeches")
    
    # Fetch speeches for each debate concurrently
    speech_batches = []
    for debate in debates[:limit]:  # Limit concurrent requests
        debate_id = debate.get('hansard_id') or debate.get('id')
        if debate_id:
            speeches = await fetch_debate_speeches_task(debate_id)
            if speeches:
                speech_batches.append(speeches)
    
    logger_task.info(
        f"Fetched speeches from {len(speech_batches)} debates "
        f"({sum(len(s) for s in speech_batches)} total speeches)"
    )
    
    return {
        "debates": len(debates),
        "debates_with_speeches": len(speech_batches),
        "total_speeches": sum(len(s) for s in speech_batches)
    }


# MARK: Main Flows

@flow(name="fetch_recent_debates_flow", task_runner=ConcurrentTaskRunner())
async def fetch_recent_debates_flow(limit: int = 50) -> Dict[str, Any]:
    """
    Fetch recent debates and store in database.
    
    Args:
        limit: Number of debates to fetch
        
    Returns:
        Result dictionary
    """
    logger.info("🚀 Starting recent debates fetch flow")
    
    # Fetch debates
    debates = await fetch_debates_task(limit=limit)
    
    if not debates:
        logger.warning("No debates fetched")
        return {"debates": 0}
    
    # Store debates
    result = await store_debates_task(debates)
    
    logger.info(f"✅ Completed recent debates flow: {result}")
    return result


@flow(name="fetch_debates_with_speeches_flow", task_runner=ConcurrentTaskRunner())
async def fetch_debates_with_speeches_flow(
    limit: int = 10,
    parliament: Optional[int] = None,
    session: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch debates and store all speeches from each debate.
    
    Main flow for speech extraction and storage.
    
    Args:
        limit: Number of debates to process
        parliament: Filter by parliament
        session: Filter by session
        
    Returns:
        Result dictionary with counts
    """
    logger.info("🚀 Starting debates with speeches flow")
    
    # Fetch debates
    debates = await fetch_debates_task(
        limit=limit,
        parliament=parliament,
        session=session
    )
    
    if not debates:
        logger.warning("No debates fetched")
        return {"debates": 0, "speeches": 0}
    
    logger.info(f"Processing {len(debates)} debates for speeches")
    
    # Store debates first
    await store_debates_task(debates)
    
    # Fetch and store speeches for each debate
    total_speeches = 0
    for debate in debates:
        debate_id = debate.get('hansard_id') or debate.get('id')
        if debate_id:
            try:
                speeches = await fetch_debate_speeches_task(debate_id)
                if speeches:
                    result = await store_speeches_task(speeches)
                    total_speeches += result.get('stored', 0)
            except Exception as e:
                logger.error(f"Error processing debate {debate_id}: {e}")
    
    logger.info(
        f"✅ Completed debates with speeches flow: "
        f"debates={len(debates)}, speeches={total_speeches}"
    )
    
    return {
        "debates": len(debates),
        "speeches": total_speeches
    }


@flow(name="fetch_top_debates_daily_flow")
async def fetch_top_debates_daily_flow() -> Dict[str, Any]:
    """
    Daily flow: Fetch top 20 recent debates and all their speeches.
    
    Scheduled to run once daily (e.g., 2 AM UTC).
    Extracts speeches for complete parliamentary record updates.
    
    Returns:
        Result dictionary
    """
    logger.info("🚀 Starting daily top debates flow")
    
    result = await fetch_debates_with_speeches_flow(limit=20)
    
    logger.info(f"✅ Daily top debates flow completed: {result}")
    return result


@flow(name="fetch_politician_speeches_flow")
async def fetch_politician_speeches_flow(
    politician_id: int,
    limit: int = 500
) -> Dict[str, Any]:
    """
    Fetch and store recent speeches by a politician.
    
    Useful for individual politician profile updates.
    
    Args:
        politician_id: Politician database ID
        limit: Maximum speeches to fetch
        
    Returns:
        Result dictionary
    """
    logger.info(f"🚀 Starting politician speeches flow for ID {politician_id}")
    
    # Fetch speeches
    speeches = await fetch_politician_speeches_task(politician_id, limit)
    
    if not speeches:
        logger.warning(f"No speeches found for politician {politician_id}")
        return {"politician_id": politician_id, "speeches": 0}
    
    # Store speeches
    result = await store_speeches_task(speeches)
    
    logger.info(
        f"✅ Completed politician speeches flow: "
        f"politician_id={politician_id}, speeches={result.get('stored', 0)}"
    )
    return result
