"""
Politicians API endpoints.

Provides REST endpoints for querying politicians/MPs.

Responsibility: Politician endpoints for API v1
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc

from src.db.session import get_db
from src.db.models import PoliticianModel
from api.v1.schemas.politicians import PoliticianResponse, PoliticianListResponse

router = APIRouter()


@router.get("/politicians", response_model=PoliticianListResponse)
async def list_politicians(
    party: Optional[str] = Query(None, description="Filter by party"),
    riding: Optional[str] = Query(None, description="Filter by riding"),
    current_only: bool = Query(True, description="Only show current MPs"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    List politicians with optional filters.
    
    Args:
        party: Filter by party name
        riding: Filter by riding name
        current_only: Only return current MPs
        limit: Maximum results (1-200)
        offset: Pagination offset
        db: Database session
        
    Returns:
        PoliticianListResponse with politicians
    """
    query = select(PoliticianModel)
    
    # Apply filters
    if party:
        query = query.where(PoliticianModel.current_party.ilike(f"%{party}%"))
    if riding:
        query = query.where(PoliticianModel.current_riding.ilike(f"%{riding}%"))
    if current_only:
        # Assume current MPs have current_party set
        query = query.where(PoliticianModel.current_party.isnot(None))
    
    # Order by name
    query = query.order_by(PoliticianModel.name)
    
    # Execute query
    result = await db.execute(query.limit(limit).offset(offset))
    politicians = result.scalars().all()
    
    # Get total count
    count_query = select(PoliticianModel)
    if party:
        count_query = count_query.where(PoliticianModel.current_party.ilike(f"%{party}%"))
    if riding:
        count_query = count_query.where(PoliticianModel.current_riding.ilike(f"%{riding}%"))
    if current_only:
        count_query = count_query.where(PoliticianModel.current_party.isnot(None))
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return {
        "politicians": [PoliticianResponse.from_orm(p) for p in politicians],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + len(politicians)) < total
    }


@router.get("/politicians/{politician_id}", response_model=PoliticianResponse)
async def get_politician(
    politician_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific politician.
    
    Args:
        politician_id: Politician database ID
        db: Database session
        
    Returns:
        PoliticianResponse with full information
        
    Raises:
        HTTPException: 404 if politician not found
    """
    query = select(PoliticianModel).where(PoliticianModel.id == politician_id)
    result = await db.execute(query)
    politician = result.scalar_one_or_none()
    
    if not politician:
        raise HTTPException(status_code=404, detail=f"Politician {politician_id} not found")
    
    return PoliticianResponse.from_orm(politician)


@router.get("/politicians/search")
async def search_politicians(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """
    Search politicians by name.
    
    Args:
        q: Search query
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        
    Returns:
        PoliticianListResponse with matching politicians
    """
    query = select(PoliticianModel).where(
        or_(
            PoliticianModel.name.ilike(f"%{q}%"),
            PoliticianModel.given_name.ilike(f"%{q}%"),
            PoliticianModel.family_name.ilike(f"%{q}%")
        )
    ).order_by(PoliticianModel.name).limit(limit).offset(offset)
    
    result = await db.execute(query)
    politicians = result.scalars().all()
    
    return {
        "politicians": [PoliticianResponse.from_orm(p) for p in politicians],
        "total": len(politicians),
        "limit": limit,
        "offset": offset,
        "query": q
    }
