"""
Base adapter interface for all data sources.

Defines the contract that all adapters (OpenParliament, LEGISinfo, etc.)
must implement. Ensures consistent error handling, rate limiting, and
response format across all data sources.

Responsibility: Abstract base class defining adapter contract
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generic, TypeVar, Any, Optional
import logging

from ..models.adapter_models import (
    AdapterResponse,
    AdapterStatus,
    AdapterError,
    AdapterMetrics,
)
from ..utils.rate_limiter import RateLimiter


# Generic type for normalized data models
T = TypeVar('T')


class BaseAdapter(ABC, Generic[T]):
    """
    Abstract base class for all data source adapters.
    
    Every adapter MUST:
    1. Implement fetch() method to retrieve data
    2. Implement normalize() method to convert raw data to domain models
    3. Handle rate limiting internally using self.rate_limiter
    4. Return AdapterResponse with normalized data or errors
    5. Log all operations for observability
    
    Subclasses should NOT:
    - Directly raise exceptions from fetch() (catch and return in AdapterResponse)
    - Make synchronous blocking calls (use async/await)
    - Store state between fetch() calls (each call should be independent)
    """
    
    def __init__(
        self,
        source_name: str,
        rate_limit_per_second: float = 0.5,
        max_retries: int = 3,
        timeout_seconds: int = 30
    ):
        """
        Initialize base adapter.
        
        Args:
            source_name: Identifier for this adapter (e.g., "openparliament")
            rate_limit_per_second: Maximum requests per second
            max_retries: Maximum retry attempts for retryable errors
            timeout_seconds: Request timeout in seconds
        """
        self.source_name = source_name
        self.rate_limit_per_second = rate_limit_per_second
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        
        # Initialize rate limiter
        # burst=1 means no bursting, strict rate limiting
        self.rate_limiter = RateLimiter(
            rate=rate_limit_per_second,
            burst=1
        )
        
        # Set up logger
        self.logger = logging.getLogger(f"adapter.{source_name}")
    
    @abstractmethod
    async def fetch(self, **kwargs: Any) -> AdapterResponse[T]:
        """
        Fetch data from the source.
        
        This method must:
        1. Validate input parameters
        2. Apply rate limiting using self.rate_limiter.acquire()
        3. Make HTTP requests or scrape pages
        4. Normalize raw data using self.normalize()
        5. Build and return AdapterResponse with status, data, errors, metrics
        
        Args:
            **kwargs: Source-specific parameters (e.g., parliament, session, limit)
        
        Returns:
            AdapterResponse containing normalized records, errors, and metrics
        """
        pass
    
    @abstractmethod
    def normalize(self, raw_data: Any) -> T:
        """
        Normalize raw source data into unified domain model.
        
        This method should:
        1. Extract relevant fields from raw response
        2. Convert types (strings to dates, IDs, etc.)
        3. Handle missing/null values with appropriate defaults
        4. Return instance of domain model (e.g., Bill)
        
        Args:
            raw_data: Raw response from source (JSON dict, HTML soup, etc.)
        
        Returns:
            Normalized domain model instance
        
        Raises:
            ValueError: If raw_data cannot be normalized (caught by fetch())
        """
        pass
    
    def _build_success_response(
        self,
        data: list[T],
        errors: list[AdapterError],
        start_time: datetime,
        cache_ttl_seconds: Optional[int] = None
    ) -> AdapterResponse[T]:
        """
        Build a successful AdapterResponse.
        
        Helper method to construct response with calculated metrics.
        """
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        # Determine status
        if not errors:
            status = AdapterStatus.SUCCESS
        else:
            status = AdapterStatus.PARTIAL_SUCCESS
        
        # Calculate cache expiry
        cache_until = None
        if cache_ttl_seconds:
            from datetime import timedelta
            cache_until = end_time + timedelta(seconds=cache_ttl_seconds)
        
        return AdapterResponse(
            status=status,
            data=data,
            errors=errors,
            metrics=AdapterMetrics(
                records_attempted=len(data) + len(errors),
                records_succeeded=len(data),
                records_failed=len(errors),
                duration_seconds=duration,
                rate_limit_hits=0,  # TODO: Track this in rate_limiter
                retry_count=0  # TODO: Track this in retry logic
            ),
            source=self.source_name,
            fetch_timestamp=end_time,
            cache_until=cache_until
        )
    
    def _build_failure_response(
        self,
        error: Exception,
        start_time: datetime,
        retryable: bool = False
    ) -> AdapterResponse[T]:
        """
        Build a failed AdapterResponse.
        
        Used when entire fetch operation fails (source unavailable, etc.)
        """
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        return AdapterResponse(
            status=AdapterStatus.SOURCE_UNAVAILABLE if retryable else AdapterStatus.FAILURE,
            data=None,
            errors=[AdapterError(
                timestamp=end_time,
                error_type=type(error).__name__,
                message=str(error),
                context={"adapter": self.source_name},
                retryable=retryable
            )],
            metrics=AdapterMetrics(
                records_attempted=0,
                records_succeeded=0,
                records_failed=0,
                duration_seconds=duration,
                rate_limit_hits=0,
                retry_count=0
            ),
            source=self.source_name,
            fetch_timestamp=end_time
        )
