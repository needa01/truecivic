"""
Debate Pydantic models for API responses.

These models define the shape of data returned by the debate API endpoints.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Speech(BaseModel):
    """Individual speech in a debate."""
    natural_id: str = Field(description="Unique identifier for this speech")
    jurisdiction: str = Field(description="Jurisdiction (e.g., ca-federal)")
    debate_id: str = Field(description="ID of the parent debate")
    politician_id: Optional[int] = Field(None, description="ID of the politician who spoke")
    content_en: Optional[str] = Field(None, description="English content of the speech")
    content_fr: Optional[str] = Field(None, description="French content of the speech")
    speech_time: Optional[datetime] = Field(None, description="Time of the speech")
    speaker_name: Optional[str] = Field(None, description="Name of the speaker")
    speaker_role: Optional[str] = Field(None, description="Role of the speaker")
    sequence: int = Field(description="Sequence order of speech in debate")
    created_at: datetime = Field(description="When this record was created")
    updated_at: datetime = Field(description="When this record was last updated")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "natural_id": "ca-federal-44-1-debate-20240115-speech-1",
                "jurisdiction": "ca-federal",
                "debate_id": "ca-federal-44-1-debate-20240115",
                "politician_id": 456,
                "content_en": "Mr. Speaker, I rise today to speak about...",
                "content_fr": "Monsieur le Président, je prends la parole aujourd'hui pour parler de...",
                "speech_time": "2024-01-15T14:35:00Z",
                "speaker_name": "John Doe",
                "speaker_role": "Member of Parliament",
                "sequence": 1,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class Debate(BaseModel):
    """Parliamentary debate/Hansard session."""
    natural_id: str = Field(description="Unique identifier for this debate")
    jurisdiction: str = Field(description="Jurisdiction (e.g., ca-federal)")
    parliament: int = Field(description="Parliament number")
    session: int = Field(description="Session number")
    debate_number: str = Field(description="Debate number/identifier")
    chamber: str = Field(description="Chamber where debate occurred (House, Senate)")
    debate_date: Optional[datetime] = Field(None, description="Date of the debate")
    topic_en: Optional[str] = Field(None, description="English topic/title")
    topic_fr: Optional[str] = Field(None, description="French topic/title")
    debate_type: str = Field(description="Type of debate (Question Period, Main Estimates, etc.)")
    source_url: Optional[str] = Field(None, description="URL to source data")
    created_at: datetime = Field(description="When this record was created")
    updated_at: datetime = Field(description="When this record was last updated")
    
    # Optional related data
    speeches: List[Speech] = Field(default_factory=list, description="Individual speeches in this debate")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "natural_id": "ca-federal-44-1-debate-20240115",
                "jurisdiction": "ca-federal",
                "parliament": 44,
                "session": 1,
                "debate_number": "20240115",
                "chamber": "House",
                "debate_date": "2024-01-15T14:00:00Z",
                "topic_en": "Government Orders",
                "topic_fr": "Ordres émanant du gouvernement",
                "debate_type": "Main Estimates",
                "source_url": "https://api.openparliament.ca/debates/44-1/2024-01-15/",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "speeches": []
            }
        }


class DebateList(BaseModel):
    """Paginated list of debates."""
    debates: List[Debate] = Field(description="List of debates")
    total: int = Field(description="Total number of debates matching the query")
    skip: int = Field(description="Number of records skipped")
    limit: int = Field(description="Maximum number of records returned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "debates": [],
                "total": 250,
                "skip": 0,
                "limit": 100
            }
        }
