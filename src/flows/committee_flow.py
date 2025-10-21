"""
Prefect flow for fetching and storing committee data.

Orchestrates the committee adapter to fetch parliamentary committee information.
"""
import asyncio
from datetime import datetime
from typing import List, Dict, Any
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.committee_adapter import CommitteeAdapter
from src.db.session import async_session_factory
from src.db.repositories.committee_repository import CommitteeRepository
from src.models.adapter_models import CommitteeData
from src.utils.committee_registry import build_committee_identifier, resolve_source_slug

logger = logging.getLogger(__name__)


@task(name="fetch_committees", retries=2, retry_delay_seconds=30)
async def fetch_committees_task(parliament: int, session: int, limit: int = 100) -> List[CommitteeData]:
    """
    Fetch committees for a parliament session.
    
    Args:
        parliament: Parliament number
        session: Session number
        limit: Results per page
        
    Returns:
        List of CommitteeData objects
    """
    logger = get_run_logger()
    logger.info(f"Fetching committees for Parliament {parliament}, Session {session}")
    
    adapter = CommitteeAdapter()
    committees = await adapter.fetch_committees_for_session(parliament, session, limit)
    
    logger.info(f"Fetched {len(committees)} committees")
    return committees


@task(name="fetch_all_committees", retries=2, retry_delay_seconds=30)
async def fetch_all_committees_task(limit: int = 100) -> List[CommitteeData]:
    """
    Fetch all committees across all sessions.
    
    Args:
        limit: Results per page
        
    Returns:
        List of CommitteeData objects
    """
    logger = get_run_logger()
    logger.info(f"Fetching all committees")
    
    adapter = CommitteeAdapter()
    committees = await adapter.fetch_all_committees(limit)
    
    logger.info(f"Fetched {len(committees)} total committees")
    return committees


@task(name="store_committees", retries=1)
async def store_committees_task(committees: List[CommitteeData]) -> int:
    """
    Store committees in the database.
    
    Args:
        committees: List of CommitteeData objects
        
    Returns:
        Number of committees stored
    """
    logger = get_run_logger()
    logger.info(f"Storing {len(committees)} committees in database")
    
    stored_count = 0

    if not committees:
        logger.info("No committee records received")
        return 0

    async with async_session_factory() as session:
        repository = CommitteeRepository(session)
        payloads: List[Dict[str, Any]] = []

        canonical_jurisdiction = "ca-federal"

        for committee_data in committees:
            try:
                identifier_seed = (
                    committee_data.committee_slug
                    or committee_data.acronym_en
                    or committee_data.acronym_fr
                    or committee_data.committee_id
                )
                identifier = build_committee_identifier(identifier_seed)

                parliament = committee_data.parliament
                session = committee_data.session

                if parliament is None or session is None:
                    raise ValueError("Committee payload missing parliament/session metadata")

                name_en = committee_data.name_en or identifier.code
                name_fr = committee_data.name_fr or name_en
                source_slug = committee_data.source_slug or identifier.source_slug
                source_url = committee_data.source_url

                parliament_value = int(parliament)
                session_value = int(session)

                if not source_url and source_slug:
                    source_url = f"https://api.openparliament.ca/committees/{source_slug}/"
                if not source_url:
                    source_url = (
                        f"https://www.ourcommons.ca/Committees/en/{identifier.code}"
                        f"?parl={parliament_value}&session={session_value}"
                    )

                acronym_en = (committee_data.acronym_en or identifier.code).upper()
                acronym_fr = (committee_data.acronym_fr or acronym_en).upper()
                short_name_en = committee_data.short_name_en or name_en
                short_name_fr = committee_data.short_name_fr or name_fr or short_name_en

                natural_id = (
                    f"{canonical_jurisdiction}-{parliament_value}-{session_value}-committee-{identifier.code}"
                )

                payloads.append(
                    {
                        "natural_id": natural_id,
                        "jurisdiction": canonical_jurisdiction,
                        "parliament": parliament_value,
                        "session": session_value,
                        "committee_code": identifier.code,
                        "committee_slug": identifier.internal_slug,
                        "source_slug": source_slug,
                        "name_en": name_en,
                        "name_fr": name_fr,
                        "chamber": committee_data.chamber or "House",
                        "acronym_en": acronym_en,
                        "acronym_fr": acronym_fr,
                        "short_name_en": short_name_en,
                        "short_name_fr": short_name_fr,
                        "parent_committee": committee_data.parent_committee,
                        "source_url": source_url,
                        "committee_type": None,
                        "website_url": None,
                    }
                )
            except Exception as exc:
                logger.error(
                    "Failed to prepare committee payload %s: %s",
                    committee_data.committee_id,
                    exc,
                )

        if not payloads:
            logger.warning("All committee payloads failed validation; nothing stored")
            return 0

        stored_committees = await repository.upsert_many(payloads)
        await session.commit()
        stored_count = len(stored_committees)

    logger.info(f"Stored {stored_count} committees")
    return stored_count


@flow(
    name="fetch_committees",
    description="Fetch and store parliamentary committee data",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_committees_flow(
    parliament: int = 44,
    session: int = 1,
    limit: int = 100
) -> dict:
    """
    Main flow to fetch and store committee data for a specific session.
    
    Args:
        parliament: Parliament number (default: 44)
        session: Session number (default: 1)
        limit: Results per page (default: 100)
        
    Returns:
        Dictionary with flow results
    """
    logger = get_run_logger()
    logger.info(f"Starting committee fetch flow for {parliament}-{session}")
    
    start_time = datetime.utcnow()
    
    # Fetch committees
    committees = await fetch_committees_task(parliament, session, limit)
    
    # Store committees
    stored_count = await store_committees_task(committees)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "parliament": parliament,
        "session": session,
        "committees_fetched": len(committees),
        "committees_stored": stored_count,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger.info(f"Committee fetch flow completed: {result}")
    return result


@flow(
    name="fetch_all_committees",
    description="Fetch and store all parliamentary committees",
    task_runner=ConcurrentTaskRunner(),
    log_prints=True
)
async def fetch_all_committees_flow(limit: int = 100) -> dict:
    """
    Fetch and store all committees across all sessions.
    
    Args:
        limit: Results per page (default: 100)
        
    Returns:
        Dictionary with flow results
    """
    logger = get_run_logger()
    logger.info(f"Starting all committees fetch flow")
    
    start_time = datetime.utcnow()
    
    # Fetch all committees
    committees = await fetch_all_committees_task(limit)
    
    # Store committees
    stored_count = await store_committees_task(committees)
    
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()
    
    result = {
        "status": "success",
        "committees_fetched": len(committees),
        "committees_stored": stored_count,
        "duration_seconds": duration,
        "timestamp": end_time.isoformat()
    }
    
    logger.info(f"All committees fetch flow completed: {result}")
    return result


if __name__ == "__main__":
    # Run the flow for testing
    asyncio.run(fetch_all_committees_flow(limit=100))
