"""Backfill embeddings for documents lacking vector representations.

Usage examples:
    python scripts/backfill_embeddings.py --env production --batch-size 200
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Sequence

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure project root on path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.validate_backfill_results import load_environment
from src.config import Settings
from src.db.models import DocumentModel, EmbeddingModel
from src.db.repositories.embedding_repository import EmbeddingRepository
from src.services.embedding_service import EmbeddingService


LOGGER = logging.getLogger("backfill_embeddings")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


async def _fetch_batch(
    repository_session: AsyncSession,
    *,
    entity_type: str,
    batch_size: int,
    offset_document_id: int | None,
) -> Sequence[tuple[int, str]]:
    stmt = (
        select(DocumentModel.id, DocumentModel.text_content)
        .where(DocumentModel.entity_type == entity_type)
        .where(~exists().where(EmbeddingModel.document_id == DocumentModel.id))
        .order_by(DocumentModel.id)
        .limit(batch_size)
    )

    if offset_document_id is not None:
        stmt = stmt.where(DocumentModel.id > offset_document_id)

    result = await repository_session.execute(stmt)
    rows = result.all()
    return [(row.id, row.text_content or "") for row in rows]


async def _backfill_embeddings(
    *,
    environment: str,
    entity_type: str,
    batch_size: int,
    limit: int | None,
) -> int:
    load_environment(environment)

    settings = Settings()

    service = EmbeddingService()
    if not service.enabled and service.fallback_mode not in {"auto", "deterministic"}:
        LOGGER.error(
            "EmbeddingService disabled and no deterministic fallback configured. Set OPENAI_API_KEY or EMBEDDING_FALLBACK_MODE=deterministic."
        )
        return 1

    processed = 0
    last_id: int | None = None

    engine = create_async_engine(
        settings.db.connection_string,
        echo=settings.db.echo,
        echo_pool=settings.db.echo_pool,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.max_overflow,
        pool_timeout=settings.db.pool_timeout,
        pool_recycle=settings.db.pool_recycle,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )

    try:
        async with session_factory() as session:
            repository = EmbeddingRepository(session)

            while True:
                batch = await _fetch_batch(
                    session,
                    entity_type=entity_type,
                    batch_size=batch_size,
                    offset_document_id=last_id,
                )

                if not batch:
                    break

                if limit is not None and processed >= limit:
                    break

                if limit is not None and processed + len(batch) > limit:
                    batch = batch[: max(limit - processed, 0)]

                embeddings = await service.embed_documents(batch)

                if embeddings:
                    await repository.upsert_many(
                        [
                            {
                                "document_id": chunk.document_id,
                                "chunk_id": chunk.chunk_id,
                                "chunk_text": chunk.chunk_text,
                                "vector": chunk.vector,
                                "token_count": chunk.token_count,
                                "start_char": chunk.start_char,
                                "end_char": chunk.end_char,
                            }
                            for chunk in embeddings
                        ]
                    )
                    await session.commit()
                    LOGGER.info(
                        "Stored %s embeddings for %s documents (last document id=%s)",
                        len(embeddings),
                        len(batch),
                        batch[-1][0],
                    )
                else:
                    LOGGER.warning(
                        "No embeddings generated for current batch (size=%s).", len(batch)
                    )
                    await session.rollback()

                processed += len(batch)
                last_id = batch[-1][0]

                if limit is not None and processed >= limit:
                    break
    finally:
        await engine.dispose()

    await service.close()
    LOGGER.info("Embedding backfill complete. Documents processed: %s", processed)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill embeddings for documents without vectors")
    parser.add_argument("--env", default="production", choices=("production", "local"), help="Environment configuration to load")
    parser.add_argument("--entity-type", default="speech", help="Document entity_type to backfill (default: speech)")
    parser.add_argument("--batch-size", type=int, default=100, help="Number of documents to process per batch")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of documents to process")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _configure_logging(args.verbose)
    exit_code = asyncio.run(
        _backfill_embeddings(
            environment=args.env,
            entity_type=args.entity_type,
            batch_size=args.batch_size,
            limit=args.limit,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
