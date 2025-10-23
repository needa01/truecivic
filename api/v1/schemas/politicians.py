"""
Politician API response schemas.

Pydantic models for politician endpoint responses.

Responsibility: API v1 politician response schemas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PoliticianResponse(BaseModel):
    """Basic politician information."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    jurisdiction: str
    politician_id: str
    name: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    other_names: Optional[Dict[str, Any]] = None
    current_party: Optional[str] = None
    current_riding: Optional[str] = None
    gender: Optional[str] = None
    photo_url: Optional[str] = None
    memberships: Optional[List[Dict[str, Any]]] = None
    source_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PoliticianListResponse(BaseModel):
    """Paginated politician list response."""
    
    politicians: List[PoliticianResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
