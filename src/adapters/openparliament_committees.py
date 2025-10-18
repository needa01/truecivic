"""
Adapter for fetching committee and committee meeting data.

Fetches parliamentary committees, meetings, and witness information.

Responsibility: Fetch committee data from OpenParliament and LEGISinfo APIs
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import aiohttp

from src.adapters.base_adapter import BaseAdapter
from src.models.adapter_models import AdapterResponse

logger = logging.getLogger(__name__)


class OpenParliamentCommitteeAdapter(BaseAdapter):
    """
    Adapter for fetching committee data from OpenParliament API.
    
    Endpoints:
    - /committees/ - List all committees
    - /committees/{acronym}/meetings/ - Meetings for a committee
    """
    
    BASE_URL = "https://api.openparliament.ca"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the OpenParliament committee adapter.
        
        Args:
            session: Optional aiohttp session for connection pooling
        """
        super().__init__(session)
        self.source_name = "openparliament_committees"
    
    async def fetch_committees(
        self,
        limit: int = 100
    ) -> AdapterResponse:
        """
        Fetch all parliamentary committees.
        
        Args:
            limit: Maximum number of committees to fetch
            
        Returns:
            AdapterResponse with committee records
        """
        url = f"{self.BASE_URL}/committees/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": limit
        }
        
        logger.info(f"Fetching committees: limit={limit}")
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                logger.warning(f"No committee data returned from {url}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            committees = data["objects"]
            logger.info(f"Fetched {len(committees)} committees")
            
            # Transform to standard format
            transformed = [self._transform_committee(c) for c in committees]
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(f"Error fetching committees: {str(e)}", exc_info=True)
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{
                    "error": str(e),
                    "context": "fetch_committees"
                }]
            )
    
    async def fetch_committee_meetings(
        self,
        committee_acronym: str,
        limit: int = 50,
        parliament: Optional[int] = None,
        session: Optional[int] = None
    ) -> AdapterResponse:
        """
        Fetch meetings for a specific committee.
        
        Args:
            committee_acronym: Committee acronym (e.g., 'HUMA', 'FINA')
            limit: Maximum number of meetings to fetch
            parliament: Filter by parliament number
            session: Filter by session number
            
        Returns:
            AdapterResponse with meeting records
        """
        url = f"{self.BASE_URL}/committees/{committee_acronym}/meetings/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": limit
        }
        
        if parliament:
            params["parliament"] = parliament
        if session:
            params["session"] = session
        
        logger.info(
            f"Fetching meetings for committee {committee_acronym}: "
            f"limit={limit}, parliament={parliament}, session={session}"
        )
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                logger.warning(f"No meeting data returned for {committee_acronym}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            meetings = data["objects"]
            logger.info(f"Fetched {len(meetings)} meetings for {committee_acronym}")
            
            # Transform to standard format
            transformed = [
                self._transform_meeting(m, committee_acronym) 
                for m in meetings
            ]
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(
                f"Error fetching meetings for {committee_acronym}: {str(e)}", 
                exc_info=True
            )
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{
                    "error": str(e),
                    "context": f"fetch_committee_meetings_{committee_acronym}"
                }]
            )
    
    async def fetch_meeting_details(
        self,
        meeting_id: int
    ) -> AdapterResponse:
        """
        Fetch detailed meeting information including witnesses.
        
        Args:
            meeting_id: Meeting ID from OpenParliament
            
        Returns:
            AdapterResponse with detailed meeting record
        """
        url = f"{self.BASE_URL}/committees/meetings/{meeting_id}/"
        params = {"format": "json"}
        
        logger.info(f"Fetching meeting details: {meeting_id}")
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data:
                logger.warning(f"No data for meeting {meeting_id}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params={"meeting_id": meeting_id}
                )
            
            transformed = self._transform_meeting_details(data)
            
            return AdapterResponse(
                source=self.source_name,
                records=[transformed],
                total_fetched=1,
                fetch_params={"meeting_id": meeting_id}
            )
            
        except Exception as e:
            logger.error(
                f"Error fetching meeting {meeting_id}: {str(e)}", 
                exc_info=True
            )
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params={"meeting_id": meeting_id},
                errors=[{
                    "error": str(e),
                    "context": f"fetch_meeting_details_{meeting_id}"
                }]
            )
    
    def _transform_committee(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw OpenParliament committee data.
        
        Args:
            raw_data: Raw committee data from API
            
        Returns:
            Standardized committee dictionary
        """
        names = raw_data.get("name", {})
        short_names = raw_data.get("short_name", {})
        
        return {
            "committee_code": raw_data.get("acronym", ""),
            "name_en": names.get("en", "") if isinstance(names, dict) else names,
            "name_fr": names.get("fr", "") if isinstance(names, dict) else "",
            "short_name_en": short_names.get("en", "") if isinstance(short_names, dict) else short_names,
            "short_name_fr": short_names.get("fr", "") if isinstance(short_names, dict) else "",
            "parent": raw_data.get("parent", ""),
            "chamber": raw_data.get("parent", "Commons"),  # 'Commons' or 'Senate'
            "committee_type": "standing",  # Most are standing committees
            "website_url": raw_data.get("url", ""),
            "source": "openparliament",
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def _transform_meeting(
        self, 
        raw_data: Dict[str, Any],
        committee_acronym: str
    ) -> Dict[str, Any]:
        """
        Transform raw meeting data (list view).
        
        Args:
            raw_data: Raw meeting data from API
            committee_acronym: Committee acronym
            
        Returns:
            Standardized meeting dictionary
        """
        return {
            "meeting_id": raw_data.get("id"),
            "committee_code": committee_acronym,
            "meeting_number": raw_data.get("number", 0),
            "parliament": raw_data.get("parliament", 44),
            "session": raw_data.get("session", 1),
            "meeting_date": raw_data.get("date"),
            "meeting_type": raw_data.get("meeting_type", "regular"),
            "url": raw_data.get("url", ""),
            "source": "openparliament",
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def _transform_meeting_details(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform detailed meeting data including witnesses.
        
        Args:
            raw_data: Raw detailed meeting data from API
            
        Returns:
            Standardized meeting dictionary with witnesses
        """
        committee = raw_data.get("committee", {})
        committee_acronym = committee.get("acronym", "UNKNOWN")
        
        # Extract witnesses
        witnesses = []
        evidence = raw_data.get("evidence", [])
        for item in evidence:
            witness_info = item.get("witness", {})
            if witness_info:
                witnesses.append({
                    "name": witness_info.get("name", ""),
                    "organization": witness_info.get("organization", ""),
                    "title": witness_info.get("title", "")
                })
        
        # Extract documents
        documents = []
        for doc in raw_data.get("documents", []):
            documents.append({
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "doc_type": doc.get("doctype", "")
            })
        
        return {
            "meeting_id": raw_data.get("id"),
            "committee_code": committee_acronym,
            "meeting_number": raw_data.get("number", 0),
            "parliament": raw_data.get("parliament", 44),
            "session": raw_data.get("session", 1),
            "meeting_date": raw_data.get("date"),
            "meeting_type": raw_data.get("meeting_type", "regular"),
            "title_en": raw_data.get("title", {}).get("en", "") if isinstance(raw_data.get("title"), dict) else raw_data.get("title", ""),
            "title_fr": raw_data.get("title", {}).get("fr", "") if isinstance(raw_data.get("title"), dict) else "",
            "witnesses": witnesses,
            "witness_count": len(witnesses),
            "documents": documents,
            "document_count": len(documents),
            "url": raw_data.get("url", ""),
            "source": "openparliament",
            "fetched_at": datetime.utcnow().isoformat()
        }
