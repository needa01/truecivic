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
from src.utils.committee_registry import build_committee_identifier, resolve_source_slug

logger = logging.getLogger(__name__)


CANONICAL_JURISDICTION = "ca-federal"
JURISDICTION_NORMALIZATION = {
    "ca",
    "canada",
    "ca-canada",
    "ca_federal",
    "cafederal",
    "ca-federal",
}


class CommitteeRepository:
    """Repository for committee database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: Async database session
        """
        self.session = session

    def _normalize_committee_payload(self, committee_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize committee identifiers before persistence.

        Ensures we always store the canonical acronym, the jurisdiction-prefixed
        slug, and a lowercase OpenParliament slug when available.
        """
        identifier_seed = (
            committee_data.get("committee_slug")
            or committee_data.get("committee_code")
            or committee_data.get("source_slug")
            or committee_data.get("acronym_en")
        )
        if not identifier_seed:
            raise ValueError("Committee payload requires a code or slug")

        identifier = build_committee_identifier(identifier_seed)
        committee_data["committee_code"] = identifier.code
        committee_data["committee_slug"] = identifier.internal_slug

        # Canonical jurisdiction handling
        jurisdiction = self._canonical_jurisdiction(committee_data.get("jurisdiction"))
        committee_data["jurisdiction"] = jurisdiction

        # Parliament/session are required for natural-id construction
        parliament = committee_data.get("parliament")
        session = committee_data.get("session")
        if parliament is None or session is None:
            raise ValueError("Committee payload requires parliament and session values")
        committee_data["parliament"] = int(parliament)
        committee_data["session"] = int(session)
        parliament = committee_data["parliament"]
        session = committee_data["session"]

        # Ensure acronyms default to committee code for backwards compatibility
        acronym_en = (committee_data.get("acronym_en") or identifier.code).strip().upper()
        committee_data["acronym_en"] = acronym_en
        acronym_fr_value = committee_data.get("acronym_fr")
        if acronym_fr_value:
            committee_data["acronym_fr"] = acronym_fr_value.strip().upper()
        else:
            committee_data["acronym_fr"] = acronym_en

        # Compute natural_id leveraging canonical components
        committee_data["natural_id"] = (
            f"{jurisdiction}-{int(parliament)}-{int(session)}-committee-{identifier.code}"
        )

        source_slug = committee_data.get("source_slug") or identifier.source_slug
        normalized_source_slug = resolve_source_slug(source_slug) if source_slug else None
        committee_data["source_slug"] = normalized_source_slug

        parent_committee = committee_data.get("parent_committee")
        if parent_committee:
            try:
                parent_identifier = build_committee_identifier(parent_committee)
                committee_data["parent_committee"] = parent_identifier.internal_slug
            except ValueError:
                committee_data["parent_committee"] = parent_committee

        return committee_data

    @staticmethod
    def _canonical_jurisdiction(value: Optional[str]) -> str:
        """
        Map legacy jurisdiction strings to the canonical committee jurisdiction.
        """
        if not value:
            return CANONICAL_JURISDICTION
        trimmed = value.strip()
        if not trimmed:
            return CANONICAL_JURISDICTION
        if trimmed.lower() in JURISDICTION_NORMALIZATION:
            return CANONICAL_JURISDICTION
        return trimmed
    
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
            jurisdiction: Jurisdiction code (e.g., 'ca-federal')
            committee_code: Committee code (e.g., 'HUMA', 'FINA')
            
        Returns:
            CommitteeModel or None if not found
        """
        jurisdiction = self._canonical_jurisdiction(jurisdiction)

        normalized_code = build_committee_identifier(committee_code).code

        result = await self.session.execute(
            select(CommitteeModel).where(
                and_(
                    CommitteeModel.jurisdiction == jurisdiction,
                    CommitteeModel.committee_code == normalized_code
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(
        self,
        committee_slug: str,
    ) -> Optional[CommitteeModel]:
        """
        Fetch a committee by its jurisdiction-prefixed slug.
        """
        normalized_slug = build_committee_identifier(committee_slug).internal_slug
        result = await self.session.execute(
            select(CommitteeModel).where(CommitteeModel.committee_slug == normalized_slug)
        )
        return result.scalar_one_or_none()

    async def get_by_natural_id(self, natural_id: str) -> Optional[CommitteeModel]:
        """
        Fetch a committee by its natural identifier.
        """
        result = await self.session.execute(
            select(CommitteeModel).where(CommitteeModel.natural_id == natural_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(
        self,
        jurisdiction: str = CANONICAL_JURISDICTION,
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
        jurisdiction = self._canonical_jurisdiction(jurisdiction)
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
        normalized_payload = self._normalize_committee_payload(dict(committee_data))
        jurisdiction = self._canonical_jurisdiction(normalized_payload.get("jurisdiction"))
        committee_code = normalized_payload["committee_code"]
        
        # Check if exists
        existing = await self.get_by_code(jurisdiction, committee_code)
        
        if existing:
            # Update
            for key, value in normalized_payload.items():
                if hasattr(existing, key) and key not in ["id", "created_at"]:
                    setattr(existing, key, value)
            existing.updated_at = datetime.utcnow()
            await self.session.flush()
            logger.debug(f"Updated committee: {committee_code}")
            return existing
        else:
            # Insert
            committee = CommitteeModel(**normalized_payload)
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
        normalized_committees: List[Dict[str, Any]] = []
        for committee in committees_data:
            normalized = self._normalize_committee_payload(dict(committee))
            normalized["jurisdiction"] = self._canonical_jurisdiction(
                normalized.get("jurisdiction")
            )
            if "created_at" not in normalized:
                normalized["created_at"] = datetime.utcnow()
            if "updated_at" not in normalized:
                normalized["updated_at"] = datetime.utcnow()
            normalized_committees.append(normalized)
        
        # PostgreSQL upsert
        stmt = insert(CommitteeModel).values(normalized_committees)
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
    
    async def count(self, jurisdiction: str = CANONICAL_JURISDICTION) -> int:
        """
        Count committees in a jurisdiction.
        
        Args:
            jurisdiction: Jurisdiction code
            
        Returns:
            Count of committees
        """
        result = await self.session.execute(
            select(func.count(CommitteeModel.id)).where(
                CommitteeModel.jurisdiction == self._canonical_jurisdiction(jurisdiction)
            )
        )
        return result.scalar() or 0
    
    async def search_by_name(
        self,
        search_term: str,
        jurisdiction: str = CANONICAL_JURISDICTION,
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
                    CommitteeModel.jurisdiction == self._canonical_jurisdiction(jurisdiction),
                    func.lower(CommitteeModel.name_en).contains(search_term.lower())
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())
