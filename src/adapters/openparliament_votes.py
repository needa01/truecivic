"""
Adapter for fetching vote data from OpenParliament API.

Fetches parliamentary votes including individual MP voting records.

Responsibility: Fetch vote data from OpenParliament API
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import aiohttp

from src.adapters.base_adapter import BaseAdapter
from src.models.adapter_models import AdapterResponse

logger = logging.getLogger(__name__)


class OpenParliamentVotesAdapter(BaseAdapter):
    """
    Adapter for fetching vote data from OpenParliament API.
    
    Endpoints:
    - /votes/ - List all votes
    - /votes/{id}/ - Individual vote details with MP records
    """
    
    BASE_URL = "https://api.openparliament.ca"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the OpenParliament votes adapter.
        
        Args:
            session: Optional aiohttp session for connection pooling
        """
        super().__init__(session)
        self.source_name = "openparliament_votes"
    
    async def fetch_votes(
        self,
        limit: int = 50,
        offset: int = 0,
        session: Optional[int] = None,
        parliament: Optional[int] = None
    ) -> AdapterResponse:
        """
        Fetch votes from OpenParliament API.
        
        Args:
            limit: Maximum number of votes to fetch
            offset: Offset for pagination
            session: Filter by session number
            parliament: Filter by parliament number
            
        Returns:
            AdapterResponse with vote records
        """
        url = f"{self.BASE_URL}/votes/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": limit,
            "offset": offset
        }
        
        if session:
            params["session"] = session
        if parliament:
            params["parliament"] = parliament
        
        logger.info(
            f"Fetching votes: limit={limit}, offset={offset}, "
            f"session={session}, parliament={parliament}"
        )
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                logger.warning(f"No vote data returned from {url}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            votes = data["objects"]
            logger.info(f"Fetched {len(votes)} votes")
            
            # Transform to standard format
            transformed = [self._transform_vote(v) for v in votes]
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(f"Error fetching votes: {str(e)}", exc_info=True)
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{
                    "error": str(e),
                    "context": "fetch_votes"
                }]
            )
    
    async def fetch_vote_by_id(self, vote_id: str) -> AdapterResponse:
        """
        Fetch a single vote with full details including individual MP records.
        
        Args:
            vote_id: OpenParliament vote ID (e.g., "44-1-123")
            
        Returns:
            AdapterResponse with vote and MP voting records
        """
        url = f"{self.BASE_URL}/votes/{vote_id}/"
        params = {"format": "json"}
        
        logger.info(f"Fetching vote ID: {vote_id}")
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data:
                logger.warning(f"No data for vote ID {vote_id}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params={"vote_id": vote_id}
                )
            
            transformed = self._transform_vote_with_records(data)
            
            return AdapterResponse(
                source=self.source_name,
                records=[transformed],
                total_fetched=1,
                fetch_params={"vote_id": vote_id}
            )
            
        except Exception as e:
            logger.error(
                f"Error fetching vote {vote_id}: {str(e)}",
                exc_info=True
            )
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params={"vote_id": vote_id},
                errors=[{
                    "error": str(e),
                    "vote_id": vote_id
                }]
            )
    
    async def fetch_votes_for_bill(self, bill_number: str) -> AdapterResponse:
        """
        Fetch all votes related to a specific bill.
        
        Args:
            bill_number: Bill number (e.g., "C-30")
            
        Returns:
            AdapterResponse with vote records
        """
        url = f"{self.BASE_URL}/votes/"
        params = {
            "format": "json",
            "limit": 100,
            "bill": bill_number
        }
        
        logger.info(f"Fetching votes for bill {bill_number}")
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            votes = data["objects"]
            transformed = [self._transform_vote(v) for v in votes]
            
            logger.info(f"Fetched {len(transformed)} votes for bill {bill_number}")
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(
                f"Error fetching votes for bill {bill_number}: {str(e)}",
                exc_info=True
            )
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{"error": str(e)}]
            )
    
    def _transform_vote(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw OpenParliament vote data (without MP records).
        
        Args:
            raw_data: Raw vote data from API
            
        Returns:
            Standardized vote dictionary
        """
        # Extract session info from vote number (e.g., "44-1-123" -> parliament=44, session=1, number=123)
        vote_number_parts = raw_data.get("number", "").split("-")
        parliament = int(vote_number_parts[0]) if len(vote_number_parts) >= 1 else None
        session = int(vote_number_parts[1]) if len(vote_number_parts) >= 2 else None
        vote_num = int(vote_number_parts[2]) if len(vote_number_parts) >= 3 else None
        
        # Extract bill number if present
        bill_number = None
        if raw_data.get("bill") and isinstance(raw_data["bill"], dict):
            bill_number = raw_data["bill"].get("number")
        
        return {
            "vote_id": raw_data.get("number", ""),
            "parliament": parliament,
            "session": session,
            "vote_number": vote_num,
            "chamber": raw_data.get("context", "House"),  # Assume House if not specified
            "vote_date": raw_data.get("date"),
            "vote_description_en": raw_data.get("description", {}).get("en"),
            "vote_description_fr": raw_data.get("description", {}).get("fr"),
            "bill_number": bill_number,
            "result": raw_data.get("result", "Unknown"),
            "yeas": raw_data.get("yea_total", 0),
            "nays": raw_data.get("nay_total", 0),
            "abstentions": raw_data.get("paired_total", 0),
            "url": raw_data.get("url"),
            "source": "openparliament",
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def _transform_vote_with_records(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform vote data including individual MP voting records.
        
        Args:
            raw_data: Raw vote data with ballot records
            
        Returns:
            Standardized vote dictionary with MP records
        """
        vote_data = self._transform_vote(raw_data)
        
        # Extract individual MP voting records
        mp_votes = []
        if "ballots" in raw_data and raw_data["ballots"]:
            for ballot in raw_data["ballots"]:
                politician = ballot.get("politician", {})
                mp_votes.append({
                    "politician_id": politician.get("id"),
                    "politician_name": politician.get("name"),
                    "party": ballot.get("party", {}).get("short_name"),
                    "riding": ballot.get("politician_membership", {}).get("riding", {}).get("name", {}).get("en"),
                    "vote_position": ballot.get("vote", "Unknown"),  # Yea, Nay, Paired
                })
        
        vote_data["mp_votes"] = mp_votes
        vote_data["mp_vote_count"] = len(mp_votes)
        
        return vote_data
