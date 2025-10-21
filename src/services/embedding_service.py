"""
Service responsible for generating text embeddings.

Uses OpenAI's embedding endpoint when an API key is configured. Falls back
to a no-op (logging warnings) when embeddings are disabled so upstream flows
can continue without failing.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Iterable, List, Optional

import httpx

DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_ENDPOINT = "https://api.openai.com/v1/embeddings"

logger = logging.getLogger(__name__)


def _word_chunks(text: str, *, max_words: int = 750) -> List[tuple[str, int, int]]:
    """
    Split text into roughly ``max_words`` sized chunks.

    Returns tuples of (chunk_text, start_char, end_char).
    """
    words = text.split()
    if not words:
        return []

    chunks: List[tuple[str, int, int]] = []
    start_idx = 0
    char_offset = 0

    while start_idx < len(words):
        end_idx = min(start_idx + max_words, len(words))
        chunk_words = words[start_idx:end_idx]
        chunk_text = " ".join(chunk_words).strip()
        if not chunk_text:
            break

        start_char = char_offset
        end_char = char_offset + len(chunk_text)
        chunks.append((chunk_text, start_char, end_char))

        char_offset = end_char + 1  # account for the space reintroduced by joining
        start_idx = end_idx

    return chunks


@dataclass
class EmbeddingChunk:
    """Output dataclass for embedding repository consumption."""

    document_id: int
    chunk_id: int
    chunk_text: str
    vector: List[float]
    token_count: int
    start_char: int
    end_char: int


class EmbeddingService:
    """Generate embeddings for document text content."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_MODEL)
        self.endpoint = endpoint
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def enabled(self) -> bool:
        """Return ``True`` when embeddings can be generated."""
        return bool(self.api_key)

    async def _client_instance(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Cleanup underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed_text(
        self,
        *,
        document_id: int,
        text: str,
        max_words: int = 750,
    ) -> List[EmbeddingChunk]:
        """
        Generate embeddings for provided text, chunking as required.

        Returns an empty list when embeddings are disabled or the text is empty.
        """
        if not self.enabled:
            logger.warning(
                "EmbeddingService disabled (missing OPENAI_API_KEY); skipping embeddings."
            )
            return []

        if not text:
            return []

        chunks = _word_chunks(text, max_words=max_words)
        if not chunks:
            return []

        client = await self._client_instance()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.model, "input": [chunk[0] for chunk in chunks]}

        try:
            response = await client.post(self.endpoint, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Embedding API error (%s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            return []
        except httpx.HTTPError as exc:
            logger.error("Embedding API request failed: %s", exc)
            return []

        json_payload = response.json()
        data = json_payload.get("data") or []
        if len(data) != len(chunks):
            logger.warning(
                "Embedding API returned %s vectors for %s chunks",
                len(data),
                len(chunks),
            )

        results: List[EmbeddingChunk] = []
        for idx, (chunk_text, start_char, end_char) in enumerate(chunks):
            vector_item = data[idx] if idx < len(data) else {}
            vector = vector_item.get("embedding") or []

            if not isinstance(vector, list) or not vector:
                logger.debug("Skipping empty embedding vector for chunk %s", idx)
                continue

            token_count = len(chunk_text.split())
            results.append(
                EmbeddingChunk(
                    document_id=document_id,
                    chunk_id=idx,
                    chunk_text=chunk_text,
                    vector=vector,
                    token_count=token_count,
                    start_char=start_char,
                    end_char=end_char,
                )
            )

        return results

    async def embed_documents(
        self,
        document_payloads: Iterable[tuple[int, str]],
        *,
        max_words: int = 750,
    ) -> List[EmbeddingChunk]:
        """
        Generate embeddings for multiple documents.

        ``document_payloads`` expects an iterable of (document_id, text_content).
        """
        results: List[EmbeddingChunk] = []
        for document_id, text in document_payloads:
            chunks = await self.embed_text(document_id=document_id, text=text, max_words=max_words)
            results.extend(chunks)
        return results

    def __del__(self) -> None:  # pragma: no cover - best effort
        if self._client and not self._client.is_closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except Exception:
                pass

