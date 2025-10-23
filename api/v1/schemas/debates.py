"""
Debate API response schemas.

Pydantic models for debate endpoint responses.

Responsibility: API v1 debate response schemas
"""

from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class SpeechResponse(BaseModel):
    """Individual speech in debate."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    debate_id: int
    politician_id: Optional[int] = None
    sequence: int
    speaker_name: Optional[str] = None
    speaker_display_name: Optional[str] = None
    speaker_role: Optional[str] = None
    text_content: Optional[str] = None
    language: Optional[str] = None
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DebateResponse(BaseModel):
    """Basic debate information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    jurisdiction: str
    hansard_id: str
    parliament: Optional[int] = None
    session: Optional[int] = None
    sitting_date: Optional[date] = None
    chamber: Optional[str] = None
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DebateListResponse(BaseModel):
    """Paginated debate list response."""
    
    debates: List[DebateResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
