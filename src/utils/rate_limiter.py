"""
Rate limiter using token bucket algorithm.

Ensures respectful rate limiting for external APIs and scrapers.
Prevents overwhelming government servers and getting blocked.

Responsibility: Token bucket rate limiting for adapter requests
"""

import asyncio
import time
from typing import Optional


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.
    
    The token bucket algorithm allows for burst traffic while maintaining
    an average rate limit. Tokens are added at a constant rate, and each
    request consumes one token.
    
    Example:
        limiter = RateLimiter(rate=2.0, burst=5)
        await limiter.acquire()  # Blocks until token available
    """
    
    def __init__(self, rate: float, burst: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            rate: Requests per second (e.g., 2.0 = 2 req/sec)
            burst: Maximum burst size (tokens in bucket at full capacity)
        """
        if rate <= 0:
            raise ValueError("Rate must be positive")
        if burst < 1:
            raise ValueError("Burst must be at least 1")
        
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)  # Start with full bucket
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """
        Acquire a token, blocking until one is available.
        
        This method will:
        1. Refill tokens based on time elapsed since last update
        2. If no tokens available, wait for the next token
        3. Consume one token and return
        """
        async with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # Refill tokens based on elapsed time
            # Add (elapsed * rate) tokens, capped at burst capacity
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            # If we don't have a token, wait for one
            if self.tokens < 1:
                # Calculate how long to wait for next token
                wait_time = (1 - self.tokens) / self.rate
                await asyncio.sleep(wait_time)
                
                # After waiting, we have consumed the wait time
                # Update state to reflect we now have the token
                self.tokens = 0
                self.last_update = time.monotonic()
            else:
                # We have tokens, consume one
                self.tokens -= 1
    
    def get_current_tokens(self) -> float:
        """
        Get current number of tokens in bucket (for monitoring).
        
        Note: This doesn't acquire the lock, so it's approximate.
        """
        now = time.monotonic()
        elapsed = now - self.last_update
        current_tokens = min(self.burst, self.tokens + elapsed * self.rate)
        return current_tokens
    
    def reset(self) -> None:
        """
        Reset the rate limiter to full capacity.
        
        Useful for testing or after long idle periods.
        """
        self.tokens = float(self.burst)
        self.last_update = time.monotonic()
