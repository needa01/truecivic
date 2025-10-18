"""
Vote API endpoints.

Provides REST API for parliamentary votes and vote records.
"""
from typing import List, Optional
from datetime import datetime, date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.session import get_session
from src.db.models import VoteModel, VoteRecordModel
from src.models.vote import Vote, VoteRecord, VoteList

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/votes", tags=["votes"])


@router.get("/", response_model=VoteList)
async def list_votes(
    parliament: Optional[int] = Query(None, description="Filter by parliament number"),
    session: Optional[int] = Query(None, description="Filter by session number"),
    chamber: Optional[str] = Query(None, description="Filter by chamber (House, Senate)"),
    result: Optional[str] = Query(None, description="Filter by vote result"),
    bill_number: Optional[str] = Query(None, description="Filter by associated bill number"),
    from_date: Optional[date] = Query(None, description="Filter votes from this date"),
    to_date: Optional[date] = Query(None, description="Filter votes to this date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session)
) -> VoteList:
    """
    List parliamentary votes with optional filters.
    
    Returns a paginated list of votes with metadata.
    """
    logger.info(f"Listing votes: parliament={parliament}, session={session}, skip={skip}, limit={limit}")
    
    # Build query
    query = select(VoteModel).where(VoteModel.jurisdiction == "ca-federal")
    
    # Apply filters
    if parliament is not None:
        query = query.where(VoteModel.parliament == parliament)
    if session is not None:
        query = query.where(VoteModel.session == session)
    if chamber:
        query = query.where(VoteModel.chamber == chamber)
    if result:
        query = query.where(VoteModel.result == result)
    if bill_number:
        query = query.where(VoteModel.bill_number == bill_number)
    if from_date:
        query = query.where(VoteModel.vote_date >= from_date)
    if to_date:
        query = query.where(VoteModel.vote_date <= to_date)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(VoteModel.vote_date), desc(VoteModel.vote_number))
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    votes = result.scalars().all()
    
    # Convert to Pydantic models
    vote_list = [Vote.from_orm(vote) for vote in votes]
    
    logger.info(f"Found {len(vote_list)} votes (total: {total})")
    
    return VoteList(
        votes=vote_list,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{vote_id}", response_model=Vote)
async def get_vote(
    vote_id: str,
    include_records: bool = Query(False, description="Include individual vote records"),
    db: AsyncSession = Depends(get_session)
) -> Vote:
    """
    Get a specific vote by ID.
    
    Optionally includes individual MP voting records.
    """
    logger.info(f"Getting vote: {vote_id}")
    
    # Build query
    query = select(VoteModel).where(
        and_(
            VoteModel.natural_id == vote_id,
            VoteModel.jurisdiction == "ca-federal"
        )
    )
    
    # Optionally load vote records
    if include_records:
        query = query.options(selectinload(VoteModel.vote_records))
    
    # Execute query
    result = await db.execute(query)
    vote = result.scalar_one_or_none()
    
    if not vote:
        raise HTTPException(status_code=404, detail=f"Vote {vote_id} not found")
    
    # Convert to Pydantic model
    vote_data = Vote.from_orm(vote)
    
    # If records requested, fetch them separately if not already loaded
    if include_records and not vote.vote_records:
        records_query = select(VoteRecordModel).where(
            and_(
                VoteRecordModel.vote_id == vote_id,
                VoteRecordModel.jurisdiction == "ca-federal"
            )
        )
        records_result = await db.execute(records_query)
        records = records_result.scalars().all()
        vote_data.vote_records = [VoteRecord.from_orm(record) for record in records]
    
    logger.info(f"Found vote: {vote_id}")
    return vote_data


@router.get("/{vote_id}/records", response_model=List[VoteRecord])
async def get_vote_records(
    vote_id: str,
    position: Optional[str] = Query(None, description="Filter by vote position (Yea, Nay, Paired)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(500, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session)
) -> List[VoteRecord]:
    """
    Get individual voting records for a specific vote.
    
    Returns how each MP voted on this particular vote.
    """
    logger.info(f"Getting vote records for: {vote_id}")
    
    # Verify vote exists
    vote_query = select(VoteModel).where(
        and_(
            VoteModel.natural_id == vote_id,
            VoteModel.jurisdiction == "ca-federal"
        )
    )
    vote_result = await db.execute(vote_query)
    vote = vote_result.scalar_one_or_none()
    
    if not vote:
        raise HTTPException(status_code=404, detail=f"Vote {vote_id} not found")
    
    # Build records query
    query = select(VoteRecordModel).where(
        and_(
            VoteRecordModel.vote_id == vote_id,
            VoteRecordModel.jurisdiction == "ca-federal"
        )
    )
    
    # Apply filters
    if position:
        query = query.where(VoteRecordModel.vote_position == position)
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    records = result.scalars().all()
    
    # Convert to Pydantic models
    records_list = [VoteRecord.from_orm(record) for record in records]
    
    logger.info(f"Found {len(records_list)} vote records")
    return records_list


@router.get("/by-bill/{bill_number}", response_model=VoteList)
async def get_votes_by_bill(
    bill_number: str,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_session)
) -> VoteList:
    """
    Get all votes related to a specific bill.
    
    Returns votes associated with the given bill number.
    """
    logger.info(f"Getting votes for bill: {bill_number}")
    
    # Build query
    query = select(VoteModel).where(
        and_(
            VoteModel.bill_number == bill_number,
            VoteModel.jurisdiction == "ca-federal"
        )
    )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination and ordering
    query = query.order_by(desc(VoteModel.vote_date))
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    votes = result.scalars().all()
    
    # Convert to Pydantic models
    vote_list = [Vote.from_orm(vote) for vote in votes]
    
    logger.info(f"Found {len(vote_list)} votes for bill {bill_number}")
    
    return VoteList(
        votes=vote_list,
        total=total,
        skip=skip,
        limit=limit
    )
