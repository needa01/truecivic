"""Vote Adapter for the OpenParliament API."""

from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import logging

import httpx

from src.adapters.base_adapter import BaseAdapter
from src.models.adapter_models import (
    AdapterError,
    AdapterResponse,
    AdapterStatus,
    VoteData,
    VoteRecordData,
)

logger = logging.getLogger(__name__)


class VoteAdapter(BaseAdapter[VoteData]):
    """Adapter for fetching vote data from OpenParliament."""

    BASE_URL = "https://api.openparliament.ca"

    def __init__(self):
        super().__init__(
            source_name="openparliament_votes",
            rate_limit_per_second=2.0,
            max_retries=3,
            timeout_seconds=30,
        )
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout_seconds,
            headers={
                "User-Agent": "ParliamentExplorer/1.0 (votes)",
                "Accept": "application/json",
            },
            follow_redirects=True,
        )
        self._politician_cache: Dict[str, Optional[int]] = {}

    @staticmethod
    def _extract_text(value: Any) -> Optional[str]:
        """Normalize textual fields that may arrive as localized dictionaries."""

        if value is None:
            return None

        if isinstance(value, str):
            return value

        if isinstance(value, dict):
            for key in ("en", "fr", "value"):
                text_val = value.get(key)
                if isinstance(text_val, str) and text_val.strip():
                    return text_val

        if isinstance(value, list):
            joined = " ".join(str(item) for item in value if item)
            return joined or None

        return str(value)

    async def fetch(
        self,
        parliament: Optional[int] = None,
        session: Optional[int] = None,
        limit: int = 500,
        include_ballots: bool = False,
        **_: Any,
    ) -> AdapterResponse[VoteData]:
        """Fetch votes for a specific parliament/session."""

        if parliament is None or session is None:
            raise ValueError("parliament and session must be provided for vote fetch")

        start_time = datetime.utcnow()
        votes: List[VoteData] = []
        errors: List[AdapterError] = []

        url = "/votes/"
        params: Dict[str, Any] = {
            "session": f"{parliament}-{session}",
            "limit": min(limit, 100),
            "format": "json",
            "order_by": "-date",
        }

        fetched = 0

        try:
            while url and fetched < limit:
                await self.rate_limiter.acquire()
                response = await self.client.get(url, params=params if params else None)
                response.raise_for_status()
                payload = response.json()

                for raw_vote in payload.get("objects", []):
                    try:
                        vote = self.normalize(raw_vote, parliament=parliament, session=session)
                        if include_ballots:
                            detail_url = raw_vote.get("url")
                            if detail_url:
                                detail_vote = await self._fetch_vote_detail(
                                    detail_url,
                                    parliament=parliament,
                                    session=session,
                                    include_ballots=True,
                                )
                                if detail_vote:
                                    vote.vote_records = detail_vote.vote_records
                                    if detail_vote.bill_number and not vote.bill_number:
                                        vote.bill_number = detail_vote.bill_number
                                    vote.yeas = detail_vote.yeas
                                    vote.nays = detail_vote.nays
                                    vote.abstentions = detail_vote.abstentions
                        votes.append(vote)
                        fetched += 1
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning("Error normalizing vote: %s", exc, exc_info=True)
                        errors.append(
                            AdapterError(
                                timestamp=datetime.utcnow(),
                                error_type=type(exc).__name__,
                                message=str(exc),
                                context={"vote": raw_vote.get("url")},
                                retryable=False,
                            )
                        )

                    if fetched >= limit:
                        break

                pagination = payload.get("pagination", {})
                next_url = pagination.get("next_url")
                if next_url:
                    url = next_url if next_url.startswith("/") else next_url
                    params = None
                else:
                    url = None

            return self._build_success_response(votes, errors, start_time)

        except httpx.HTTPError as exc:
            logger.error("HTTP error fetching votes: %s", exc, exc_info=True)
            return self._build_failure_response(exc, start_time, retryable=True)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Unexpected vote fetch error: %s", exc, exc_info=True)
            return self._build_failure_response(exc, start_time, retryable=False)

    def normalize(
        self,
        raw_data: Dict[str, Any],
        parliament: Optional[int] = None,
        session: Optional[int] = None,
    ) -> VoteData:
        """Normalize OpenParliament vote payload to VoteData."""

        session_info = raw_data.get("session")
        parliament_num = parliament
        session_num = session

        if not parliament_num or not session_num:
            if isinstance(session_info, dict):
                parliament_num = parliament_num or session_info.get("parliamentnum") or session_info.get("parliament")
                session_num = session_num or session_info.get("sessnum") or session_info.get("session")
            elif isinstance(session_info, str):
                parts = session_info.split("-")
                if len(parts) >= 2:
                    parliament_num = parliament_num or parts[0]
                    session_num = session_num or parts[1]

        if parliament_num is None or session_num is None:
            raise ValueError("Vote payload missing parliament/session metadata")

        number = raw_data.get("number")
        if not number:
            raise ValueError("Vote record missing number")

        date_str = raw_data.get("date")
        vote_date = (
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if date_str
            else None
        )

        vote_total = raw_data.get("vote_total") or {}
        yeas = vote_total.get("yea") if isinstance(vote_total, dict) else None
        nays = vote_total.get("nay") if isinstance(vote_total, dict) else None
        abstentions = vote_total.get("paired") if isinstance(vote_total, dict) else None

        if yeas is None:
            yeas = raw_data.get("yea_total")
        if nays is None:
            nays = raw_data.get("nay_total")
        if abstentions is None:
            abstentions = raw_data.get("paired_total")

        bill_number = self._extract_bill_number(raw_data)

        description_en = self._extract_text(raw_data.get("description_en"))
        description_fr = self._extract_text(raw_data.get("description_fr"))
        if not description_en:
            description_en = self._extract_text(raw_data.get("description"))
        if not description_fr:
            description_fr = self._extract_text(raw_data.get("description"))

        return VoteData(
            vote_id=f"ca-federal-{parliament_num}-{session_num}-vote-{number}",
            parliament=int(parliament_num),
            session=int(session_num),
            vote_number=number,
            chamber=(raw_data.get("chamber") or "House"),
            vote_date=vote_date,
            vote_description_en=description_en,
            vote_description_fr=description_fr,
            bill_number=bill_number,
            result=raw_data.get("result", "Unknown"),
            yeas=int(yeas or 0),
            nays=int(nays or 0),
            abstentions=int(abstentions or 0),
            vote_records=[],
        )

    async def _fetch_vote_detail(
        self,
        url: str,
        parliament: Optional[int] = None,
        session: Optional[int] = None,
        include_ballots: bool = False,
    ) -> Optional[VoteData]:
        """Fetch detailed vote information and optionally ballots."""

        try:
            await self.rate_limiter.acquire()
            response = await self.client.get(url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - defensive
            logger.warning("Failed to fetch vote detail: %s", exc, exc_info=True)
            return None

        vote = self.normalize(payload, parliament=parliament, session=session)

        if include_ballots:
            ballots_url = payload.get("related", {}).get("ballots_url")
            if ballots_url:
                vote.vote_records = await self._fetch_ballots(ballots_url)

        return vote

    async def fetch_votes_for_session(
        self,
        parliament: int,
        session: int,
        limit: int = 500,
        include_ballots: bool = False,
    ) -> List[VoteData]:
        """Convenience wrapper returning a plain list of VoteData."""

        response = await self.fetch(
            parliament=parliament,
            session=session,
            limit=limit,
            include_ballots=include_ballots,
        )

        if response.status == AdapterStatus.FAILURE:
            raise RuntimeError(
                f"Vote fetch failed: {response.errors[0].message if response.errors else 'unknown error'}"
            )

        return response.data or []

    async def fetch_vote_detail(self, vote_url: str) -> Optional[VoteData]:
        """Fetch individual vote with ballots using detail endpoint."""

        return await self._fetch_vote_detail(vote_url, include_ballots=True)

    async def _fetch_ballots(self, url: str) -> List[VoteRecordData]:
        """Fetch all ballot records for a vote."""

        records: List[VoteRecordData] = []
        next_url: Optional[str] = url
        params: Optional[Dict[str, Any]] = None

        while next_url:
            try:
                await self.rate_limiter.acquire()
                response = await self.client.get(next_url, params=params)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:  # pragma: no cover - defensive
                logger.warning("Failed to fetch ballots %s: %s", next_url, exc, exc_info=True)
                break

            for ballot in payload.get("objects", []):
                record = await self._parse_ballot(ballot)
                if record:
                    records.append(record)

            pagination = payload.get("pagination", {})
            next_link = pagination.get("next_url")
            if next_link:
                next_url = next_link if next_link.startswith("/") else next_link
                params = None
            else:
                next_url = None

        return records

    async def _parse_ballot(self, ballot: Dict[str, Any]) -> Optional[VoteRecordData]:
        """Convert a ballot payload to VoteRecordData."""

        ballot_vote = ballot.get("ballot")
        if not ballot_vote:
            return None

        politician_path = ballot.get("politician_url")
        politician_id = await self._get_politician_id(politician_path)
        if not politician_id:
            return None

        return VoteRecordData(
            politician_id=politician_id,
            vote_position=str(ballot_vote).title(),
        )

    async def _get_politician_id(self, politician_path: Optional[str]) -> Optional[int]:
        """Resolve a politician path to a numeric ID (cached)."""

        if not politician_path:
            return None

        normalized = politician_path.strip("/")
        if not normalized:
            return None

        if normalized in self._politician_cache:
            return self._politician_cache[normalized]

        parts = normalized.split("/")
        identifier = parts[-1]

        if identifier.isdigit():
            result = int(identifier)
            self._politician_cache[normalized] = result
            return result

        lookup_url = f"/politicians/{identifier}/"

        try:
            await self.rate_limiter.acquire()
            response = await self.client.get(lookup_url)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - defensive
            logger.warning("Failed to fetch politician %s: %s", identifier, exc, exc_info=True)
            self._politician_cache[normalized] = None
            return None

        activity_url = payload.get("related", {}).get("activity_rss_url")
        numeric_id = self._extract_digits(activity_url)

        if numeric_id is None:
            other_ids = payload.get("other_info", {}).get("parl_mp_id")
            if other_ids:
                numeric_id = self._extract_digits(other_ids[0])

        self._politician_cache[normalized] = numeric_id
        return numeric_id

    @staticmethod
    def _extract_digits(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        match = re.findall(r"\d+", str(value))
        if not match:
            return None
        try:
            return int(match[-1])
        except ValueError:  # pragma: no cover - defensive
            return None

    @staticmethod
    def _extract_bill_number(raw_data: Dict[str, Any]) -> Optional[str]:
        """Determine bill number from vote payload."""

        bill = raw_data.get("bill")
        if isinstance(bill, dict):
            number = bill.get("number")
            if number:
                return str(number).upper()

        bill_url = raw_data.get("bill_url")
        if isinstance(bill_url, str) and bill_url.strip():
            parts = bill_url.strip("/").split("/")
            if parts:
                return parts[-1].upper()

        related_bill_url = raw_data.get("related", {}).get("bill_url") if isinstance(raw_data.get("related"), dict) else None
        if isinstance(related_bill_url, str) and related_bill_url.strip():
            parts = related_bill_url.strip("/").split("/")
            if parts:
                return parts[-1].upper()

        return None

    async def fetch_latest_votes(self, limit: int = 50) -> List[VoteData]:
        """Fetch the most recent votes regardless of session."""

        start_time = datetime.utcnow()
        votes: List[VoteData] = []
        errors: List[AdapterError] = []

        try:
            await self.rate_limiter.acquire()
            response = await self.client.get(
                "/votes/",
                params={"limit": limit, "format": "json", "order_by": "-date"},
            )
            response.raise_for_status()
            payload = response.json()

            for raw_vote in payload.get("objects", []):
                try:
                    vote = self.normalize(raw_vote)
                    votes.append(vote)
                except Exception as exc:  # pragma: no cover - defensive
                    errors.append(
                        AdapterError(
                            timestamp=datetime.utcnow(),
                            error_type=type(exc).__name__,
                            message=str(exc),
                            context={"vote": raw_vote.get("url")},
                            retryable=False,
                        )
                    )

            response_obj = self._build_success_response(votes, errors, start_time)
            return response_obj.data or []

        except httpx.HTTPError as exc:  # pragma: no cover - defensive
            logger.error("HTTP error fetching latest votes: %s", exc, exc_info=True)
            raise

    async def close(self) -> None:
        """Close the underlying HTTP client."""

        await self.client.aclose()
