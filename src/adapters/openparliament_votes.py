"""
OpenParliament API adapter for vote metadata and roll-call records.

Responsibility: Fetch vote summaries and individual MP ballots.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base_adapter import BaseAdapter
from ..models.adapter_models import AdapterError, AdapterResponse


class OpenParliamentVotesAdapter(BaseAdapter[Dict[str, Any]]):
    """Adapter for OpenParliament vote endpoints."""

    BASE_URL = "https://api.openparliament.ca"

    def __init__(self) -> None:
        super().__init__(
            source_name="openparliament_votes",
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
        bill: Optional[str] = None,
        session: Optional[int] = None,
        **_: Any,
    ) -> AdapterResponse[Dict[str, Any]]:
        """
        Fetch vote summaries.

        Args:
            limit: Maximum number of votes to retrieve.
            offset: Result offset for pagination.
            parliament: Optional parliament filter.
            session: Optional session filter.

        Returns:
            AdapterResponse containing vote dictionaries.
        """
        start_time = datetime.utcnow()
        records: List[Dict[str, Any]] = []
        errors: List[AdapterError] = []

        url = f"{self.BASE_URL}/votes/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": min(limit, 100),
            "offset": offset,
        }
        if parliament:
            params["parliament"] = parliament
        if session:
            params["session"] = session
        if bill:
            params["bill"] = bill

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

    async def fetch_vote_by_id(
        self,
        vote_id: str,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch a specific vote with MP ballots."""
        start_time = datetime.utcnow()
        url = f"{self.BASE_URL}/votes/{vote_id}/"

        try:
            await self.rate_limiter.acquire()
            response = await self.client.get(url, params={"format": "json"})
            response.raise_for_status()

            payload = response.json()
            record = self._normalize_vote_with_records(payload)
            return self._build_success_response([record], [], start_time)

        except httpx.HTTPError as exc:
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover
            return self._build_failure_response(exc, start_time, retryable=False)

    async def fetch_votes_for_bill(
        self,
        bill_number: str,
        limit: int = 100,
    ) -> AdapterResponse[Dict[str, Any]]:
        """Fetch all votes associated with a specific bill number."""
        return await self.fetch(limit=limit, bill=bill_number)

    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize vote summary payload."""
        vote_number = raw_data.get("number", "")
        parliament = None
        session = None
        vote_sequence = None
        if vote_number:
            parts = vote_number.split("-")
            if len(parts) >= 1:
                try:
                    parliament = int(parts[0])
                except ValueError:
                    parliament = None
            if len(parts) >= 2:
                try:
                    session = int(parts[1])
                except ValueError:
                    session = None
            if len(parts) >= 3:
                try:
                    vote_sequence = int(parts[2])
                except ValueError:
                    vote_sequence = None

        bill_number = None
        bill_payload = raw_data.get("bill")
        if isinstance(bill_payload, dict):
            bill_number = bill_payload.get("number")

        description = raw_data.get("description") or {}

        return {
            "jurisdiction": "ca",
            "vote_id": vote_number,
            "parliament": parliament,
            "session": session,
            "vote_number": vote_sequence,
            "chamber": raw_data.get("context", "House"),
            "vote_date": self._parse_date(raw_data.get("date")),
            "vote_description_en": description.get("en")
            if isinstance(description, dict)
            else None,
            "vote_description_fr": description.get("fr")
            if isinstance(description, dict)
            else None,
            "bill_number": bill_number,
            "result": raw_data.get("result"),
            "yeas": raw_data.get("yea_total", 0),
            "nays": raw_data.get("nay_total", 0),
            "abstentions": raw_data.get("paired_total", 0),
        }

    def _normalize_vote_with_records(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a vote payload including MP ballots."""
        vote = self.normalize(raw_data)
        ballots = []
        for ballot in raw_data.get("ballots") or []:
            politician = ballot.get("politician") or {}
            membership = ballot.get("politician_membership") or {}
            riding = membership.get("riding") or {}
            riding_name = None
            if isinstance(riding.get("name"), dict):
                riding_name = riding["name"].get("en")
            ballots.append(
                {
                    "politician_id": politician.get("id"),
                    "politician_name": politician.get("name"),
                    "party": ballot.get("party", {}).get("short_name"),
                    "riding": riding_name,
                    "vote_position": ballot.get("vote"),
                }
            )

        vote["mp_votes"] = ballots
        vote["mp_vote_count"] = len(ballots)
        return vote

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string into datetime."""
        if not value:
            return None
        try:
            if "T" in value:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self.client.aclose()
