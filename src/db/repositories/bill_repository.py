"""
Repository for bill data operations.

Implements repository pattern for bill CRUD operations with
natural key lookups and bulk operations.

Responsibility: Abstract database operations for bills
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
import logging

from ..models import BillModel
from ...models.bill import Bill
from ...config import settings
from ...utils.hash_utils import compute_bill_hash

logger = logging.getLogger(__name__)


class BillPersistenceStatus(Enum):
    """Outcome classification for bill persistence operations."""

    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(slots=True)
class BillPersistenceOutcome:
    """Represents the result of persisting a single bill."""

    model: BillModel
    status: BillPersistenceStatus
    content_hash: str


class BillRepository:
    """
    Repository for bill data persistence.
    
    Provides methods for creating, reading, updating bills with
    support for natural key lookups and upsert operations.
    
    Example:
        repo = BillRepository(session)
        
        # Find by natural key
        bill_model = await repo.get_by_natural_key("ca-federal", 44, 1, "C-1")
        
    # Bulk upsert
    outcomes = await repo.upsert_many(bills)
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            session: Active database session
        """
        self.session = session
    
    async def get_by_id(self, bill_id: int) -> Optional[BillModel]:
        """Get bill by database ID"""
        result = await self.session.execute(
            select(BillModel).where(BillModel.id == bill_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_natural_key(
        self,
        jurisdiction: str,
        parliament: int,
        session: int,
        number: str
    ) -> Optional[Bill]:
        """
        Get bill by natural key (jurisdiction, parliament, session, number).
        
        Args:
            jurisdiction: Jurisdiction code (e.g., "ca-federal")
            parliament: Parliament number
            session: Session number
            number: Bill number
        
        Returns:
            Bill domain object if found, None otherwise
        """
        result = await self.session.execute(
            select(BillModel).where(
                and_(
                    BillModel.jurisdiction == jurisdiction,
                    BillModel.parliament == parliament,
                    BillModel.session == session,
                    BillModel.number == number
                )
            )
        )
        model = result.scalar_one_or_none()
        return self._model_to_domain(model) if model else None
    
    async def _get_model_by_natural_key(
        self,
        jurisdiction: str,
        parliament: int,
        session: int,
        number: str
    ) -> Optional[BillModel]:
        """
        Get BillModel by natural key (internal use for updates).
        
        Args:
            jurisdiction: Jurisdiction code (e.g., "ca-federal")
            parliament: Parliament number
            session: Session number
            number: Bill number
        
        Returns:
            BillModel if found, None otherwise
        """
        result = await self.session.execute(
            select(BillModel).where(
                and_(
                    BillModel.jurisdiction == jurisdiction,
                    BillModel.parliament == parliament,
                    BillModel.session == session,
                    BillModel.number == number
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_parliament_session(
        self,
        parliament: int,
        session: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[BillModel]:
        """
        Get bills by parliament and optional session.
        
        Returns bills ordered by introduced_date DESC (latest first).
        
        Args:
            parliament: Parliament number
            session: Optional session number
            limit: Maximum results
            offset: Results offset for pagination
        
        Returns:
            List of BillModel instances
        """
        query = select(BillModel).where(BillModel.parliament == parliament)
        
        if session is not None:
            query = query.where(BillModel.session == session)
        
        query = query.order_by(desc(BillModel.introduced_date))
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        models = list(result.scalars().all())
        
        # Convert models to domain objects
        return [self._model_to_domain(model) for model in models]
    
    async def create(
        self,
        bill: Bill,
        *,
        content_hash: Optional[str] = None
    ) -> BillModel:
        """
        Create a new bill in database.
        
        Args:
            bill: Bill domain model
        
        Returns:
            Created BillModel
        """
        bill_model = self._domain_to_model(bill, content_hash=content_hash)
        
        self.session.add(bill_model)
        await self.session.flush()  # Get ID without committing
        
        logger.debug(f"Created bill: {bill.natural_key()}")
        
        return bill_model
    
    async def update(
        self,
        bill_model: BillModel,
        bill: Bill,
        *,
        content_hash: Optional[str] = None
    ) -> BillModel:
        """
        Update existing bill with new data.
        
        Args:
            bill_model: Existing BillModel to update
            bill: Updated Bill domain model
        
        Returns:
            Updated BillModel
        """
        # Update fields from domain model
        bill_model.title_en = bill.title_en
        bill_model.title_fr = bill.title_fr
        bill_model.short_title_en = bill.short_title_en
        bill_model.short_title_fr = bill.short_title_fr
        bill_model.sponsor_politician_id = bill.sponsor_politician_id
        bill_model.sponsor_politician_name = getattr(bill, 'sponsor_politician_name', None)
        bill_model.introduced_date = bill.introduced_date
        bill_model.law_status = bill.law_status
        
        # Update enrichment fields
        bill_model.legisinfo_id = bill.legisinfo_id
        bill_model.legisinfo_status = getattr(bill, 'legisinfo_status', None)
        bill_model.legisinfo_summary_en = getattr(bill, 'legisinfo_summary_en', None)
        bill_model.legisinfo_summary_fr = getattr(bill, 'legisinfo_summary_fr', None)
        bill_model.subject_tags = bill.subject_tags
        bill_model.committee_studies = bill.committee_studies
        bill_model.royal_assent_date = bill.royal_assent_date
        bill_model.royal_assent_chapter = bill.royal_assent_chapter
        bill_model.related_bill_numbers = bill.related_bill_numbers
        
        # Update source tracking
        bill_model.source_openparliament = bill.source_openparliament
        bill_model.source_legisinfo = bill.source_legisinfo
        bill_model.last_fetched_at = bill.last_fetched_at or datetime.utcnow()
        bill_model.last_enriched_at = bill.last_enriched_at
        bill_model.content_hash = content_hash or self._compute_content_hash(bill)
        
        # Update timestamp
        bill_model.updated_at = datetime.utcnow()
        
        await self.session.flush()
        
        logger.debug(f"Updated bill: {bill.natural_key()}")
        
        return bill_model
    
    async def upsert(self, bill: Bill) -> BillPersistenceOutcome:
        """Insert or update bill (upsert)."""
        content_hash = self._compute_content_hash(bill)
        existing = await self._get_model_by_natural_key(
            bill.jurisdiction,
            bill.parliament,
            bill.session,
            bill.number
        )

        if existing:
            if existing.content_hash == content_hash:
                existing.last_fetched_at = bill.last_fetched_at or datetime.utcnow()
                await self.session.flush()
                logger.debug(
                    "Skipped update for bill %s (unchanged content)",
                    bill.natural_key(),
                )
                return BillPersistenceOutcome(
                    model=existing,
                    status=BillPersistenceStatus.UNCHANGED,
                    content_hash=content_hash,
                )

            updated = await self.update(existing, bill, content_hash=content_hash)
            return BillPersistenceOutcome(
                model=updated,
                status=BillPersistenceStatus.UPDATED,
                content_hash=content_hash,
            )

        created = await self.create(bill, content_hash=content_hash)
        return BillPersistenceOutcome(
            model=created,
            status=BillPersistenceStatus.CREATED,
            content_hash=content_hash,
        )
    
    async def upsert_many(self, bills: List[Bill]) -> List[BillPersistenceOutcome]:
        """
        Bulk upsert bills.
        
        For SQLite: Uses individual upserts (slower but works)
        For PostgreSQL: Uses native UPSERT (ON CONFLICT DO UPDATE)
        
        Args:
            bills: List of Bill domain models
        
        Returns:
            List of BillPersistenceOutcome entries
        """
        if not bills:
            return []
        
        logger.info(f"Upserting {len(bills)} bills...")
        
        # Check if we're using PostgreSQL or SQLite
        if "postgresql" in settings.db.driver:
            return await self._upsert_many_postgresql(bills)
        else:
            return await self._upsert_many_sqlite(bills)
    
    async def _upsert_many_sqlite(self, bills: List[Bill]) -> List[BillPersistenceOutcome]:
        """Bulk upsert for SQLite (individual operations)"""
        outcomes: List[BillPersistenceOutcome] = []
        
        for bill in bills:
            outcome = await self.upsert(bill)
            outcomes.append(outcome)
        
        logger.info(
            "Processed %d bills (SQLite) [created=%d, updated=%d, unchanged=%d]",
            len(outcomes),
            sum(1 for o in outcomes if o.status == BillPersistenceStatus.CREATED),
            sum(1 for o in outcomes if o.status == BillPersistenceStatus.UPDATED),
            sum(1 for o in outcomes if o.status == BillPersistenceStatus.UNCHANGED),
        )

        return outcomes
    
    async def _upsert_many_postgresql(self, bills: List[Bill]) -> List[BillPersistenceOutcome]:
        """Bulk upsert for PostgreSQL with change detection."""
        outcomes: List[BillPersistenceOutcome] = []

        if not bills:
            return outcomes

        # Preload existing models for natural keys present in this batch
        natural_keys = [bill.natural_key() for bill in bills]
        existing_models: Dict[Tuple[str, int, int, str], BillModel] = {}

        if natural_keys:
            clauses = [
                and_(
                    BillModel.jurisdiction == nk[0],
                    BillModel.parliament == nk[1],
                    BillModel.session == nk[2],
                    BillModel.number == nk[3],
                )
                for nk in natural_keys
            ]

            if clauses:
                result = await self.session.execute(select(BillModel).where(or_(*clauses)))
                for model in result.scalars().all():
                    existing_models[self._model_natural_key(model)] = model

        to_persist: List[tuple[Bill, str, BillPersistenceStatus]] = []

        for bill in bills:
            content_hash = self._compute_content_hash(bill)
            nk = bill.natural_key()
            existing = existing_models.get(nk)

            if existing is None:
                to_persist.append((bill, content_hash, BillPersistenceStatus.CREATED))
                continue

            if existing.content_hash == content_hash:
                outcomes.append(
                    BillPersistenceOutcome(
                        model=existing,
                        status=BillPersistenceStatus.UNCHANGED,
                        content_hash=content_hash,
                    )
                )
                continue

            to_persist.append((bill, content_hash, BillPersistenceStatus.UPDATED))

        if to_persist:
            bill_dicts = [
                self._domain_to_dict(bill, content_hash=content_hash)
                for bill, content_hash, _ in to_persist
            ]

            stmt = pg_insert(BillModel).values(bill_dicts)
            stmt = stmt.on_conflict_do_update(
                constraint='uq_bill_natural_key',
                set_={
                    'title_en': stmt.excluded.title_en,
                    'title_fr': stmt.excluded.title_fr,
                    'short_title_en': stmt.excluded.short_title_en,
                    'short_title_fr': stmt.excluded.short_title_fr,
                    'sponsor_politician_id': stmt.excluded.sponsor_politician_id,
                    'sponsor_politician_name': stmt.excluded.sponsor_politician_name,
                    'introduced_date': stmt.excluded.introduced_date,
                    'law_status': stmt.excluded.law_status,
                    'legisinfo_id': stmt.excluded.legisinfo_id,
                    'legisinfo_status': stmt.excluded.legisinfo_status,
                    'legisinfo_summary_en': stmt.excluded.legisinfo_summary_en,
                    'legisinfo_summary_fr': stmt.excluded.legisinfo_summary_fr,
                    'subject_tags': stmt.excluded.subject_tags,
                    'committee_studies': stmt.excluded.committee_studies,
                    'royal_assent_date': stmt.excluded.royal_assent_date,
                    'royal_assent_chapter': stmt.excluded.royal_assent_chapter,
                    'related_bill_numbers': stmt.excluded.related_bill_numbers,
                    'source_openparliament': stmt.excluded.source_openparliament,
                    'source_legisinfo': stmt.excluded.source_legisinfo,
                    'last_fetched_at': stmt.excluded.last_fetched_at,
                    'last_enriched_at': stmt.excluded.last_enriched_at,
                    'content_hash': stmt.excluded.content_hash,
                    'updated_at': datetime.utcnow(),
                }
            ).returning(BillModel)

            result = await self.session.execute(stmt)
            await self.session.flush()

            persisted_map = {
                self._model_natural_key(model): model
                for model in result.scalars().all()
            }

            for bill, content_hash, status in to_persist:
                model = persisted_map.get(bill.natural_key())
                if not model:
                    continue
                outcomes.append(
                    BillPersistenceOutcome(
                        model=model,
                        status=status,
                        content_hash=content_hash,
                    )
                )

        logger.info(
            "Processed %d bills (PostgreSQL) [created=%d, updated=%d, unchanged=%d]",
            len(outcomes),
            sum(1 for o in outcomes if o.status == BillPersistenceStatus.CREATED),
            sum(1 for o in outcomes if o.status == BillPersistenceStatus.UPDATED),
            sum(1 for o in outcomes if o.status == BillPersistenceStatus.UNCHANGED),
        )

        return outcomes
    
    def _compute_content_hash(self, bill: Bill) -> str:
        """Compute a deterministic hash for the given bill."""
        return compute_bill_hash(bill)

    @staticmethod
    def _model_natural_key(model: BillModel) -> Tuple[str, int, int, str]:
        """Return the natural key tuple for a persisted bill."""
        return (
            model.jurisdiction,
            model.parliament,
            model.session,
            model.number,
        )

    def _domain_to_model(
        self,
        bill: Bill,
        *,
        content_hash: Optional[str] = None
    ) -> BillModel:
        """Convert Bill domain model to BillModel ORM model"""
        return BillModel(
            jurisdiction=bill.jurisdiction,
            parliament=bill.parliament,
            session=bill.session,
            number=bill.number,
            title_en=bill.title_en,
            title_fr=bill.title_fr,
            short_title_en=bill.short_title_en,
            short_title_fr=bill.short_title_fr,
            sponsor_politician_id=bill.sponsor_politician_id,
            sponsor_politician_name=getattr(bill, 'sponsor_politician_name', None),
            introduced_date=bill.introduced_date,
            law_status=bill.law_status,
            legisinfo_id=bill.legisinfo_id,
            legisinfo_status=getattr(bill, 'legisinfo_status', None),
            legisinfo_summary_en=getattr(bill, 'legisinfo_summary_en', None),
            legisinfo_summary_fr=getattr(bill, 'legisinfo_summary_fr', None),
            subject_tags=bill.subject_tags,
            committee_studies=bill.committee_studies,
            royal_assent_date=bill.royal_assent_date,
            royal_assent_chapter=bill.royal_assent_chapter,
            related_bill_numbers=bill.related_bill_numbers,
            source_openparliament=bill.source_openparliament,
            source_legisinfo=bill.source_legisinfo,
            last_fetched_at=bill.last_fetched_at or datetime.utcnow(),
            last_enriched_at=bill.last_enriched_at,
            content_hash=content_hash or self._compute_content_hash(bill),
        )
    
    def _domain_to_dict(
        self,
        bill: Bill,
        *,
        content_hash: Optional[str] = None
    ) -> dict:
        """Convert Bill domain model to dict for bulk operations"""
        return {
            'jurisdiction': bill.jurisdiction,
            'parliament': bill.parliament,
            'session': bill.session,
            'number': bill.number,
            'title_en': bill.title_en,
            'title_fr': bill.title_fr,
            'short_title_en': bill.short_title_en,
            'short_title_fr': bill.short_title_fr,
            'sponsor_politician_id': bill.sponsor_politician_id,
            'sponsor_politician_name': getattr(bill, 'sponsor_politician_name', None),
            'introduced_date': bill.introduced_date,
            'law_status': bill.law_status,
            'legisinfo_id': bill.legisinfo_id,
            'legisinfo_status': getattr(bill, 'legisinfo_status', None),
            'legisinfo_summary_en': getattr(bill, 'legisinfo_summary_en', None),
            'legisinfo_summary_fr': getattr(bill, 'legisinfo_summary_fr', None),
            'subject_tags': bill.subject_tags,
            'committee_studies': bill.committee_studies,
            'royal_assent_date': bill.royal_assent_date,
            'royal_assent_chapter': bill.royal_assent_chapter,
            'related_bill_numbers': bill.related_bill_numbers,
            'source_openparliament': bill.source_openparliament,
            'source_legisinfo': bill.source_legisinfo,
            'last_fetched_at': bill.last_fetched_at or datetime.utcnow(),
            'last_enriched_at': bill.last_enriched_at,
            'content_hash': content_hash or self._compute_content_hash(bill),
        }
    
    def _model_to_domain(self, model: BillModel) -> Bill:
        """Convert BillModel ORM model to Bill domain model"""
        return Bill(
            jurisdiction=model.jurisdiction,
            parliament=model.parliament,
            session=model.session,
            number=model.number,
            title_en=model.title_en,
            title_fr=model.title_fr,
            short_title_en=model.short_title_en,
            short_title_fr=model.short_title_fr,
            sponsor_politician_id=model.sponsor_politician_id,
            introduced_date=model.introduced_date,
            law_status=model.law_status,
            legisinfo_id=model.legisinfo_id,
            subject_tags=model.subject_tags or [],
            committee_studies=model.committee_studies or [],
            royal_assent_date=model.royal_assent_date,
            royal_assent_chapter=model.royal_assent_chapter,
            related_bill_numbers=model.related_bill_numbers or [],
            source_openparliament=model.source_openparliament,
            source_legisinfo=model.source_legisinfo,
            last_fetched_at=model.last_fetched_at,
            last_enriched_at=model.last_enriched_at,
        )
