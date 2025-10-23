"""
Preferences API Endpoints
==========================
Device-level personalization without authentication.

Endpoints:
    - POST /api/v1/ca/preferences/ignore - Add item to ignore list
    - DELETE /api/v1/ca/preferences/ignore - Remove from ignore list
    - GET /api/v1/ca/preferences/ignored - List all ignored items
    - POST /api/v1/ca/preferences/token - Generate personalized feed token
    - GET /api/v1/ca/preferences/token/{token} - Get token details

Responsibility: Manage device-level ignores for bills, politicians, committees
"""

from typing import Optional, List, Literal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Body, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from pydantic import BaseModel, Field
import secrets
import hashlib

from src.db.session import get_db
from src.db.models import IgnoredBillModel, PersonalizedFeedTokenModel


router = APIRouter()


# Request/Response Models
class IgnoreRequest(BaseModel):
    """Request to ignore an entity"""
    entity_type: Literal["bill", "politician", "committee"] = Field(..., description="Entity type to ignore")
    entity_id: int = Field(..., description="Entity ID")


class IgnoreResponse(BaseModel):
    """Response after ignore operation"""
    success: bool
    message: str
    ignored_count: int = Field(..., description="Total items ignored by this device")


class IgnoredItem(BaseModel):
    """Single ignored item"""
    entity_type: str
    entity_id: int
    created_at: datetime


class IgnoredListResponse(BaseModel):
    """List of ignored items"""
    anon_id: str
    items: List[IgnoredItem]
    total: int


class TokenRequest(BaseModel):
    """Request to generate feed token"""
    anon_id: str = Field(..., description="Anonymous device ID")


class TokenResponse(BaseModel):
    """Feed token response"""
    token: str = Field(..., description="Personalized feed token")
    anon_id: str
    feed_url: str = Field(..., description="Personalized feed URL")
    created_at: datetime
    expires_at: Optional[datetime] = None


# Helper Functions
def validate_anon_id(anon_id: str) -> bool:
    """
    Validate anonymous ID format.
    
    Should be a UUID v4 or similar unique identifier.
    Minimum 16 characters, alphanumeric + hyphens.
    """
    if not anon_id:
        return False
    if len(anon_id) < 16:
        return False
    # Allow alphanumeric and hyphens
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")
    if not all(c in allowed for c in anon_id):
        return False
    return True


def generate_feed_token(anon_id: str) -> str:
    """
    Generate a unique feed token for personalized feeds.
    
    Token format: {hash(anon_id + secret)}
    """
    random_suffix = secrets.token_urlsafe(16)
    combined = f"{anon_id}:{random_suffix}"
    token_hash = hashlib.sha256(combined.encode()).hexdigest()[:32]
    return token_hash


