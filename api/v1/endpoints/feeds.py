"""
Feed API Endpoints
==================
REST API endpoints for RSS/Atom feeds.

Endpoints:
    - GET /api/v1/ca/feeds/all.xml - All activity (bills, votes, debates)
    - GET /api/v1/ca/feeds/bills/latest.xml - Latest bills
    - GET /api/v1/ca/feeds/bills/tag/{tag}.xml - Bills by tag
    - GET /api/v1/ca/feeds/bills/parliament/{parliament}/{session}.xml - Bills by parliament/session

Responsibility: Expose RSS/Atom feeds via REST API with caching and ETag support
"""

from typing import Optional, AsyncGenerator
from datetime import datetime
from fastapi import APIRouter, Depends, Response, Query, Path
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import Database
from src.feeds import (
    LatestBillsFeedBuilder,
    BillsByTagFeedBuilder,
    AllEntitiesFeedBuilder,
    FeedFormat,
    feed_cache
)

router = APIRouter(
    prefix="/feeds",
    tags=["feeds"],
    responses={
        200: {
            "description": "RSS/Atom feed XML",
            "content": {"application/xml": {}, "application/rss+xml": {}, "application/atom+xml": {}}
        },
        304: {"description": "Not Modified (cached)"},
        404: {"description": "Feed not found"}
    }
)

# Database dependency
db = Database()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    if not db._initialized:
        await db.initialize()
    async with db.session() as session:
        yield session


def get_feed_content_type(format: FeedFormat) -> str:
    """Get appropriate content type for feed format"""
    if format == FeedFormat.RSS:
        return "application/rss+xml; charset=utf-8"
    elif format == FeedFormat.ATOM:
        return "application/atom+xml; charset=utf-8"
    else:
        return "application/xml; charset=utf-8"


def build_etag(content: str) -> str:
    """Build ETag from content hash"""
    import hashlib
    return hashlib.md5(content.encode()).hexdigest()


@router.get(
    "/all.{format}",
    summary="All Parliamentary Activity Feed",
    description="Unified feed of recent bills, votes, and debates",
    response_class=FastAPIResponse
)
async def get_all_activity_feed(
    format: str = Path(..., description="Feed format: xml, rss, or atom"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of entries"),
    session: AsyncSession = Depends(get_db_session),
    if_none_match: Optional[str] = None
) -> Response:
    """
    Get unified feed of all parliamentary activity.
    
    Args:
        format: Feed format (xml/rss/atom)
        limit: Maximum entries (1-500)
        session: Database session
        if_none_match: ETag for conditional requests
    
    Returns:
        RSS/Atom XML feed
    """
    # Determine format
    feed_format = FeedFormat.ATOM if format.lower() == "atom" else FeedFormat.RSS
    
    # Build cache key
    cache_key = f"feed:all:{format}:{limit}"
    
    # Check cache
    cached_content = feed_cache.get(cache_key)
    if cached_content:
        etag = build_etag(cached_content)
        if if_none_match == etag:
            return Response(status_code=304)  # Not Modified
        
        return Response(
            content=cached_content,
            media_type=get_feed_content_type(feed_format),
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=300"  # 5 minutes
            }
        )
    
    # Build feed
    feed_url = f"https://truecivic.ca/api/v1/ca/feeds/all.{format}"
    builder = await AllEntitiesFeedBuilder.from_materialized_view(
        session=session,
        feed_url=feed_url,
        limit=limit
    )
    
    # Generate XML
    xml_content = builder.generate(feed_format)
    
    # Cache it
    feed_cache.set(cache_key, xml_content)
    
    # Build ETag
    etag = build_etag(xml_content)
    
    return Response(
        content=xml_content,
        media_type=get_feed_content_type(feed_format),
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=300",
            "X-Feed-Entries": str(builder.get_entry_count())
        }
    )


@router.get(
    "/bills/latest.{format}",
    summary="Latest Bills Feed",
    description="Feed of recently introduced bills",
    response_class=FastAPIResponse
)
async def get_latest_bills_feed(
    format: str = Path(..., description="Feed format: xml, rss, or atom"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of entries"),
    session: AsyncSession = Depends(get_db_session),
    if_none_match: Optional[str] = None
) -> Response:
    """
    Get feed of latest bills from mv_feed_bills_latest.
    
    Args:
        format: Feed format (xml/rss/atom)
        limit: Maximum entries (1-500)
        session: Database session
        if_none_match: ETag for conditional requests
    
    Returns:
        RSS/Atom XML feed
    """
    # Determine format
    feed_format = FeedFormat.ATOM if format.lower() == "atom" else FeedFormat.RSS
    
    # Build cache key
    cache_key = f"feed:bills:latest:{format}:{limit}"
    
    # Check cache
    cached_content = feed_cache.get(cache_key)
    if cached_content:
        etag = build_etag(cached_content)
        if if_none_match == etag:
            return Response(status_code=304)
        
        return Response(
            content=cached_content,
            media_type=get_feed_content_type(feed_format),
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=300"
            }
        )
    
    # Build feed
    feed_url = f"https://truecivic.ca/api/v1/ca/feeds/bills/latest.{format}"
    builder = await LatestBillsFeedBuilder.from_materialized_view(
        session=session,
        feed_url=feed_url,
        limit=limit
    )
    
    # Generate XML
    xml_content = builder.generate(feed_format)
    
    # Cache it
    feed_cache.set(cache_key, xml_content)
    
    # Build ETag
    etag = build_etag(xml_content)
    
    return Response(
        content=xml_content,
        media_type=get_feed_content_type(feed_format),
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=300",
            "X-Feed-Entries": str(builder.get_entry_count())
        }
    )


