"""
Committee and CommitteeMeeting models for parliamentary committees.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class Committee(Base):
    """Parliamentary committee."""
    
    __tablename__ = "committees"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Natural Key Components
    jurisdiction = Column(String(50), nullable=False, index=True)
    committee_code = Column(String(50), nullable=False, index=True)
    
    # Committee Details
    name_en = Column(String(200), nullable=False)
    name_fr = Column(String(200), nullable=True)
    chamber = Column(String(50), nullable=False)  # House, Senate, Joint
    committee_type = Column(String(50), nullable=True)  # Standing, Special, Legislative
    website_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # meetings = relationship("CommitteeMeeting", back_populates="committee", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Committee(id={self.id}, code='{self.committee_code}', name='{self.name_en}')>"


class CommitteeMeeting(Base):
    """Committee meeting session.
    
    Note: This model is prepared for future implementation.
    Not included in current migration.
    """
    
    __tablename__ = "committee_meetings"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Key
    committee_id = Column(Integer, ForeignKey("committees.id"), nullable=False, index=True)
    
    # Meeting Details
    meeting_number = Column(Integer, nullable=True)
    meeting_date = Column(DateTime, nullable=False, index=True)
    parliament = Column(Integer, nullable=False)
    session = Column(Integer, nullable=False)
    
    # Content
    title_en = Column(Text, nullable=True)
    title_fr = Column(Text, nullable=True)
    topics = Column(Text, nullable=True)  # JSON array of topics
    evidence_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # committee = relationship("Committee", back_populates="meetings")
    
    def __repr__(self) -> str:
        return f"<CommitteeMeeting(id={self.id}, committee_id={self.committee_id}, date={self.meeting_date})>"
