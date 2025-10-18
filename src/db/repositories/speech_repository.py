"""
Repository for speech database operations.

Handles CRUD and batch operations for parliamentary speeches.

Responsibility: Data access layer for speeches table
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, and_, func, desc, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.db.models import SpeechModel

logger = logging.getLogger(__name__)


class SpeechRepository:
    """Repository for speech database operations."""
    
    def __init__(self, session: AsyncSession):
        """
        Initialize repository.
        
        Args:
            session: Async database session
        """
        self.session = session
    
    async def get_by_id(self, speech_id: int) -> Optional[SpeechModel]:
        """
        Get speech by database ID.
        
        Args:
            speech_id: Database primary key
            
        Returns:
            SpeechModel or None if not found
        """
        result = await self.session.execute(
            select(SpeechModel).where(SpeechModel.id == speech_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_debate_id(
        self,
        debate_id: int,
        limit: int = 1000,
        offset: int = 0,
        politician_id: Optional[int] = None
    ) -> List[SpeechModel]:
        """
        Get all speeches for a debate.
        
        Args:
            debate_id: Debate database ID
            limit: Maximum results to return
            offset: Pagination offset
            politician_id: Optional filter by politician
            
        Returns:
            List of SpeechModel objects
        """
        query = select(SpeechModel).where(
            SpeechModel.debate_id == debate_id
        )
        
        if politician_id:
            query = query.where(SpeechModel.politician_id == politician_id)
        
        query = query.order_by(SpeechModel.sequence).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_politician_id(
        self,
        politician_id: int,
        limit: int = 500,
        offset: int = 0,
        language: Optional[str] = None
    ) -> List[SpeechModel]:
        """
        Get speeches by a politician.
        
        Args:
            politician_id: Politician database ID
            limit: Maximum results to return
            offset: Pagination offset
            language: Optional filter by language (en/fr)
            
        Returns:
            List of SpeechModel objects
        """
        query = select(SpeechModel).where(
            SpeechModel.politician_id == politician_id
        )
        
        if language:
            query = query.where(SpeechModel.language == language)
        
        query = query.order_by(desc(SpeechModel.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_recent(
        self,
        limit: int = 100,
        language: Optional[str] = None
    ) -> List[SpeechModel]:
        """
        Get most recent speeches.
        
        Args:
            limit: Maximum results to return
            language: Optional filter by language (en/fr)
            
        Returns:
            List of SpeechModel objects sorted by creation date
        """
        query = select(SpeechModel)
        
        if language:
            query = query.where(SpeechModel.language == language)
        
        query = query.order_by(desc(SpeechModel.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def search_by_content(
        self,
        search_term: str,
        limit: int = 100,
        politician_id: Optional[int] = None
    ) -> List[SpeechModel]:
        """
        Search speeches by content text.
        
        Args:
            search_term: Text to search for (case-insensitive)
            limit: Maximum results to return
            politician_id: Optional filter by politician
            
        Returns:
            List of matching SpeechModel objects
        """
        search_pattern = f"%{search_term}%"
        query = select(SpeechModel).where(
            SpeechModel.text_content.ilike(search_pattern)
        )
        
        if politician_id:
            query = query.where(SpeechModel.politician_id == politician_id)
        
        query = query.order_by(desc(SpeechModel.created_at)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_by_debate(self, debate_id: int) -> int:
        """
        Count speeches in a debate.
        
        Args:
            debate_id: Debate database ID
            
        Returns:
            Count of speeches
        """
        result = await self.session.execute(
            select(func.count(SpeechModel.id)).where(
                SpeechModel.debate_id == debate_id
            )
        )
        return result.scalar() or 0
    
    async def count_by_politician(self, politician_id: int) -> int:
        """
        Count speeches by politician.
        
        Args:
            politician_id: Politician database ID
            
        Returns:
            Count of speeches
        """
        result = await self.session.execute(
            select(func.count(SpeechModel.id)).where(
                SpeechModel.politician_id == politician_id
            )
        )
        return result.scalar() or 0
    
    async def upsert(
        self,
        speech_data: Dict[str, Any]
    ) -> SpeechModel:
        """
        Insert or update a single speech.
        
        Uses database unique constraint on (debate_id, sequence).
        
        Args:
            speech_data: Speech dictionary with fields matching SpeechModel
            
        Returns:
            Created or updated SpeechModel
        """
        # Ensure required fields
        required_fields = ['debate_id', 'speaker_name', 'sequence', 'text_content']
        for field in required_fields:
            if field not in speech_data:
                logger.warning(f"Missing required field: {field}")
        
        # Try to find existing speech by unique key
        existing = await self.session.execute(
            select(SpeechModel).where(
                and_(
                    SpeechModel.debate_id == speech_data.get('debate_id'),
                    SpeechModel.sequence == speech_data.get('sequence')
                )
            )
        )
        speech = existing.scalar_one_or_none()
        
        if speech:
            # Update existing
            for key, value in speech_data.items():
                if hasattr(speech, key):
                    setattr(speech, key, value)
            logger.debug(f"Updated speech: {speech.id}")
        else:
            # Create new
            speech = SpeechModel(**speech_data)
            self.session.add(speech)
            logger.debug(f"Created new speech")
        
        return speech
    
    async def upsert_many(
        self,
        speeches_data: List[Dict[str, Any]]
    ) -> List[SpeechModel]:
        """
        Batch insert or update speeches with database optimization.
        
        For PostgreSQL: Uses ON CONFLICT DO UPDATE for single query.
        For SQLite: Falls back to individual upserts.
        
        Args:
            speeches_data: List of speech dictionaries
            
        Returns:
            List of created/updated SpeechModel objects
        """
        if not speeches_data:
            logger.info("No speeches to upsert")
            return []
        
        # Ensure all required fields
        for speech in speeches_data:
            required_fields = ['debate_id', 'speaker_name', 'sequence', 'text_content']
            for field in required_fields:
                if field not in speech:
                    logger.warning(f"Speech missing required field: {field}")
                    speech[field] = None
        
        try:
            dialect_name = self.session.bind.dialect.name
        except Exception:
            dialect_name = "sqlite"
        
        stored_speeches = []
        
        if dialect_name == 'postgresql':
            # PostgreSQL: Use bulk insert with ON CONFLICT
            try:
                stmt = pg_insert(SpeechModel).values(speeches_data)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_speech_natural_key',
                    set_={
                        'politician_id': stmt.excluded.politician_id,
                        'speaker_name': stmt.excluded.speaker_name,
                        'language': stmt.excluded.language,
                        'text_content': stmt.excluded.text_content,
                        'timestamp_start': stmt.excluded.timestamp_start,
                        'timestamp_end': stmt.excluded.timestamp_end,
                    }
                )
                result = await self.session.execute(stmt)
                
                logger.info(
                    f"Batch upserted {len(speeches_data)} speeches "
                    f"(PostgreSQL ON CONFLICT)"
                )
                
                # Fetch back the upserted records to return SpeechModel objects
                debate_ids = set(s.get('debate_id') for s in speeches_data)
                for debate_id in debate_ids:
                    speeches = await self.get_by_debate_id(debate_id, limit=10000)
                    stored_speeches.extend(speeches)
                
            except Exception as e:
                logger.error(f"PostgreSQL batch upsert failed: {e}")
                # Fall through to SQLite approach
                for speech_data in speeches_data:
                    speech = await self.upsert(speech_data)
                    stored_speeches.append(speech)
        else:
            # SQLite: Individual upserts
            logger.info(f"Using SQLite fallback for {len(speeches_data)} speeches")
            for speech_data in speeches_data:
                speech = await self.upsert(speech_data)
                stored_speeches.append(speech)
        
        return stored_speeches
    
    async def delete_by_id(self, speech_id: int) -> bool:
        """
        Delete a speech by ID.
        
        Args:
            speech_id: Speech database ID
            
        Returns:
            True if deleted, False if not found
        """
        speech = await self.get_by_id(speech_id)
        if not speech:
            return False
        
        await self.session.delete(speech)
        logger.info(f"Deleted speech: {speech_id}")
        return True
    
    async def delete_by_debate(self, debate_id: int) -> int:
        """
        Delete all speeches for a debate (cascade cleanup).
        
        Args:
            debate_id: Debate database ID
            
        Returns:
            Number of speeches deleted
        """
        # Count before delete
        result = await self.session.execute(
            select(func.count(SpeechModel.id)).where(
                SpeechModel.debate_id == debate_id
            )
        )
        count = result.scalar() or 0
        
        # Delete all speeches for this debate
        if count > 0:
            await self.session.execute(
                delete(SpeechModel).where(
                    SpeechModel.debate_id == debate_id
                )
            )
        
        logger.info(f"Deleted {count} speeches for debate: {debate_id}")
        return count
