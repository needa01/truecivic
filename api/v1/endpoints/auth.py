"""
API endpoints for authentication and API key management.

Provides endpoints for:
- Creating and managing API keys
- Retrieving key information
- Revoking access

Responsibility: API key management endpoints
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.db.repositories.api_key_repository import APIKeyRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# MARK: Schemas

class APIKeyCreateRequest(BaseModel):
    """Request schema for creating an API key."""
    
    name: str = Field(..., min_length=1, max_length=200, description="Human-readable name")
    rate_limit_requests: int = Field(default=1000, ge=1, le=100000)
    rate_limit_window_seconds: int = Field(default=3600, ge=60, le=86400)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=730, description="Days until expiration")


class APIKeyResponse(BaseModel):
    """Response schema for API key (without raw key)."""
    
    id: int
    name: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    requests_count: int
    rate_limit_requests: int
    rate_limit_window_seconds: int


class APIKeyCreateResponse(APIKeyResponse):
    """Response schema for key creation (includes raw key)."""
    
    key: str = Field(..., description="Raw API key (shown only once!)")


class APIKeyListResponse(BaseModel):
    """Response schema for listing keys."""
    
    total: int
    keys: List[APIKeyResponse]


class APIKeyUpdateRateLimitRequest(BaseModel):
    """Request schema for updating rate limits."""
    
    requests: int = Field(..., ge=1, le=100000)
    window_seconds: int = Field(..., ge=60, le=86400)


class APIKeyUsageResponse(BaseModel):
    """Response schema for usage statistics."""
    
    key_id: int
    name: str
    created_at: datetime
    last_used_at: Optional[datetime]
    requests_count: int
    is_active: bool
    expires_at: Optional[datetime]
    rate_limit: dict


# MARK: Endpoints

@router.post(
    "/keys",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new API key",
    description="Create a new API key for authentication. The raw key is displayed only once!"
)
async def create_api_key(
    request: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Create a new API key.
    
    Args:
        request: Key creation request with name and optional rate limits
        db: Database session
        
    Returns:
        APIKeyCreateResponse with raw key (only shown once!)
    """
    try:
        repo = APIKeyRepository(db)
        
        # Calculate expiration if specified
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        # Create key
        raw_key, api_key_model = await repo.create_key(
            name=request.name,
            rate_limit_requests=request.rate_limit_requests,
            rate_limit_window_seconds=request.rate_limit_window_seconds,
            expires_at=expires_at
        )
        
        await db.commit()
        await db.refresh(api_key_model)
        
        logger.info(f"✅ Created API key: {request.name}")
        
        return {
            "id": api_key_model.id,
            "name": api_key_model.name,
            "key": raw_key,
            "is_active": api_key_model.is_active,
            "created_at": api_key_model.created_at,
            "last_used_at": api_key_model.last_used_at,
            "expires_at": api_key_model.expires_at,
            "requests_count": api_key_model.requests_count,
            "rate_limit_requests": api_key_model.rate_limit_requests,
            "rate_limit_window_seconds": api_key_model.rate_limit_window_seconds
        }
    
    except Exception as e:
        logger.error(f"Error creating API key: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get(
    "/keys",
    response_model=APIKeyListResponse,
    summary="List API keys",
    description="List all API keys (active and inactive)"
)
async def list_api_keys(
    active_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    List all API keys.
    
    Args:
        active_only: Filter to only active keys
        limit: Maximum results
        offset: Pagination offset
        db: Database session
        
    Returns:
        APIKeyListResponse with list of keys
    """
    try:
        repo = APIKeyRepository(db)
        
        # Get keys
        keys = await repo.list_all(
            active_only=active_only,
            limit=limit,
            offset=offset
        )
        
        # Count total
        total = await repo.count_active() if active_only else len(keys)
        
        return {
            "total": total,
            "keys": [
                {
                    "id": k.id,
                    "name": k.name,
                    "is_active": k.is_active,
                    "created_at": k.created_at,
                    "last_used_at": k.last_used_at,
                    "expires_at": k.expires_at,
                    "requests_count": k.requests_count,
                    "rate_limit_requests": k.rate_limit_requests,
                    "rate_limit_window_seconds": k.rate_limit_window_seconds
                }
                for k in keys
            ]
        }
    
    except Exception as e:
        logger.error(f"Error listing API keys: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list API keys"
        )


@router.get(
    "/keys/{key_id}/usage",
    response_model=APIKeyUsageResponse,
    summary="Get key usage statistics",
    description="Get usage statistics for an API key"
)
async def get_key_usage(
    key_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get usage statistics for an API key.
    
    Args:
        key_id: Key ID
        db: Database session
        
    Returns:
        APIKeyUsageResponse with statistics
    """
    try:
        repo = APIKeyRepository(db)
        stats = await repo.get_usage_stats(key_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return stats
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting key usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get key usage statistics"
        )


@router.patch(
    "/keys/{key_id}/rate-limit",
    response_model=APIKeyResponse,
    summary="Update rate limit",
    description="Update rate limiting for an API key"
)
async def update_rate_limit(
    key_id: int,
    request: APIKeyUpdateRateLimitRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update rate limiting for an API key.
    
    Args:
        key_id: Key ID
        request: New rate limit settings
        db: Database session
        
    Returns:
        Updated APIKeyResponse
    """
    try:
        repo = APIKeyRepository(db)
        
        # Update rate limit
        updated = await repo.update_rate_limit(
            key_id,
            request.requests,
            request.window_seconds
        )
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        await db.commit()
        
        # Fetch and return updated key
        api_key = await repo.get_by_id(key_id)
        
        return {
            "id": api_key.id,
            "name": api_key.name,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at,
            "last_used_at": api_key.last_used_at,
            "expires_at": api_key.expires_at,
            "requests_count": api_key.requests_count,
            "rate_limit_requests": api_key.rate_limit_requests,
            "rate_limit_window_seconds": api_key.rate_limit_window_seconds
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rate limit: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update rate limit"
        )


@router.post(
    "/keys/{key_id}/deactivate",
    response_model=APIKeyResponse,
    summary="Deactivate API key",
    description="Deactivate an API key (revoke access)"
)
async def deactivate_key(
    key_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Deactivate an API key (revoke access).
    
    Args:
        key_id: Key ID
        db: Database session
        
    Returns:
        Updated APIKeyResponse
    """
    try:
        repo = APIKeyRepository(db)
        
        deactivated = await repo.deactivate_key(key_id)
        
        if not deactivated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        await db.commit()
        
        # Fetch and return updated key
        api_key = await repo.get_by_id(key_id)
        
        logger.info(f"Deactivated API key: {api_key.name}")
        
        return {
            "id": api_key.id,
            "name": api_key.name,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at,
            "last_used_at": api_key.last_used_at,
            "expires_at": api_key.expires_at,
            "requests_count": api_key.requests_count,
            "rate_limit_requests": api_key.rate_limit_requests,
            "rate_limit_window_seconds": api_key.rate_limit_window_seconds
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating key: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate API key"
        )


@router.post(
    "/keys/{key_id}/activate",
    response_model=APIKeyResponse,
    summary="Activate API key",
    description="Reactivate a deactivated API key"
)
async def activate_key(
    key_id: int,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Reactivate a deactivated API key.
    
    Args:
        key_id: Key ID
        db: Database session
        
    Returns:
        Updated APIKeyResponse
    """
    try:
        repo = APIKeyRepository(db)
        
        activated = await repo.activate_key(key_id)
        
        if not activated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        await db.commit()
        
        # Fetch and return updated key
        api_key = await repo.get_by_id(key_id)
        
        logger.info(f"Activated API key: {api_key.name}")
        
        return {
            "id": api_key.id,
            "name": api_key.name,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at,
            "last_used_at": api_key.last_used_at,
            "expires_at": api_key.expires_at,
            "requests_count": api_key.requests_count,
            "rate_limit_requests": api_key.rate_limit_requests,
            "rate_limit_window_seconds": api_key.rate_limit_window_seconds
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating key: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate API key"
        )


@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete API key",
    description="Permanently delete an API key"
)
async def delete_key(
    key_id: int,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Permanently delete an API key.
    
    Args:
        key_id: Key ID
        db: Database session
    """
    try:
        repo = APIKeyRepository(db)
        
        deleted = await repo.delete_key(key_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        await db.commit()
        logger.info(f"Deleted API key: {key_id}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting key: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete API key"
        )
