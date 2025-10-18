"""
Vote Pydantic models for API responses.

These models define the shape of data returned by the vote API endpoints.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class VoteRecord(BaseModel):
    """Individual MP voting record."""
    natural_id: str = Field(description="Unique identifier for this vote record")
    jurisdiction: str = Field(description="Jurisdiction (e.g., ca-federal)")
    vote_id: str = Field(description="ID of the parent vote")
    politician_id: int = Field(description="ID of the politician who voted")
    vote_position: str = Field(description="Vote position: Yea, Nay, or Paired")
    created_at: datetime = Field(description="When this record was created")
    updated_at: datetime = Field(description="When this record was last updated")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "natural_id": "ca-federal-44-1-vote-123-456",
                "jurisdiction": "ca-federal",
                "vote_id": "ca-federal-44-1-vote-123",
                "politician_id": 456,
                "vote_position": "Yea",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class Vote(BaseModel):
    """Parliamentary vote."""
    natural_id: str = Field(description="Unique identifier for this vote")
    jurisdiction: str = Field(description="Jurisdiction (e.g., ca-federal)")
    parliament: int = Field(description="Parliament number")
    session: int = Field(description="Session number")
    vote_number: int = Field(description="Vote number within the session")
    chamber: str = Field(description="Chamber where vote occurred (House, Senate)")
    vote_date: Optional[datetime] = Field(None, description="Date of the vote")
    vote_description_en: Optional[str] = Field(None, description="English description of the vote")
    vote_description_fr: Optional[str] = Field(None, description="French description of the vote")
    bill_number: Optional[str] = Field(None, description="Associated bill number")
    result: str = Field(description="Vote result (Passed, Failed, etc.)")
    yeas: int = Field(description="Number of yea votes")
    nays: int = Field(description="Number of nay votes")
    abstentions: int = Field(description="Number of abstentions/paired votes")
    source_url: Optional[str] = Field(None, description="URL to source data")
    created_at: datetime = Field(description="When this record was created")
    updated_at: datetime = Field(description="When this record was last updated")
    
    # Optional related data
    vote_records: List[VoteRecord] = Field(default_factory=list, description="Individual voting records")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "natural_id": "ca-federal-44-1-vote-123",
                "jurisdiction": "ca-federal",
                "parliament": 44,
                "session": 1,
                "vote_number": 123,
                "chamber": "House",
                "vote_date": "2024-01-15T14:30:00Z",
                "vote_description_en": "Bill C-10, An Act to amend...",
                "vote_description_fr": "Projet de loi C-10, Loi modifiant...",
                "bill_number": "C-10",
                "result": "Passed",
                "yeas": 180,
                "nays": 145,
                "abstentions": 3,
                "source_url": "https://api.openparliament.ca/votes/44-1/123/",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "vote_records": []
            }
        }


class VoteList(BaseModel):
    """Paginated list of votes."""
    votes: List[Vote] = Field(description="List of votes")
    total: int = Field(description="Total number of votes matching the query")
    skip: int = Field(description="Number of records skipped")
    limit: int = Field(description="Maximum number of records returned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "votes": [],
                "total": 450,
                "skip": 0,
                "limit": 100
            }
        }
