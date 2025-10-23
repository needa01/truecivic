"""
Repository for vote and vote record database operations.

Handles CRUD and batch operations for parliamentary votes and individual MP voting records.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.db.models import VoteModel, VoteRecordModel, BillModel, PoliticianModel

logger = logging.getLogger(__name__)


class VoteRepository:
    """Repository for vote database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_id(self, vote_id: int) -> Optional[VoteModel]:
        """
        Get vote by database ID.
        
        Args:
            vote_id: Database primary key
            
        Returns:
            VoteModel or None if not found
        """
        result = await self.session.execute(
            select(VoteModel).where(VoteModel.id == vote_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_vote_id(
        self, 
        jurisdiction: str, 
        vote_id: str
    ) -> Optional[VoteModel]:
        """
        Get vote by natural key (jurisdiction + vote_id).
        
        Args:
            jurisdiction: Jurisdiction code (e.g., 'ca')
            vote_id: Vote identifier (e.g., '44-1-123')
            
        Returns:
            VoteModel or None if not found
        """
        result = await self.session.execute(
            select(VoteModel).where(
                and_(
                    VoteModel.jurisdiction == jurisdiction,
                    VoteModel.vote_id == vote_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_bill(self, bill_id: int, limit: int = 100) -> List[VoteModel]:
        """
        Get all votes for a specific bill.
        
        Args:
            bill_id: Bill database ID
            limit: Maximum results
            
        Returns:
            List of VoteModel
        """
        result = await self.session.execute(
            select(VoteModel)
            .where(VoteModel.bill_id == bill_id)
            .order_by(desc(VoteModel.vote_date))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_session(
        self, 
        parliament: int, 
        session: int, 
        limit: int = 500
    ) -> List[VoteModel]:
        """
        Get votes for a parliament session.
        
        Args:
            parliament: Parliament number
            session: Session number
            limit: Maximum results
            
        Returns:
            List of VoteModel
        """
        result = await self.session.execute(
            select(VoteModel)
            .where(
                and_(
                    VoteModel.parliament == parliament,
                    VoteModel.session == session
                )
            )
            .order_by(desc(VoteModel.vote_date))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def upsert_one(self, vote_data: Dict[str, Any]) -> VoteModel:
        """
        Insert or update a single vote.
        
        Args:
            vote_data: Vote attributes
            
        Returns:
            VoteModel (newly created or updated)
        """
        jurisdiction = vote_data.get("jurisdiction", "ca")
        vote_id = vote_data["vote_id"]
        
        # Check if exists
        existing = await self.get_by_vote_id(jurisdiction, vote_id)
        
        if existing:
            # Update
            for key, value in vote_data.items():
                if hasattr(existing, key) and key not in ["id", "created_at"]:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            logger.debug(f"Updated vote: {vote_id}")
            return existing
        else:
            # Insert
            vote = VoteModel(**vote_data)
            self.session.add(vote)
            await self.session.flush()
            logger.debug(f"Created vote: {vote_id}")
            return vote
    
    async def upsert_many(self, votes_data: List[Dict[str, Any]]) -> List[VoteModel]:
        """
        Batch insert or update votes using PostgreSQL upsert.
        
        Args:
            votes_data: List of vote attribute dictionaries
            
        Returns:
            List of VoteModel
        """
        if not votes_data:
            return []
        
        # Prepare data with timestamps
        for vote in votes_data:
            if "jurisdiction" not in vote:
                vote["jurisdiction"] = "ca"
            if "created_at" not in vote:
                vote["created_at"] = datetime.utcnow()
            if "updated_at" not in vote:
                vote["updated_at"] = datetime.utcnow()
        
        # PostgreSQL upsert
        stmt = insert(VoteModel).values(votes_data)
        update_dict = {
            col.name: stmt.excluded[col.name]
            for col in VoteModel.__table__.columns
            if col.name not in ["id", "created_at"]
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_vote_natural_key",
            set_=update_dict
        ).returning(VoteModel)
        
        result = await self.session.execute(stmt)
        votes = list(result.scalars().all())
        
        logger.info(f"Upserted {len(votes)} votes")
        return votes
    
    async def count_by_session(self, parliament: int, session: int) -> int:
        """
        Count votes in a parliament session.
        
        Args:
            parliament: Parliament number
            session: Session number
            
        Returns:
            Count of votes
        """
        result = await self.session.execute(
            select(func.count(VoteModel.id)).where(
                and_(
                    VoteModel.parliament == parliament,
                    VoteModel.session == session
                )
            )
        )
        return result.scalar() or 0


class VoteRecordRepository:
    """Repository for individual MP vote record operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_vote(self, vote_id: int) -> List[VoteRecordModel]:
        """
        Get all MP vote records for a specific vote.
        
        Args:
            vote_id: Vote database ID
            
        Returns:
            List of VoteRecordModel
        """
        result = await self.session.execute(
            select(VoteRecordModel)
            .where(VoteRecordModel.vote_id == vote_id)
            .order_by(VoteRecordModel.politician_id)
        )
        return list(result.scalars().all())
    
    async def get_by_politician(
        self, 
        politician_id: int, 
        limit: int = 100
    ) -> List[VoteRecordModel]:
        """
        Get all vote records for a specific politician.
        
        Args:
            politician_id: Politician database ID
            limit: Maximum results
            
        Returns:
            List of VoteRecordModel
        """
        result = await self.session.execute(
            select(VoteRecordModel)
            .where(VoteRecordModel.politician_id == politician_id)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def upsert_one(
        self, 
        vote_id: int, 
        politician_id: int, 
        vote_position: str
    ) -> VoteRecordModel:
        """
        Insert or update a single vote record.
        
        Args:
            vote_id: Vote database ID
            politician_id: Politician database ID
            vote_position: 'Yea', 'Nay', 'Paired'
            
        Returns:
            VoteRecordModel
        """
        # Check if exists
        result = await self.session.execute(
            select(VoteRecordModel).where(
                and_(
                    VoteRecordModel.vote_id == vote_id,
                    VoteRecordModel.politician_id == politician_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update
            existing.vote_position = vote_position
            await self.session.flush()
            return existing
        else:
            # Insert
            record = VoteRecordModel(
                vote_id=vote_id,
                politician_id=politician_id,
                vote_position=vote_position
            )
            self.session.add(record)
            await self.session.flush()
            return record
    
    async def upsert_many(
        self, 
        records_data: List[Dict[str, Any]]
    ) -> List[VoteRecordModel]:
        """
        Batch insert or update vote records using PostgreSQL upsert.
        
        Args:
            records_data: List of vote record dicts with keys:
                - vote_id (int)
                - politician_id (int)
                - vote_position (str)
            
        Returns:
            List of VoteRecordModel
        """
        if not records_data:
            return []
        
        # Add timestamps
        for record in records_data:
            if "created_at" not in record:
                record["created_at"] = datetime.utcnow()
        
        # PostgreSQL upsert
        stmt = insert(VoteRecordModel).values(records_data)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_vote_record_natural_key",
            set_={"vote_position": stmt.excluded.vote_position}
        ).returning(VoteRecordModel)
        
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        
        logger.info(f"Upserted {len(records)} vote records")
        return records
    
    async def count_by_vote(self, vote_id: int) -> int:
        """
        Count vote records for a specific vote.
        
        Args:
            vote_id: Vote database ID
            
        Returns:
            Count of records
        """
        result = await self.session.execute(
            select(func.count(VoteRecordModel.id))
            .where(VoteRecordModel.vote_id == vote_id)
        )
        return result.scalar() or 0
    
    async def get_politician_voting_pattern(
        self, 
        politician_id: int
    ) -> Dict[str, int]:
        """
        Get voting pattern statistics for a politician.
        
        Args:
            politician_id: Politician database ID
            
        Returns:
            Dict with keys 'Yea', 'Nay', 'Paired' and counts
        """
        result = await self.session.execute(
            select(
                VoteRecordModel.vote_position,
                func.count(VoteRecordModel.id)
            )
            .where(VoteRecordModel.politician_id == politician_id)
            .group_by(VoteRecordModel.vote_position)
        )
        
        pattern = {"Yea": 0, "Nay": 0, "Paired": 0}
        for position, count in result.all():
            pattern[position] = count
        
        return pattern
