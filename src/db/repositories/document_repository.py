"""
Repository for the documents table.

Stores normalised text blobs (debates, speeches, summaries) that feed the
embedding pipeline.

Responsibility: Data access layer for ``DocumentModel`` records.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import and_, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import DocumentModel

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository handling persistence for ``DocumentModel`` records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _counts(text: str) -> tuple[int, int]:
        """Return character and word counts for the given text."""
        char_count = len(text or "")
        word_count = len(text.split())
        return char_count, word_count

    async def _normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure payload satisfies model requirements."""
        data = dict(payload)

        required = ["jurisdiction", "entity_type", "entity_id", "content_type", "language"]
        for key in required:
            if key not in data:
                raise ValueError(f"document payload missing '{key}'")

        text = data.get("text_content", "")
        char_count, word_count = self._counts(text)
        data["text_content"] = text
        data["char_count"] = data.get("char_count", char_count)
        data["word_count"] = data.get("word_count", word_count)

        now = datetime.utcnow()
        data.setdefault("created_at", now)
        data["updated_at"] = now

        return data

    async def get_by_natural_key(
        self,
        *,
        entity_type: str,
        entity_id: int,
        content_type: str,
        language: str,
    ) -> Optional[DocumentModel]:
        """Fetch a document by natural key."""
        stmt = select(DocumentModel).where(
            and_(
                DocumentModel.entity_type == entity_type,
                DocumentModel.entity_id == entity_id,
                DocumentModel.content_type == content_type,
                DocumentModel.language == language,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, payload: Dict[str, Any]) -> DocumentModel:
        """Insert or update a single document."""
        normalized = await self._normalize_payload(payload)
        existing = await self.get_by_natural_key(
            entity_type=normalized["entity_type"],
            entity_id=normalized["entity_id"],
            content_type=normalized["content_type"],
            language=normalized["language"],
        )
        if existing:
            update_fields = [
                "text_content",
                "char_count",
                "word_count",
                "updated_at",
            ]
            for field in update_fields:
                setattr(existing, field, normalized[field])
            await self.session.flush()
            return existing

        model = DocumentModel(**normalized)
        self.session.add(model)
        await self.session.flush()
        return model

    async def upsert_many(self, payloads: Iterable[Dict[str, Any]]) -> List[DocumentModel]:
        """Batch upsert documents."""
        normalized_payloads = [
            await self._normalize_payload(item) for item in payloads
        ]
        if not normalized_payloads:
            return []

        try:
            dialect = self.session.bind.dialect.name  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            dialect = "sqlite"

        if dialect == "postgresql":
            stmt = pg_insert(DocumentModel).values(normalized_payloads)
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    DocumentModel.entity_type,
                    DocumentModel.entity_id,
                    DocumentModel.content_type,
                    DocumentModel.language,
                ],
                set_={
                    "text_content": stmt.excluded.text_content,
                    "char_count": stmt.excluded.char_count,
                    "word_count": stmt.excluded.word_count,
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            await self.session.execute(stmt)
            await self.session.flush()

            keys = [
                (
                    item["entity_type"],
                    item["entity_id"],
                    item["content_type"],
                    item["language"],
                )
                for item in normalized_payloads
            ]
            stmt_fetch = select(DocumentModel).where(
                tuple_(
                    DocumentModel.entity_type,
                    DocumentModel.entity_id,
                    DocumentModel.content_type,
                    DocumentModel.language,
                ).in_(keys)  # type: ignore[name-defined]
            )
            result = await self.session.execute(stmt_fetch)
            models = list(result.scalars().all())
            logger.info("Upserted %s documents (bulk)", len(models))
            return models

        models: List[DocumentModel] = []
        for payload in normalized_payloads:
            models.append(await self.upsert(payload))
        logger.info("Upserted %s documents (sequential)", len(models))
        return models

    async def delete_for_entity(
        self,
        *,
        entity_type: str,
        entity_id: int,
    ) -> int:
        """Delete all documents associated with the provided entity."""
        stmt = select(DocumentModel).where(
            and_(
                DocumentModel.entity_type == entity_type,
                DocumentModel.entity_id == entity_id,
            )
        )
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())
        deleted = len(records)
        for record in records:
            await self.session.delete(record)
        if deleted:
            await self.session.flush()
        return deleted
