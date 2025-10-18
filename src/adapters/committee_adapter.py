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

logger = logging.getLogger(__name__)


class CommitteeAdapter(BaseAdapter):
    """Adapter for fetching committee data from OpenParliament API."""
    
    def __init__(self, api_base_url: str = "https://api.openparliament.ca"):
        super().__init__(api_base_url)
        self.source_name = "openparliament_committees"
    
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
            
            # Get committee names
            name_en = data.get("name_en") or data.get("name")
            name_fr = data.get("name_fr")
            
            # Get short names if available
            short_name_en = data.get("short_name_en") or data.get("short_name")
            short_name_fr = data.get("short_name_fr")
            
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
            if data.get("joint"):
                chamber = "Joint"
            elif "senate" in (name_en or "").lower():
                chamber = "Senate"
            
            return CommitteeData(
                committee_id=f"ca-federal-{parliament}-{session}-committee-{slug}",
                parliament=parliament,
                session=session,
                committee_slug=slug,
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
