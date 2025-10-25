"""
Prefect flows for generating embeddings for documents.

Scans the documents table for rows missing embeddings and generates vector
representations using the EmbeddingService.
"""

try:
    from .create_github_storage import github_block
except Exception as e:
    print("GitHub storage block not created yet:", e)
    

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bs4 import BeautifulSoup
from prefect import flow, task, get_run_logger
from sqlalchemy import select

from src.db.session import async_session_factory
from src.db.models import DocumentModel, EmbeddingModel
from src.db.repositories.embedding_repository import EmbeddingRepository
from src.services.embedding_service import EmbeddingService, EmbeddingChunk

logger = logging.getLogger(__name__)


def _strip_html(text: Optional[str]) -> str:
    """Convert HTML content to plain text for embedding generation."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(" ", strip=True)


@task(name="fetch_documents_without_embeddings", retries=2, retry_delay_seconds=30)
async def fetch_documents_without_embeddings_task(
    limit: int = 100,
    entity_types: Optional[Sequence[str]] = None,
    language: Optional[str] = None,
    content_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch documents that do not yet have embeddings.
    """
    logger_task = get_run_logger()
    logger_task.info(
        "Fetching up to %s documents without embeddings (entity_types=%s, language=%s, content_type=%s)",
        limit,
        entity_types,
        language,
        content_type,
    )

    async with async_session_factory() as session:
        stmt = (
            select(DocumentModel)
            .outerjoin(EmbeddingModel, EmbeddingModel.document_id == DocumentModel.id)
            .where(EmbeddingModel.id.is_(None))
        )

        if entity_types:
            stmt = stmt.where(DocumentModel.entity_type.in_(entity_types))
        if language:
            stmt = stmt.where(DocumentModel.language == language)
        if content_type:
            stmt = stmt.where(DocumentModel.content_type == content_type)

        stmt = stmt.order_by(DocumentModel.created_at.asc()).limit(limit)

        result = await session.execute(stmt)
        documents = result.scalars().all()

    payload: List[Dict[str, Any]] = []
    seen_ids = set()
    for document in documents:
        if document.id in seen_ids:
            logger_task.warning("Duplicate document id %s detected; skipping duplicate row", document.id)
            continue
        seen_ids.add(document.id)
        payload.append(
            {
                "id": document.id,
                "text_content": document.text_content,
                "language": document.language,
                "entity_type": document.entity_type,
                "content_type": document.content_type,
            }
        )

    logger_task.info("Fetched %s documents requiring embeddings", len(payload))
    return payload


@task(name="generate_embeddings_for_documents", retries=1)
async def generate_embeddings_for_documents_task(
    documents: List[Dict[str, Any]],
    max_words_per_chunk: int = 750,
) -> Dict[str, int]:
    """
    Generate and persist embeddings for provided documents.
    """
    logger_task = get_run_logger()

    if not documents:
        logger_task.info("No documents provided for embedding generation")
        return {"documents": 0, "embeddings": 0}

    embedding_inputs: List[Tuple[int, str]] = []
    for document in documents:
        plain = _strip_html(document.get("text_content"))
        if plain:
            embedding_inputs.append((document["id"], plain))
        else:
            logger_task.warning(
                "Skipping document %s due to empty text content", document["id"]
            )

    if not embedding_inputs:
        logger_task.warning("All candidate documents had empty content")
        return {"documents": 0, "embeddings": 0}

    embedding_service = EmbeddingService()
    try:
        chunks: List[EmbeddingChunk] = await embedding_service.embed_documents(
            embedding_inputs,
            max_words=max_words_per_chunk,
        )
    except Exception as exc:
        logger_task.error("Embedding generation failed: %s", exc, exc_info=True)
        await embedding_service.close()
        return {"documents": len(embedding_inputs), "embeddings": 0, "error": str(exc)}
    else:
        await embedding_service.close()

    if not chunks:
        logger_task.warning("Embedding service returned no vectors")
        return {"documents": len(embedding_inputs), "embeddings": 0}

    chunk_payloads = [
        {
            "document_id": chunk.document_id,
            "chunk_id": chunk.chunk_id,
            "chunk_text": chunk.chunk_text,
            "vector": chunk.vector,
            "token_count": chunk.token_count,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
        }
        for chunk in chunks
    ]

    async with async_session_factory() as session:
        repo = EmbeddingRepository(session)
        await repo.upsert_many(chunk_payloads)
        await session.commit()

    logger_task.info(
        "Generated %s embedding chunks across %s documents",
        len(chunk_payloads),
        len(embedding_inputs),
    )
    return {"documents": len(embedding_inputs), "embeddings": len(chunk_payloads)}


@flow(name="generate_document_embeddings")
async def generate_document_embeddings_flow(
    limit: int = 100,
    entity_types: Optional[Sequence[str]] = None,
    language: Optional[str] = None,
    content_type: Optional[str] = None,
    max_words_per_chunk: int = 750,
) -> Dict[str, int]:
    """
    Flow entrypoint for generating embeddings for documents lacking vectors.
    """
    logger.info(
        "Starting document embedding flow (limit=%s, entity_types=%s, language=%s, content_type=%s)",
        limit,
        entity_types,
        language,
        content_type,
    )

    documents = await fetch_documents_without_embeddings_task(
        limit=limit,
        entity_types=entity_types,
        language=language,
        content_type=content_type,
    )
    if not documents:
        logger.info("No documents pending embeddings")
        return {"documents": 0, "embeddings": 0}

    result = await generate_embeddings_for_documents_task(
        documents,
        max_words_per_chunk=max_words_per_chunk,
    )

    logger.info("Completed document embedding flow: %s", result)
    return result


if __name__ == "__main__":  # pragma: no cover
    import asyncio

    asyncio.run(generate_document_embeddings_flow(limit=25))
