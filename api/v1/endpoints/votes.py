"""
Votes API endpoints.

Provides REST endpoints for querying parliamentary votes.

Responsibility: Vote endpoints for API v1
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.db.session import get_db
from src.db.models import VoteModel, VoteRecordModel
from api.v1.schemas.votes import VoteResponse, VoteListResponse, VoteDetailResponse

router = APIRouter()


@router.get("/votes", response_model=VoteListResponse)
async def list_votes(
    parliament: Optional[int] = Query(None, description="Filter by parliament"),
    session: Optional[int] = Query(None, description="Filter by session"),
    bill_id: Optional[int] = Query(None, description="Filter by bill ID"),
    result: Optional[str] = Query(None, description="Filter by result (Passed, Defeated)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List votes with optional filters.
    
    Args:
        parliament: Filter by parliament number
        session: Filter by session number
        bill_id: Filter by bill ID
        result: Filter by vote result
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        
    Returns:
        VoteListResponse with votes
    """
    query = select(VoteModel).where(
        VoteModel.jurisdiction == "ca-federal"
    )
    
    if parliament:
        query = query.where(VoteModel.parliament == parliament)
    if session:
        query = query.where(VoteModel.session == session)
    if bill_id:
        query = query.where(VoteModel.bill_id == bill_id)
    if result:
        query = query.where(VoteModel.result.ilike(f"%{result}%"))
    
    query = query.order_by(desc(VoteModel.vote_date))
    
    result_query = await db.execute(query.limit(limit).offset(offset))
    votes = result_query.scalars().all()
    
    # Get total
    count_query = select(VoteModel).where(VoteModel.jurisdiction == "ca-federal")
    if parliament:
        count_query = count_query.where(VoteModel.parliament == parliament)
    if session:
        count_query = count_query.where(VoteModel.session == session)
    if bill_id:
        count_query = count_query.where(VoteModel.bill_id == bill_id)
    if result:
        count_query = count_query.where(VoteModel.result.ilike(f"%{result}%"))
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return {
        "votes": [VoteResponse.from_orm(v) for v in votes],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(votes)) < total
    }


@router.get("/votes/{vote_id}", response_model=VoteDetailResponse)
async def get_vote(
    vote_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed vote information including individual MP votes.
    
    Args:
        vote_id: Vote database ID
        db: Database session
        
    Returns:
        VoteDetailResponse with full vote data
        
    Raises:
        HTTPException: 404 if vote not found
    """
    query = select(VoteModel).where(VoteModel.id == vote_id)
    result = await db.execute(query)
    vote = result.scalar_one_or_none()
    
    if not vote:
        raise HTTPException(status_code=404, detail=f"Vote {vote_id} not found")
    
    # Get vote records
    records_query = select(VoteRecordModel).where(VoteRecordModel.vote_id == vote_id)
    records_result = await db.execute(records_query)
    vote_records = records_result.scalars().all()
    
    return VoteDetailResponse.from_orm_with_records(vote, vote_records)
