"""
Retry logic with exponential backoff for resilient API calls.

Handles transient failures with configurable retry strategies,
exponential backoff, and jitter to prevent thundering herd.

Responsibility: Provide retry decorators and utilities for network operations
"""

import asyncio
import random
from typing import TypeVar, Callable, Optional, Type, Tuple
from functools import wraps
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryError(Exception):
    """Raised when all retry attempts are exhausted"""
    
    def __init__(self, message: str, last_exception: Optional[Exception] = None):
        super().__init__(message)
        self.last_exception = last_exception


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> float:
    """
    Calculate backoff delay for retry attempt.
    
    Uses exponential backoff with optional jitter to prevent thundering herd.
    Formula: min(max_delay, base_delay * (exponential_base ** attempt))
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential calculation (usually 2.0)
        jitter: Add randomization to prevent synchronized retries
    
    Returns:
        Delay in seconds for this attempt
    
    Example:
        >>> calculate_backoff(0)  # ~1.0s
        >>> calculate_backoff(1)  # ~2.0s
        >>> calculate_backoff(2)  # ~4.0s
        >>> calculate_backoff(3)  # ~8.0s
    """
    # Calculate exponential delay
    delay = base_delay * (exponential_base ** attempt)
    
    # Cap at max_delay
    delay = min(delay, max_delay)
    
    # Add jitter: randomize between 0.5x and 1.0x of calculated delay
    if jitter:
        delay = delay * (0.5 + random.random() * 0.5)
    
    return delay


def is_retryable_error(
    exception: Exception,
    retryable_exceptions: Tuple[Type[Exception], ...] = ()
) -> bool:
    """
    Determine if an exception should trigger a retry.
    
    Args:
        exception: Exception that was raised
        retryable_exceptions: Tuple of exception types that are retryable
    
    Returns:
        True if exception is retryable, False otherwise
    
    Default retryable conditions:
        - Network timeouts
        - HTTP 5xx errors
        - HTTP 429 (rate limit)
        - Connection errors
    """
    # Check if exception is in user-specified retryable types
    if retryable_exceptions and isinstance(exception, retryable_exceptions):
        return True
    
    # Check for common retryable HTTP errors (if httpx is available)
    try:
        import httpx
        
        if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
            return True
        
        if isinstance(exception, httpx.HTTPStatusError):
            # Retry on server errors (5xx) and rate limits (429)
            status_code = exception.response.status_code
            return status_code >= 500 or status_code == 429
    except ImportError:
        pass
    
    return False


async def retry_async(
    func: Callable[..., T],
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (),
    logger_instance: Optional[logging.Logger] = None
) -> T:
    """
    Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        max_attempts: Maximum retry attempts (1 = no retries)
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff
        jitter: Add randomization to delays
        retryable_exceptions: Additional exception types to retry
        logger_instance: Logger to use (defaults to module logger)
    
    Returns:
        Result of successful function call
    
    Raises:
        RetryError: If all attempts are exhausted
    
    Example:
        async def fetch_data():
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.example.com/data")
                response.raise_for_status()
                return response.json()
        
        data = await retry_async(fetch_data, max_attempts=3)
    """
    log = logger_instance or logger
    last_exception: Optional[Exception] = None
    
    for attempt in range(max_attempts):
        try:
            # Attempt the function call
            result = await func()
            
            # Success - return result
            if attempt > 0:
                log.info(f"Succeeded after {attempt + 1} attempts")
            
            return result
        
        except Exception as e:
            last_exception = e
            
            # Check if we should retry
            if not is_retryable_error(e, retryable_exceptions):
                log.warning(f"Non-retryable error: {e}")
                raise
            
            # Check if we have attempts left
            if attempt + 1 >= max_attempts:
                log.error(
                    f"All {max_attempts} retry attempts exhausted. "
                    f"Last error: {e}"
                )
                raise RetryError(
                    f"Failed after {max_attempts} attempts",
                    last_exception=e
                )
            
            # Calculate backoff delay
            delay = calculate_backoff(
                attempt=attempt,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter
            )
            
            log.warning(
                f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            # Wait before retry
            await asyncio.sleep(delay)
    
    # Should never reach here, but for type safety
    raise RetryError(
        f"Failed after {max_attempts} attempts",
        last_exception=last_exception
    )


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = ()
):
    """
    Decorator to add retry logic to async functions.
    
    Args:
        max_attempts: Maximum retry attempts (1 = no retries)
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff
        jitter: Add randomization to delays
        retryable_exceptions: Additional exception types to retry
    
    Example:
        @with_retry(max_attempts=3, base_delay=1.0)
        async def fetch_bills(parliament: int):
            async with httpx.AsyncClient() as client:
                response = await client.get(f"/bills/{parliament}")
                response.raise_for_status()
                return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async def call():
                return await func(*args, **kwargs)
            
            return await retry_async(
                call,
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                retryable_exceptions=retryable_exceptions,
                logger_instance=logging.getLogger(func.__module__)
            )
        
        return wrapper
    
    return decorator
