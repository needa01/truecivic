"""
Adapter for fetching debate/Hansard data from OpenParliament API.

Fetches parliamentary debates and individual speeches.

Responsibility: Fetch debate/Hansard data from OpenParliament API
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import aiohttp

from src.adapters.base_adapter import BaseAdapter
from src.models.adapter_models import AdapterResponse

logger = logging.getLogger(__name__)


class OpenParliamentDebatesAdapter(BaseAdapter):
    """
    Adapter for fetching debate/Hansard data from OpenParliament API.
    
    Endpoints:
    - /debates/ - List debate sessions
    - /speeches/ - List speeches across debates
    """
    
    BASE_URL = "https://api.openparliament.ca"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        """
        Initialize the OpenParliament debates adapter.
        
        Args:
            session: Optional aiohttp session for connection pooling
        """
        super().__init__(session)
        self.source_name = "openparliament_debates"
    
    async def fetch_debates(
        self,
        limit: int = 50,
        offset: int = 0,
        session: Optional[int] = None,
        parliament: Optional[int] = None
    ) -> AdapterResponse:
        """
        Fetch debate sessions from OpenParliament API.
        
        Args:
            limit: Maximum number of debates to fetch
            offset: Offset for pagination
            session: Filter by session number
            parliament: Filter by parliament number
            
        Returns:
            AdapterResponse with debate records
        """
        url = f"{self.BASE_URL}/debates/"
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
            f"Fetching debates: limit={limit}, offset={offset}, "
            f"session={session}, parliament={parliament}"
        )
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                logger.warning(f"No debate data returned from {url}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            debates = data["objects"]
            logger.info(f"Fetched {len(debates)} debates")
            
            # Transform to standard format
            transformed = [self._transform_debate(d) for d in debates]
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(f"Error fetching debates: {str(e)}", exc_info=True)
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{
                    "error": str(e),
                    "context": "fetch_debates"
                }]
            )
    
    async def fetch_speeches(
        self,
        limit: int = 100,
        offset: int = 0,
        debate_id: Optional[str] = None,
        politician_id: Optional[int] = None,
        date: Optional[str] = None
    ) -> AdapterResponse:
        """
        Fetch speeches from OpenParliament API.
        
        Args:
            limit: Maximum number of speeches to fetch
            offset: Offset for pagination
            debate_id: Filter by specific debate
            politician_id: Filter by politician
            date: Filter by date (YYYY-MM-DD)
            
        Returns:
            AdapterResponse with speech records
        """
        url = f"{self.BASE_URL}/speeches/"
        params: Dict[str, Any] = {
            "format": "json",
            "limit": limit,
            "offset": offset
        }
        
        if debate_id:
            params["debate"] = debate_id
        if politician_id:
            params["politician"] = politician_id
        if date:
            params["date"] = date
        
        logger.info(
            f"Fetching speeches: limit={limit}, offset={offset}, "
            f"debate={debate_id}, politician={politician_id}, date={date}"
        )
        
        try:
            data = await self._fetch_json(url, params)
            
            if not data or "objects" not in data:
                logger.warning(f"No speech data returned from {url}")
                return AdapterResponse(
                    source=self.source_name,
                    records=[],
                    total_fetched=0,
                    fetch_params=params
                )
            
            speeches = data["objects"]
            logger.info(f"Fetched {len(speeches)} speeches")
            
            # Transform to standard format
            transformed = [self._transform_speech(s) for s in speeches]
            
            return AdapterResponse(
                source=self.source_name,
                records=transformed,
                total_fetched=len(transformed),
                fetch_params=params
            )
            
        except Exception as e:
            logger.error(f"Error fetching speeches: {str(e)}", exc_info=True)
            return AdapterResponse(
                source=self.source_name,
                records=[],
                total_fetched=0,
                fetch_params=params,
                errors=[{
                    "error": str(e),
                    "context": "fetch_speeches"
                }]
            )
    
    async def fetch_speeches_for_debate(self, debate_id: str) -> AdapterResponse:
        """
        Fetch all speeches for a specific debate session.
        
        Args:
            debate_id: Debate identifier
            
        Returns:
            AdapterResponse with speech records
        """
        return await self.fetch_speeches(
            limit=1000,  # Large limit for single debate
            debate_id=debate_id
        )
    
    async def fetch_speeches_for_politician(
        self,
        politician_id: int,
        limit: int = 100
    ) -> AdapterResponse:
        """
        Fetch recent speeches by a specific politician.
        
        Args:
            politician_id: Politician ID
            limit: Maximum speeches to fetch
            
        Returns:
            AdapterResponse with speech records
        """
        return await self.fetch_speeches(
            limit=limit,
            politician_id=politician_id
        )
    
    def _transform_debate(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw OpenParliament debate data.
        
        Args:
            raw_data: Raw debate data from API
            
        Returns:
            Standardized debate dictionary
        """
        # Extract session info from URL or id
        debate_url = raw_data.get("url", "")
        hansard_id = raw_data.get("id", debate_url.split("/")[-2] if "/" in debate_url else None)
        
        # Parse parliament/session from structure like "2024-03-21"
        parliament = raw_data.get("parliament")
        session = raw_data.get("session")
        
        return {
            "hansard_id": hansard_id,
            "parliament": parliament,
            "session": session,
            "sitting_date": raw_data.get("date"),
            "chamber": raw_data.get("h1", {}).get("en", "House"),  # h1 contains chamber name
            "debate_type": raw_data.get("h2", {}).get("en"),  # h2 contains debate type
            "document_url": raw_data.get("url"),
            "source": "openparliament",
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def _transform_speech(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw OpenParliament speech data.
        
        Args:
            raw_data: Raw speech data from API
            
        Returns:
            Standardized speech dictionary
        """
        politician = raw_data.get("politician", {})
        
        # Extract sequence from URL or h3
        sequence = raw_data.get("sequence", 0)
        
        # Determine language
        language = None
        if "language" in raw_data:
            language = raw_data["language"]
        elif "content" in raw_data:
            # Simple heuristic: if content has French words, mark as fr
            content_lower = raw_data["content"].get("en", "").lower()
            if any(word in content_lower for word in ["oui", "non", "monsieur", "madame"]):
                language = "fr"
            else:
                language = "en"
        
        return {
            "debate_hansard_id": raw_data.get("debate", ""),  # URL to debate
            "politician_id": politician.get("id") if politician else None,
            "speaker_name": politician.get("name") if politician else raw_data.get("h3", {}).get("en", "Speaker"),
            "sequence": sequence,
            "language": language,
            "text_content": raw_data.get("content", {}).get("en", ""),
            "timestamp_start": raw_data.get("time"),
            "timestamp_end": None,  # Not provided by API
            "url": raw_data.get("url"),
            "source": "openparliament",
            "fetched_at": datetime.utcnow().isoformat()
        }
