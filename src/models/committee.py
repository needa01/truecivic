"""
Committee Pydantic models for API responses.

These models define the shape of data returned by the committee API endpoints.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Committee(BaseModel):
    """Parliamentary committee."""
    natural_id: str = Field(description="Unique identifier for this committee")
    jurisdiction: str = Field(description="Jurisdiction (e.g., ca-federal)")
    parliament: int = Field(description="Parliament number")
    session: int = Field(description="Session number")
    committee_slug: str = Field(description="Jurisdiction-prefixed committee slug (e.g., ca-HUMA)")
    acronym_en: Optional[str] = Field(None, description="English acronym")
    acronym_fr: Optional[str] = Field(None, description="French acronym")
    name_en: Optional[str] = Field(None, description="English name")
    name_fr: Optional[str] = Field(None, description="French name")
    short_name_en: Optional[str] = Field(None, description="English short name")
    short_name_fr: Optional[str] = Field(None, description="French short name")
    chamber: str = Field(description="Chamber (House, Senate, Joint)")
    parent_committee: Optional[str] = Field(None, description="Parent committee slug (for subcommittees)")
    source_url: Optional[str] = Field(None, description="URL to source data")
    created_at: datetime = Field(description="When this record was created")
    updated_at: datetime = Field(description="When this record was last updated")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "natural_id": "ca-federal-44-1-committee-HUMA",
                "jurisdiction": "ca-federal",
                "parliament": 44,
                "session": 1,
                "committee_slug": "ca-HUMA",
                "acronym_en": "HUMA",
                "acronym_fr": "HUMA",
                "name_en": "Standing Committee on Human Resources, Skills and Social Development and the Status of Persons with Disabilities",
                "name_fr": "Comité permanent des ressources humaines, du développement des compétences, du développement social et de la condition des personnes handicapées",
                "short_name_en": "Human Resources Committee",
                "short_name_fr": "Comité des ressources humaines",
                "chamber": "House",
                "parent_committee": None,
                "source_url": "https://api.openparliament.ca/committees/HUMA/",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }


class CommitteeList(BaseModel):
    """Paginated list of committees."""
    committees: List[Committee] = Field(description="List of committees")
    total: int = Field(description="Total number of committees matching the query")
    skip: int = Field(description="Number of records skipped")
    limit: int = Field(description="Maximum number of records returned")
    
    class Config:
        json_schema_extra = {
            "example": {
                "committees": [],
                "total": 45,
                "skip": 0,
                "limit": 100
            }
        }


class CommitteeMeeting(BaseModel):
    """Committee meeting details."""
    id: int = Field(description="Meeting database identifier")
    committee_id: int = Field(description="ID of the committee this meeting belongs to")
    committee_slug: str = Field(description="Jurisdiction-prefixed committee slug")
    meeting_number: int = Field(description="Sequential meeting number within the committee")
    parliament: int = Field(description="Parliament number")
    session: int = Field(description="Session number")
    meeting_date: datetime = Field(description="Meeting date and time")
    time_of_day: Optional[str] = Field(None, description="Time of day (morning, afternoon, etc.)")
    title_en: Optional[str] = Field(None, description="English meeting title")
    title_fr: Optional[str] = Field(None, description="French meeting title")
    meeting_type: Optional[str] = Field(None, description="Meeting type (e.g., Regular, Special)")
    room: Optional[str] = Field(None, description="Meeting room location")
    witnesses: Optional[List[Dict[str, Any]]] = Field(None, description="Witness list metadata")
    documents: Optional[List[Dict[str, Any]]] = Field(None, description="Associated document metadata")
    source_url: Optional[str] = Field(None, description="Source URL for the meeting")
    created_at: datetime = Field(description="When this meeting was created in the system")
    updated_at: datetime = Field(description="When this meeting was last updated in the system")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 123,
                "committee_id": 456,
                "committee_slug": "ca-HUMA",
                "meeting_number": 87,
                "parliament": 44,
                "session": 1,
                "meeting_date": "2025-02-15T14:00:00Z",
                "time_of_day": "Afternoon",
                "title_en": "Human Resources Committee",
                "title_fr": "Comité des ressources humaines",
                "meeting_type": "Regular",
                "room": "Room 237-C, West Block",
                "witnesses": [{"name": "Jane Doe", "organization": "Labour Council"}],
                "documents": [{"title": "Briefing Note", "url": "https://example.com/doc.pdf"}],
                "source_url": "https://api.openparliament.ca/committees/HUMA/meetings/87/",
                "created_at": "2025-02-15T16:30:00Z",
                "updated_at": "2025-02-15T16:35:00Z"
            }
        }


class CommitteeMeetingList(BaseModel):
    """Paginated list of committee meetings for a committee."""
    committee: Committee = Field(description="Committee metadata")
    meetings: List[CommitteeMeeting] = Field(description="List of committee meetings")
    total: int = Field(description="Total number of meetings matching the query")
    skip: int = Field(description="Number of records skipped")
    limit: int = Field(description="Maximum number of records returned")
