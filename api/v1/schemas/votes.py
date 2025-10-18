"""
Vote API response schemas.

Pydantic models for vote endpoint responses.

Responsibility: API v1 vote response schemas
"""

from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class VoteRecordResponse(BaseModel):
    """Individual MP vote record."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    politician_id: int
    ballot: str  # Yea, Nay, Paired
    politician_name: Optional[str] = None


class VoteResponse(BaseModel):
    """Basic vote information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    jurisdiction: str
    vote_id: str
    parliament: int
    session: int
    number: int
    bill_id: Optional[int] = None
    vote_date: Optional[date] = None
    result: Optional[str] = None
    yea_count: Optional[int] = None
    nay_count: Optional[int] = None
    paired_count: Optional[int] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class VoteDetailResponse(VoteResponse):
    """Detailed vote information with individual MP votes."""
    
    vote_records: List[VoteRecordResponse] = []
    
    @classmethod
    def from_orm_with_records(cls, vote, vote_records):
        """Create response with vote records."""
        vote_dict = {
            "id": vote.id,
            "jurisdiction": vote.jurisdiction,
            "vote_id": vote.vote_id,
            "parliament": vote.parliament,
            "session": vote.session,
            "number": vote.number,
            "bill_id": vote.bill_id,
            "vote_date": vote.vote_date,
            "result": vote.result,
            "yea_count": vote.yea_count,
            "nay_count": vote.nay_count,
            "paired_count": vote.paired_count,
            "description": vote.description,
            "source_url": vote.source_url,
            "created_at": vote.created_at,
            "updated_at": vote.updated_at,
            "vote_records": [VoteRecordResponse.from_orm(r) for r in vote_records]
        }
        return cls(**vote_dict)


class VoteListResponse(BaseModel):
    """Paginated vote list response."""
    
    votes: List[VoteResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
