"""
Utilities package for Parliament Explorer.

This package contains reusable utility classes for:
- Rate limiting
- Retry logic
- Logging helpers
"""

from .rate_limiter import RateLimiter
from .retry import (
    retry_async,
    with_retry,
    calculate_backoff,
    is_retryable_error,
    RetryError,
)
from .hash_utils import (
    calculate_hash,
    compute_bill_hash,
    deduplicate_by_hash,
)
from .dedupe import dedupe_by_key

__all__ = [
    "RateLimiter",
    "retry_async",
    "with_retry",
    "calculate_backoff",
    "is_retryable_error",
    "RetryError",
    "calculate_hash",
    "compute_bill_hash",
    "deduplicate_by_hash",
    "dedupe_by_key",
]
