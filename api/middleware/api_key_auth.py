"""
API key authentication middleware.

Validates API key in X-API-Key header and enforces rate limiting.

Responsibility: Request authentication and rate limiting
"""

import logging
import time
from typing import Optional, Dict
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication and rate limiting."""
    
    # Simple in-memory rate limit store (for single-process deployments)
    # For production, use Redis instead
    _rate_limit_store: Dict[str, Dict[str, float]] = {}
    
    def __init__(self, app, protected_paths: Optional[list[str]] = None):
        """
        Initialize API key middleware.
        
        Args:
            app: FastAPI application
            protected_paths: List of paths requiring API key (default: all /api/ routes)
        """
        super().__init__(app)
        self.protected_paths = protected_paths or ["/api/"]
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and check API key if needed.
        
        Args:
            request: HTTP request
            call_next: Next middleware handler
            
        Returns:
            Response
        """
        # Check if path requires authentication
        if not self._should_protect(request.url.path):
            return await call_next(request)
        
        # Skip authentication for public docs endpoints
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Extract API key from header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning(f"Missing API key for {request.method} {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing X-API-Key header"}
            )
        
        # Validate and authenticate key
        try:
            from src.db.repositories.api_key_repository import APIKeyRepository
            from src.db.session import async_session_factory
            
            async with async_session_factory() as session:
                repo = APIKeyRepository(session)
                api_key_model = await repo.authenticate_key(api_key)
                
                if not api_key_model:
                    logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid or expired API key"}
                    )
                
                # Check rate limit
                rate_limit_result = self._check_rate_limit(api_key_model)
                if not rate_limit_result['allowed']:
                    logger.warning(
                        f"Rate limit exceeded for key: {api_key_model.name} "
                        f"({rate_limit_result['used']}/{rate_limit_result['limit']})"
                    )
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": "Rate limit exceeded",
                            "retry_after": rate_limit_result['retry_after']
                        },
                        headers={
                            "X-RateLimit-Limit": str(rate_limit_result['limit']),
                            "X-RateLimit-Used": str(rate_limit_result['used']),
                            "X-RateLimit-Reset": str(rate_limit_result['reset_at']),
                            "Retry-After": str(rate_limit_result['retry_after'])
                        }
                    )
                
                # Attach API key to request state for use in handlers
                request.state.api_key = api_key_model
                
                # Commit the updated request count
                await session.commit()
        
        except Exception as e:
            logger.error(f"Error authenticating API key: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Authentication service error"}
            )
        
        # Call next handler
        response = await call_next(request)
        
        # Add rate limit headers to response
        if hasattr(request.state, 'api_key'):
            rate_limit_result = self._get_rate_limit_status(request.state.api_key)
            response.headers["X-RateLimit-Limit"] = str(rate_limit_result['limit'])
            response.headers["X-RateLimit-Used"] = str(rate_limit_result['used'])
            response.headers["X-RateLimit-Reset"] = str(rate_limit_result['reset_at'])
        
        return response
    
    def _should_protect(self, path: str) -> bool:
        """
        Check if path should be protected by API key.
        
        Args:
            path: Request path
            
        Returns:
            True if path should be protected
        """
        for protected_path in self.protected_paths:
            if path.startswith(protected_path):
                return True
        return False
    
    def _check_rate_limit(self, api_key_model) -> dict:
        """
        Check if API key has exceeded rate limit.
        
        Args:
            api_key_model: APIKeyModel instance
            
        Returns:
            Dictionary with rate limit status
        """
        key_id = str(api_key_model.id)
        limit = api_key_model.rate_limit_requests
        window = api_key_model.rate_limit_window_seconds
        
        now = time.time()
        
        # Initialize or get rate limit entry
        if key_id not in self._rate_limit_store:
            self._rate_limit_store[key_id] = {
                'count': 1,
                'window_start': now,
                'window_end': now + window
            }
            return {
                'allowed': True,
                'used': 1,
                'limit': limit,
                'reset_at': int(now + window),
                'retry_after': 0
            }
        
        entry = self._rate_limit_store[key_id]
        
        # Check if window has expired
        if now > entry['window_end']:
            # Reset window
            entry['count'] = 1
            entry['window_start'] = now
            entry['window_end'] = now + window
            return {
                'allowed': True,
                'used': 1,
                'limit': limit,
                'reset_at': int(now + window),
                'retry_after': 0
            }
        
        # Check if limit exceeded
        if entry['count'] >= limit:
            retry_after = int(entry['window_end'] - now) + 1
            return {
                'allowed': False,
                'used': entry['count'],
                'limit': limit,
                'reset_at': int(entry['window_end']),
                'retry_after': retry_after
            }
        
        # Increment counter
        entry['count'] += 1
        return {
            'allowed': True,
            'used': entry['count'],
            'limit': limit,
            'reset_at': int(entry['window_end']),
            'retry_after': 0
        }
    
    def _get_rate_limit_status(self, api_key_model) -> dict:
        """
        Get current rate limit status for key.
        
        Args:
            api_key_model: APIKeyModel instance
            
        Returns:
            Dictionary with current status
        """
        key_id = str(api_key_model.id)
        limit = api_key_model.rate_limit_requests
        
        if key_id not in self._rate_limit_store:
            return {
                'used': 0,
                'limit': limit,
                'reset_at': int(time.time() + 3600)
            }
        
        entry = self._rate_limit_store[key_id]
        now = time.time()
        
        if now > entry['window_end']:
            return {
                'used': 0,
                'limit': limit,
                'reset_at': int(now + 3600)
            }
        
        return {
            'used': entry['count'],
            'limit': limit,
            'reset_at': int(entry['window_end'])
        }
