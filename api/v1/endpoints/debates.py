"""
Debate API endpoints.

Provides REST API for parliamentary debates and speeches.
"""
from typing import List, Optional
from datetime import datetime, date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.session import get_session
from src.db.models import DebateModel, SpeechModel
from src.models.debate import Debate, Speech, DebateList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debates", tags=["debates"])


@router.get("/", response_model=DebateList)
async def list_debates(
    parliament: Optional[int] = Query(None, description="Filter by parliament number"),
    session: Optional[int] = Query(None, description="Filter by session number"),
    chamber: Optional[str] = Query(None, description="Filter by chamber (House, Senate)"),
    debate_type: Optional[str] = Query(None, description="Filter by debate type"),
    from_date: Optional[date] = Query(None, description="Filter debates from this date"),
    to_date: Optional[date] = Query(None, description="Filter debates to this date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session)
) -> DebateList:
    """
    List parliamentary debates with optional filters.
    
    Returns a paginated list of debates with metadata.
    """
    logger.info(f"Listing debates: parliament={parliament}, session={session}, skip={skip}, limit={limit}")
    
    # Build query
    query = select(DebateModel).where(DebateModel.jurisdiction == "ca-federal")
    
    # Apply filters
    if parliament is not None:
        query = query.where(DebateModel.parliament == parliament)
    if session is not None:
        query = query.where(DebateModel.session == session)
    if chamber:
        query = query.where(DebateModel.chamber == chamber)
    if debate_type:
        query = query.where(DebateModel.debate_type == debate_type)
    if from_date:
        query = query.where(DebateModel.debate_date >= from_date)
    if to_date:
        query = query.where(DebateModel.debate_date <= to_date)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(DebateModel.debate_date), desc(DebateModel.debate_number))
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    debates = result.scalars().all()
    
    # Convert to Pydantic models
    debate_list = [Debate.from_orm(debate) for debate in debates]
    
    logger.info(f"Found {len(debate_list)} debates (total: {total})")
    
    return DebateList(
        debates=debate_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{debate_id}", response_model=Debate)
async def get_debate(
    debate_id: str,
    include_speeches: bool = Query(False, description="Include individual speeches"),
    db: AsyncSession = Depends(get_session)
) -> Debate:
    """
    Get a specific debate by ID.
    
    Optionally includes individual speeches from the debate.
    """
    logger.info(f"Getting debate: {debate_id}")
    
    # Build query
    query = select(DebateModel).where(
        and_(
            DebateModel.natural_id == debate_id,
            DebateModel.jurisdiction == "ca-federal"
        )
    )
    
    # Optionally load speeches
    if include_speeches:
        query = query.options(selectinload(DebateModel.speeches))
    
    # Execute query
    result = await db.execute(query)
    debate = result.scalar_one_or_none()
    
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")
    
    # Convert to Pydantic model
    debate_data = Debate.from_orm(debate)
    
    # If speeches requested, fetch them separately if not already loaded
    if include_speeches and not debate.speeches:
        speeches_query = select(SpeechModel).where(
            and_(
                SpeechModel.debate_id == debate_id,
                SpeechModel.jurisdiction == "ca-federal"
            )
        ).order_by(SpeechModel.sequence)
        speeches_result = await db.execute(speeches_query)
        speeches = speeches_result.scalars().all()
        debate_data.speeches = [Speech.from_orm(speech) for speech in speeches]
    
    logger.info(f"Found debate: {debate_id}")
    return debate_data


@router.get("/{debate_id}/speeches", response_model=List[Speech])
async def get_debate_speeches(
    debate_id: str,
    politician_id: Optional[int] = Query(None, description="Filter by politician ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session)
) -> List[Speech]:
    """
    Get speeches for a specific debate.
    
    Returns speeches in sequence order.
    """
    logger.info(f"Getting speeches for debate: {debate_id}")
    
    # Verify debate exists
    debate_query = select(DebateModel).where(
        and_(
            DebateModel.natural_id == debate_id,
            DebateModel.jurisdiction == "ca-federal"
        )
    )
    debate_result = await db.execute(debate_query)
    debate = debate_result.scalar_one_or_none()
    
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")
    
    # Build speeches query
    query = select(SpeechModel).where(
        and_(
            SpeechModel.debate_id == debate_id,
            SpeechModel.jurisdiction == "ca-federal"
        )
    )
    
    # Apply filters
    if politician_id is not None:
        query = query.where(SpeechModel.politician_id == politician_id)
    
    # Apply pagination and ordering
    query = query.order_by(SpeechModel.sequence)
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    speeches = result.scalars().all()
    
    # Convert to Pydantic models
    speeches_list = [Speech.from_orm(speech) for speech in speeches]
    
    logger.info(f"Found {len(speeches_list)} speeches")
    return speeches_list


@router.get("/by-politician/{politician_id}", response_model=List[Speech])
async def get_speeches_by_politician(
    politician_id: int,
    parliament: Optional[int] = Query(None, description="Filter by parliament number"),
    session: Optional[int] = Query(None, description="Filter by session number"),
    from_date: Optional[date] = Query(None, description="Filter speeches from this date"),
    to_date: Optional[date] = Query(None, description="Filter speeches to this date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session)
) -> List[Speech]:
    """
    Get all speeches by a specific politician.
    
    Returns speeches in reverse chronological order.
    """
    logger.info(f"Getting speeches for politician: {politician_id}")
    
    # Build query - join with debates to get date
    query = select(SpeechModel).join(
        DebateModel,
        and_(
            SpeechModel.debate_id == DebateModel.natural_id,
            SpeechModel.jurisdiction == DebateModel.jurisdiction
        )
    ).where(
        and_(
            SpeechModel.politician_id == politician_id,
            SpeechModel.jurisdiction == "ca-federal"
        )
    )
    
    # Apply filters
    if parliament is not None:
        query = query.where(DebateModel.parliament == parliament)
    if session is not None:
        query = query.where(DebateModel.session == session)
    if from_date:
        query = query.where(DebateModel.debate_date >= from_date)
    if to_date:
        query = query.where(DebateModel.debate_date <= to_date)
    
    # Apply pagination and ordering
    query = query.order_by(desc(DebateModel.debate_date), SpeechModel.sequence)
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    speeches = result.scalars().all()
    
    # Convert to Pydantic models
    speeches_list = [Speech.from_orm(speech) for speech in speeches]
    
    logger.info(f"Found {len(speeches_list)} speeches for politician {politician_id}")
    return speeches_list
