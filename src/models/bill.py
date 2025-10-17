"""
Bill domain model.

Represents a legislative bill from Canadian Parliament.
Normalized across multiple sources (OpenParliament, LEGISinfo).

Responsibility: Single bill entity with all fields from primary + enrichment sources
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class Bill(BaseModel):
    """
    Unified bill model combining OpenParliament + LEGISinfo data.
    
    Natural key: (jurisdiction, parliament, session, number)
    Example: ("ca-federal", 44, 1, "C-15")
    """
    
    # MARK: - Natural Key Fields
    jurisdiction: str = Field(
        description="Jurisdiction code (e.g., 'ca-federal', 'ca-ontario')"
    )
    parliament: int = Field(
        ge=1,
        description="Parliament number (e.g., 44 for 44th Parliament)"
    )
    session: int = Field(
        ge=1,
        description="Session number within parliament (e.g., 1 for 1st session)"
    )
    number: str = Field(
        description="Bill number (e.g., 'C-15', 'S-3')",
        max_length=20
    )
    
    # MARK: - Core Fields (from OpenParliament)
    title_en: str = Field(description="Full bill title in English")
    title_fr: Optional[str] = Field(
        default=None,
        description="Full bill title in French"
    )
    short_title_en: Optional[str] = Field(
        default=None,
        description="Short title in English"
    )
    short_title_fr: Optional[str] = Field(
        default=None,
        description="Short title in French"
    )
    
    sponsor_politician_id: Optional[int] = Field(
        default=None,
        description="OpenParliament politician ID of sponsor"
    )
    
    introduced_date: Optional[datetime] = Field(
        default=None,
        description="Date bill was introduced (first reading)"
    )
    
    law_status: Optional[str] = Field(
        default=None,
        description="Law status if passed (e.g., 'Statute of Canada 2023 c. 15')"
    )
    
    # MARK: - Enrichment Fields (from LEGISinfo)
    legisinfo_id: Optional[int] = Field(
        default=None,
        description="LEGISinfo bill ID for cross-referencing"
    )
    
    subject_tags: List[str] = Field(
        default_factory=list,
        description="Subject classification tags from LEGISinfo"
    )
    
    committee_studies: List[str] = Field(
        default_factory=list,
        description="Committee acronyms that studied this bill (e.g., ['HUMA', 'FINA'])"
    )
    
    royal_assent_date: Optional[datetime] = Field(
        default=None,
        description="Date of Royal Assent (when bill became law)"
    )
    
    royal_assent_chapter: Optional[str] = Field(
        default=None,
        description="Chapter number when bill received Royal Assent"
    )
    
    related_bill_numbers: List[str] = Field(
        default_factory=list,
        description="Related or predecessor bill numbers"
    )
    
    # MARK: - Metadata
    source_openparliament: bool = Field(
        default=False,
        description="Whether data was fetched from OpenParliament"
    )
    source_legisinfo: bool = Field(
        default=False,
        description="Whether data was enriched from LEGISinfo"
    )
    
    last_fetched_at: Optional[datetime] = Field(
        default=None,
        description="When this record was last fetched from OpenParliament"
    )
    last_enriched_at: Optional[datetime] = Field(
        default=None,
        description="When this record was last enriched from LEGISinfo"
    )
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
    
    def natural_key(self) -> tuple:
        """
        Return natural key tuple for this bill.
        
        Used for deduplication and upsert logic in database.
        """
        return (self.jurisdiction, self.parliament, self.session, self.number)
    
    def is_government_bill(self) -> bool:
        """Check if this is a government bill (C-prefix)"""
        return self.number.upper().startswith('C-')
    
    def is_senate_bill(self) -> bool:
        """Check if this is a Senate bill (S-prefix)"""
        return self.number.upper().startswith('S-')
    
    def is_private_members_bill(self) -> bool:
        """Check if this is a private member's bill (higher C/S number)"""
        if self.is_government_bill():
            # Government bills: C-1 to C-200
            # Private member's bills: C-201+
            try:
                num = int(self.number.upper().replace('C-', ''))
                return num > 200
            except ValueError:
                return False
        return False
