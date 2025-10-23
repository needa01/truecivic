"""
Repository for vector embedding persistence.

Responsibility: Data access layer for ``EmbeddingModel`` records.
"""

from __future__ import annotations

import logging
from typing import Iterable, List

from sqlalchemy import and_, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import EmbeddingModel

logger = logging.getLogger(__name__)


class EmbeddingRepository:
    """Repository encapsulating embedding persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_many(self, payloads: Iterable[dict]) -> List[EmbeddingModel]:
        """
        Batch upsert embedding chunks.

        Each payload must contain:
            - document_id
            - chunk_id
            - chunk_text
            - vector (list[float])
            - token_count
            - start_char
            - end_char
        """
        payload_list = list(payloads)
        if not payload_list:
            return []

        try:
            dialect = self.session.bind.dialect.name  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            dialect = "sqlite"

        if dialect == "postgresql":
            stmt = pg_insert(EmbeddingModel).values(payload_list)
            stmt = stmt.on_conflict_do_update(
                index_elements=[EmbeddingModel.document_id, EmbeddingModel.chunk_id],
                set_={
                    "chunk_text": stmt.excluded.chunk_text,
                    "vector": stmt.excluded.vector,
                    "token_count": stmt.excluded.token_count,
                    "start_char": stmt.excluded.start_char,
                    "end_char": stmt.excluded.end_char,
                },
            )
            await self.session.execute(stmt)
            await self.session.flush()

            ids = [
                (item["document_id"], item["chunk_id"])
                for item in payload_list
            ]
            stmt_fetch = select(EmbeddingModel).where(
                tuple_(EmbeddingModel.document_id, EmbeddingModel.chunk_id).in_(ids)  # type: ignore[name-defined]
            )
            result = await self.session.execute(stmt_fetch)
            models = list(result.scalars().all())
            logger.info("Upserted %s embeddings (bulk)", len(models))
            return models

        models: List[EmbeddingModel] = []
        for payload in payload_list:
            stmt = select(EmbeddingModel).where(
                and_(
                    EmbeddingModel.document_id == payload["document_id"],
                    EmbeddingModel.chunk_id == payload["chunk_id"],
                )
            )
            existing_result = await self.session.execute(stmt)
            existing = existing_result.scalar_one_or_none()
            if existing:
                existing.chunk_text = payload["chunk_text"]
                existing.vector = payload["vector"]
                existing.token_count = payload["token_count"]
                existing.start_char = payload["start_char"]
                existing.end_char = payload["end_char"]
                models.append(existing)
            else:
                model = EmbeddingModel(**payload)
                self.session.add(model)
                models.append(model)
        await self.session.flush()
        logger.info("Upserted %s embeddings (sequential)", len(models))
        return models
