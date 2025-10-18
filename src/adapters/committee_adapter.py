"""
Committee Adapter for OpenParliament API.

Fetches parliamentary committee data including committee info and meetings.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.adapter_models import CommitteeData
from src.adapters.base_adapter import BaseAdapter
from src.utils.committee_registry import build_committee_identifier, resolve_source_slug

logger = logging.getLogger(__name__)


class CommitteeAdapter(BaseAdapter[CommitteeData]):
    """Adapter for fetching committee data from OpenParliament API."""
    
    def __init__(self, api_base_url: str = "https://api.openparliament.ca"):
        super().__init__(
            source_name="openparliament_committees",
            rate_limit_per_second=1.0,
            max_retries=3,
            timeout_seconds=30,
        )
        self.api_base_url = api_base_url
    
    async def fetch(self, **kwargs: Any):  # type: ignore[override]
        """Generic fetch is not implemented for this legacy adapter."""
        raise NotImplementedError(
            "Use fetch_committees_for_session or fetch_all_committees instead."
        )

    def normalize(self, raw_data: Any) -> CommitteeData:  # type: ignore[override]
        """Normalization is handled by specialized parser helpers."""
        raise NotImplementedError(
            "CommitteeAdapter uses _parse_committee for normalization."
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_committees_for_session(
        self,
        parliament: int,
        session: int,
        limit: int = 100
    ) -> List[CommitteeData]:
        """
        Fetch all committees for a given parliament session.
        
        Args:
            parliament: Parliament number (e.g., 44)
            session: Session number (e.g., 1)
            limit: Results per page
            
        Returns:
            List of CommitteeData objects
        """
        committees = []
        url = f"{self.api_base_url}/committees/"
        params = {
            "session": f"{parliament}-{session}",
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching committees for Parliament {parliament}, Session {session}")
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while url:
                response = await client.get(url, params=params if url == f"{self.api_base_url}/committees/" else None)
                response.raise_for_status()
                data = response.json()
                
                for committee_obj in data.get("objects", []):
                    try:
                        committee = self._parse_committee(committee_obj, parliament, session)
                        if committee:
                            committees.append(committee)
                    except Exception as e:
                        logger.error(f"Error parsing committee: {e}")
                
                # Get next page
                url = data.get("pagination", {}).get("next_url")
                if url:
                    url = f"{self.api_base_url}{url}" if url.startswith("/") else url
                params = None
        
        logger.info(f"Fetched {len(committees)} committees for {parliament}-{session}")
        return committees
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_committee_detail(self, committee_slug: str, parliament: int, session: int) -> Optional[CommitteeData]:
        """
        Fetch detailed committee information.
        
        Args:
            committee_slug: Committee slug/acronym (e.g., "HUMA")
            parliament: Parliament number
            session: Session number
            
        Returns:
            CommitteeData object
        """
        url = f"{self.api_base_url}/committees/{committee_slug}/"
        params = {
            "session": f"{parliament}-{session}",
            "format": "json"
        }
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_committee(data, parliament, session)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_committee_activities(
        self,
        committee_slug: str,
        parliament: int,
        session: int,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Fetch committee activities (meetings, reports, etc.).
        
        Args:
            committee_slug: Committee slug/acronym
            parliament: Parliament number
            session: Session number
            limit: Results per page
            
        Returns:
            List of activity dictionaries
        """
        activities = []
        url = f"{self.api_base_url}/committees/{committee_slug}/activities/"
        params = {
            "session": f"{parliament}-{session}",
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching activities for committee {committee_slug}")
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            while url:
                response = await client.get(url, params=params if "/activities/" in url and "?" not in url else None)
                response.raise_for_status()
                data = response.json()
                
                for activity_obj in data.get("objects", []):
                    activities.append(activity_obj)
                
                # Get next page
                url = data.get("pagination", {}).get("next_url")
                if url:
                    url = f"{self.api_base_url}{url}" if url.startswith("/") else url
                params = None
        
        logger.info(f"Fetched {len(activities)} activities for committee {committee_slug}")
        return activities
    
    def _parse_committee(self, data: Dict[str, Any], parliament: int, session: int) -> Optional[CommitteeData]:
        """Parse committee data from API response."""
        try:
            # Extract committee identifiers
            slug = data.get("slug")
            acronym = data.get("acronym", {})

            if not slug:
                return None

            # Get acronym based on language
            acronym_en = acronym.get("en") if isinstance(acronym, dict) else acronym
            acronym_fr = acronym.get("fr") if isinstance(acronym, dict) else None

            identifier_seed = acronym_en or slug
            identifier = build_committee_identifier(identifier_seed)
            internal_slug = identifier.internal_slug
            source_slug = resolve_source_slug(slug) or identifier.source_slug
            
            # Get committee names
            name_en_raw = data.get("name_en") or data.get("name")
            name_fr_raw = data.get("name_fr") or data.get("name")

            if isinstance(name_en_raw, dict):
                name_en = name_en_raw.get("en") or name_en_raw.get("fr")
            else:
                name_en = name_en_raw

            if isinstance(name_fr_raw, dict):
                name_fr = name_fr_raw.get("fr") or name_fr_raw.get("en")
            else:
                name_fr = name_fr_raw
            
            # Get short names if available
            short_name_en_raw = data.get("short_name_en") or data.get("short_name")
            short_name_fr_raw = data.get("short_name_fr") or data.get("short_name")

            if isinstance(short_name_en_raw, dict):
                short_name_en = short_name_en_raw.get("en") or short_name_en_raw.get("fr")
            else:
                short_name_en = short_name_en_raw

            if isinstance(short_name_fr_raw, dict):
                short_name_fr = short_name_fr_raw.get("fr") or short_name_fr_raw.get("en")
            else:
                short_name_fr = short_name_fr_raw
            
            # Determine parent committee (for subcommittees)
            parent_committee = data.get("parent")
            parent_slug = None
            if parent_committee:
                if isinstance(parent_committee, dict):
                    parent_slug = parent_committee.get("slug")
                elif isinstance(parent_committee, str):
                    parent_slug = parent_committee
            
            # Committee type/chamber
            chamber = "House"  # Most committees are House committees
            normalized_name_en = (name_en or "") if isinstance(name_en, str) else str(name_en or "")

            if data.get("joint"):
                chamber = "Joint"
            elif "senate" in normalized_name_en.lower():
                chamber = "Senate"
            
            return CommitteeData(
                committee_id=f"ca-federal-{parliament}-{session}-committee-{identifier.code}",
                parliament=parliament,
                session=session,
                committee_slug=internal_slug,
                source_slug=source_slug,
                acronym_en=acronym_en,
                acronym_fr=acronym_fr,
                name_en=name_en,
                name_fr=name_fr,
                short_name_en=short_name_en,
                short_name_fr=short_name_fr,
                chamber=chamber,
                parent_committee=parent_slug
            )
            
        except Exception as e:
            logger.error(f"Error parsing committee data: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_all_committees(self, limit: int = 100) -> List[CommitteeData]:
        """
        Fetch all committees across all sessions.
        
        Args:
            limit: Results per page
            
        Returns:
            List of CommitteeData objects
        """
        committees = []
        url = f"{self.api_base_url}/committees/"
        params = {
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching all committees")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(url, params=params if url == f"{self.api_base_url}/committees/" else None)
                response.raise_for_status()
                data = response.json()
                
                for committee_obj in data.get("objects", []):
                    try:
                        # Extract session info
                        session_info = committee_obj.get("sessions", [])
                        if session_info:
                            # Get most recent session
                            latest_session = session_info[0] if isinstance(session_info, list) else session_info
                            if isinstance(latest_session, dict):
                                parliament = latest_session.get("parliamentnum", 44)
                                session = latest_session.get("sessnum", 1)
                            else:
                                # Parse from string like "44-1"
                                parts = str(latest_session).split("-")
                                parliament = int(parts[0]) if len(parts) > 0 else 44
                                session = int(parts[1]) if len(parts) > 1 else 1
                        else:
                            # Default to current parliament/session
                            parliament = 44
                            session = 1
                        
                        committee = self._parse_committee(committee_obj, parliament, session)
                        if committee:
                            committees.append(committee)
                    except Exception as e:
                        logger.error(f"Error parsing committee: {e}")
                
                # Get next page
                url = data.get("pagination", {}).get("next_url")
                if url:
                    url = f"{self.api_base_url}{url}" if url.startswith("/") else url
                params = None
        
        logger.info(f"Fetched {len(committees)} total committees")
        return committees