# Endpoints
@router.post("/preferences/ignore", response_model=IgnoreResponse)
async def add_ignore(
    request: IgnoreRequest = Body(...),
    x_anon_id: str = Header(..., description="Anonymous device ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Add an entity to the ignore list for this device.
    
    Ignored entities will be filtered from:
    - Bill lists
    - Search results
    - Personalized feeds
    - Graph visualizations
    
    Args:
        request: Entity to ignore
        x_anon_id: Device ID from X-Anon-Id header
        db: Database session
        
    Returns:
        IgnoreResponse with success status
        
    Headers:
        X-Anon-Id: UUID v4 device identifier
        
    Examples:
        POST /preferences/ignore
        X-Anon-Id: 550e8400-e29b-41d4-a716-446655440000
        {"entity_type": "bill", "entity_id": 123}
    """
    # Validate anon_id
    if not validate_anon_id(x_anon_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Anon-Id header. Must be UUID v4 format (min 16 chars)."
        )
    
    # Currently only bills are supported in database
    if request.entity_type != "bill":
        raise HTTPException(
            status_code=400,
            detail=f"Entity type '{request.entity_type}' not yet supported. Currently only 'bill' is supported."
        )
    
    # Check if already ignored
    existing_query = select(IgnoredBillModel).where(
        and_(
            IgnoredBillModel.anon_id == x_anon_id,
            IgnoredBillModel.bill_id == request.entity_id
        )
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        # Already ignored, count total
        count_query = select(IgnoredBillModel).where(
            IgnoredBillModel.anon_id == x_anon_id
        )
        count_result = await db.execute(count_query)
        total = len(count_result.scalars().all())
        
        return IgnoreResponse(
            success=True,
            message=f"{request.entity_type.capitalize()} {request.entity_id} already ignored",
            ignored_count=total
        )
    
    # Add to ignore list
    ignored_item = IgnoredBillModel(
        anon_id=x_anon_id,
        bill_id=request.entity_id,
        jurisdiction="ca-federal",
        created_at=datetime.utcnow()
    )
    db.add(ignored_item)
    await db.commit()
    
    # Count total ignored
    count_query = select(IgnoredBillModel).where(
        IgnoredBillModel.anon_id == x_anon_id
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return IgnoreResponse(
        success=True,
        message=f"{request.entity_type.capitalize()} {request.entity_id} added to ignore list",
        ignored_count=total
    )


@router.delete("/preferences/ignore", response_model=IgnoreResponse)
async def remove_ignore(
    entity_type: Literal["bill", "politician", "committee"] = Body(...),
    entity_id: int = Body(...),
    x_anon_id: str = Header(..., description="Anonymous device ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an entity from the ignore list.
    
    Args:
        entity_type: Entity type
        entity_id: Entity ID
        x_anon_id: Device ID
        db: Database session
        
    Returns:
        IgnoreResponse with success status
    """
    # Validate anon_id
    if not validate_anon_id(x_anon_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Anon-Id header."
        )
    
    # Currently only bills supported
    if entity_type != "bill":
        raise HTTPException(
            status_code=400,
            detail=f"Entity type '{entity_type}' not yet supported."
        )
    
    # Delete from database
    delete_query = delete(IgnoredBillModel).where(
        and_(
            IgnoredBillModel.anon_id == x_anon_id,
            IgnoredBillModel.bill_id == entity_id
        )
    )
    result = await db.execute(delete_query)
    await db.commit()
    
    # Count remaining
    count_query = select(IgnoredBillModel).where(
        IgnoredBillModel.anon_id == x_anon_id
    )
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    if result.rowcount > 0:
        return IgnoreResponse(
            success=True,
            message=f"{entity_type.capitalize()} {entity_id} removed from ignore list",
            ignored_count=total
        )
    else:
        return IgnoreResponse(
            success=False,
            message=f"{entity_type.capitalize()} {entity_id} was not in ignore list",
            ignored_count=total
        )


@router.get("/preferences/ignored", response_model=IgnoredListResponse)
async def list_ignored(
    x_anon_id: str = Header(..., description="Anonymous device ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all ignored entities for this device.
    
    Args:
        x_anon_id: Device ID
        db: Database session
        
    Returns:
        IgnoredListResponse with all ignored items
    """
    # Validate anon_id
    if not validate_anon_id(x_anon_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid X-Anon-Id header."
        )
    
    # Get all ignored bills
    query = select(IgnoredBillModel).where(
        IgnoredBillModel.anon_id == x_anon_id
    ).order_by(IgnoredBillModel.created_at.desc())
    
    result = await db.execute(query)
    ignored_bills = result.scalars().all()
    
    items = [
        IgnoredItem(
            entity_type="bill",
            entity_id=item.bill_id,
            created_at=item.created_at
        )
        for item in ignored_bills
    ]
    
    return IgnoredListResponse(
        anon_id=x_anon_id,
        items=items,
        total=len(items)
    )


@router.post("/preferences/token", response_model=TokenResponse)
async def create_feed_token(
    request: TokenRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a personalized feed token for this device.
    
    This token can be used to access personalized RSS feeds that
    respect the device's ignore list without requiring authentication.
    
    Args:
        request: Token request with anon_id
        db: Database session
        
    Returns:
        TokenResponse with token and feed URL
        
    Examples:
        POST /preferences/token
        {"anon_id": "550e8400-e29b-41d4-a716-446655440000"}
        
        Response:
        {
            "token": "abc123...",
            "feed_url": "/api/v1/ca/feeds/p/abc123.xml"
        }
    """
    # Validate anon_id
    if not validate_anon_id(request.anon_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid anon_id format."
        )
    
    # Check if token already exists
    existing_query = select(PersonalizedFeedTokenModel).where(
        PersonalizedFeedTokenModel.anon_id == request.anon_id
    )
    existing_result = await db.execute(existing_query)
    existing = existing_result.scalar_one_or_none()
    
    if existing:
        # Return existing token
        return TokenResponse(
            token=existing.token,
            anon_id=existing.anon_id,
            feed_url=f"/api/v1/ca/feeds/p/{existing.token}.xml",
            created_at=existing.created_at,
            expires_at=None
        )
    
    # Generate new token
    token = generate_feed_token(request.anon_id)
    
    # Save to database
    token_record = PersonalizedFeedTokenModel(
        token=token,
        anon_id=request.anon_id,
        created_at=datetime.utcnow(),
        last_used=datetime.utcnow()
    )
    db.add(token_record)
    await db.commit()
    
    return TokenResponse(
        token=token,
        anon_id=request.anon_id,
        feed_url=f"/api/v1/ca/feeds/p/{token}.xml",
        created_at=token_record.created_at,
        expires_at=None
    )


@router.get("/preferences/token/{token}", response_model=TokenResponse)
async def get_token_details(
    token: str = Path(..., description="Feed token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details about a feed token.
    
    Args:
        token: Feed token
        db: Database session
        
    Returns:
        TokenResponse with token details
    """
    query = select(PersonalizedFeedTokenModel).where(
        PersonalizedFeedTokenModel.token == token
    )
    result = await db.execute(query)
    token_record = result.scalar_one_or_none()
    
    if not token_record:
        raise HTTPException(
            status_code=404,
            detail="Token not found"
        )
    
    # Update last_used
    token_record.last_used = datetime.utcnow()
    await db.commit()
    
    return TokenResponse(
        token=token_record.token,
        anon_id=token_record.anon_id,
        feed_url=f"/api/v1/ca/feeds/p/{token}.xml",
        created_at=token_record.created_at,
        expires_at=None
    )
