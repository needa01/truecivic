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
    
    # Convert to Pydantic models - manually construct to add natural_id
    vote_list = []
    for vote in votes:
        vote_dict = {
            "natural_id": f"ca-federal-{vote.parliament}-{vote.session}-vote-{vote.vote_number}",
            "jurisdiction": vote.jurisdiction,
            "parliament": vote.parliament,
            "session": vote.session,
            "vote_number": vote.vote_number,
            "chamber": vote.chamber,
            "vote_date": vote.vote_date,
            "vote_description_en": vote.vote_description_en,
            "vote_description_fr": vote.vote_description_fr,
            "bill_number": vote.bill_number,
            "result": vote.result,
            "yeas": vote.yeas,
            "nays": vote.nays,
            "abstentions": vote.abstentions,
            "source_url": vote.source_url,
            "created_at": vote.created_at,
            "updated_at": vote.updated_at,
            "vote_records": []  # Will be populated if needed
        }
        vote_list.append(Vote(**vote_dict))
    
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
    
    # Build query - use vote_id (database field) not natural_id
    query = select(VoteModel).where(
        and_(
            VoteModel.vote_id == vote_id,
            VoteModel.jurisdiction == "ca-federal"
        )
    )
    
    # Execute query
    result = await db.execute(query)
    vote = result.scalar_one_or_none()
    
    if not vote:
        raise HTTPException(status_code=404, detail=f"Vote {vote_id} not found")
    
    # Convert to Pydantic model - manually construct to add natural_id
    vote_dict = {
        "natural_id": f"ca-federal-{vote.parliament}-{vote.session}-vote-{vote.vote_number}",
        "jurisdiction": vote.jurisdiction,
        "parliament": vote.parliament,
        "session": vote.session,
        "vote_number": vote.vote_number,
        "chamber": vote.chamber,
        "vote_date": vote.vote_date,
        "vote_description_en": vote.vote_description_en,
        "vote_description_fr": vote.vote_description_fr,
        "bill_number": getattr(vote, 'bill_number', None),
        "result": vote.result,
        "yeas": vote.yeas,
        "nays": vote.nays,
        "abstentions": vote.abstentions,
        "source_url": getattr(vote, 'source_url', None),
        "created_at": vote.created_at,
        "updated_at": vote.updated_at,
        "vote_records": []
    }
    
    # If records requested, fetch them and manually construct
    if include_records:
        records_query = select(VoteRecordModel).where(VoteRecordModel.vote_id == vote.id)
        records_result = await db.execute(records_query)
        records = records_result.scalars().all()
        
        vote_records = []
        for record in records:
            record_dict = {
                "natural_id": f"ca-federal-{vote.parliament}-{vote.session}-vote-{vote.vote_number}-{record.politician_id}",
                "jurisdiction": "ca-federal",
                "vote_id": f"ca-federal-{vote.parliament}-{vote.session}-vote-{vote.vote_number}",
                "politician_id": record.politician_id,
                "vote_position": record.vote_position,
                "created_at": record.created_at,
                "updated_at": getattr(record, 'updated_at', record.created_at)
            }
            vote_records.append(VoteRecord(**record_dict))
        vote_dict["vote_records"] = vote_records
    
    vote_data = Vote(**vote_dict)
    
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
    
    # Verify vote exists - use vote_id field
    vote_query = select(VoteModel).where(
        and_(
            VoteModel.vote_id == vote_id,
            VoteModel.jurisdiction == "ca-federal"
        )
    )
    vote_result = await db.execute(vote_query)
    vote = vote_result.scalar_one_or_none()
    
    if not vote:
        raise HTTPException(status_code=404, detail=f"Vote {vote_id} not found")
    
    # Build records query - vote_id FK is vote.id (integer)
    query = select(VoteRecordModel).where(VoteRecordModel.vote_id == vote.id)
    
    # Apply filters
    if position:
        query = query.where(VoteRecordModel.vote_position == position)
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    records = result.scalars().all()
    
    # Convert to Pydantic models - manually construct to add natural_id
    records_list = []
    for record in records:
        record_dict = {
            "natural_id": f"ca-federal-{vote.parliament}-{vote.session}-vote-{vote.vote_number}-{record.politician_id}",
            "jurisdiction": "ca-federal",
            "vote_id": f"ca-federal-{vote.parliament}-{vote.session}-vote-{vote.vote_number}",
            "politician_id": record.politician_id,
            "vote_position": record.vote_position,
            "created_at": record.created_at,
            "updated_at": getattr(record, 'updated_at', record.created_at)
        }
        records_list.append(VoteRecord(**record_dict))

    
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
    
    # Need to import BillModel for join
    from src.db.models import BillModel
    
    # Build query - join with bills to filter by bill number
    query = select(VoteModel).join(
        BillModel, VoteModel.bill_id == BillModel.id
    ).where(
        and_(
            BillModel.number == bill_number,
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
    
    # Convert to Pydantic models - manually construct to add natural_id
    vote_list = []
    for vote in votes:
        vote_dict = {
            "natural_id": f"ca-federal-{vote.parliament}-{vote.session}-vote-{vote.vote_number}",
            "jurisdiction": vote.jurisdiction,
            "parliament": vote.parliament,
            "session": vote.session,
            "vote_number": vote.vote_number,
            "chamber": vote.chamber,
            "vote_date": vote.vote_date,
            "vote_description_en": vote.vote_description_en,
            "vote_description_fr": vote.vote_description_fr,
            "bill_number": bill_number,  # Use the query parameter
            "result": vote.result,
            "yeas": vote.yeas,
            "nays": vote.nays,
            "abstentions": vote.abstentions,
            "source_url": getattr(vote, 'source_url', None),
            "created_at": vote.created_at,
            "updated_at": vote.updated_at,
            "vote_records": []
        }
        vote_list.append(Vote(**vote_dict))
    
    logger.info(f"Found {len(vote_list)} votes for bill {bill_number}")
    
    return VoteList(
        votes=vote_list,
        total=total,
        skip=skip,
        limit=limit
    )
