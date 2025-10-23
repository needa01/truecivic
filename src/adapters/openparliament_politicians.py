"""
Adapter for fetching politician/MP data from OpenParliament API.

Fetches current and historical MP information including party
affiliations, ridings, and membership history.

Responsibility: Fetch politician data from OpenParliament API
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import aiohttp

from src.adapters.base_adapter import BaseAdapter
from src.models.adapter_models import AdapterResponse

logger = logging.getLogger(__name__)


class OpenParliamentPoliticiansAdapter(BaseAdapter):
    """
    Adapter for fetching politician data from OpenParliament API.
    
    Endpoints:
    - /politicians/ - List all politicians
    - /politicians/{id}/ - Individual politician details
    """
    
    BASE_URL = "https://api.openparliament.ca"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the OpenParliament politicians adapter.
        
        Args:
            session: Optional aiohttp session for connection pooling
        """
        super().__init__(session)
        self.source_name = "openparliament_politicians"
    
    async def fetch_politicians(
        self,
        limit: int = 100,
        offset: int = 0,
        riding: Optional[str] = None,
        party: Optional[str] = None
    ) -> AdapterResponse:
        """
        Fetch politicians from OpenParliament API.
        
        Args:
            limit: Maximum number of politicians to fetch
            offset: Offset for pagination
            riding: Filter by riding name
            party: Filter by party name
            
        Returns:
            AdapterResponse with politician records
        """
        url = f"{self.BASE_URL}/politicians/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": limit,
            "offset": offset
        }
        
        if riding:
            params["riding"] = riding
        if party:
            params["party"] = party
        
        logger.info(
            f"Fetching politicians: limit={limit}, offset={offset}, "
            f"riding={riding}, party={party}"
        )
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                logger.warning(f"No politician data returned from {url}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            politicians = data["objects"]
            logger.info(f"Fetched {len(politicians)} politicians")
            
            # Transform to standard format
            transformed = [self._transform_politician(p) for p in politicians]
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(f"Error fetching politicians: {str(e)}", exc_info=True)
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{
                    "error": str(e),
                    "context": "fetch_politicians"
                }]
            )
    
    async def fetch_politician_by_id(self, politician_id: int) -> AdapterResponse:
        """
        Fetch a single politician by ID.
        
        Args:
            politician_id: OpenParliament politician ID
            
        Returns:
            AdapterResponse with single politician record
        """
        url = f"{self.BASE_URL}/politicians/{politician_id}/"
        params = {"format": "json"}
        
        logger.info(f"Fetching politician ID: {politician_id}")
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data:
                logger.warning(f"No data for politician ID {politician_id}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params={"politician_id": politician_id}
                )
            
            transformed = self._transform_politician(data)
            
            return AdapterResponse(
                source=self.source_name,
                records=[transformed],
                total_fetched=1,
                fetch_params={"politician_id": politician_id}
            )
            
        except Exception as e:
            logger.error(
                f"Error fetching politician {politician_id}: {str(e)}",
                exc_info=True
            )
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params={"politician_id": politician_id},
                errors=[{
                    "error": str(e),
                    "politician_id": politician_id
                }]
            )
    
    async def fetch_current_mps(self) -> AdapterResponse:
        """
        Fetch all current MPs (members in current parliament).
        
        Returns:
            AdapterResponse with current MPs
        """
        # OpenParliament marks current MPs with current=true
        url = f"{self.BASE_URL}/politicians/"
        params = {
            "format": "json",
            "limit": 400,  # Max MPs in House
            "current": "true"
        }
        
        logger.info("Fetching all current MPs")
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            politicians = data["objects"]
            transformed = [self._transform_politician(p) for p in politicians]
            
            logger.info(f"Fetched {len(transformed)} current MPs")
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(f"Error fetching current MPs: {str(e)}", exc_info=True)
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{"error": str(e)}]
            )
    
    def _transform_politician(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw OpenParliament politician data to standard format.
        
        Args:
            raw_data: Raw politician data from API
            
        Returns:
            Standardized politician dictionary
        """
        # Extract current membership if available
        current_membership = None
        memberships = []
        
        if "memberships" in raw_data and raw_data["memberships"]:
            memberships = raw_data["memberships"]
            # Find current membership (no end_date or most recent)
            current = [m for m in memberships if not m.get("end_date")]
            if current:
                current_membership = current[0]
        
        return {
            "id": raw_data.get("id"),
            "name": raw_data.get("name", ""),
            "given_name": raw_data.get("given_name"),
            "family_name": raw_data.get("family_name"),
            "gender": raw_data.get("gender"),
            "email": raw_data.get("email"),
            "image_url": raw_data.get("image"),
            "url": raw_data.get("url"),
            
            # Current info
            "current_party": (
                current_membership.get("party", {}).get("short_name")
                if current_membership else None
            ),
            "current_riding": (
                current_membership.get("riding", {}).get("name", {}).get("en")
                if current_membership else None
            ),
            "current_role": raw_data.get("current_office", {}).get("title") if raw_data.get("current_office") else None,
            
            # All memberships (historical)
            "memberships": [
                {
                    "party": m.get("party", {}).get("short_name"),
                    "party_full": m.get("party", {}).get("name", {}).get("en"),
                    "riding": m.get("riding", {}).get("name", {}).get("en"),
                    "riding_province": m.get("riding", {}).get("province"),
                    "start_date": m.get("start_date"),
                    "end_date": m.get("end_date"),
                }
                for m in memberships
            ],
            
            # External IDs
            "parl_mp_id": str(raw_data.get("id")) if raw_data.get("id") else None,
            
            # Metadata
            "source": "openparliament",
            "fetched_at": datetime.utcnow().isoformat()
        }
