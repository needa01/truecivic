"""
Prefect flow for fetching debate and speech data.

Orchestrates debate and speech data fetching and storage.

Responsibility: Orchestration of debate data pipeline
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner
from bs4 import BeautifulSoup

from src.adapters.openparliament_debates import OpenParliamentDebatesAdapter
from src.db.session import async_session_factory
from src.db.repositories.speech_repository import SpeechRepository
from src.db.repositories.debate_repository import DebateRepository
from src.db.repositories.document_repository import DocumentRepository
from src.db.repositories.embedding_repository import EmbeddingRepository
from src.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@task(name="fetch_debates", retries=2, retry_delay_seconds=30)
async def fetch_debates_task(
    limit: int = 100,
    offset: int = 0,
    parliament: Optional[int] = None,
    session: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Fetch parliamentary debates.
    
    Args:
        limit: Maximum debates to fetch
        offset: Pagination offset
        parliament: Filter by parliament number
        session: Filter by session number
        
    Returns:
        List of debate dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching debates: limit={limit}, offset={offset}")
    
    adapter = OpenParliamentDebatesAdapter()
    response = await adapter.fetch(
        limit=limit,
        offset=offset,
        parliament=parliament,
        session=session
    )
    
    if response.errors:
        logger_task.error(f"Errors fetching debates: {response.errors}")
    
    records = response.data or []
    logger_task.info(f"Fetched {len(records)} debates")
    return records


@task(name="fetch_debate_speeches", retries=2, retry_delay_seconds=30)
async def fetch_debate_speeches_task(
    debate_path: str,
    speeches_url: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Fetch all speeches for a specific debate.
    
    Args:
        debate_path: Debate path (e.g., '/debates/2025/10/10/')
        speeches_url: Optional fully-qualified speeches endpoint
        limit: Maximum number of speeches to retrieve
        
    Returns:
        List of speech dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info("Fetching speeches for debate path %s", debate_path)

    adapter = OpenParliamentDebatesAdapter()
    response = await adapter.fetch_speeches_for_debate(
        debate_id=debate_path,
        speeches_url=speeches_url,
        limit=limit,
    )

    if response.errors:
        logger_task.error("Errors fetching speeches: %s", response.errors)

    records = response.data or []
    logger_task.info(
        "Fetched %s speeches for debate path %s", len(records), debate_path
    )
    return records


@task(name="fetch_politician_speeches", retries=2, retry_delay_seconds=30)
async def fetch_politician_speeches_task(
    politician_id: int,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    Fetch recent speeches by a politician.
    
    Args:
        politician_id: Politician database ID
        limit: Maximum speeches to fetch
        
    Returns:
        List of speech dictionaries
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching speeches for politician: {politician_id}")
    
    adapter = OpenParliamentDebatesAdapter()
    response = await adapter.fetch_speeches_for_politician(
        politician_id=politician_id,
        limit=limit
    )
    
    if response.errors:
        logger_task.error(f"Errors fetching speeches: {response.errors}")
    
    records = response.data or []
    logger_task.info(f"Fetched {len(records)} speeches for politician")
    return records


@task(name="store_debates", retries=1)
async def store_debates_task(debates_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Store fetched debates in the database.

    Args:
        debates_data: Normalised debate dictionaries from the adapter

    Returns:
        Summary dictionary with counts and lookup tables.
    """
    logger_task = get_run_logger()

    if not debates_data:
        logger_task.info("No debates to store")
        return {"stored": 0, "url_to_id": {}, "hansard_to_id": {}}

    logger_task.info("Storing %s debates", len(debates_data))

    try:
        async with async_session_factory() as session:
            debate_repo = DebateRepository(session)
            document_repo = DocumentRepository(session)

            stored_models = await debate_repo.upsert_many(debates_data)

            documents_payload: List[Dict[str, Any]] = []
            model_by_url = {model.document_url: model for model in stored_models if model.document_url}

            for debate in debates_data:
                document_path = debate.get("url")
                model = model_by_url.get(document_path)
                if not model:
                    continue

                title_en = debate.get("title_en") or ""
                title_fr = debate.get("title_fr") or ""
                source_url = debate.get("source_url")

                lines = [
                    title_en or title_fr or "Parliamentary Debate",
                    f"Chamber: {model.chamber}",
                    f"Sitting date: {model.sitting_date.date().isoformat()}",
                ]
                if debate.get("sitting_number"):
                    lines.append(f"Sitting number: {debate.get('sitting_number')}")
                if source_url:
                    lines.append(f"Source: {source_url}")

                documents_payload.append(
                    {
                        "jurisdiction": model.jurisdiction,
                        "entity_type": "debate",
                        "entity_id": model.id,
                        "content_type": "metadata",
                        "language": "en",
                        "text_content": "\n".join(lines),
                    }
                )

            documents_created = 0
            if documents_payload:
                await document_repo.upsert_many(documents_payload)
                documents_created = len(documents_payload)

            await session.commit()

        url_to_id = {model.document_url: model.id for model in stored_models if model.document_url}
        hansard_to_id = {model.hansard_id: model.id for model in stored_models if model.hansard_id}

        result = {
            "stored": len(stored_models),
            "documents_created": documents_created,
            "url_to_id": url_to_id,
            "hansard_to_id": hansard_to_id,
        }
        logger_task.info("Stored debates result: %s", result)
        return result

    except Exception as exc:
        logger_task.error("Error storing debates: %s", exc, exc_info=True)
        raise


