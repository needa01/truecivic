"""
Adapter response models.

Defines unified response structures for all data source adapters.
These models ensure consistent error handling, metrics tracking,
and data normalization across different data sources.

Responsibility: Data transfer objects for adapter operations
"""

from datetime import datetime
from enum import Enum
from typing import Generic, TypeVar, Optional, List, Dict, Any

from pydantic import BaseModel, Field


class AdapterStatus(str, Enum):
    """
    Status of an adapter operation.
    
    Used to quickly determine if retry logic or error handling is needed.
    """
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"  # Some records failed, some succeeded
    FAILURE = "failure"
    RATE_LIMITED = "rate_limited"
    SOURCE_UNAVAILABLE = "source_unavailable"


class AdapterError(BaseModel):
    """
    Structured error information from adapter operations.
    
    Captures context needed for debugging, alerting, and retry decisions.
    """
    timestamp: datetime = Field(description="When the error occurred (UTC)")
    error_type: str = Field(description="Exception class name or error category")
    message: str = Field(description="Human-readable error message")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (URL, record ID, etc.)"
    )
    retryable: bool = Field(
        default=False,
        description="Whether this error can be retried"
    )


class AdapterMetrics(BaseModel):
    """
    Operational metrics for adapter execution.
    
    Used for monitoring, alerting, and performance optimization.
    """
    records_attempted: int = Field(
        ge=0,
        description="Total records attempted to fetch/process"
    )
    records_succeeded: int = Field(
        ge=0,
        description="Records successfully fetched and normalized"
    )
    records_failed: int = Field(
        ge=0,
        description="Records that failed during fetch or normalization"
    )
    duration_seconds: float = Field(
        ge=0.0,
        description="Total execution time in seconds"
    )
    rate_limit_hits: int = Field(
        ge=0,
        default=0,
        description="Number of times rate limiter delayed requests"
    )
    retry_count: int = Field(
        ge=0,
        default=0,
        description="Number of retries performed"
    )


T = TypeVar('T')


class AdapterResponse(BaseModel, Generic[T]):
    """
    Unified response wrapper for all adapter operations.
    
    Generic type T represents the normalized data model (e.g., Bill, MP, Vote).
    All adapters return this structure for consistent handling in Dagster assets.
    
    Responsibility: Standard response container with status, data, errors, metrics
    """
    status: AdapterStatus = Field(description="Operation status")
    data: Optional[List[T]] = Field(
        default=None,
        description="List of successfully normalized records"
    )
    errors: List[AdapterError] = Field(
        default_factory=list,
        description="List of errors encountered during operation"
    )
    metrics: AdapterMetrics = Field(description="Operation performance metrics")
    source: str = Field(description="Adapter/source identifier")
    fetch_timestamp: datetime = Field(description="When data was fetched (UTC)")
    cache_until: Optional[datetime] = Field(
        default=None,
        description="When cached data should expire (UTC)"
    )
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
