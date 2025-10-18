"""
OpenParliament API adapter for committee metadata and meetings.

Responsibility: Fetch committee entities and meeting details from the public
OpenParliament JSON API and expose them through the BaseAdapter interface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base_adapter import BaseAdapter
from ..models.adapter_models import AdapterError, AdapterResponse
from ..utils.committee_registry import (
    SOURCE_SLUG_TO_CODE,
    CommitteeIdentifier,
    build_committee_identifier,
    ensure_internal_slug,
    resolve_source_slug,
)


class OpenParliamentCommitteeAdapter(BaseAdapter[Dict[str, Any]]):
    """Adapter for fetching committee and committee meeting data."""

    BASE_URL = "https://api.openparliament.ca"

    def __init__(self) -> None:
        super().__init__(
            source_name="openparliament_committees",
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
        limit: int = 100,
        parliament: Optional[int] = None,
        session: Optional[int] = None,
        **_: Any,
    ) -> AdapterResponse[Dict[str, Any]]:
        """
        Fetch committee metadata.

        Args:
            limit: Maximum number of committees to return.
            parliament: Optional parliament filter.
            session: Optional session filter.

        Returns:
            AdapterResponse containing committee dictionaries.
        """
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []
        errors: List[AdapterError] = []

        url = f"{self.BASE_URL}/committees/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(limit, 100),
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
                    except Exception as exc:  # pragma: no cover - defensive
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
                    params = None  # subsequent pages already include params in URL
                else:
                    url = None

            return self._build_success_response(records, errors, start_time)

        except httpx.HTTPError as exc:
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover - defensive
            return self._build_failure_response(exc, start_time, retryable=False)

    async def fetch_committee_meetings(
        self,
        committee_acronym: str,
        limit: int = 50,
        parliament: Optional[int] = None,
        session: Optional[int] = None,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch meetings for a specific committee."""
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []
        errors: List[AdapterError] = []

        slug = self._resolve_slug(committee_acronym)
        if not slug:
            return self._build_failure_response(
                ValueError(f"Unknown committee code or slug: {committee_acronym}"),
                start_time,
                retryable=False,
            )

        identifier_input = committee_acronym or slug
        if not identifier_input:
            identifier_input = slug or "UNKNOWN"
        identifier = build_committee_identifier(identifier_input)

        url = f"{self.BASE_URL}/committees/meetings/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(limit, 100),
            "committee": slug,
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
                    records.append(self._normalize_meeting(raw, identifier, slug))
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

            return self._build_success_response(records, errors, start_time)

        except httpx.HTTPError as exc:
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover
            return self._build_failure_response(exc, start_time, retryable=False)

    async def fetch_meeting_details(
        self,
        meeting_id: int,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch detailed information for a single meeting."""
        start_time = datetime.utcnow()

        url = f"{self.BASE_URL}/committees/meetings/{meeting_id}/"

        try:
            await self.rate_limiter.acquire()
            response = await self.client.get(url, params={"format": "json"})
            response.raise_for_status()
            payload = response.json()

            record = self._normalize_meeting_details(payload)
            return self._build_success_response([record], [], start_time)

        except httpx.HTTPError as exc:
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover
            return self._build_failure_response(exc, start_time, retryable=False)

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize committee metadata."""
        names = raw_data.get("name") or {}
        short_names = raw_data.get("short_name") or {}
        slug = raw_data.get("slug") or ""

        acronym = raw_data.get("acronym")
        if isinstance(acronym, dict):
            acronym_value = acronym.get("en") or acronym.get("fr")
        else:
            acronym_value = acronym

        identifier_source = acronym_value or slug
        if not identifier_source:
            raise ValueError("Committee record missing both acronym and slug")

        identifier = build_committee_identifier(identifier_source)

        return {
            "committee_code": identifier.code,
            "committee_slug": identifier.internal_slug,
            "source_slug": identifier.source_slug,
            "jurisdiction": raw_data.get("jurisdiction") or "ca",
            "name_en": names.get("en") if isinstance(names, dict) else names,
            "name_fr": names.get("fr") if isinstance(names, dict) else None,
            "chamber": raw_data.get("context", "House"),
            "committee_type": raw_data.get("type"),
            "website_url": raw_data.get("url"),
        }

    def _normalize_meeting(
        self,
        raw_data: Dict[str, Any],
        identifier: CommitteeIdentifier,
        explicit_source_slug: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Normalize meeting list record."""
        committee_url = raw_data.get("committee_url") or ""
        slug_from_url = (
            committee_url.strip("/").split("/")[1] if "/" in committee_url.strip("/") else None
        )
        resolved_source_slug = explicit_source_slug or identifier.source_slug or (
            slug_from_url.lower() if slug_from_url else None
        )

        if resolved_source_slug and resolved_source_slug in SOURCE_SLUG_TO_CODE:
            code_value = SOURCE_SLUG_TO_CODE[resolved_source_slug]
        else:
            code_value = identifier.code

        internal_slug = ensure_internal_slug(code_value)

        meeting_path = raw_data.get("url") or ""
        parts = meeting_path.strip("/").split("/")
        parliament = raw_data.get("parliament")
        session = raw_data.get("session")
        if (parliament is None or session is None) and len(parts) >= 4:
            parliament_session = parts[2].split("-")
            if len(parliament_session) == 2:
                try:
                    parliament = parliament or int(parliament_session[0])
                    session = session or int(parliament_session[1])
                except ValueError:
                    pass

        return {
            "committee_code": code_value,
            "committee_slug": internal_slug,
            "source_slug": resolved_source_slug,
            "meeting_number": raw_data.get("number"),
            "parliament": parliament,
            "session": session,
            "meeting_date": raw_data.get("date"),
            "meeting_type": raw_data.get("meeting_type"),
            "title_en": raw_data.get("title", {}).get("en")
            if isinstance(raw_data.get("title"), dict)
            else raw_data.get("title"),
            "title_fr": raw_data.get("title", {}).get("fr")
            if isinstance(raw_data.get("title"), dict)
            else None,
            "source_url": f"{self.BASE_URL}{meeting_path.lstrip('/')}" if meeting_path else None,
        }

    def _normalize_meeting_details(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize detailed meeting record including witnesses/documents."""
        committee = raw_data.get("committee") or {}
        committee_acronym = committee.get("acronym")
        if isinstance(committee_acronym, dict):
            committee_acronym = committee_acronym.get("en") or committee_acronym.get("fr")
        committee_slug_raw = committee.get("slug")
        committee_url = committee.get("url") or raw_data.get("committee_url") or raw_data.get("url") or ""
        slug_from_url = (
            committee_url.strip("/").split("/")[1] if committee_url and "/" in committee_url.strip("/") else None
        )

        identifier_source = committee_acronym or committee_slug_raw or slug_from_url or "UNKNOWN"
        identifier = build_committee_identifier(identifier_source)
        resolved_source_slug = identifier.source_slug or (committee_slug_raw.lower() if committee_slug_raw else None)

        if resolved_source_slug and resolved_source_slug in SOURCE_SLUG_TO_CODE:
            committee_code = SOURCE_SLUG_TO_CODE[resolved_source_slug]
        else:
            committee_code = identifier.code

        internal_slug = ensure_internal_slug(committee_code)

        witnesses: List[Dict[str, Any]] = []
        for entry in raw_data.get("evidence", []) or []:
            witness = entry.get("witness") or {}
            if witness:
                witnesses.append(
                    {
                        "name": witness.get("name"),
                        "organization": witness.get("organization"),
                        "title": witness.get("title"),
                    }
                )

        documents: List[Dict[str, Any]] = []
        for doc in raw_data.get("documents", []) or []:
            documents.append(
                {
                    "title": doc.get("title"),
                    "url": doc.get("url"),
                    "doc_type": doc.get("doctype"),
                }
            )

        meeting_path = raw_data.get("url") or ""
        parts = meeting_path.strip("/").split("/")
        parliament = raw_data.get("parliament")
        session = raw_data.get("session")
        if isinstance(session, str) and "-" in session:
            try:
                parliament_value, session_value = session.split("-", 1)
                parliament = int(parliament_value)
                session = int(session_value)
            except ValueError:
                pass
        elif (parliament is None or session is None) and len(parts) >= 4:
            try:
                parliament_value, session_value = parts[2].split("-", 1)
                parliament = parliament or int(parliament_value)
                session = session or int(session_value)
            except ValueError:
                pass

        return {
            "committee_code": committee_code,
            "committee_slug": internal_slug,
            "source_slug": resolved_source_slug,
            "meeting_number": raw_data.get("number"),
            "parliament": parliament,
            "session": session,
            "meeting_date": raw_data.get("date"),
            "meeting_type": raw_data.get("meeting_type"),
            "title_en": raw_data.get("title", {}).get("en")
            if isinstance(raw_data.get("title"), dict)
            else raw_data.get("title"),
            "title_fr": raw_data.get("title", {}).get("fr")
            if isinstance(raw_data.get("title"), dict)
            else None,
            "witnesses": witnesses,
            "documents": documents,
            "time_of_day": raw_data.get("start_time"),
            "source_url": f"{self.BASE_URL}{meeting_path.lstrip('/')}" if meeting_path else None,
        }

    def _resolve_slug(self, value: Optional[str]) -> Optional[str]:
        """Resolve committee codes (e.g., HUMA) to OpenParliament slugs."""
        return resolve_source_slug(value)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
