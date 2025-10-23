"""
Vote and VoteRecord models for parliamentary voting records.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship

from models.base import Base


class Vote(Base):
    """Parliamentary vote record."""
    
    __tablename__ = "votes"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Natural Key Components
    jurisdiction = Column(String(50), nullable=False, index=True)
    vote_id = Column(String(100), nullable=False)  # External ID from source
    
    # Parliamentary Context
    parliament = Column(Integer, nullable=False)
    session = Column(Integer, nullable=False)
    vote_number = Column(Integer, nullable=False)
    chamber = Column(String(50), nullable=False)  # House, Senate
    
    # Vote Details
    vote_date = Column(DateTime, nullable=False, index=True)
    vote_description_en = Column(Text, nullable=True)
    vote_description_fr = Column(Text, nullable=True)
    
    # Bill Reference
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=True, index=True)
    
    # Results
    result = Column(String(50), nullable=False)  # Passed, Defeated, Tied
    yeas = Column(Integer, nullable=False, default=0)
    nays = Column(Integer, nullable=False, default=0)
    abstentions = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bill = relationship("Bill", back_populates="votes")
    vote_records = relationship("VoteRecord", back_populates="vote", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("parliament > 0", name="ck_vote_parliament_positive"),
        CheckConstraint("session > 0", name="ck_vote_session_positive"),
        CheckConstraint("yeas >= 0", name="ck_vote_yeas_nonnegative"),
        CheckConstraint("nays >= 0", name="ck_vote_nays_nonnegative"),
        CheckConstraint("abstentions >= 0", name="ck_vote_abstentions_nonnegative"),
    )
    
    def __repr__(self) -> str:
        return f"<Vote(id={self.id}, vote_id='{self.vote_id}', date={self.vote_date}, result='{self.result}')>"


class VoteRecord(Base):
    """Individual politician vote within a parliamentary vote."""
    
    __tablename__ = "vote_records"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign Keys
    vote_id = Column(Integer, ForeignKey("votes.id"), nullable=False, index=True)
    politician_id = Column(Integer, ForeignKey("politicians.id"), nullable=False, index=True)
    
    # Vote Position
    vote_position = Column(String(20), nullable=False)  # Yea, Nay, Abstain, Absent
    
    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    vote = relationship("Vote", back_populates="vote_records")
    politician = relationship("Politician", back_populates="vote_records")
    
    def __repr__(self) -> str:
        return f"<VoteRecord(id={self.id}, vote_id={self.vote_id}, politician_id={self.politician_id}, position='{self.vote_position}')>"
