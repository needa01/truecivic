"""
Bills API endpoints.

Provides REST endpoints for querying parliamentary bills.

Responsibility: Bill endpoints for API v1
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from datetime import datetime

from src.db.session import get_db
from src.db.models import BillModel
from api.v1.schemas.bills import BillResponse, BillListResponse, BillDetailResponse

router = APIRouter()


@router.get("/bills", response_model=BillListResponse)
async def list_bills(
    parliament: Optional[int] = Query(None, description="Filter by parliament number"),
    session: Optional[int] = Query(None, description="Filter by session number"),
    law_status: Optional[str] = Query(None, description="Filter by law status"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort: str = Query("introduced_date", description="Sort field (introduced_date, updated_at)"),
    order: str = Query("desc", description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db)
):
    """
    List bills with optional filters and pagination.
    
    Args:
        parliament: Filter by parliament number
        session: Filter by session number
        law_status: Filter by status (e.g., "In force", "Royal assent")
        limit: Maximum results to return (1-100)
        offset: Number of results to skip
        sort: Field to sort by
        order: Sort order (asc/desc)
        db: Database session
        
    Returns:
        BillListResponse with bills and metadata
    """
    # Build query
    query = select(BillModel).where(
        BillModel.jurisdiction == "ca-federal"
    )
    
    # Apply filters
    if parliament:
        query = query.where(BillModel.parliament == parliament)
    if session:
        query = query.where(BillModel.session == session)
    if law_status:
        query = query.where(BillModel.law_status.ilike(f"%{law_status}%"))
    
    # Apply sorting
    sort_field = getattr(BillModel, sort, BillModel.introduced_date)
    if order == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(sort_field)
    
    # Get total count (before pagination)
    count_query = select(BillModel).where(
        BillModel.jurisdiction == "ca-federal"
    )
    if parliament:
        count_query = count_query.where(BillModel.parliament == parliament)
    if session:
        count_query = count_query.where(BillModel.session == session)
    if law_status:
        count_query = count_query.where(BillModel.law_status.ilike(f"%{law_status}%"))
    
    # Execute queries
    result = await db.execute(query.limit(limit).offset(offset))
    bills = result.scalars().all()
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return {
        "bills": [BillResponse.from_orm(bill) for bill in bills],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(bills)) < total
    }


@router.get("/bills/{bill_id}", response_model=BillDetailResponse)
async def get_bill(
    bill_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific bill.
    
    Args:
        bill_id: Bill database ID
        db: Database session
        
    Returns:
        BillDetailResponse with full bill information
        
    Raises:
        HTTPException: 404 if bill not found
    """
    query = select(BillModel).where(BillModel.id == bill_id)
    result = await db.execute(query)
    bill = result.scalar_one_or_none()
    
    if not bill:
        raise HTTPException(status_code=404, detail=f"Bill {bill_id} not found")
    
    return BillDetailResponse.from_orm(bill)


@router.get("/bills/number/{bill_number}", response_model=BillDetailResponse)
async def get_bill_by_number(
    bill_number: str,
    parliament: int = Query(..., description="Parliament number"),
    session: int = Query(..., description="Session number"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get bill by its number (e.g., "C-30").
    
    Args:
        bill_number: Bill number
        parliament: Parliament number
        session: Session number
        db: Database session
        
    Returns:
        BillDetailResponse with full bill information
        
    Raises:
        HTTPException: 404 if bill not found
    """
    query = select(BillModel).where(
        and_(
            BillModel.jurisdiction == "ca-federal",
            BillModel.number == bill_number,
            BillModel.parliament == parliament,
            BillModel.session == session
        )
    )
    result = await db.execute(query)
    bill = result.scalar_one_or_none()
    
    if not bill:
        raise HTTPException(
            status_code=404,
            detail=f"Bill {bill_number} not found in parliament {parliament}, session {session}"
        )
    
    return BillDetailResponse.from_orm(bill)


@router.get("/bills/search")
async def search_bills(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Search bills by title or summary.
    
    Args:
        q: Search query string
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        
    Returns:
        BillListResponse with matching bills
    """
    query = select(BillModel).where(
        and_(
            BillModel.jurisdiction == "ca-federal",
            or_(
                BillModel.title_en.ilike(f"%{q}%"),
                BillModel.title_fr.ilike(f"%{q}%"),
                BillModel.legisinfo_summary_en.ilike(f"%{q}%"),
                BillModel.legisinfo_summary_fr.ilike(f"%{q}%")
            )
        )
    ).order_by(desc(BillModel.introduced_date)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    bills = result.scalars().all()
    
    return {
        "bills": [BillResponse.from_orm(bill) for bill in bills],
        "total": len(bills),
        "limit": limit,
        "offset": offset,
        "query": q
    }
