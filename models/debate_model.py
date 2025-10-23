"""
Debate and Speech models for Hansard parliamentary debates.
"""
from datetime import datetime, time
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, Time, ForeignKey
from sqlalchemy.orm import relationship

from src.db.models import Base


class Debate(Base):
    """Parliamentary debate session (Hansard)."""
    
    __tablename__ = "debates"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Natural Key Components
    jurisdiction = Column(String(50), nullable=False, index=True)
    hansard_id = Column(String(100), nullable=False)  # External ID from source
    
    # Parliamentary Context
    parliament = Column(Integer, nullable=False)
    session = Column(Integer, nullable=False)
    sitting_date = Column(DateTime, nullable=False, index=True)
    chamber = Column(String(50), nullable=False)  # House, Senate
    
    # Debate Details
    debate_type = Column(String(100), nullable=True)  # Question Period, Bill Reading, etc.
    document_url = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    speeches = relationship("Speech", back_populates="debate", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Debate(id={self.id}, hansard_id='{self.hansard_id}', date={self.sitting_date})>"


class Speech(Base):
    """Individual speech within a parliamentary debate."""
    
    __tablename__ = "speeches"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    debate_id = Column(Integer, ForeignKey("debates.id"), nullable=False, index=True)
    politician_id = Column(Integer, ForeignKey("politicians.id"), nullable=True, index=True)  # Nullable for Speaker
    
    # Speaker Information
    speaker_name = Column(String(200), nullable=False)
    speaker_display_name = Column(Text, nullable=False)
    
    # Speech Order and Content
    sequence = Column(Integer, nullable=False)  # Order within debate
    language = Column(String(2), nullable=True)  # en, fr
    text_content = Column(Text, nullable=False)
    
    # Timestamps (within debate)
    timestamp_start = Column(Time, nullable=True)
    timestamp_end = Column(Time, nullable=True)
    
    # Created Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    debate = relationship("Debate", back_populates="speeches")
    politician = relationship("PoliticianModel")
    
    def __repr__(self) -> str:
        return f"<Speech(id={self.id}, debate_id={self.debate_id}, speaker='{self.speaker_name}', seq={self.sequence})>"
