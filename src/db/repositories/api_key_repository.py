"""
Repository for API key database operations.

Handles CRUD and authentication operations for API keys.

Responsibility: Data access layer for api_keys table
"""

import logging
import hashlib
import hmac
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import APIKeyModel

logger = logging.getLogger(__name__)


class APIKeyRepository:
    """Repository for API key database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    @staticmethod
    def hash_key(key: str) -> str:
        """
        Hash an API key for secure storage.
        
        Args:
            key: Raw API key string
            
        Returns:
            SHA-256 hash of the key
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    async def create_key(
        self,
        name: str,
        created_by: Optional[str] = None,
        rate_limit_requests: int = 1000,
        rate_limit_window_seconds: int = 3600,
        expires_at: Optional[datetime] = None
    ) -> tuple[str, APIKeyModel]:
        """
        Create a new API key.
        
        Args:
            name: Human-readable name for the key
            created_by: User who created the key
            rate_limit_requests: Max requests in window
            rate_limit_window_seconds: Time window in seconds
            expires_at: Optional expiration datetime
            
        Returns:
            Tuple of (raw_key_string, APIKeyModel)
        """
        # Generate a new key (format: "sk-" + 48 random chars)
        import secrets
        raw_key = f"sk-{secrets.token_urlsafe(36)}"
        key_hash = self.hash_key(raw_key)
        
        # Create model
        api_key = APIKeyModel(
            key_hash=key_hash,
            name=name,
            is_active=True,
            created_by=created_by,
            rate_limit_requests=rate_limit_requests,
            rate_limit_window_seconds=rate_limit_window_seconds,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        
        self.session.add(api_key)
        logger.info(f"Created API key: {name}")
        
        return raw_key, api_key
    
    async def get_by_id(self, key_id: int) -> Optional[APIKeyModel]:
        """
        Get API key by database ID.
        
        Args:
            key_id: Database primary key
            
        Returns:
            APIKeyModel or None if not found
        """
        result = await self.session.execute(
            select(APIKeyModel).where(APIKeyModel.id == key_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_hash(self, key_hash: str) -> Optional[APIKeyModel]:
        """
        Get API key by hash (for authentication).
        
        Args:
            key_hash: Hash of the API key
            
        Returns:
            APIKeyModel or None if not found
        """
        result = await self.session.execute(
            select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
        )
        return result.scalar_one_or_none()
    
    async def authenticate_key(self, raw_key: str) -> Optional[APIKeyModel]:
        """
        Authenticate an API key and update last_used_at.
        
        Args:
            raw_key: Raw API key string from request
            
        Returns:
            APIKeyModel if valid and active, None otherwise
        """
        key_hash = self.hash_key(raw_key)
        result = await self.session.execute(
            select(APIKeyModel).where(
                and_(
                    APIKeyModel.key_hash == key_hash,
                    APIKeyModel.is_active == True
                )
            )
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            logger.warning(f"Authentication failed for key hash: {key_hash[:8]}...")
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            logger.warning(f"Attempted use of expired key: {api_key.name}")
            return None
        
        # Update last used time and request count
        api_key.last_used_at = datetime.utcnow()
        api_key.requests_count = (api_key.requests_count or 0) + 1
        
        logger.debug(f"Authenticated key: {api_key.name} (requests: {api_key.requests_count})")
        
        return api_key
    
    async def list_all(
        self,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[APIKeyModel]:
        """
        List all API keys.
        
        Args:
            active_only: Filter to only active keys
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of APIKeyModel objects
        """
        query = select(APIKeyModel)
        
        if active_only:
            query = query.where(APIKeyModel.is_active == True)
        
        query = query.order_by(desc(APIKeyModel.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def deactivate_key(self, key_id: int) -> bool:
        """
        Deactivate an API key.
        
        Args:
            key_id: Key ID to deactivate
            
        Returns:
            True if deactivated, False if not found
        """
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return False
        
        api_key.is_active = False
        logger.info(f"Deactivated API key: {api_key.name}")
        return True
    
    async def activate_key(self, key_id: int) -> bool:
        """
        Reactivate a deactivated API key.
        
        Args:
            key_id: Key ID to activate
            
        Returns:
            True if activated, False if not found
        """
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return False
        
        api_key.is_active = True
        logger.info(f"Activated API key: {api_key.name}")
        return True
    
    async def delete_key(self, key_id: int) -> bool:
        """
        Delete an API key permanently.
        
        Args:
            key_id: Key ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return False
        
        await self.session.delete(api_key)
        logger.info(f"Deleted API key: {api_key.name}")
        return True
    
    async def update_rate_limit(
        self,
        key_id: int,
        requests: int,
        window_seconds: int
    ) -> bool:
        """
        Update rate limiting for a key.
        
        Args:
            key_id: Key ID to update
            requests: Max requests in window
            window_seconds: Time window in seconds
            
        Returns:
            True if updated, False if not found
        """
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return False
        
        api_key.rate_limit_requests = requests
        api_key.rate_limit_window_seconds = window_seconds
        
        logger.info(
            f"Updated rate limit for {api_key.name}: "
            f"{requests} requests per {window_seconds}s"
        )
        return True
    
    async def extend_expiration(
        self,
        key_id: int,
        days: int = 365
    ) -> bool:
        """
        Extend API key expiration date.
        
        Args:
            key_id: Key ID to extend
            days: Number of days to extend
            
        Returns:
            True if extended, False if not found
        """
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return False
        
        api_key.expires_at = datetime.utcnow() + timedelta(days=days)
        
        logger.info(
            f"Extended expiration for {api_key.name} to {api_key.expires_at}"
        )
        return True
    
    async def count_active(self) -> int:
        """
        Count active API keys.
        
        Returns:
            Count of active keys
        """
        result = await self.session.execute(
            select(func.count(APIKeyModel.id)).where(
                APIKeyModel.is_active == True
            )
        )
        return result.scalar() or 0
    
    async def get_usage_stats(self, key_id: int) -> Optional[Dict[str, Any]]:
        """
        Get usage statistics for an API key.
        
        Args:
            key_id: Key ID
            
        Returns:
            Dictionary with usage stats or None if not found
        """
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return None
        
        return {
            'key_id': api_key.id,
            'name': api_key.name,
            'created_at': api_key.created_at,
            'last_used_at': api_key.last_used_at,
            'requests_count': api_key.requests_count,
            'is_active': api_key.is_active,
            'expires_at': api_key.expires_at,
            'rate_limit': {
                'requests': api_key.rate_limit_requests,
                'window_seconds': api_key.rate_limit_window_seconds
            }
        }
