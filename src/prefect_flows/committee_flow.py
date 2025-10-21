"""
Prefect flow for fetching committee and committee meeting data.

Orchestrates committee data fetching and storage.
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

from src.adapters.openparliament_committees import OpenParliamentCommitteeAdapter
from src.db.session import async_session_factory
from src.db.repositories.committee_repository import CommitteeRepository
from src.utils import dedupe_by_key
from src.utils.committee_registry import build_committee_identifier, resolve_source_slug

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
    response = await adapter.fetch(limit=limit)
    
    if response.errors:
        logger_task.error(f"Errors fetching committees: {response.errors}")
    
    records = response.data or []
    records, duplicates = dedupe_by_key(
        records,
        lambda r: r.get("committee_slug") or r.get("committee_code"),
    )
    if duplicates:
        logger_task.warning("Removed %s duplicate committees", duplicates)
    logger_task.info(f"Fetched {len(records)} committees")
    return records


@task(name="fetch_committee_meetings", retries=2, retry_delay_seconds=30)
async def fetch_committee_meetings_task(
    committee_identifier: str,
    limit: int = 50,
    parliament: int = None,
    session: int = None
) -> List[Dict[str, Any]]:
    """
    Fetch meetings for a specific committee.
    
    Args:
        committee_identifier: Committee slug or acronym
        limit: Maximum meetings to fetch
        parliament: Filter by parliament number
        session: Filter by session number
        
    Returns:
        List of meeting dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching meetings for committee: {committee_identifier}")
    
    adapter = OpenParliamentCommitteeAdapter()
    response = await adapter.fetch_committee_meetings(
        committee_acronym=committee_identifier,
        limit=limit,
        parliament=parliament,
        session=session
    )
    
    if response.errors:
        logger_task.error(f"Errors fetching meetings: {response.errors}")
    
    records = response.data or []
    records, duplicates = dedupe_by_key(
        records,
        lambda r: (
            r.get("committee_slug") or r.get("committee_code"),
            r.get("meeting_number"),
            r.get("parliament"),
            r.get("session"),
        ),
    )
    if duplicates:
        logger_task.warning(
            "Removed %s duplicate meetings for committee %s", duplicates, committee_identifier
        )
    logger_task.info(
        f"Fetched {len(records)} meetings for {committee_identifier}"
    )
    return records


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
    
    records = response.data or []
    if records:
        return records[0]
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
    
    allowed_keys = {
        "committee_code",
        "committee_slug",
        "source_slug",
        "jurisdiction",
        "name_en",
        "name_fr",
        "short_name_en",
        "short_name_fr",
        "acronym_en",
        "acronym_fr",
        "chamber",
        "committee_type",
        "website_url",
        "source_url",
        "parent_committee",
        "parliament",
        "session",
        "created_at",
        "updated_at",
    }

    sanitized_committees: List[Dict[str, Any]] = []
    for committee in committees_data:
        identifier_seed = (
            committee.get("committee_slug")
            or committee.get("committee_code")
            or committee.get("source_slug")
        )
        if not identifier_seed:
            continue
        try:
            identifier = build_committee_identifier(identifier_seed)
        except ValueError as exc:
            logger_task.warning("Skipping committee with unknown identifier %s: %s", identifier_seed, exc)
            continue
        sanitized = {k: v for k, v in committee.items() if k in allowed_keys}
        sanitized.setdefault("committee_code", identifier.code)
        sanitized.setdefault("committee_slug", identifier.internal_slug)

        source_slug = sanitized.get("source_slug") or identifier.source_slug
        sanitized["source_slug"] = resolve_source_slug(source_slug) if source_slug else None

        sanitized["jurisdiction"] = "ca-federal"

        parliament_value = committee.get("parliament")
        if parliament_value is None:
            parliament_value = 44
        sanitized["parliament"] = int(parliament_value)

        session_value = committee.get("session")
        if session_value is None:
            session_value = 1
        sanitized["session"] = int(session_value)

        name_en = sanitized.get("name_en") or committee.get("name_en") or identifier.code
        sanitized["name_en"] = name_en
        sanitized.setdefault("name_fr", committee.get("name_fr"))

        sanitized["short_name_en"] = (
            sanitized.get("short_name_en") or committee.get("short_name_en") or name_en
        )
        sanitized["short_name_fr"] = (
            sanitized.get("short_name_fr") or committee.get("short_name_fr") or sanitized["name_fr"]
        )

        acronym_en = sanitized.get("acronym_en") or committee.get("acronym_en") or identifier.code
        sanitized["acronym_en"] = acronym_en.upper()
        acronym_fr = sanitized.get("acronym_fr") or committee.get("acronym_fr") or acronym_en
        sanitized["acronym_fr"] = acronym_fr.upper()

        source_url_value = sanitized.get("source_url") or committee.get("source_url") or committee.get("url")
        if source_url_value and isinstance(source_url_value, str):
            if source_url_value.startswith("/"):
                source_url_value = f"https://api.openparliament.ca{source_url_value.lstrip('/')}"
        sanitized["source_url"] = source_url_value
        sanitized.setdefault("website_url", source_url_value)

        parent_committee = sanitized.get("parent_committee") or committee.get("parent_committee")
        if parent_committee:
            try:
                sanitized["parent_committee"] = build_committee_identifier(parent_committee).internal_slug
            except ValueError:
                sanitized["parent_committee"] = parent_committee

        sanitized_committees.append(sanitized)

    if not sanitized_committees:
        logger_task.warning("No committees with recognized codes to store")
        return {"stored": 0}
    
    async with async_session_factory() as session:
        committee_repo = CommitteeRepository(session)
        
        # Use batch upsert
        stored_committees = await committee_repo.upsert_many(sanitized_committees)
        await session.commit()
        
        logger_task.info(f"Stored {len(stored_committees)} committees")
        
        return {"stored": len(stored_committees)}


