"""
SQLAlchemy database models for Parliament Explorer.

ORM models that map to database tables with proper indexing,
constraints, and relationships.

Responsibility: Define database schema and ORM mappings
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, DateTime, Boolean, Text, JSON,
    ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models"""
    pass


class BillModel(Base):
    """
    Database model for legislative bills.
    
    Maps to the 'bills' table with proper indexing on natural keys
    and foreign keys for relationships.
    """
    
    __tablename__ = "bills"
    
    # Primary key (auto-increment)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Natural key fields (unique together)
    jurisdiction: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    parliament: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # Core fields from OpenParliament
    title_en: Mapped[str] = mapped_column(Text, nullable=False)
    title_fr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_title_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    short_title_fr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    sponsor_politician_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        index=True
    )
    
    introduced_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True
    )
    
    law_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # LEGISinfo enrichment fields
    legisinfo_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        unique=True,
        index=True
    )
    
    subject_tags: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    
    committee_studies: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    
    royal_assent_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        index=True
    )
    
    royal_assent_chapter: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )
    
    related_bill_numbers: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    
    # Source tracking
    source_openparliament: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    source_legisinfo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    
    # Timestamps
    last_fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    last_enriched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Constraints
    __table_args__ = (
        # Natural key uniqueness
        UniqueConstraint(
            'jurisdiction',
            'parliament',
            'session',
            'number',
            name='uq_bill_natural_key'
        ),
        # Composite indexes for common queries
        Index(
            'idx_bill_parliament_session',
            'parliament',
            'session',
            'introduced_date'
        ),
        Index(
            'idx_bill_fetch_timestamp',
            'last_fetched_at',
            'parliament',
            'session'
        ),
        # Check constraints
        CheckConstraint(
            'parliament > 0',
            name='ck_parliament_positive'
        ),
        CheckConstraint(
            'session > 0',
            name='ck_session_positive'
        ),
    )
    
    def __repr__(self) -> str:
        return (
            f"<BillModel(id={self.id}, "
            f"number={self.number}, "
            f"parliament={self.parliament}, "
            f"session={self.session})>"
        )


class PoliticianModel(Base):
    """
    Database model for politicians (MPs and Senators).
    
    Maps to the 'politicians' table for tracking sponsors and members.
    """
    
    __tablename__ = "politicians"
    
    # Primary key (OpenParliament politician ID)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Basic information
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    given_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    family_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Contact information
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Current membership (JSON for flexibility)
    current_party: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    current_riding: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)
    current_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # All memberships (historical)
    memberships: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    
    # External IDs
    parl_mp_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    
    # Timestamps
    last_fetched_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_politician_party_riding', 'current_party', 'current_riding'),
        Index('idx_politician_fetch_timestamp', 'last_fetched_at'),
    )
    
    def __repr__(self) -> str:
        return f"<PoliticianModel(id={self.id}, name={self.name})>"


class FetchLogModel(Base):
    """
    Database model for tracking data fetch operations.
    
    Logs all adapter fetch operations for monitoring and debugging.
    """
    
    __tablename__ = "fetch_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Fetch metadata
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Metrics
    records_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_seconds: Mapped[float] = mapped_column(nullable=False)
    
    # Parameters (JSON for flexibility)
    fetch_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Errors (if any)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_fetch_log_source_status', 'source', 'status', 'created_at'),
        Index('idx_fetch_log_created', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<FetchLogModel(id={self.id}, "
            f"source={self.source}, "
            f"status={self.status})>"
        )
