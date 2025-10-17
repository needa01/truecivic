"""
Repository for bill data operations.

Implements repository pattern for bill CRUD operations with
natural key lookups and bulk operations.

Responsibility: Abstract database operations for bills
"""

from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import logging

from ..models import BillModel
from ...models.bill import Bill
from ...config import settings

logger = logging.getLogger(__name__)


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
        bill_models = await repo.upsert_many(bills)
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
    
    async def create(self, bill: Bill) -> BillModel:
        """
        Create a new bill in database.
        
        Args:
            bill: Bill domain model
        
        Returns:
            Created BillModel
        """
        bill_model = self._domain_to_model(bill)
        
        self.session.add(bill_model)
        await self.session.flush()  # Get ID without committing
        
        logger.debug(f"Created bill: {bill.natural_key()}")
        
        return bill_model
    
    async def update(self, bill_model: BillModel, bill: Bill) -> BillModel:
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
        bill_model.introduced_date = bill.introduced_date
        bill_model.law_status = bill.law_status
        
        # Update enrichment fields
        bill_model.legisinfo_id = bill.legisinfo_id
        bill_model.subject_tags = bill.subject_tags
        bill_model.committee_studies = bill.committee_studies
        bill_model.royal_assent_date = bill.royal_assent_date
        bill_model.royal_assent_chapter = bill.royal_assent_chapter
        bill_model.related_bill_numbers = bill.related_bill_numbers
        
        # Update source tracking
        bill_model.source_openparliament = bill.source_openparliament
        bill_model.source_legisinfo = bill.source_legisinfo
        bill_model.last_fetched_at = bill.last_fetched_at
        bill_model.last_enriched_at = bill.last_enriched_at
        
        # Update timestamp
        bill_model.updated_at = datetime.utcnow()
        
        await self.session.flush()
        
        logger.debug(f"Updated bill: {bill.natural_key()}")
        
        return bill_model
    
    async def upsert(self, bill: Bill) -> Tuple[BillModel, bool]:
        """
        Insert or update bill (upsert).
        
        Args:
            bill: Bill domain model
        
        Returns:
            Tuple of (BillModel, created) where created is True if new
        """
        # Check if bill exists
        existing = await self.get_by_natural_key(
            bill.jurisdiction,
            bill.parliament,
            bill.session,
            bill.number
        )
        
        if existing:
            # Update existing
            updated = await self.update(existing, bill)
            return updated, False
        else:
            # Create new
            created = await self.create(bill)
            return created, True
    
    async def upsert_many(self, bills: List[Bill]) -> List[BillModel]:
        """
        Bulk upsert bills.
        
        For SQLite: Uses individual upserts (slower but works)
        For PostgreSQL: Uses native UPSERT (ON CONFLICT DO UPDATE)
        
        Args:
            bills: List of Bill domain models
        
        Returns:
            List of BillModel instances
        """
        if not bills:
            return []
        
        logger.info(f"Upserting {len(bills)} bills...")
        
        # Check if we're using PostgreSQL or SQLite
        if "postgresql" in settings.db.driver:
            return await self._upsert_many_postgresql(bills)
        else:
            return await self._upsert_many_sqlite(bills)
    
    async def _upsert_many_sqlite(self, bills: List[Bill]) -> List[BillModel]:
        """Bulk upsert for SQLite (individual operations)"""
        models = []
        
        for bill in bills:
            model, _ = await self.upsert(bill)
            models.append(model)
        
        logger.info(f"Upserted {len(models)} bills (SQLite)")
        
        return models
    
    async def _upsert_many_postgresql(self, bills: List[Bill]) -> List[BillModel]:
        """
        Bulk upsert for PostgreSQL (native UPSERT).
        
        Uses PostgreSQL's ON CONFLICT DO UPDATE for efficient bulk operations.
        """
        # Convert bills to dict format
        bill_dicts = [self._domain_to_dict(bill) for bill in bills]
        
        # Build upsert statement
        stmt = pg_insert(BillModel).values(bill_dicts)
        
        # On conflict, update all fields except natural key
        stmt = stmt.on_conflict_do_update(
            constraint='uq_bill_natural_key',
            set_={
                'title_en': stmt.excluded.title_en,
                'title_fr': stmt.excluded.title_fr,
                'short_title_en': stmt.excluded.short_title_en,
                'short_title_fr': stmt.excluded.short_title_fr,
                'sponsor_politician_id': stmt.excluded.sponsor_politician_id,
                'introduced_date': stmt.excluded.introduced_date,
                'law_status': stmt.excluded.law_status,
                'legisinfo_id': stmt.excluded.legisinfo_id,
                'subject_tags': stmt.excluded.subject_tags,
                'committee_studies': stmt.excluded.committee_studies,
                'royal_assent_date': stmt.excluded.royal_assent_date,
                'royal_assent_chapter': stmt.excluded.royal_assent_chapter,
                'related_bill_numbers': stmt.excluded.related_bill_numbers,
                'source_openparliament': stmt.excluded.source_openparliament,
                'source_legisinfo': stmt.excluded.source_legisinfo,
                'last_fetched_at': stmt.excluded.last_fetched_at,
                'last_enriched_at': stmt.excluded.last_enriched_at,
                'updated_at': datetime.utcnow(),
            }
        )
        
        await self.session.execute(stmt)
        await self.session.flush()
        
        logger.info(f"Upserted {len(bills)} bills (PostgreSQL)")
        
        # Fetch and return the models
        natural_keys = [
            (b.jurisdiction, b.parliament, b.session, b.number)
            for b in bills
        ]
        
        result = await self.session.execute(
            select(BillModel).where(
                or_(*[
                    and_(
                        BillModel.jurisdiction == nk[0],
                        BillModel.parliament == nk[1],
                        BillModel.session == nk[2],
                        BillModel.number == nk[3]
                    )
                    for nk in natural_keys
                ])
            )
        )
        
        return list(result.scalars().all())
    
    def _domain_to_model(self, bill: Bill) -> BillModel:
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
            introduced_date=bill.introduced_date,
            law_status=bill.law_status,
            legisinfo_id=bill.legisinfo_id,
            subject_tags=bill.subject_tags,
            committee_studies=bill.committee_studies,
            royal_assent_date=bill.royal_assent_date,
            royal_assent_chapter=bill.royal_assent_chapter,
            related_bill_numbers=bill.related_bill_numbers,
            source_openparliament=bill.source_openparliament,
            source_legisinfo=bill.source_legisinfo,
            last_fetched_at=bill.last_fetched_at or datetime.utcnow(),
            last_enriched_at=bill.last_enriched_at,
        )
    
    def _domain_to_dict(self, bill: Bill) -> dict:
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
            'introduced_date': bill.introduced_date,
            'law_status': bill.law_status,
            'legisinfo_id': bill.legisinfo_id,
            'subject_tags': bill.subject_tags,
            'committee_studies': bill.committee_studies,
            'royal_assent_date': bill.royal_assent_date,
            'royal_assent_chapter': bill.royal_assent_chapter,
            'related_bill_numbers': bill.related_bill_numbers,
            'source_openparliament': bill.source_openparliament,
            'source_legisinfo': bill.source_legisinfo,
            'last_fetched_at': bill.last_fetched_at or datetime.utcnow(),
            'last_enriched_at': bill.last_enriched_at,
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
            sponsor_politician_name=model.sponsor_politician_name,
            introduced_date=model.introduced_date,
            law_status=model.law_status,
            legisinfo_id=model.legisinfo_id,
            legisinfo_status=model.legisinfo_status,
            legisinfo_summary_en=model.legisinfo_summary_en,
            legisinfo_summary_fr=model.legisinfo_summary_fr,
            subject_tags=model.subject_tags,
            committee_studies=model.committee_studies,
            royal_assent_date=model.royal_assent_date,
            royal_assent_chapter=model.royal_assent_chapter,
            related_bill_numbers=model.related_bill_numbers,
            source_openparliament=model.source_openparliament,
            source_legisinfo=model.source_legisinfo,
            last_fetched_at=model.last_fetched_at,
            last_enriched_at=model.last_enriched_at,
        )
