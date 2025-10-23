"""
Search API Endpoints
====================
Full-text search across bills, debates, speeches using PostgreSQL full-text search.

Endpoints:
    - GET /api/v1/ca/search - Search all entities
    - GET /api/v1/ca/search/bills - Search bills only
    - GET /api/v1/ca/search/debates - Search debates only
    - GET /api/v1/ca/search/speeches - Search speeches only

Responsibility: Hybrid search with BM25 ranking using PostgreSQL GIN indexes
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func, or_
from pydantic import BaseModel, Field

from src.db.session import get_db
from src.db.models import BillModel, DebateModel, SpeechModel


router = APIRouter()


# Response Models
class SearchResult(BaseModel):
    """Single search result"""
    entity_type: str = Field(..., description="Type: bill, debate, speech")
    entity_id: int = Field(..., description="Entity ID")
    title: str = Field(..., description="Result title")
    snippet: str = Field(..., description="Text snippet with highlights")
    rank: float = Field(..., description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    url: Optional[str] = Field(None, description="Link to entity")


class SearchResponse(BaseModel):
    """Search response with results"""
    query: str = Field(..., description="Original search query")
    total: int = Field(..., description="Total results found")
    results: List[SearchResult] = Field(default_factory=list)
    took_ms: int = Field(..., description="Query execution time in milliseconds")


# Search Functions
async def search_bills(
    session: AsyncSession,
    query: str,
    limit: int = 20
) -> List[SearchResult]:
    """
    Search bills using PostgreSQL full-text search.
    
    Uses the search_vector GIN index for fast text matching.
    Returns results ranked by ts_rank.
    """
    sql = text("""
        SELECT 
            id,
            number,
            title_en,
            title_fr,
            parliament,
            session,
            ts_rank(search_vector, websearch_to_tsquery('english', :query)) as rank,
            ts_headline('english', 
                COALESCE(summary_en, title_en, ''), 
                websearch_to_tsquery('english', :query),
                'MaxWords=50, MinWords=20, StartSel=<mark>, StopSel=</mark>'
            ) as snippet
        FROM bills
        WHERE search_vector @@ websearch_to_tsquery('english', :query)
        ORDER BY rank DESC, introduced_date DESC
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {"query": query, "limit": limit})
    rows = result.fetchall()
    
    results = []
    for row in rows:
        results.append(SearchResult(
            entity_type="bill",
            entity_id=row.id,
            title=row.title_en or row.title_fr or f"Bill {row.number}",
            snippet=row.snippet or "",
            rank=float(row.rank) if row.rank else 0.0,
            metadata={
                "number": row.number,
                "parliament": row.parliament,
                "session": row.session
            },
            url=f"/bills/{row.id}"
        ))
    
    return results


async def search_debates(
    session: AsyncSession,
    query: str,
    limit: int = 20
) -> List[SearchResult]:
    """
    Search debates using PostgreSQL full-text search.
    """
    sql = text("""
        SELECT 
            id,
            sitting_date,
            parliament,
            session,
            chamber,
            ts_rank(search_vector, websearch_to_tsquery('english', :query)) as rank,
            ts_headline('english', 
                COALESCE(title_en, title_fr, ''), 
                websearch_to_tsquery('english', :query),
                'MaxWords=50, MinWords=20, StartSel=<mark>, StopSel=</mark>'
            ) as snippet
        FROM debates
        WHERE search_vector @@ websearch_to_tsquery('english', :query)
        ORDER BY rank DESC, sitting_date DESC
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {"query": query, "limit": limit})
    rows = result.fetchall()
    
    results = []
    for row in rows:
        results.append(SearchResult(
            entity_type="debate",
            entity_id=row.id,
            title=f"Debate - {row.sitting_date}",
            snippet=row.snippet or "",
            rank=float(row.rank) if row.rank else 0.0,
            metadata={
                "sitting_date": str(row.sitting_date),
                "parliament": row.parliament,
                "session": row.session,
                "chamber": row.chamber
            },
            url=f"/debates/{row.id}"
        ))
    
    return results


async def search_speeches(
    session: AsyncSession,
    query: str,
    limit: int = 20
) -> List[SearchResult]:
    """
    Search speeches using PostgreSQL full-text search.
    """
    sql = text("""
        SELECT 
            s.id,
            s.debate_id,
            s.politician_id,
            p.name as politician_name,
            s.h_id,
            ts_rank(s.search_vector, websearch_to_tsquery('english', :query)) as rank,
            ts_headline('english', 
                s.content, 
                websearch_to_tsquery('english', :query),
                'MaxWords=50, MinWords=20, StartSel=<mark>, StopSel=</mark>'
            ) as snippet
        FROM speeches s
        LEFT JOIN politicians p ON s.politician_id = p.id
        WHERE s.search_vector @@ websearch_to_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {"query": query, "limit": limit})
    rows = result.fetchall()
    
    results = []
    for row in rows:
        results.append(SearchResult(
            entity_type="speech",
            entity_id=row.id,
            title=f"Speech by {row.politician_name or 'Unknown'}" if row.politician_name else f"Speech #{row.h_id}",
            snippet=row.snippet or "",
            rank=float(row.rank) if row.rank else 0.0,
            metadata={
                "debate_id": row.debate_id,
                "politician_id": row.politician_id,
                "politician_name": row.politician_name
            },
            url=f"/speeches/{row.id}"
        ))
    
    return results


