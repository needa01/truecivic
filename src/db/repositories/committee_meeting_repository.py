"""
Repository for committee meeting database operations.

Handles CRUD operations and batch upserts for committee meetings.

Responsibility: Database access layer for committee_meetings table
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import Base

logger = logging.getLogger(__name__)


# CommitteeMeetingModel - Add to models.py later
class CommitteeMeetingModel(Base):
    """Database model for committee meetings."""
    
    __tablename__ = "committee_meetings"
    
    from sqlalchemy.orm import Mapped, mapped_column
    from sqlalchemy import Integer, String, DateTime, Text, JSON, ForeignKey, UniqueConstraint, Index
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    committee_id: Mapped[int] = mapped_column(Integer, ForeignKey('committees.id', ondelete='CASCADE'), nullable=False)
    meeting_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parliament: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    session: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    meeting_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    time_of_day: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    title_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title_fr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meeting_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    room: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    witnesses: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    documents: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('committee_id', 'meeting_number', 'parliament', 'session', name='uq_committee_meeting_natural_key'),
        Index('idx_committee_meetings_committee', 'committee_id'),
        Index('idx_committee_meetings_date', 'meeting_date'),
        Index('idx_committee_meetings_parliament_session', 'parliament', 'session'),
        Index('idx_committee_meetings_committee_date', 'committee_id', 'meeting_date'),
    )
    
    def __repr__(self) -> str:
        return f"<CommitteeMeetingModel(id={self.id}, committee_id={self.committee_id}, number={self.meeting_number})>"


class CommitteeMeetingRepository:
    """
    Repository for committee meeting database operations.
    
    Provides methods for creating, reading, updating, and deleting
    committee meeting records with batch operations.
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: SQLAlchemy async session
        """
        self.session = session
    
    async def get_by_id(self, meeting_id: int) -> Optional[CommitteeMeetingModel]:
        """
        Get a meeting by ID.
        
        Args:
            meeting_id: Meeting ID
            
        Returns:
            CommitteeMeetingModel or None if not found
        """
        stmt = select(CommitteeMeetingModel).where(CommitteeMeetingModel.id == meeting_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_committee(
        self,
        committee_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[CommitteeMeetingModel]:
        """
        Get meetings for a specific committee.
        
        Args:
            committee_id: Committee ID
            limit: Maximum number of meetings to return
            offset: Number of meetings to skip
            
        Returns:
            List of CommitteeMeetingModel objects
        """
        stmt = (
            select(CommitteeMeetingModel)
            .where(CommitteeMeetingModel.committee_id == committee_id)
            .order_by(desc(CommitteeMeetingModel.meeting_date))
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        committee_id: Optional[int] = None
    ) -> List[CommitteeMeetingModel]:
        """
        Get meetings within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            committee_id: Optional committee ID filter
            
        Returns:
            List of CommitteeMeetingModel objects
        """
        stmt = select(CommitteeMeetingModel).where(
            and_(
                CommitteeMeetingModel.meeting_date >= start_date,
                CommitteeMeetingModel.meeting_date <= end_date
            )
        )
        
        if committee_id:
            stmt = stmt.where(CommitteeMeetingModel.committee_id == committee_id)
        
        stmt = stmt.order_by(desc(CommitteeMeetingModel.meeting_date))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_parliament_session(
        self,
        parliament: int,
        session: int,
        committee_id: Optional[int] = None
    ) -> List[CommitteeMeetingModel]:
        """
        Get meetings for a specific parliament and session.
        
        Args:
            parliament: Parliament number
            session: Session number
            committee_id: Optional committee ID filter
            
        Returns:
            List of CommitteeMeetingModel objects
        """
        stmt = select(CommitteeMeetingModel).where(
            and_(
                CommitteeMeetingModel.parliament == parliament,
                CommitteeMeetingModel.session == session
            )
        )
        
        if committee_id:
            stmt = stmt.where(CommitteeMeetingModel.committee_id == committee_id)
        
        stmt = stmt.order_by(desc(CommitteeMeetingModel.meeting_date))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def upsert(self, meeting_data: Dict[str, Any]) -> CommitteeMeetingModel:
        """
        Insert or update a single meeting record.
        
        Args:
            meeting_data: Meeting data dictionary
            
        Returns:
            CommitteeMeetingModel object
        """
        # Try to find existing meeting
        stmt = select(CommitteeMeetingModel).where(
            and_(
                CommitteeMeetingModel.committee_id == meeting_data.get('committee_id'),
                CommitteeMeetingModel.meeting_number == meeting_data.get('meeting_number'),
                CommitteeMeetingModel.parliament == meeting_data.get('parliament'),
                CommitteeMeetingModel.session == meeting_data.get('session')
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            for key, value in meeting_data.items():
                if hasattr(existing, key) and key not in ['id', 'created_at']:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            return existing
        else:
            # Create new
            meeting = CommitteeMeetingModel(**meeting_data)
            self.session.add(meeting)
            await self.session.flush()
            return meeting
    
    async def upsert_many(self, meetings_data: List[Dict[str, Any]]) -> List[CommitteeMeetingModel]:
        """
        Batch upsert multiple meeting records.
        
        Uses PostgreSQL ON CONFLICT for performance. Falls back to
        individual upserts for SQLite.
        
        Args:
            meetings_data: List of meeting data dictionaries
            
        Returns:
            List of CommitteeMeetingModel objects
        """
        if not meetings_data:
            return []
        
        # Check if we're using PostgreSQL
        dialect_name = self.session.bind.dialect.name
        
        if dialect_name == 'postgresql':
            # Use PostgreSQL ON CONFLICT for batch upsert
            stmt = pg_insert(CommitteeMeetingModel).values(meetings_data)
            stmt = stmt.on_conflict_do_update(
                constraint='uq_committee_meeting_natural_key',
                set_={
                    'meeting_date': stmt.excluded.meeting_date,
                    'time_of_day': stmt.excluded.time_of_day,
                    'title_en': stmt.excluded.title_en,
                    'title_fr': stmt.excluded.title_fr,
                    'meeting_type': stmt.excluded.meeting_type,
                    'room': stmt.excluded.room,
                    'witnesses': stmt.excluded.witnesses,
                    'documents': stmt.excluded.documents,
                    'source_url': stmt.excluded.source_url,
                    'updated_at': datetime.utcnow()
                }
            )
            await self.session.execute(stmt)
            await self.session.flush()
            
            # Fetch and return the upserted records
            committee_ids = [m['committee_id'] for m in meetings_data]
            stmt = select(CommitteeMeetingModel).where(
                CommitteeMeetingModel.committee_id.in_(committee_ids)
            ).order_by(desc(CommitteeMeetingModel.meeting_date))
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        else:
            # Fall back to individual upserts for SQLite
            logger.warning("Using individual upserts (not PostgreSQL)")
            upserted = []
            for meeting_data in meetings_data:
                meeting = await self.upsert(meeting_data)
                upserted.append(meeting)
            return upserted
    
    async def delete_by_id(self, meeting_id: int) -> bool:
        """
        Delete a meeting by ID.
        
        Args:
            meeting_id: Meeting ID
            
        Returns:
            True if deleted, False if not found
        """
        meeting = await self.get_by_id(meeting_id)
        if meeting:
            await self.session.delete(meeting)
            await self.session.flush()
            return True
        return False
    
    async def count_by_committee(self, committee_id: int) -> int:
        """
        Count meetings for a committee.
        
        Args:
            committee_id: Committee ID
            
        Returns:
            Number of meetings
        """
        from sqlalchemy import func
        stmt = select(func.count()).select_from(CommitteeMeetingModel).where(
            CommitteeMeetingModel.committee_id == committee_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
