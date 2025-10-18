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
from src.models.committee import Committee, CommitteeList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/committees", tags=["committees"])


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
    
    # Build query
    query = select(CommitteeModel).where(
        and_(
            CommitteeModel.natural_id == committee_id,
            CommitteeModel.jurisdiction == "ca-federal"
        )
    )
    
    # Execute query
    result = await db.execute(query)
    committee = result.scalar_one_or_none()
    
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
