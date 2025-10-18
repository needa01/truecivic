"""
Repository for committee database operations.

Handles CRUD and batch operations for parliamentary committees and meetings.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from src.db.models import CommitteeModel

logger = logging.getLogger(__name__)


class CommitteeRepository:
    """Repository for committee database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_id(self, committee_id: int) -> Optional[CommitteeModel]:
        """
        Get committee by database ID.
        
        Args:
            committee_id: Database primary key
            
        Returns:
            CommitteeModel or None if not found
        """
        result = await self.session.execute(
            select(CommitteeModel).where(CommitteeModel.id == committee_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(
        self, 
        jurisdiction: str, 
        committee_code: str
    ) -> Optional[CommitteeModel]:
        """
        Get committee by natural key (jurisdiction + code).
        
        Args:
            jurisdiction: Jurisdiction code (e.g., 'ca')
            committee_code: Committee code (e.g., 'HUMA', 'FINA')
            
        Returns:
            CommitteeModel or None if not found
        """
        result = await self.session.execute(
            select(CommitteeModel).where(
                and_(
                    CommitteeModel.jurisdiction == jurisdiction,
                    CommitteeModel.committee_code == committee_code
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        jurisdiction: str = "ca",
        chamber: Optional[str] = None,
        limit: int = 100
    ) -> List[CommitteeModel]:
        """
        Get all committees with optional filtering.
        
        Args:
            jurisdiction: Jurisdiction code
            chamber: Filter by chamber ('Commons', 'Senate')
            limit: Maximum results
            
        Returns:
            List of CommitteeModel
        """
        query = select(CommitteeModel).where(
            CommitteeModel.jurisdiction == jurisdiction
        )
        
        if chamber:
            query = query.where(CommitteeModel.chamber == chamber)
        
        query = query.order_by(CommitteeModel.committee_code).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def upsert_one(self, committee_data: Dict[str, Any]) -> CommitteeModel:
        """
        Insert or update a single committee.
        
        Args:
            committee_data: Committee attributes
            
        Returns:
            CommitteeModel (newly created or updated)
        """
        jurisdiction = committee_data.get("jurisdiction", "ca")
        committee_code = committee_data["committee_code"]
        
        # Check if exists
        existing = await self.get_by_code(jurisdiction, committee_code)
        
        if existing:
            # Update
            for key, value in committee_data.items():
                if hasattr(existing, key) and key not in ["id", "created_at"]:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            logger.debug(f"Updated committee: {committee_code}")
            return existing
        else:
            # Insert
            committee = CommitteeModel(**committee_data)
            self.session.add(committee)
            await self.session.flush()
            logger.debug(f"Created committee: {committee_code}")
            return committee
    
    async def upsert_many(
        self, 
        committees_data: List[Dict[str, Any]]
    ) -> List[CommitteeModel]:
        """
        Batch insert or update committees using PostgreSQL upsert.
        
        Args:
            committees_data: List of committee attribute dictionaries
            
        Returns:
            List of CommitteeModel
        """
        if not committees_data:
            return []
        
        # Prepare data with timestamps
        for committee in committees_data:
            if "jurisdiction" not in committee:
                committee["jurisdiction"] = "ca"
            if "created_at" not in committee:
                committee["created_at"] = datetime.utcnow()
            if "updated_at" not in committee:
                committee["updated_at"] = datetime.utcnow()
        
        # PostgreSQL upsert
        stmt = insert(CommitteeModel).values(committees_data)
        update_dict = {
            col.name: stmt.excluded[col.name]
            for col in CommitteeModel.__table__.columns
            if col.name not in ["id", "created_at"]
        }
        stmt = stmt.on_conflict_do_update(
            constraint="uq_committee_natural_key",
            set_=update_dict
        ).returning(CommitteeModel)
        
        result = await self.session.execute(stmt)
        committees = list(result.scalars().all())
        
        logger.info(f"Upserted {len(committees)} committees")
        return committees
    
    async def count(self, jurisdiction: str = "ca") -> int:
        """
        Count committees in a jurisdiction.
        
        Args:
            jurisdiction: Jurisdiction code
            
        Returns:
            Count of committees
        """
        result = await self.session.execute(
            select(func.count(CommitteeModel.id)).where(
                CommitteeModel.jurisdiction == jurisdiction
            )
        )
        return result.scalar() or 0
    
    async def search_by_name(
        self,
        search_term: str,
        jurisdiction: str = "ca",
        limit: int = 20
    ) -> List[CommitteeModel]:
        """
        Search committees by name.
        
        Args:
            search_term: Search string
            jurisdiction: Jurisdiction code
            limit: Maximum results
            
        Returns:
            List of matching CommitteeModel
        """
        result = await self.session.execute(
            select(CommitteeModel)
            .where(
                and_(
                    CommitteeModel.jurisdiction == jurisdiction,
                    func.lower(CommitteeModel.name_en).contains(search_term.lower())
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())
