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
        self._reset_metrics()
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
        self._reset_metrics()
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
        self._reset_metrics()
        start_time = datetime.utcnow()

        url = f"{self.BASE_URL}/committees/meetings/{meeting_id}/"

        try:
            await self.rate_limiter.acquire()
            response = await self._request_with_retries(
                self.client.get,
                url,
                params={"format": "json"},
            )
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
            acronym_en = acronym.get("en") or acronym.get("fr")
            acronym_fr = acronym.get("fr") or acronym.get("en")
        else:
            acronym_en = acronym
            acronym_fr = None

        identifier_source = acronym_en or slug
        if not identifier_source:
            raise ValueError("Committee record missing both acronym and slug")

        identifier = build_committee_identifier(identifier_source)

        sessions = raw_data.get("sessions") or []
        parliament: Optional[int] = None
        session: Optional[int] = None
        session_acronym: Optional[str] = None
        session_source_url: Optional[str] = None
        if isinstance(sessions, list):
            for entry in sessions:
                if not isinstance(entry, dict):
                    continue
                session_str = entry.get("session")
                if session_str and isinstance(session_str, str) and "-" in session_str:
                    parts = session_str.split("-", 1)
                    try:
                        parliament = parliament or int(parts[0])
                        session = session or int(parts[1])
                    except ValueError:
                        pass
                parliament = parliament or entry.get("parliamentnum")
                session = session or entry.get("sessnum")
                session_acronym = session_acronym or entry.get("acronym")
                session_source_url = session_source_url or entry.get("source_url")
                if parliament is not None and session is not None:
                    break

        if parliament is None:
            parliament = 44
        if session is None:
            session = 1

        acronym_en = (acronym_en or session_acronym or identifier.code or "").upper()
        acronym_fr = (acronym_fr or session_acronym or acronym_en or "").upper() or None

        short_name_en = (
            short_names.get("en")
            if isinstance(short_names, dict)
            else short_names
        )
        short_name_fr = (
            short_names.get("fr")
            if isinstance(short_names, dict)
            else None
        )

        parent_url = raw_data.get("parent_url")
        parent_committee: Optional[str] = None
        if isinstance(parent_url, str) and parent_url.strip():
            parent_slug = parent_url.strip("/").split("/")[-1]
            try:
                parent_identifier = build_committee_identifier(parent_slug)
                parent_committee = parent_identifier.internal_slug
            except ValueError:
                parent_committee = parent_slug

        source_url = raw_data.get("url")
        if isinstance(source_url, str) and source_url:
            source_url = f"{self.BASE_URL}{source_url.lstrip('/')}"
        else:
            source_url = None
        if session_source_url:
            source_url = session_source_url

        name_en = names.get("en") if isinstance(names, dict) else names
        name_fr = names.get("fr") if isinstance(names, dict) else None
        if not short_name_en:
            short_name_en = name_en
        if not short_name_fr:
            short_name_fr = name_fr

        return {
            "committee_code": identifier.code,
            "committee_slug": identifier.internal_slug,
            "source_slug": identifier.source_slug,
            "jurisdiction": "ca-federal",
            "name_en": name_en,
            "name_fr": name_fr,
            "short_name_en": short_name_en,
            "short_name_fr": short_name_fr,
            "acronym_en": acronym_en or identifier.code,
            "acronym_fr": acronym_fr or acronym_en or identifier.code,
            "parliament": parliament,
            "session": session,
            "parent_committee": parent_committee,
            "chamber": raw_data.get("context", "House"),
            "committee_type": raw_data.get("type"),
            "website_url": source_url,
            "source_url": source_url,
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