# Endpoints
@router.get("/search", response_model=SearchResponse)
async def search_all(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Results per entity type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search across all entities (bills, debates, speeches).
    
    Uses PostgreSQL full-text search with GIN indexes.
    Results are ranked by relevance using ts_rank.
    
    Args:
        q: Search query (supports phrases, AND/OR, negation)
        limit: Maximum results per entity type
        db: Database session
        
    Returns:
        SearchResponse with ranked results
        
    Examples:
        - Simple: ?q=climate change
        - Phrase: ?q="carbon tax"
        - Boolean: ?q=climate AND carbon
        - Negation: ?q=climate -tax
    """
    import time
    start = time.time()
    
    # Search all entity types
    bills_results = await search_bills(db, q, limit)
    debates_results = await search_debates(db, q, limit)
    speeches_results = await search_speeches(db, q, limit)
    
    # Combine and sort by rank
    all_results = bills_results + debates_results + speeches_results
    all_results.sort(key=lambda x: x.rank, reverse=True)
    
    # Limit total results
    all_results = all_results[:limit * 3]  # Max 3x limit total
    
    took_ms = int((time.time() - start) * 1000)
    
    return SearchResponse(
        query=q,
        total=len(all_results),
        results=all_results,
        took_ms=took_ms
    )


@router.get("/search/bills", response_model=SearchResponse)
async def search_bills_only(
    q: str = Query(..., min_length=2, description="Search query"),
    parliament: Optional[int] = Query(None, description="Filter by parliament"),
    session: Optional[int] = Query(None, description="Filter by session"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search bills only.
    
    Args:
        q: Search query
        parliament: Filter by parliament number
        session: Filter by session number
        limit: Maximum results
        db: Database session
        
    Returns:
        SearchResponse with bill results only
    """
    import time
    start = time.time()
    
    results = await search_bills(db, q, limit)
    
    # Apply filters if provided
    if parliament is not None:
        results = [r for r in results if r.metadata.get("parliament") == parliament]
    if session is not None:
        results = [r for r in results if r.metadata.get("session") == session]
    
    took_ms = int((time.time() - start) * 1000)
    
    return SearchResponse(
        query=q,
        total=len(results),
        results=results,
        took_ms=took_ms
    )


@router.get("/search/debates", response_model=SearchResponse)
async def search_debates_only(
    q: str = Query(..., min_length=2, description="Search query"),
    parliament: Optional[int] = Query(None, description="Filter by parliament"),
    session: Optional[int] = Query(None, description="Filter by session"),
    chamber: Optional[str] = Query(None, description="Filter by chamber (commons/senate)"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search debates only.
    
    Args:
        q: Search query
        parliament: Filter by parliament number
        session: Filter by session number
        chamber: Filter by chamber
        limit: Maximum results
        db: Database session
        
    Returns:
        SearchResponse with debate results only
    """
    import time
    start = time.time()
    
    results = await search_debates(db, q, limit)
    
    # Apply filters
    if parliament is not None:
        results = [r for r in results if r.metadata.get("parliament") == parliament]
    if session is not None:
        results = [r for r in results if r.metadata.get("session") == session]
    if chamber is not None:
        results = [r for r in results if r.metadata.get("chamber") == chamber]
    
    took_ms = int((time.time() - start) * 1000)
    
    return SearchResponse(
        query=q,
        total=len(results),
        results=results,
        took_ms=took_ms
    )


@router.get("/search/speeches", response_model=SearchResponse)
async def search_speeches_only(
    q: str = Query(..., min_length=2, description="Search query"),
    politician_id: Optional[int] = Query(None, description="Filter by politician ID"),
    debate_id: Optional[int] = Query(None, description="Filter by debate ID"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Search speeches only.
    
    Args:
        q: Search query
        politician_id: Filter by politician
        debate_id: Filter by debate
        limit: Maximum results
        db: Database session
        
    Returns:
        SearchResponse with speech results only
    """
    import time
    start = time.time()
    
    results = await search_speeches(db, q, limit)
    
    # Apply filters
    if politician_id is not None:
        results = [r for r in results if r.metadata.get("politician_id") == politician_id]
    if debate_id is not None:
        results = [r for r in results if r.metadata.get("debate_id") == debate_id]
    
    took_ms = int((time.time() - start) * 1000)
    
    return SearchResponse(
        query=q,
        total=len(results),
        results=results,
        took_ms=took_ms
    )
