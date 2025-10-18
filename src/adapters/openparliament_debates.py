"""
OpenParliament API adapter for debates and speeches.

Responsibility: Fetch debate sessions and speech transcripts from the public
OpenParliament API and expose them via the BaseAdapter contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base_adapter import BaseAdapter
from ..models.adapter_models import AdapterError, AdapterResponse


class OpenParliamentDebatesAdapter(BaseAdapter[Dict[str, Any]]):
    """Adapter for OpenParliament debate endpoints."""

    BASE_URL = "https://api.openparliament.ca"

    def __init__(self) -> None:
        super().__init__(
            source_name="openparliament_debates",
            rate_limit_per_second=1.0,
            max_retries=3,
            timeout_seconds=30,
        )
        self.client = httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={
                "User-Agent": "ParliamentExplorer/1.0 (production)",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )

    async def fetch(
        self,
        limit: int = 50,
        offset: int = 0,
        parliament: Optional[int] = None,
        session: Optional[int] = None,
        **_: Any,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch debate sessions."""
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []
        errors: List[AdapterError] = []

        url = f"{self.BASE_URL}/debates/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(limit, 100),
            "offset": offset,
        }
        if parliament:
            params["parliament"] = parliament
        if session:
            params["session"] = session

        fetched = 0

        try:
            while url and fetched < limit:
                await self.rate_limiter.acquire()
                response = await self.client.get(url, params=params if params else None)
                response.raise_for_status()

                payload = response.json()
                objects = payload.get("objects", [])

                for raw in objects:
                    if fetched >= limit:
                        break
                    try:
                        records.append(self.normalize(raw))
                        fetched += 1
                    except Exception as exc:  # pragma: no cover
                        errors.append(
                            AdapterError(
                                timestamp=datetime.utcnow(),
                                error_type=type(exc).__name__,
                                message=str(exc),
                                context={"adapter": self.source_name, "payload": raw},
                                retryable=False,
                            )
                        )

                next_url = payload.get("pagination", {}).get("next_url")
                if next_url and fetched < limit:
                    url = (
                        f"{self.BASE_URL}{next_url}"
                        if next_url.startswith("/")
                        else next_url
                    )
                    params = None
                else:
                    url = None

            return self._build_success_response(records, errors, start_time)

        except httpx.HTTPError as exc:
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover
            return self._build_failure_response(exc, start_time, retryable=False)

    async def fetch_speeches_for_debate(
        self,
        debate_id: str,
        limit: int = 500,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch speeches for a specific debate."""
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []

        url = f"{self.BASE_URL}/debates/{debate_id}/speeches/"
        params: Dict[str, Any] = {"format": "json", "limit": min(limit, 100)}

        fetched = 0

        try:
            while url and fetched < limit:
                await self.rate_limiter.acquire()
                response = await self.client.get(url, params=params if params else None)
                response.raise_for_status()

                payload = response.json()
                speeches = payload.get("objects", [])

                for raw in speeches:
                    if fetched >= limit:
                        break
                    records.append(self._normalize_speech(raw))
                    fetched += 1

                next_url = payload.get("pagination", {}).get("next_url")
                if next_url and fetched < limit:
                    url = (
                        f"{self.BASE_URL}{next_url}"
                        if next_url.startswith("/")
                        else next_url
                    )
                    params = None
                else:
                    url = None

            return self._build_success_response(records, [], start_time)

        except httpx.HTTPError as exc:
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover
            return self._build_failure_response(exc, start_time, retryable=False)

    async def fetch_speeches_for_politician(
        self,
        politician_id: int,
        limit: int = 500,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch speeches delivered by a specific politician."""
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []

        url = f"{self.BASE_URL}/speeches/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(limit, 100),
            "politician": politician_id,
        }

        fetched = 0

        try:
            while url and fetched < limit:
                await self.rate_limiter.acquire()
                response = await self.client.get(url, params=params if params else None)
                response.raise_for_status()

                payload = response.json()
                speeches = payload.get("objects", [])

                for raw in speeches:
                    if fetched >= limit:
                        break
                    records.append(self._normalize_speech(raw))
                    fetched += 1

                next_url = payload.get("pagination", {}).get("next_url")
                if next_url and fetched < limit:
                    url = (
                        f"{self.BASE_URL}{next_url}"
                        if next_url.startswith("/")
                        else next_url
                    )
                    params = None
                else:
                    url = None

            return self._build_success_response(records, [], start_time)

        except httpx.HTTPError as exc:
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover
            return self._build_failure_response(exc, start_time, retryable=False)

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize debate session payload."""
        session = raw_data.get("session") or {}
        sitting = raw_data.get("sitting") or {}

        return {
            "hansard_id": raw_data.get("hansard_id") or raw_data.get("id"),
            "title_en": raw_data.get("title", {}).get("en")
            if isinstance(raw_data.get("title"), dict)
            else raw_data.get("title"),
            "title_fr": raw_data.get("title", {}).get("fr")
            if isinstance(raw_data.get("title"), dict)
            else None,
            "parliament": session.get("parliament"),
            "session": session.get("session"),
            "sitting_number": sitting.get("number"),
            "sitting_date": raw_data.get("date"),
            "chamber": raw_data.get("chamber"),
            "debate_type": raw_data.get("type"),
            "url": raw_data.get("url"),
            "source": self.source_name,
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def _normalize_speech(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize speech payload."""
        politician = raw_data.get("politician") or {}
        content = raw_data.get("content") or {}
        if isinstance(content, dict):
            text_en = content.get("en")
            text_fr = content.get("fr")
            text_primary = text_en or text_fr
        else:
            text_primary = content
            text_en = None
            text_fr = None

        debate = raw_data.get("debate") or {}
        debate_id = debate.get("id") if isinstance(debate, dict) else debate

        return {
            "speech_id": raw_data.get("id"),
            "debate_id": debate_id,
            "politician_id": politician.get("id"),
            "speaker_name": politician.get("name") or raw_data.get("speaker"),
            "language": raw_data.get("language"),
            "sequence": raw_data.get("sequence"),
            "text_content": text_primary,
            "text_content_en": text_en,
            "text_content_fr": text_fr,
            "timestamp_start": raw_data.get("time"),
            "timestamp_end": raw_data.get("end_time"),
            "source": self.source_name,
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
