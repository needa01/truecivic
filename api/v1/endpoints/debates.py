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
        query = query.where(DebateModel.sitting_date >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        query = query.where(DebateModel.sitting_date <= datetime.combine(to_date, datetime.max.time()))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(DebateModel.sitting_date), DebateModel.hansard_id)
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    debates = result.scalars().all()
    
    # Convert to Pydantic models - manually construct to match schema
    debate_list = []
    for debate in debates:
        debate_dict = {
            "natural_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}",
            "jurisdiction": debate.jurisdiction,
            "parliament": debate.parliament,
            "session": debate.session,
            "debate_number": debate.hansard_id,
            "chamber": debate.chamber,
            "debate_date": debate.sitting_date,
            "topic_en": None,  # Not in database
            "topic_fr": None,  # Not in database
            "debate_type": debate.debate_type or "",
            "source_url": debate.document_url,
            "created_at": debate.created_at,
            "updated_at": debate.updated_at,
            "speeches": []
        }
        debate_list.append(Debate(**debate_dict))
    
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
    
    # Build query - use hansard_id from database
    query = select(DebateModel).where(
        and_(
            DebateModel.hansard_id == debate_id,
            DebateModel.jurisdiction == "ca-federal"
        )
    )
    
    # Execute query
    result = await db.execute(query)
    debate = result.scalar_one_or_none()
    
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")
    
    # Convert to Pydantic model - manually construct to match schema
    debate_dict = {
        "natural_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}",
        "jurisdiction": debate.jurisdiction,
        "parliament": debate.parliament,
        "session": debate.session,
        "debate_number": debate.hansard_id,
        "chamber": debate.chamber,
        "debate_date": debate.sitting_date,
        "topic_en": None,  # Not in database
        "topic_fr": None,  # Not in database
        "debate_type": debate.debate_type or "",
        "source_url": debate.document_url,
        "created_at": debate.created_at,
        "updated_at": debate.updated_at,
        "speeches": []
    }
    
    # If speeches requested, fetch them and manually construct
    if include_speeches:
        speeches_query = select(SpeechModel).where(
            SpeechModel.debate_id == debate.id
        ).order_by(SpeechModel.sequence)
        speeches_result = await db.execute(speeches_query)
        speeches = speeches_result.scalars().all()
        
        speeches_list = []
        for speech in speeches:
            speech_dict = {
                "natural_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}-speech-{speech.sequence}",
                "jurisdiction": "ca-federal",
                "debate_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}",
                "politician_id": speech.politician_id,
                "content_en": speech.text_content if speech.language == 'en' else None,
                "content_fr": speech.text_content if speech.language == 'fr' else None,
                "speech_time": datetime.combine(debate.sitting_date.date(), speech.timestamp_start) if speech.timestamp_start else None,
                "speaker_name": speech.speaker_name,
                "speaker_display_name": speech.speaker_display_name,
                "speaker_role": None,  # Not in database
                "sequence": speech.sequence,
                "created_at": speech.created_at,
                "updated_at": getattr(speech, 'updated_at', speech.created_at)
            }
            speeches_list.append(Speech(**speech_dict))
        debate_dict["speeches"] = speeches_list
    
    debate_data = Debate(**debate_dict)
    
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
    
    # Verify debate exists - use hansard_id
    debate_query = select(DebateModel).where(
        and_(
            DebateModel.hansard_id == debate_id,
            DebateModel.jurisdiction == "ca-federal"
        )
    )
    debate_result = await db.execute(debate_query)
    debate = debate_result.scalar_one_or_none()
    
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")
    
    # Build speeches query - debate_id FK is debate.id (integer)
    query = select(SpeechModel).where(SpeechModel.debate_id == debate.id)
    
    # Apply filters
    if politician_id is not None:
        query = query.where(SpeechModel.politician_id == politician_id)
    
    # Apply pagination and ordering
    query = query.order_by(SpeechModel.sequence)
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    speeches = result.scalars().all()
    
    # Convert to Pydantic models - manually construct
    speeches_list = []
    for speech in speeches:
        speech_dict = {
            "natural_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}-speech-{speech.sequence}",
            "jurisdiction": "ca-federal",
            "debate_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}",
            "politician_id": speech.politician_id,
            "content_en": speech.text_content if speech.language == 'en' else None,
            "content_fr": speech.text_content if speech.language == 'fr' else None,
            "speech_time": datetime.combine(debate.sitting_date.date(), speech.timestamp_start) if speech.timestamp_start else None,
            "speaker_name": speech.speaker_name,
            "speaker_display_name": speech.speaker_display_name,
            "speaker_role": None,  # Not in database
            "sequence": speech.sequence,
            "created_at": speech.created_at,
            "updated_at": getattr(speech, 'updated_at', speech.created_at)
        }
        speeches_list.append(Speech(**speech_dict))
    
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
    
    # Build query - join with debates to get date and parliament/session info
    query = select(SpeechModel, DebateModel).join(
        DebateModel,
        SpeechModel.debate_id == DebateModel.id
    ).where(SpeechModel.politician_id == politician_id)
    
    # Apply filters
    if parliament is not None:
        query = query.where(DebateModel.parliament == parliament)
    if session is not None:
        query = query.where(DebateModel.session == session)
    if from_date:
        query = query.where(DebateModel.sitting_date >= datetime.combine(from_date, datetime.min.time()))
    if to_date:
        query = query.where(DebateModel.sitting_date <= datetime.combine(to_date, datetime.max.time()))
    
    # Apply pagination and ordering
    query = query.order_by(desc(DebateModel.sitting_date), SpeechModel.sequence)
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    rows = result.all()
    
    # Convert to Pydantic models - manually construct
    speeches_list = []
    for speech, debate in rows:
        speech_dict = {
            "natural_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}-speech-{speech.sequence}",
            "jurisdiction": "ca-federal",
            "debate_id": f"ca-federal-{debate.parliament}-{debate.session}-debate-{debate.hansard_id}",
            "politician_id": speech.politician_id,
            "content_en": speech.text_content if speech.language == 'en' else None,
            "content_fr": speech.text_content if speech.language == 'fr' else None,
            "speech_time": datetime.combine(debate.sitting_date.date(), speech.timestamp_start) if speech.timestamp_start else None,
            "speaker_name": speech.speaker_name,
            "speaker_display_name": speech.speaker_display_name,
            "speaker_role": None,  # Not in database
            "sequence": speech.sequence,
            "created_at": speech.created_at,
            "updated_at": getattr(speech, 'updated_at', speech.created_at)
        }
        speeches_list.append(Speech(**speech_dict))
    
    logger.info(f"Found {len(speeches_list)} speeches for politician {politician_id}")
    return speeches_list