@task(name="store_speeches", retries=1)
async def store_speeches_task(
    speeches_data: List[Dict[str, Any]],
    debate_lookup: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """
    Store fetched speeches and generate downstream documents & embeddings.

    Args:
        speeches_data: List of speech dictionaries from the adapter
        debate_lookup: Optional mapping of debate document paths to database IDs

    Returns:
        Dictionary with counts of stored artefacts.
    """
    logger_task = get_run_logger()

    if not speeches_data:
        logger_task.info("No speeches to store")
        return {"stored": 0, "documents": 0, "embeddings": 0}

    debate_lookup = debate_lookup or {}
    logger_task.info("Storing %s speeches", len(speeches_data))

    def _plain_text(content: Optional[str]) -> str:
        if not content:
            return ""
        soup = BeautifulSoup(content, "html.parser")
        return soup.get_text(" ", strip=True)

    def _normalize_speaker_name(value: Optional[str]) -> tuple[str, str]:
        """Return canonical + display speaker names respecting DB limits."""
        if not value:
            return "Unknown speaker", "Unknown speaker"

        collapsed = " ".join(value.split())
        display_name = collapsed

        if len(collapsed) <= 200:
            return collapsed, display_name

        canonical = collapsed
        if "(" in collapsed:
            base = collapsed.split("(", 1)[0].strip()
            if base:
                canonical = base

        canonical = canonical.strip()
        if len(canonical) > 200:
            canonical = canonical[:200].rstrip()

        if not canonical:
            canonical = collapsed[:200].rstrip()

        return canonical, display_name

    try:
        async with async_session_factory() as session:
            speech_repo = SpeechRepository(session)
            document_repo = DocumentRepository(session)
            embedding_repo = EmbeddingRepository(session)
            debate_repo = DebateRepository(session)

            missing_paths = {
                speech.get("debate_path")
                for speech in speeches_data
                if speech.get("debate_path") and speech.get("debate_path") not in debate_lookup
            }
            if missing_paths:
                debate_map = await debate_repo.map_document_urls(missing_paths)
                debate_lookup.update({path: model.id for path, model in debate_map.items()})

            speech_payloads: List[Dict[str, Any]] = []
            plain_text_lookup: Dict[tuple[int, int], str] = {}
            language_lookup: Dict[tuple[int, int], str] = {}

            for idx, speech in enumerate(speeches_data, start=1):
                debate_path = speech.get("debate_path")
                debate_id = debate_lookup.get(debate_path)
                if not debate_id:
                    logger_task.warning(
                        "Skipping speech %s - debate path not resolved (%s)",
                        speech.get("speech_id"),
                        debate_path,
                    )
                    continue

                sequence = speech.get("sequence")
                if sequence is None:
                    sequence = idx
                try:
                    sequence = int(sequence)
                except (TypeError, ValueError):
                    logger_task.warning(
                        "Skipping speech %s - invalid sequence value %s",
                        speech.get("speech_id"),
                        sequence,
                    )
                    continue

                language = speech.get("language")
                if not language:
                    if speech.get("text_content_fr") and not speech.get("text_content_en"):
                        language = "fr"
                    else:
                        language = "en"

                text_content = (
                    speech.get("text_content_en")
                    or speech.get("text_content")
                    or speech.get("text_content_fr")
                    or ""
                )

                raw_speaker = (
                    speech.get("speaker_display_name")
                    or speech.get("speaker_name")
                )
                canonical_name, display_name = _normalize_speaker_name(raw_speaker)

                payload = {
                    "debate_id": debate_id,
                    "speaker_name": canonical_name,
                    "speaker_display_name": display_name,
                    "sequence": sequence,
                    "language": language,
                    "text_content": text_content,
                    "timestamp_start": speech.get("timestamp_start"),
                    "timestamp_end": speech.get("timestamp_end"),
                    "politician_id": None,
                }
                speech_payloads.append(payload)

                plain_text_lookup[(debate_id, sequence)] = _plain_text(
                    speech.get("text_content_en") or speech.get("text_content") or ""
                )
                language_lookup[(debate_id, sequence)] = language

            stored_speeches = await speech_repo.upsert_many(speech_payloads)

            documents_payload: List[Dict[str, Any]] = []
            for speech_model in stored_speeches:
                key = (speech_model.debate_id, speech_model.sequence)
                plain = plain_text_lookup.get(key, "")
                if not plain:
                    continue
                documents_payload.append(
                    {
                        "jurisdiction": "ca",
                        "entity_type": "speech",
                        "entity_id": speech_model.id,
                        "content_type": "transcript",
                        "language": language_lookup.get(key, "en"),
                        "text_content": plain,
                    }
                )

            stored_documents = []
            if documents_payload:
                stored_documents = await document_repo.upsert_many(documents_payload)

            embedding_chunks: List[dict] = []
            if stored_documents:
                embedding_service = EmbeddingService()
                try:
                    chunk_results = await embedding_service.embed_documents(
                        [(doc.id, doc.text_content) for doc in stored_documents if doc.text_content]
                    )
                    embedding_chunks = [
                        {
                            "document_id": chunk.document_id,
                            "chunk_id": chunk.chunk_id,
                            "chunk_text": chunk.chunk_text,
                            "vector": chunk.vector,
                            "token_count": chunk.token_count,
                            "start_char": chunk.start_char,
                            "end_char": chunk.end_char,
                        }
                        for chunk in chunk_results
                    ]
                finally:
                    await embedding_service.close()

            if embedding_chunks:
                await embedding_repo.upsert_many(embedding_chunks)

            await session.commit()

        result = {
            "stored": len(stored_speeches),
            "documents": len(stored_documents),
            "embeddings": len(embedding_chunks),
        }
        logger_task.info("Stored speeches result: %s", result)
        return result

    except Exception as exc:
        logger_task.error("Error storing speeches: %s", exc, exc_info=True)
        raise


@task(name="fetch_debates_batch_with_speeches", retries=1)
async def fetch_debates_batch_with_speeches_task(
    limit: int = 20,
    parliament: int = None,
    session: int = None
) -> Dict[str, Any]:
    """
    Fetch debates and then fetch speeches for each debate.
    
    Orchestrates multiple speech fetches for a batch of debates.
    
    Args:
        limit: Number of debates to fetch
        parliament: Filter by parliament
        session: Filter by session
        
    Returns:
        Dictionary with results
    """
    logger_task = get_run_logger()
    logger_task.info(f"Fetching {limit} debates with speeches")
    
    # Fetch debates first
    debates = await fetch_debates_task(
        limit=limit,
        parliament=parliament,
        session=session
    )
    
    if not debates:
        logger_task.warning("No debates fetched")
        return {"debates": 0, "speeches": 0}
    
    logger_task.info(f"Processing {len(debates)} debates for speeches")
    
    # Fetch speeches for each debate concurrently
    speech_batches = []
    for debate in debates[:limit]:  # Limit concurrent requests
        debate_path = debate.get("url")
        if debate_path:
            speeches = await fetch_debate_speeches_task(
                debate_path=debate_path,
                speeches_url=debate.get("speeches_url"),
            )
            if speeches:
                speech_batches.append(speeches)
    
    logger_task.info(
        f"Fetched speeches from {len(speech_batches)} debates "
        f"({sum(len(s) for s in speech_batches)} total speeches)"
    )
    
    return {
        "debates": len(debates),
        "debates_with_speeches": len(speech_batches),
        "total_speeches": sum(len(s) for s in speech_batches)
    }


# MARK: Main Flows

@flow(name="fetch_recent_debates_flow", task_runner=ConcurrentTaskRunner())
async def fetch_recent_debates_flow(limit: int = 50) -> Dict[str, Any]:
    """
    Fetch recent debates and store in database.
    
    Args:
        limit: Number of debates to fetch
        
    Returns:
        Result dictionary
    """
    logger.info("🚀 Starting recent debates fetch flow")
    
    # Fetch debates
    debates = await fetch_debates_task(limit=limit)
    
    if not debates:
        logger.warning("No debates fetched")
        return {"debates": 0}
    
    # Store debates
    result = await store_debates_task(debates)
    
    logger.info(f"✅ Completed recent debates flow: {result}")
    return result


@flow(name="fetch_debates_with_speeches_flow", task_runner=ConcurrentTaskRunner())
async def fetch_debates_with_speeches_flow(
    limit: int = 10,
    parliament: Optional[int] = None,
    session: Optional[int] = None
) -> Dict[str, Any]:
    """
    Fetch debates and store all speeches from each debate.
    
    Main flow for speech extraction and storage.
    
    Args:
        limit: Number of debates to process
        parliament: Filter by parliament
        session: Filter by session
        
    Returns:
        Result dictionary with counts
    """
    logger.info("🚀 Starting debates with speeches flow")
    
    # Fetch debates
    debates = await fetch_debates_task(
        limit=limit,
        parliament=parliament,
        session=session
    )
    
    if not debates:
        logger.warning("No debates fetched")
        return {"debates": 0, "speeches": 0}
    
    logger.info(f"Processing {len(debates)} debates for speeches")
    
    # Store debates first and build lookup tables
    debate_store_result = await store_debates_task(debates)
    debate_lookup = debate_store_result.get("url_to_id", {}) or {}

    # Fetch and store speeches for each debate
    total_speeches = 0
    total_documents = debate_store_result.get("documents_created", 0)
    total_embeddings = 0
    for debate in debates:
        debate_path = debate.get("url")
        if not debate_path:
            continue
        try:
            speeches = await fetch_debate_speeches_task(
                debate_path=debate_path,
                speeches_url=debate.get("speeches_url"),
            )
            if speeches:
                result = await store_speeches_task(speeches, debate_lookup=debate_lookup)
                total_speeches += result.get("stored", 0)
                total_documents += result.get("documents", 0)
                total_embeddings += result.get("embeddings", 0)
        except Exception as exc:
            logger.error("Error processing debate %s: %s", debate_path, exc)
    
    logger.info(
        f"✅ Completed debates with speeches flow: "
        f"debates={len(debates)}, speeches={total_speeches}"
    )
    
    return {
        "debates": len(debates),
        "speeches": total_speeches,
        "documents": total_documents,
        "embeddings": total_embeddings,
    }


@flow(name="fetch_top_debates_daily_flow")
async def fetch_top_debates_daily_flow() -> Dict[str, Any]:
    """
    Daily flow: Fetch top 20 recent debates and all their speeches.
    
    Scheduled to run once daily (e.g., 2 AM UTC).
    Extracts speeches for complete parliamentary record updates.
    
    Returns:
        Result dictionary
    """
    logger.info("🚀 Starting daily top debates flow")
    
    result = await fetch_debates_with_speeches_flow(limit=20)
    
    logger.info(f"✅ Daily top debates flow completed: {result}")
    return result


@flow(name="fetch_politician_speeches_flow")
async def fetch_politician_speeches_flow(
    politician_id: int,
    limit: int = 500
) -> Dict[str, Any]:
    """
    Fetch and store recent speeches by a politician.
    
    Useful for individual politician profile updates.
    
    Args:
        politician_id: Politician database ID
        limit: Maximum speeches to fetch
        
    Returns:
        Result dictionary
    """
    logger.info(f"🚀 Starting politician speeches flow for ID {politician_id}")
    
    # Fetch speeches
    speeches = await fetch_politician_speeches_task(politician_id, limit)
    
    if not speeches:
        logger.warning(f"No speeches found for politician {politician_id}")
        return {"politician_id": politician_id, "speeches": 0}
    
    # Store speeches
    result = await store_speeches_task(speeches)
    
    logger.info(
        f"✅ Completed politician speeches flow: "
        f"politician_id={politician_id}, speeches={result.get('stored', 0)}"
    )
    return result
