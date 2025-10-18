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
