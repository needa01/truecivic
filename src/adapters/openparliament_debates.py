"""
OpenParliament API adapter for debates and speeches.

Responsibility: Fetch debate sessions and speech transcripts from the public
OpenParliament API and expose them via the BaseAdapter contract.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote

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
        self._reset_metrics()
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
            if isinstance(session, int) and parliament:
                params["session"] = f"{parliament}-{session}"
            else:
                params["session"] = session

        fetched = 0
        sequence_counter = 0
        sequence_counter = 0

        try:
            while url and fetched < limit:
                await self.rate_limiter.acquire()
                response = await self._request_with_retries(
                    self.client.get,
                    url,
                    params=params if params else None,
                )
                response.raise_for_status()

                payload = response.json()
                objects = payload.get("objects", [])

                for raw in objects:
                    if fetched >= limit:
                        break
                    try:
                        detail = await self._fetch_debate_detail(raw)
                        normalized = self.normalize(detail or raw)
                        records.append(normalized)
                        fetched += 1
                    except Exception as exc:  # pragma: no cover
                        errors.append(
                            AdapterError(
                                timestamp=datetime.utcnow(),
                                error_type=type(exc).__name__,
                                message=str(exc),
                                context={
                                    "adapter": self.source_name,
                                    "payload": raw,
                                },
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
        *,
        speeches_url: Optional[str] = None,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch speeches for a specific debate."""
        self._reset_metrics()
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []

        # Prefer explicit speeches_url; fall back to constructing from debate path.
        url = self._api_url(speeches_url)
        if not url:
            debate_path = debate_id
            if not debate_path.startswith("/"):
                debate_path = f"/debates/{debate_path.strip('/')}/"
            encoded = quote(debate_path, safe="/")
            url = f"{self.BASE_URL}/speeches/?document={encoded}"

        params: Optional[Dict[str, Any]] = {"format": "json", "limit": min(limit, 100)}

        fetched = 0
        sequence_counter = 0

        try:
            while url and fetched < limit:
                await self.rate_limiter.acquire()
                response = await self._request_with_retries(
                    self.client.get,
                    url,
                    params=params if params else None,
                )
                response.raise_for_status()

                payload = response.json()
                speeches = payload.get("objects", [])

                for raw in speeches:
                    if fetched >= limit:
                        break
                    sequence_counter += 1
                    records.append(self._normalize_speech(raw, sequence=sequence_counter))
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
        self._reset_metrics()
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []

        url = f"{self.BASE_URL}/speeches/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(limit, 100),
            "politician": politician_id,
        }

        fetched = 0
        sequence_counter = 0

        try:
            while url and fetched < limit:
                await self.rate_limiter.acquire()
                response = await self._request_with_retries(
                    self.client.get,
                    url,
                    params=params if params else None,
                )
                response.raise_for_status()

                payload = response.json()
                speeches = payload.get("objects", [])

                for raw in speeches:
                    if fetched >= limit:
                        break
                    sequence_counter += 1
                    records.append(self._normalize_speech(raw, sequence=sequence_counter))
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

    def _api_url(self, path: Optional[str]) -> Optional[str]:
        """Convert relative API paths to absolute URLs."""
        if not path:
            return None
        if path.startswith("http"):
            return path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.BASE_URL}{path}"

    async def _fetch_debate_detail(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch enriched debate metadata (session, chamber, source URL)."""
        detail_url = self._api_url(raw.get("url"))
        if not detail_url:
            return raw

        try:
            await self.rate_limiter.acquire()
            response = await self._request_with_retries(
                self.client.get,
                detail_url,
                params={"format": "json"},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to fetch debate detail %s: %s", detail_url, exc)
            return raw

        detail = response.json()
        if isinstance(detail, dict):
            detail.setdefault("url", raw.get("url"))
            return detail
        return raw

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize debate session payload."""
        session_raw = raw_data.get("session") or {}
        parliament = None
        session_number = None
        if isinstance(session_raw, dict):
            parliament = session_raw.get("parliament")
            session_number = session_raw.get("session")
        elif isinstance(session_raw, str) and "-" in session_raw:
            parts = session_raw.split("-", 1)
            try:
                parliament = int(parts[0])
                session_number = int(parts[1])
            except ValueError:
                parliament = None
                session_number = None

        sitting = raw_data.get("sitting") or {}
        related = raw_data.get("related") or {}
        speeches_url = related.get("speeches_url") or raw_data.get("speeches_url")
        speeches_url = self._api_url(speeches_url)

        title = raw_data.get("title")
        if isinstance(title, dict):
            title_en = title.get("en")
            title_fr = title.get("fr")
        else:
            title_en = title
            title_fr = None

        hansard_id = (
            raw_data.get("source_id")
            or raw_data.get("hansard_id")
            or raw_data.get("id")
        )

        return {
            "hansard_id": str(hansard_id) if hansard_id is not None else None,
            "title_en": title_en,
            "title_fr": title_fr,
            "parliament": parliament,
            "session": session_number,
            "sitting_number": sitting.get("number") or raw_data.get("number"),
            "sitting_date": raw_data.get("date"),
            "chamber": raw_data.get("chamber") or "House of Commons",
            "debate_type": raw_data.get("type") or raw_data.get("document_type"),
            "url": raw_data.get("url"),
            "source_url": raw_data.get("source_url"),
            "speeches_url": speeches_url,
            "source": self.source_name,
            "fetched_at": datetime.utcnow().isoformat(),
        }

    def _normalize_speech(
        self,
        raw_data: Dict[str, Any],
        sequence: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Normalize speech payload."""
        attribution = raw_data.get("attribution") or {}
        content = raw_data.get("content") or {}
        if isinstance(content, dict):
            text_en = content.get("en")
            text_fr = content.get("fr")
            text_primary = text_en or text_fr
        else:
            text_primary = content
            text_en = None
            text_fr = None

        politician_slug = None
        politician_url = raw_data.get("politician_url")
        if politician_url:
            politician_slug = politician_url.strip("/").split("/")[-1]

        debate_path = raw_data.get("document_url")

        speech_id = raw_data.get("source_id") or raw_data.get("id") or raw_data.get("url")

        seq_value = sequence if sequence is not None else raw_data.get("sequence")
        if seq_value is not None:
            try:
                seq_value = int(seq_value)
            except (TypeError, ValueError):
                seq_value = None

        language = None
        if isinstance(content, dict):
            if content.get("fr") and not content.get("en"):
                language = "fr"
            elif content.get("en") and not content.get("fr"):
                language = "en"

        display_attribution = attribution.get("en") or attribution.get("fr")

        return {
            "speech_id": speech_id,
            "debate_path": debate_path,
            "politician_slug": politician_slug,
            "speaker_name": display_attribution,
            "speaker_display_name": display_attribution,
            "language": language,
            "sequence": seq_value,
            "text_content": text_primary,
            "text_content_en": text_en,
            "text_content_fr": text_fr,
            "timestamp_start": raw_data.get("time"),
            "timestamp_end": None,
            "source": self.source_name,
            "fetched_at": datetime.utcnow().isoformat(),
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
