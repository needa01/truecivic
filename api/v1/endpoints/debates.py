"""
Debates API endpoints.

Provides REST endpoints for querying debates and speeches.

Responsibility: Debate endpoints for API v1
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.db.session import get_db
from src.db.models import DebateModel, SpeechModel
from api.v1.schemas.debates import DebateResponse, DebateListResponse, SpeechResponse

router = APIRouter()


@router.get("/debates", response_model=DebateListResponse)
async def list_debates(
    parliament: Optional[int] = Query(None, description="Filter by parliament"),
    session: Optional[int] = Query(None, description="Filter by session"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List debates with optional filters.
    
    Args:
        parliament: Filter by parliament number
        session: Filter by session number
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        
    Returns:
        DebateListResponse with debates
    """
    query = select(DebateModel).where(
        DebateModel.jurisdiction == "ca-federal"
    )
    
    if parliament:
        query = query.where(DebateModel.parliament == parliament)
    if session:
        query = query.where(DebateModel.session == session)
    
    query = query.order_by(desc(DebateModel.sitting_date))
    
    result = await db.execute(query.limit(limit).offset(offset))
    debates = result.scalars().all()
    
    # Get total
    count_query = select(DebateModel).where(DebateModel.jurisdiction == "ca-federal")
    if parliament:
        count_query = count_query.where(DebateModel.parliament == parliament)
    if session:
        count_query = count_query.where(DebateModel.session == session)
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return {
        "debates": [DebateResponse.from_orm(d) for d in debates],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(debates)) < total
    }


@router.get("/debates/{debate_id}")
async def get_debate(
    debate_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get debate details.
    
    Args:
        debate_id: Debate database ID
        db: Database session
        
    Returns:
        DebateResponse
        
    Raises:
        HTTPException: 404 if not found
    """
    query = select(DebateModel).where(DebateModel.id == debate_id)
    result = await db.execute(query)
    debate = result.scalar_one_or_none()
    
    if not debate:
        raise HTTPException(status_code=404, detail=f"Debate {debate_id} not found")
    
    return DebateResponse.from_orm(debate)


@router.get("/debates/{debate_id}/speeches")
async def get_debate_speeches(
    debate_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Get speeches for a debate.
    
    Args:
        debate_id: Debate database ID
        limit: Maximum speeches
        offset: Pagination offset
        db: Database session
        
    Returns:
        List of speeches
    """
    query = select(SpeechModel).where(
        SpeechModel.debate_id == debate_id
    ).order_by(SpeechModel.sequence).limit(limit).offset(offset)
    
    result = await db.execute(query)
    speeches = result.scalars().all()
    
    return {
        "speeches": [SpeechResponse.from_orm(s) for s in speeches],
        "total": len(speeches),
        "limit": limit,
        "offset": offset,
        "debate_id": debate_id
    }


@router.get("/speeches")
async def list_speeches(
    politician_id: Optional[int] = Query(None, description="Filter by politician"),
    debate_id: Optional[int] = Query(None, description="Filter by debate"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List speeches with optional filters.
    
    Args:
        politician_id: Filter by politician
        debate_id: Filter by debate
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        
    Returns:
        List of speeches
    """
    query = select(SpeechModel)
    
    if politician_id:
        query = query.where(SpeechModel.politician_id == politician_id)
    if debate_id:
        query = query.where(SpeechModel.debate_id == debate_id)
    
    query = query.order_by(desc(SpeechModel.created_at))
    
    result = await db.execute(query.limit(limit).offset(offset))
    speeches = result.scalars().all()
    
    return {
        "speeches": [SpeechResponse.from_orm(s) for s in speeches],
        "total": len(speeches),
        "limit": limit,
        "offset": offset
    }
