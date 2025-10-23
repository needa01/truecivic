"""
Repository for speech database operations.

Handles CRUD and batch operations for parliamentary speeches.

Responsibility: Data access layer for speeches table
"""

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, time
from sqlalchemy import select, and_, func, desc, or_, delete, tuple_
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
    
    @staticmethod
    def _normalize_timestamp(value: Any) -> Optional[time]:
        """Convert various timestamp formats to time objects accepted by the DB."""
        if value is None:
            return None

        if isinstance(value, time):
            return value

        if isinstance(value, datetime):
            return value.time()

        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned or cleaned.lower() in {"null", "none"}:
                return None

            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"

            try:
                return time.fromisoformat(cleaned)
            except ValueError:
                pass

            try:
                return datetime.fromisoformat(cleaned).time()
            except ValueError:
                pass

            patterns = (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%H:%M:%S",
                "%H:%M",
                "%I:%M %p",
            )
            for pattern in patterns:
                try:
                    return datetime.strptime(cleaned, pattern).time()
                except ValueError:
                    continue

            logger.warning("Unable to parse speech timestamp: %s", value)
            return None

        logger.warning("Unexpected timestamp type: %s", type(value))
        return None

    @classmethod
    def _prepare_payload(cls, speech_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize payload before persistence."""
        normalized = dict(speech_data)
        normalized["timestamp_start"] = cls._normalize_timestamp(speech_data.get("timestamp_start"))
        normalized["timestamp_end"] = cls._normalize_timestamp(speech_data.get("timestamp_end"))
        return normalized

    @staticmethod
    def _natural_key_tuple(payload: Dict[str, Any]) -> Optional[Tuple[int, int]]:
        """Return the debate/sequence natural key tuple if available."""
        debate_id = payload.get("debate_id")
        sequence = payload.get("sequence")
        if debate_id is None or sequence is None:
            return None

        try:
            return int(debate_id), int(sequence)
        except (TypeError, ValueError):
            logger.warning("Invalid natural key values for speech payload: %s", payload)
            return None

    async def _fetch_by_keys(self, keys: List[Tuple[int, int]]) -> List[SpeechModel]:
        """Fetch speeches by their natural key order."""
        if not keys:
            return []

        # Preserve order while deduplicating keys
        ordered_unique: List[Tuple[int, int]] = list(dict.fromkeys(keys))

        stmt = select(SpeechModel).where(
            tuple_(SpeechModel.debate_id, SpeechModel.sequence).in_(ordered_unique)
        )
        result = await self.session.execute(stmt)
        fetched = list(result.scalars().all())
        lookup = {(item.debate_id, item.sequence): item for item in fetched}

        ordered_results: List[SpeechModel] = []
        for key in keys:
            model = lookup.get(key)
            if model:
                ordered_results.append(model)
            else:
                logger.warning("Speech missing after upsert for key %s", key)

        return ordered_results

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
        speech_data = self._prepare_payload(speech_data)

        # Ensure required fields
        required_fields = ['debate_id', 'speaker_name', 'speaker_display_name', 'sequence', 'text_content']
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
        normalized_payloads = [self._prepare_payload(s) for s in speeches_data]

        for speech in normalized_payloads:
            required_fields = ['debate_id', 'speaker_name', 'speaker_display_name', 'sequence', 'text_content']
            for field in required_fields:
                if field not in speech or speech[field] is None:
                    if field == 'speaker_display_name' and speech.get('speaker_name'):
                        speech[field] = speech['speaker_name']
                        continue

                    logger.warning(f"Speech missing required field: {field}")
                    speech[field] = None

        key_order: List[Tuple[int, int]] = []
        seen_keys: Set[Tuple[int, int]] = set()
        for speech in normalized_payloads:
            key = self._natural_key_tuple(speech)
            if key and key not in seen_keys:
                seen_keys.add(key)
                key_order.append(key)
        
        try:
            dialect_name = self.session.bind.dialect.name
        except Exception:
            dialect_name = "sqlite"
        
        stored_speeches = []
        
        if dialect_name == 'postgresql':
            try:
                stmt = pg_insert(SpeechModel).values(normalized_payloads)
                stmt = stmt.on_conflict_do_update(
                    constraint='uq_speech_natural_key',
                    set_={
                        'politician_id': stmt.excluded.politician_id,
                        'speaker_name': stmt.excluded.speaker_name,
                        'speaker_display_name': stmt.excluded.speaker_display_name,
                        'language': stmt.excluded.language,
                        'text_content': stmt.excluded.text_content,
                        'timestamp_start': stmt.excluded.timestamp_start,
                        'timestamp_end': stmt.excluded.timestamp_end,
                    }
                )

                await self.session.execute(stmt)
                await self.session.flush()

                logger.info(
                    f"Batch upserted {len(normalized_payloads)} speeches "
                    f"(PostgreSQL ON CONFLICT)"
                )

                stored_speeches = await self._fetch_by_keys(key_order)

            except Exception as exc:
                logger.error("PostgreSQL batch upsert failed", exc_info=True)
                await self.session.rollback()
                for speech_data in normalized_payloads:
                    speech = await self.upsert(speech_data)
                    stored_speeches.append(speech)
                await self.session.flush()
                stored_speeches = await self._fetch_by_keys(key_order)
        else:
            # SQLite: Individual upserts
            logger.info(f"Using SQLite fallback for {len(normalized_payloads)} speeches")
            for speech_data in normalized_payloads:
                speech = await self.upsert(speech_data)
                stored_speeches.append(speech)
            await self.session.flush()
            stored_speeches = await self._fetch_by_keys(key_order)
        
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
