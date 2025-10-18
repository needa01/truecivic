"""
Pydantic schemas for Bill API responses.

Defines response models for bill endpoints.

Responsibility: Bill response schemas
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BillResponse(BaseModel):
    """Basic bill response model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    jurisdiction: str
    parliament: int
    session: int
    number: str
    title_en: str
    title_fr: Optional[str] = None
    short_title_en: Optional[str] = None
    short_title_fr: Optional[str] = None
    sponsor_politician_id: Optional[int] = None
    sponsor_politician_name: Optional[str] = None
    introduced_date: Optional[datetime] = None
    law_status: Optional[str] = None
    royal_assent_date: Optional[datetime] = None
    last_fetched_at: datetime
    created_at: datetime
    updated_at: datetime


class BillDetailResponse(BillResponse):
    """Detailed bill response with all fields."""
    
    legisinfo_id: Optional[int] = None
    legisinfo_status: Optional[str] = None
    legisinfo_summary_en: Optional[str] = None
    legisinfo_summary_fr: Optional[str] = None
    subject_tags: Optional[List[str]] = None
    committee_studies: Optional[List[str]] = None
    royal_assent_chapter: Optional[str] = None
    related_bill_numbers: Optional[List[str]] = None
    source_openparliament: bool
    source_legisinfo: bool
    last_enriched_at: Optional[datetime] = None


class BillListResponse(BaseModel):
    """Paginated list of bills."""
    
    bills: List[BillResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
