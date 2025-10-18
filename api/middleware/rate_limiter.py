"""
Rate Limiting Middleware
=========================
Redis-based rate limiter with per-IP and per-endpoint limits.

Features:
    - Anonymous user limits: 600 req/day per IP
    - Burst limits: 60 req/min per IP
    - Per-endpoint limits (entity detail, graph, search, feeds)
    - 429 Too Many Requests with Retry-After header
    - Redis backend with fallback to in-memory

Limits:
    - Anonymous: 600 req/day, 60 req/min
    - Entity detail: 120 req/hour
    - Graph: 60 req/hour
    - Search: 120 req/hour
    - Feeds: 60 req/hour
"""

from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis.asyncio as aioredis
import hashlib
import time
import logging

logger = logging.getLogger(__name__)


class RateLimitConfig:
    """Rate limit configuration for different endpoint types"""
    
    # Global limits (per IP)
    ANONYMOUS_DAILY = 600  # 600 requests per day
    ANONYMOUS_BURST = 60   # 60 requests per minute
    
    # Per-endpoint limits (per IP per endpoint type)
    ENTITY_DETAIL_HOURLY = 120  # /bills/{id}, /politicians/{id}, etc.
    GRAPH_HOURLY = 60           # /graph/*
    SEARCH_HOURLY = 120         # /search/*
    FEEDS_HOURLY = 60           # /feeds/*
    
    # Time windows
    DAILY_WINDOW = 86400    # 24 hours in seconds
    HOURLY_WINDOW = 3600    # 1 hour in seconds
    MINUTE_WINDOW = 60      # 1 minute in seconds


class InMemoryRateLimiter:
    """
    Fallback in-memory rate limiter when Redis is unavailable.
    
    Not recommended for production with multiple workers.
    Use Redis for proper distributed rate limiting.
    """
    
    def __init__(self):
        self.storage: Dict[str, Dict[str, any]] = {}
        self.cleanup_interval = 300  # Clean up every 5 minutes
        self.last_cleanup = time.time()
    
    async def increment(self, key: str, window: int) -> int:
        """Increment counter for key within time window"""
        now = time.time()
        
        # Periodic cleanup
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()
        
        if key not in self.storage:
            self.storage[key] = {
                "count": 0,
                "expires_at": now + window
            }
        
        entry = self.storage[key]
        
        # Reset if expired
        if now > entry["expires_at"]:
            entry["count"] = 0
            entry["expires_at"] = now + window
        
        entry["count"] += 1
        return entry["count"]
    
    async def get_ttl(self, key: str) -> int:
        """Get TTL for key in seconds"""
        if key not in self.storage:
            return 0
        
        now = time.time()
        expires_at = self.storage[key]["expires_at"]
        ttl = int(expires_at - now)
        return max(0, ttl)
    
    def _cleanup(self):
        """Remove expired entries"""
        now = time.time()
        expired_keys = [
            key for key, entry in self.storage.items()
            if now > entry["expires_at"]
        ]
        for key in expired_keys:
            del self.storage[key]
        
        self.last_cleanup = now
        logger.info(f"In-memory rate limiter cleanup: removed {len(expired_keys)} expired entries")


