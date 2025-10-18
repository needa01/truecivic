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


# Data transfer objects for specific entity types

from dataclasses import dataclass, field


@dataclass
class VoteRecordData:
    """Individual MP vote record."""
    politician_id: int
    vote_position: str  # "Yea", "Nay", "Paired"


@dataclass
class VoteData:
    """Parliamentary vote data."""
    vote_id: str
    parliament: int
    session: int
    vote_number: int
    chamber: str
    vote_date: Optional[datetime]
    vote_description_en: Optional[str]
    vote_description_fr: Optional[str]
    bill_number: Optional[str]
    result: str
    yeas: int
    nays: int
    abstentions: int
    vote_records: List['VoteRecordData'] = field(default_factory=list)


@dataclass
class SpeechData:
    """Individual speech in a debate."""
    speech_id: str
    politician_id: Optional[int]
    content_en: Optional[str]
    content_fr: Optional[str]
    speech_time: Optional[datetime]
    speaker_name: Optional[str]
    speaker_role: Optional[str]
    sequence: int = 0


@dataclass
class DebateData:
    """Parliamentary debate/Hansard data."""
    debate_id: str
    parliament: int
    session: int
    debate_number: str
    chamber: str
    debate_date: Optional[datetime]
    topic_en: Optional[str]
    topic_fr: Optional[str]
    debate_type: str
    speeches: List['SpeechData'] = field(default_factory=list)


@dataclass
class CommitteeData:
    """Parliamentary committee data."""
    committee_id: str
    parliament: int
    session: int
    committee_slug: str
    acronym_en: Optional[str]
    acronym_fr: Optional[str]
    name_en: Optional[str]
    name_fr: Optional[str]
    short_name_en: Optional[str]
    short_name_fr: Optional[str]
    chamber: str
    source_slug: Optional[str] = None
    parent_committee: Optional[str] = None