@router.get(
    "/bills/tag/{tag}.{format}",
    summary="Bills by Tag Feed",
    description="Feed of bills filtered by subject tag",
    response_class=FastAPIResponse
)
async def get_bills_by_tag_feed(
    tag: str = Path(..., description="Subject tag to filter by"),
    format: str = Path(..., description="Feed format: xml, rss, or atom"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of entries"),
    session: AsyncSession = Depends(get_db_session),
    if_none_match: Optional[str] = None
) -> Response:
    """
    Get feed of bills filtered by tag from mv_feed_bills_by_tag.
    
    Args:
        tag: Subject tag to filter by
        format: Feed format (xml/rss/atom)
        limit: Maximum entries (1-500)
        session: Database session
        if_none_match: ETag for conditional requests
    
    Returns:
        RSS/Atom XML feed
    """
    # Determine format
    feed_format = FeedFormat.ATOM if format.lower() == "atom" else FeedFormat.RSS
    
    # Build cache key
    cache_key = f"feed:bills:tag:{tag}:{format}:{limit}"
    
    # Check cache
    cached_content = feed_cache.get(cache_key)
    if cached_content:
        etag = build_etag(cached_content)
        if if_none_match == etag:
            return Response(status_code=304)
        
        return Response(
            content=cached_content,
            media_type=get_feed_content_type(feed_format),
            headers={
                "ETag": etag,
                "Cache-Control": "public, max-age=300"
            }
        )
    
    # Build feed
    feed_url = f"https://truecivic.ca/api/v1/ca/feeds/bills/tag/{tag}.{format}"
    builder = await BillsByTagFeedBuilder.from_materialized_view(
        session=session,
        tag=tag,
        feed_url=feed_url,
        limit=limit
    )
    
    # Generate XML
    xml_content = builder.generate(feed_format)
    
    # Cache it
    feed_cache.set(cache_key, xml_content)
    
    # Build ETag
    etag = build_etag(xml_content)
    
    return Response(
        content=xml_content,
        media_type=get_feed_content_type(feed_format),
        headers={
            "ETag": etag,
            "Cache-Control": "public, max-age=300",
            "X-Feed-Entries": str(builder.get_entry_count()),
            "X-Feed-Tag": tag
        }
    )


@router.get(
    "/cache/stats",
    summary="Feed Cache Statistics",
    description="Get feed cache statistics (for monitoring)",
    response_model=dict
)
async def get_cache_stats() -> dict:
    """
    Get feed cache statistics.
    
    Returns:
        Dictionary with cache stats
    """
    return {
        "cached_feeds": feed_cache.size(),
        "ttl_seconds": feed_cache._ttl,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post(
    "/cache/clear",
    summary="Clear Feed Cache",
    description="Clear all cached feeds (admin only)",
    response_model=dict
)
async def clear_feed_cache() -> dict:
    """
    Clear all cached feeds.
    
    Returns:
        Confirmation message
    """
    feed_cache.clear()
    return {
        "status": "success",
        "message": "Feed cache cleared",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# MP Activity Feeds
# ============================================================================

@router.get(
    "/mp/{mp_id}.xml",
    summary="MP Activity Feed",
    description="RSS feed for individual MP activity (bills sponsored, votes, speeches)"
)
async def get_mp_activity_feed(
    mp_id: int = Path(..., description="Politician ID"),
    db_session: AsyncSession = Depends(get_db_session)
) -> FastAPIResponse:
    """
    Get RSS feed for MP activity.
    
    Includes:
    - Bills sponsored
    - Votes cast
    - Speeches given
    
    Args:
        mp_id: Politician ID
        db_session: Database session
        
    Returns:
        RSS feed XML
    """
    from src.feeds.politician_feeds import MPActivityFeedBuilder
    from src.db.models import PoliticianModel
    from sqlalchemy import select
    
    # Check cache
    cache_key = f"mp_{mp_id}_activity"
    cached = feed_cache.get(cache_key)
    if cached:
        return FastAPIResponse(
            content=cached,
            media_type="application/rss+xml",
            headers={"X-Cache": "HIT"}
        )
    
    # Get MP details
    mp_query = select(PoliticianModel).where(PoliticianModel.id == mp_id)
    mp_result = await db_session.execute(mp_query)
    mp = mp_result.scalar_one_or_none()
    
    if not mp:
        return FastAPIResponse(
            content="<error>MP not found</error>",
            status_code=404,
            media_type="application/xml"
        )
    
    # Build feed
    feed_url = f"/api/v1/ca/feeds/mp/{mp_id}.xml"
    builder = MPActivityFeedBuilder(
        mp_id=mp_id,
        mp_name=mp.name,
        feed_url=feed_url
    )
    
    xml = await builder.build_from_db(db_session, limit=50)
    
    # Cache for 5 minutes
    feed_cache.set(cache_key, xml)
    
    return FastAPIResponse(
        content=xml,
        media_type="application/rss+xml",
        headers={"X-Cache": "MISS"}
    )


# ============================================================================
# Committee Feeds
# ============================================================================

@router.get(
    "/committee/{committee_id}.xml",
    summary="Committee Activity Feed",
    description="RSS feed for committee meetings and reports"
)
async def get_committee_feed(
    committee_id: int = Path(..., description="Committee ID"),
    db_session: AsyncSession = Depends(get_db_session)
) -> FastAPIResponse:
    """
    Get RSS feed for committee activity.
    
    Includes:
    - Committee meetings
    - Reports published
    
    Note: Currently returns empty feed until Phase D committee adapters are complete.
    
    Args:
        committee_id: Committee ID
        db_session: Database session
        
    Returns:
        RSS feed XML
    """
    from src.feeds.committee_feeds import CommitteeFeedBuilder
    from src.db.models import CommitteeModel
    from sqlalchemy import select
    
    # Check cache
    cache_key = f"committee_{committee_id}"
    cached = feed_cache.get(cache_key)
    if cached:
        return FastAPIResponse(
            content=cached,
            media_type="application/rss+xml",
            headers={"X-Cache": "HIT"}
        )
    
    # Get committee details
    committee_query = select(CommitteeModel).where(CommitteeModel.id == committee_id)
    committee_result = await db_session.execute(committee_query)
    committee = committee_result.scalar_one_or_none()
    
    if not committee:
        return FastAPIResponse(
            content="<error>Committee not found</error>",
            status_code=404,
            media_type="application/xml"
        )
    
    # Build feed
    feed_url = f"/api/v1/ca/feeds/committee/{committee_id}.xml"
    builder = CommitteeFeedBuilder(
        committee_id=committee_id,
        committee_name=committee.name_en or committee.name_fr or f"Committee {committee_id}",
        feed_url=feed_url
    )
    
    xml = await builder.build_from_db(db_session, limit=50)
    
    # Cache for 5 minutes
    feed_cache.set(cache_key, xml)
    
    return FastAPIResponse(
        content=xml,
        media_type="application/rss+xml",
        headers={"X-Cache": "MISS"}
    )


# ============================================================================
# Single Bill Timeline Feeds
# ============================================================================

@router.get(
    "/bill/{bill_id}.xml",
    summary="Bill Timeline Feed",
    description="RSS feed for single bill timeline (votes, speeches, committee referrals)"
)
async def get_bill_timeline_feed(
    bill_id: int = Path(..., description="Bill ID"),
    db_session: AsyncSession = Depends(get_db_session)
) -> FastAPIResponse:
    """
    Get RSS feed for bill timeline.
    
    Includes:
    - Bill introduction
    - Votes on bill
    - Committee referrals
    - Royal assent
    
    Args:
        bill_id: Bill ID
        db_session: Database session
        
    Returns:
        RSS feed XML
    """
    from src.feeds.committee_feeds import BillTimelineFeedBuilder
    from src.db.models import BillModel
    from sqlalchemy import select
    
    # Check cache
    cache_key = f"bill_timeline_{bill_id}"
    cached = feed_cache.get(cache_key)
    if cached:
        return FastAPIResponse(
            content=cached,
            media_type="application/rss+xml",
            headers={"X-Cache": "HIT"}
        )
    
    # Get bill details
    bill_query = select(BillModel).where(BillModel.id == bill_id)
    bill_result = await db_session.execute(bill_query)
    bill = bill_result.scalar_one_or_none()
    
    if not bill:
        return FastAPIResponse(
            content="<error>Bill not found</error>",
            status_code=404,
            media_type="application/xml"
        )
    
    # Build feed
    feed_url = f"/api/v1/ca/feeds/bill/{bill_id}.xml"
    builder = BillTimelineFeedBuilder(
        bill_id=bill_id,
        bill_number=bill.number,
        bill_title=bill.title_en or bill.title_fr or "Untitled",
        feed_url=feed_url
    )
    
    xml = await builder.build_from_db(db_session)
    
    # Cache for 5 minutes
    feed_cache.set(cache_key, xml)
    
    return FastAPIResponse(
        content=xml,
        media_type="application/rss+xml",
        headers={"X-Cache": "MISS"}
    )
