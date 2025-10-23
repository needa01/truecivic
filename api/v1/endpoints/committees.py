"""
Committee API endpoints.

Provides REST API for parliamentary committees.
"""
from typing import List, Optional
from datetime import datetime, date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.db.models import CommitteeModel
from src.db.repositories.committee_repository import CommitteeRepository
from src.db.repositories.committee_meeting_repository import CommitteeMeetingRepository
from src.models.committee import Committee, CommitteeList, CommitteeMeeting, CommitteeMeetingList
from src.utils.committee_registry import normalize_committee_code, ensure_internal_slug

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/committees", tags=["committees"])


async def _fetch_committee_by_identifier(
    db: AsyncSession,
    identifier: str,
) -> Optional[CommitteeModel]:
    """
    Resolve a committee regardless of whether the caller provided a natural id,
    slug, or raw acronym.
    """
    cleaned_identifier = (identifier or "").strip()
    if not cleaned_identifier:
        return None

    # Preferred path: natural_id lookup when column exists on the model
    if hasattr(CommitteeModel, "natural_id"):
        natural_query = select(CommitteeModel).where(
            and_(
                CommitteeModel.natural_id == cleaned_identifier,
                CommitteeModel.jurisdiction == "ca-federal",
            )
        )
        natural_result = await db.execute(natural_query)
        committee = natural_result.scalar_one_or_none()
        if committee:
            return committee

    repo = CommitteeRepository(db)

    slug_candidates: List[str] = []
    code_candidates: List[str] = []

    # Natural-id style: ca-federal-44-1-committee-HUMA
    if "-committee-" in cleaned_identifier.lower():
        natural_code = cleaned_identifier.split("-committee-", 1)[1].strip()
        if natural_code:
            code_candidates.append(natural_code.upper())

    normalized_code = normalize_committee_code(cleaned_identifier)
    if normalized_code:
        code_candidates.append(normalized_code)

    # Generate slug candidates from known codes
    for code in code_candidates:
        try:
            slug_candidates.append(ensure_internal_slug(code))
        except ValueError:
            continue

    # Direct slug usage (e.g., ca-HUMA)
    if cleaned_identifier.startswith("ca-"):
        slug_candidates.append(cleaned_identifier)

    # Try locating by slug first
    seen_slugs = set()
    for slug in slug_candidates:
        normalized_slug = slug.strip()
        if not normalized_slug or normalized_slug in seen_slugs:
            continue
        seen_slugs.add(normalized_slug)
        try:
            committee = await repo.get_by_slug(normalized_slug)
        except ValueError:
            continue
        if committee:
            return committee

    # Fallback: locate by committee code
    seen_codes = set()
    for code in code_candidates:
        normalized_code = code.strip().upper()
        if not normalized_code or normalized_code in seen_codes:
            continue
        seen_codes.add(normalized_code)
        committee = await repo.get_by_code("ca-federal", normalized_code)
        if committee:
            return committee

    return None