@task(name="store_meetings", retries=1)
async def store_meetings_task(
    meetings: List[Dict[str, Any]]
) -> Dict[str, int]:
    """
    Store committee meetings in database.
    
    Args:
        meetings: List of meeting dictionaries
        
    Returns:
        Dict with count of stored meetings
    """
    logger_task = get_run_logger()
    
    if not meetings:
        logger_task.info("No meetings to store")
        return {"stored": 0}
    
    from src.db.repositories.committee_meeting_repository import CommitteeMeetingRepository
    
    try:
        async with async_session_factory() as session:
            meeting_repo = CommitteeMeetingRepository(session)
            committee_repo = CommitteeRepository(session)
            
            slug_to_id: Dict[str, Optional[int]] = {}
            sanitized_meetings: List[Dict[str, Any]] = []
            
            for meeting in meetings:
                committee_identifier = meeting.get("committee_slug") or meeting.get("committee_code")
                if not committee_identifier:
                    continue
                try:
                    identifier = build_committee_identifier(committee_identifier)
                except ValueError as exc:
                    logger_task.warning("Skipping meeting with unknown committee identifier %s: %s", committee_identifier, exc)
                    continue
                internal_slug = identifier.internal_slug

                if internal_slug not in slug_to_id:
                    committee = await committee_repo.get_by_slug(internal_slug)
                    if not committee:
                        committee = await committee_repo.get_by_code("ca", identifier.code)
                    slug_to_id[internal_slug] = committee.id if committee else None
                
                committee_id = slug_to_id.get(internal_slug)
                if not committee_id:
                    logger_task.warning(
                        f"Skipping meeting for committee {internal_slug} - committee not found"
                    )
                    continue
                
                meeting_date = meeting.get("meeting_date")
                if isinstance(meeting_date, str):
                    try:
                        meeting_date = datetime.fromisoformat(meeting_date.replace("Z", "+00:00"))
                    except ValueError:
                        logger_task.warning("Invalid meeting date '%s'", meeting_date)
                        continue
                elif not isinstance(meeting_date, datetime):
                    logger_task.warning("Meeting missing date; skipping")
                    continue
                
                parliament = meeting.get("parliament")
                session_number = meeting.get("session")
                try:
                    parliament = int(parliament) if parliament is not None else None
                    session_number = int(session_number) if session_number is not None else None
                except (TypeError, ValueError):
                    logger_task.warning("Invalid parliament/session for committee %s", internal_slug)
                    continue
                if parliament is None or session_number is None:
                    logger_task.warning("Missing parliament/session for committee %s", internal_slug)
                    continue

                meeting_number = meeting.get("meeting_number")
                try:
                    meeting_number = int(meeting_number) if meeting_number is not None else None
                except (TypeError, ValueError):
                    meeting_number = None
                
                sanitized_meetings.append(
                    {
                        "committee_id": committee_id,
                        "meeting_number": meeting_number,
                        "parliament": parliament,
                        "session": session_number,
                        "meeting_date": meeting_date,
                        "time_of_day": meeting.get("time_of_day"),
                        "title_en": meeting.get("title_en"),
                        "title_fr": meeting.get("title_fr"),
                        "meeting_type": meeting.get("meeting_type"),
                        "room": meeting.get("room"),
                        "witnesses": meeting.get("witnesses"),
                        "documents": meeting.get("documents"),
                        "source_url": meeting.get("source_url"),
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                    }
                )
            
            sanitized_meetings, duplicates = dedupe_by_key(
                sanitized_meetings,
                lambda m: (
                    m.get("committee_id"),
                    m.get("meeting_number"),
                    m.get("parliament"),
                    m.get("session"),
                ),
            )
            if duplicates:
                logger_task.warning("Removed %s duplicate meetings before storage", duplicates)

            if not sanitized_meetings:
                logger_task.warning("No meetings could be sanitized for storage")
                return {"stored": 0}
            
            stored_meetings = await meeting_repo.upsert_many(sanitized_meetings)
            await session.commit()
            
            logger_task.info(f"✅ Stored {len(stored_meetings)} committee meetings")
            return {"stored": len(stored_meetings)}
            
    except Exception as e:
        logger_task.error(f"Error storing meetings: {str(e)}", exc_info=True)
        raise


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
    committee_identifiers: List[str],
    limit_per_committee: int = 50,
    parliament: Optional[int] = None,
    session: Optional[int] = None
) -> Dict[str, Any]:
    """
    Flow to fetch meetings for multiple committees.
    
    Args:
        committee_identifiers: List of committee slugs or acronyms (e.g., ['ca-HUMA', 'FINA'])
        limit_per_committee: Max meetings per committee
        parliament: Parliament number
        session: Session number
        
    Returns:
        Dictionary with flow results
    """
    logger_flow = get_run_logger()
    logger_flow.info(
        "Starting fetch meetings flow for %s committees (parliament=%s, session=%s, limit=%s)",
        len(committee_identifiers),
        parliament,
        session,
        limit_per_committee,
    )
    
    start_time = datetime.utcnow()
    
    all_meetings = []
    
    # Fetch meetings for each committee
    for committee_identifier in committee_identifiers:
        meetings = await fetch_committee_meetings_task(
            committee_identifier=committee_identifier,
            limit=limit_per_committee,
            parliament=parliament,
            session=session
        )
        all_meetings.extend(meetings)
    
    # Store meetings in batches to avoid exceeding statement parameter limits
    BATCH_SIZE = 2000
    total_stored = 0
    note = ""
    for start_idx in range(0, len(all_meetings), BATCH_SIZE):
        chunk = all_meetings[start_idx : start_idx + BATCH_SIZE]
        chunk_result = await store_meetings_task(chunk)
        total_stored += chunk_result.get("stored", 0)
        chunk_note = chunk_result.get("note")
        if chunk_note:
            note = f"{note}; {chunk_note}" if note else chunk_note

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    result = {
        "status": "success",
        "committees_processed": len(committee_identifiers),
        "meetings_fetched": len(all_meetings),
        "meetings_stored": total_stored,
        "note": note,
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
        committee_identifiers=top_committees,
        limit_per_committee=20,
        parliament=44,
        session=1
    )


if __name__ == "__main__":
    # Test the flow
    asyncio.run(fetch_all_committees_flow(limit=20))