class RedisRateLimiter:
    """Redis-based distributed rate limiter"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5
            )
            await self.redis.ping()
            logger.info("Connected to Redis for rate limiting")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
    
    async def increment(self, key: str, window: int) -> int:
        """Increment counter for key within time window"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        
        return results[0]  # Count after increment
    
    async def get_ttl(self, key: str) -> int:
        """Get TTL for key in seconds"""
        if not self.redis:
            raise RuntimeError("Redis not connected")
        
        ttl = await self.redis.ttl(key)
        return max(0, ttl)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Checks rate limits before processing requests.
    Returns 429 Too Many Requests with Retry-After header when limit exceeded.
    """
    
    def __init__(self, app, redis_url: Optional[str] = None):
        super().__init__(app)
        self.redis_url = redis_url
        self.redis_limiter: Optional[RedisRateLimiter] = None
        self.memory_limiter = InMemoryRateLimiter()
        self.use_redis = False
    
    async def startup(self):
        """Initialize rate limiter on startup"""
        if self.redis_url:
            self.redis_limiter = RedisRateLimiter(self.redis_url)
            try:
                await self.redis_limiter.connect()
                self.use_redis = True
                logger.info("Rate limiter using Redis backend")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
                self.use_redis = False
        else:
            logger.info("Rate limiter using in-memory backend (not recommended for production)")
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        if self.redis_limiter:
            await self.redis_limiter.disconnect()
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check X-Forwarded-For header (from proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP if multiple
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _hash_ip(self, ip: str) -> str:
        """Hash IP for privacy"""
        return hashlib.sha256(ip.encode()).hexdigest()[:16]
    
    def _get_endpoint_type(self, path: str) -> Optional[str]:
        """Determine endpoint type from path"""
        if "/graph" in path:
            return "graph"
        elif "/search" in path:
            return "search"
        elif "/feeds" in path:
            return "feeds"
        elif any(entity in path for entity in ["/bills/", "/politicians/", "/votes/", "/debates/", "/committees/"]):
            # Detail endpoint (has ID in path)
            return "entity_detail"
        
        return None
    
    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if path should skip rate limiting"""
        # Skip rate limiting for:
        # - Root endpoint
        # - Health checks
        # - OpenAPI docs
        # - Static files
        skip_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    async def _check_limit(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, int, int]:
        """
        Check if limit exceeded.
        
        Returns:
            (allowed, current_count, ttl)
        """
        try:
            if self.use_redis and self.redis_limiter:
                count = await self.redis_limiter.increment(key, window)
                ttl = await self.redis_limiter.get_ttl(key)
            else:
                count = await self.memory_limiter.increment(key, window)
                ttl = await self.memory_limiter.get_ttl(key)
            
            allowed = count <= limit
            return (allowed, count, ttl)
        
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open (allow request) on errors
            return (True, 0, 0)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        ip_hash = self._hash_ip(client_ip)
        
        # Check global limits first
        # 1. Daily limit
        daily_key = f"rl:daily:{ip_hash}"
        daily_allowed, daily_count, daily_ttl = await self._check_limit(
            daily_key,
            RateLimitConfig.ANONYMOUS_DAILY,
            RateLimitConfig.DAILY_WINDOW
        )
        
        if not daily_allowed:
            return self._rate_limit_response(
                "Daily limit exceeded",
                RateLimitConfig.ANONYMOUS_DAILY,
                daily_count,
                daily_ttl
            )
        
        # 2. Burst limit (per minute)
        burst_key = f"rl:burst:{ip_hash}"
        burst_allowed, burst_count, burst_ttl = await self._check_limit(
            burst_key,
            RateLimitConfig.ANONYMOUS_BURST,
            RateLimitConfig.MINUTE_WINDOW
        )
        
        if not burst_allowed:
            return self._rate_limit_response(
                "Burst limit exceeded (too many requests per minute)",
                RateLimitConfig.ANONYMOUS_BURST,
                burst_count,
                burst_ttl
            )
        
        # Check per-endpoint limits
        endpoint_type = self._get_endpoint_type(request.url.path)
        
        if endpoint_type:
            # Determine limit and window based on endpoint type
            if endpoint_type == "entity_detail":
                limit = RateLimitConfig.ENTITY_DETAIL_HOURLY
            elif endpoint_type == "graph":
                limit = RateLimitConfig.GRAPH_HOURLY
            elif endpoint_type == "search":
                limit = RateLimitConfig.SEARCH_HOURLY
            elif endpoint_type == "feeds":
                limit = RateLimitConfig.FEEDS_HOURLY
            else:
                limit = None
            
            if limit:
                endpoint_key = f"rl:endpoint:{endpoint_type}:{ip_hash}"
                endpoint_allowed, endpoint_count, endpoint_ttl = await self._check_limit(
                    endpoint_key,
                    limit,
                    RateLimitConfig.HOURLY_WINDOW
                )
                
                if not endpoint_allowed:
                    return self._rate_limit_response(
                        f"{endpoint_type.replace('_', ' ').title()} limit exceeded",
                        limit,
                        endpoint_count,
                        endpoint_ttl
                    )
        
        # All checks passed, process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Daily-Limit"] = str(RateLimitConfig.ANONYMOUS_DAILY)
        response.headers["X-RateLimit-Daily-Remaining"] = str(max(0, RateLimitConfig.ANONYMOUS_DAILY - daily_count))
        response.headers["X-RateLimit-Burst-Limit"] = str(RateLimitConfig.ANONYMOUS_BURST)
        response.headers["X-RateLimit-Burst-Remaining"] = str(max(0, RateLimitConfig.ANONYMOUS_BURST - burst_count))
        
        return response
    
    def _rate_limit_response(
        self,
        message: str,
        limit: int,
        current: int,
        retry_after: int
    ) -> JSONResponse:
        """Return 429 Too Many Requests response"""
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "rate_limit_exceeded",
                "message": message,
                "limit": limit,
                "current": current,
                "retry_after_seconds": retry_after
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + retry_after)
            }
        )