@router.get("/", response_model=CommitteeList)
async def list_committees(
    parliament: Optional[int] = Query(None, description="Filter by parliament number"),
    session: Optional[int] = Query(None, description="Filter by session number"),
    chamber: Optional[str] = Query(None, description="Filter by chamber (House, Senate, Joint)"),
    slug: Optional[str] = Query(None, description="Filter by committee slug"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session)
) -> CommitteeList:
    """
    List parliamentary committees with optional filters.
    
    Returns a paginated list of committees with metadata.
    """
    logger.info(f"Listing committees: parliament={parliament}, session={session}, skip={skip}, limit={limit}")
    
    # Build query
    query = select(CommitteeModel).where(CommitteeModel.jurisdiction == "ca-federal")
    
    # Apply filters
    if parliament is not None:
        query = query.where(CommitteeModel.parliament == parliament)
    if session is not None:
        query = query.where(CommitteeModel.session == session)
    if chamber:
        query = query.where(CommitteeModel.chamber == chamber)
    if slug:
        query = query.where(CommitteeModel.committee_slug == slug)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(CommitteeModel.chamber, CommitteeModel.committee_slug)
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    committees = result.scalars().all()
    
    # Convert to Pydantic models
    committee_list = [Committee.from_orm(committee) for committee in committees]
    
    logger.info(f"Found {len(committee_list)} committees (total: {total})")
    
    return CommitteeList(
        committees=committee_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{committee_id}", response_model=Committee)
async def get_committee(
    committee_id: str,
    db: AsyncSession = Depends(get_session)
) -> Committee:
    """
    Get a specific committee by ID.
    """
    logger.info(f"Getting committee: {committee_id}")
    
    committee = await _fetch_committee_by_identifier(db, committee_id)

    if not committee:
        raise HTTPException(status_code=404, detail=f"Committee {committee_id} not found")
    
    # Convert to Pydantic model
    committee_data = Committee.from_orm(committee)
    
    logger.info(f"Found committee: {committee_id}")
    return committee_data


@router.get("/by-slug/{slug}", response_model=List[Committee])
async def get_committees_by_slug(
    slug: str,
    parliament: Optional[int] = Query(None, description="Filter by parliament number"),
    session: Optional[int] = Query(None, description="Filter by session number"),
    db: AsyncSession = Depends(get_session)
) -> List[Committee]:
    """
    Get committees by slug across different parliaments/sessions.
    
    Returns all instances of a committee (e.g., all HUMA committees).
    """
    logger.info(f"Getting committees with slug: {slug}")
    
    # Build query
    query = select(CommitteeModel).where(
        and_(
            CommitteeModel.committee_slug == slug,
            CommitteeModel.jurisdiction == "ca-federal"
        )
    )
    
    # Apply filters
    if parliament is not None:
        query = query.where(CommitteeModel.parliament == parliament)
    if session is not None:
        query = query.where(CommitteeModel.session == session)
    
    # Apply ordering
    query = query.order_by(desc(CommitteeModel.parliament), desc(CommitteeModel.session))
    
    # Execute query
    result = await db.execute(query)
    committees = result.scalars().all()
    
    # Convert to Pydantic models
    committee_list = [Committee.from_orm(committee) for committee in committees]
    
    logger.info(f"Found {len(committee_list)} committees with slug {slug}")
    return committee_list


@router.get("/by-acronym/{acronym}", response_model=List[Committee])
async def get_committees_by_acronym(
    acronym: str,
    parliament: Optional[int] = Query(None, description="Filter by parliament number"),
    session: Optional[int] = Query(None, description="Filter by session number"),
    db: AsyncSession = Depends(get_session)
) -> List[Committee]:
    """
    Get committees by acronym (English or French).
    
    Searches both English and French acronyms.
    """
    logger.info(f"Getting committees with acronym: {acronym}")
    
    # Build query
    query = select(CommitteeModel).where(
        and_(
            or_(
                CommitteeModel.acronym_en == acronym,
                CommitteeModel.acronym_fr == acronym
            ),
            CommitteeModel.jurisdiction == "ca-federal"
        )
    )
    
    # Apply filters
    if parliament is not None:
        query = query.where(CommitteeModel.parliament == parliament)
    if session is not None:
        query = query.where(CommitteeModel.session == session)
    
    # Apply ordering
    query = query.order_by(desc(CommitteeModel.parliament), desc(CommitteeModel.session))
    
    # Execute query
    result = await db.execute(query)
    committees = result.scalars().all()
    
    # Convert to Pydantic models
    committee_list = [Committee.from_orm(committee) for committee in committees]
    
    logger.info(f"Found {len(committee_list)} committees with acronym {acronym}")
    return committee_list


@router.get("/{committee_id}/meetings", response_model=CommitteeMeetingList)
async def get_committee_meetings(
    committee_id: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session),
) -> CommitteeMeetingList:
    """
    Get committee meetings for a specific committee.

    Returns paginated meetings along with committee metadata.
    """
    logger.info(
        "Getting committee meetings: committee_id=%s skip=%s limit=%s",
        committee_id,
        skip,
        limit,
    )

    committee = await _fetch_committee_by_identifier(db, committee_id)
    if not committee:
        raise HTTPException(status_code=404, detail=f"Committee {committee_id} not found")

    meeting_repo = CommitteeMeetingRepository(db)

    total = await meeting_repo.count_by_committee(committee.id)
    meetings = await meeting_repo.get_by_committee(
        committee.id,
        limit=limit,
        offset=skip,
    )

    # Manually construct CommitteeMeeting objects with committee_slug
    meetings_payload = []
    for meeting in meetings:
        meeting_dict = {
            "id": meeting.id,
            "committee_id": meeting.committee_id,
            "committee_slug": committee.committee_slug,  # Add from parent committee
            "meeting_number": meeting.meeting_number,
            "parliament": meeting.parliament,
            "session": meeting.session,
            "meeting_date": meeting.meeting_date,
            "time_of_day": meeting.time_of_day,
            "title_en": meeting.title_en,
            "title_fr": meeting.title_fr,
            "meeting_type": meeting.meeting_type,
            "room": meeting.room,
            "witnesses": meeting.witnesses,
            "documents": meeting.documents,
            "source_url": meeting.source_url,
            "created_at": meeting.created_at,
            "updated_at": meeting.updated_at,
        }
        meetings_payload.append(CommitteeMeeting(**meeting_dict))

    return CommitteeMeetingList(
        committee=Committee.from_orm(committee),
        meetings=meetings_payload,
        total=total,
        skip=skip,
        limit=limit,
    )
