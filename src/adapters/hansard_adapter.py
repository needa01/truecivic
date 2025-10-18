"""
Hansard Adapter for OpenParliament API.

Fetches parliamentary debate transcripts including speeches and debates.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.adapter_models import DebateData, SpeechData
from src.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class HansardAdapter(BaseAdapter):
    """Adapter for fetching Hansard debate data from OpenParliament API."""
    
    def __init__(self, api_base_url: str = "https://api.openparliament.ca"):
        super().__init__(api_base_url)
        self.source_name = "openparliament_hansard"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_debates_for_session(
        self,
        parliament: int,
        session: int,
        limit: int = 500
    ) -> List[DebateData]:
        """
        Fetch all debates for a given parliament session.
        
        Args:
            parliament: Parliament number (e.g., 44)
            session: Session number (e.g., 1)
            limit: Results per page
            
        Returns:
            List of DebateData objects
        """
        debates = []
        url = f"{self.api_base_url}/debates/"
        params = {
            "session": f"{parliament}-{session}",
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching debates for Parliament {parliament}, Session {session}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(url, params=params if url == f"{self.api_base_url}/debates/" else None)
                response.raise_for_status()
                data = response.json()
                
                for debate_obj in data.get("objects", []):
                    try:
                        debate = self._parse_debate(debate_obj, parliament, session)
                        if debate:
                            debates.append(debate)
                    except Exception as e:
                        logger.error(f"Error parsing debate: {e}")
                
                # Get next page
                url = data.get("pagination", {}).get("next_url")
                if url:
                    url = f"{self.api_base_url}{url}" if url.startswith("/") else url
                params = None
        
        logger.info(f"Fetched {len(debates)} debates for {parliament}-{session}")
        return debates
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_debate_detail(self, debate_url: str) -> Optional[DebateData]:
        """
        Fetch detailed debate information including all speeches.
        
        Args:
            debate_url: API URL for the debate
            
        Returns:
            DebateData with speeches
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(debate_url)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_debate_with_speeches(data)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_speeches_for_debate(self, debate_id: str, limit: int = 500) -> List[SpeechData]:
        """
        Fetch all speeches for a specific debate.
        
        Args:
            debate_id: Natural debate ID
            limit: Results per page
            
        Returns:
            List of SpeechData objects
        """
        speeches = []
        url = f"{self.api_base_url}/debates/speeches/"
        params = {
            "debate": debate_id,
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching speeches for debate {debate_id}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(url, params=params if url == f"{self.api_base_url}/debates/speeches/" else None)
                response.raise_for_status()
                data = response.json()
                
                for speech_obj in data.get("objects", []):
                    try:
                        speech = self._parse_speech(speech_obj)
                        if speech:
                            speeches.append(speech)
                    except Exception as e:
                        logger.error(f"Error parsing speech: {e}")
                
                # Get next page
                url = data.get("pagination", {}).get("next_url")
                if url:
                    url = f"{self.api_base_url}{url}" if url.startswith("/") else url
                params = None
        
        logger.info(f"Fetched {len(speeches)} speeches for debate {debate_id}")
        return speeches
    
    def _parse_debate(self, data: Dict[str, Any], parliament: int, session: int) -> Optional[DebateData]:
        """Parse debate data from API response."""
        try:
            # Extract debate details
            debate_number = data.get("number")
            if not debate_number:
                return None
            
            # Parse date
            date_str = data.get("date")
            debate_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else None
            
            # Get topic/title
            topic_en = data.get("topic_en") or data.get("topic")
            topic_fr = data.get("topic_fr")
            
            # Extract debate type (e.g., "Main Estimates", "Question Period")
            debate_type = data.get("document_type", "Debate")
            
            return DebateData(
                debate_id=f"ca-federal-{parliament}-{session}-debate-{debate_number}",
                parliament=parliament,
                session=session,
                debate_number=debate_number,
                chamber="House",
                debate_date=debate_date,
                topic_en=topic_en,
                topic_fr=topic_fr,
                debate_type=debate_type,
                speeches=[]  # Will be populated separately if needed
            )
            
        except Exception as e:
            logger.error(f"Error parsing debate data: {e}")
            return None
    
    def _parse_debate_with_speeches(self, data: Dict[str, Any]) -> Optional[DebateData]:
        """Parse debate data with all speeches."""
        try:
            # Parse basic debate info
            parliament = data.get("session", {}).get("parliamentnum", 44)
            session = data.get("session", {}).get("sessnum", 1)
            
            debate = self._parse_debate(data, parliament, session)
            if not debate:
                return None
            
            # Parse speeches
            speeches_data = data.get("speeches", {}).get("objects", [])
            speeches = []
            
            for idx, speech_obj in enumerate(speeches_data):
                try:
                    speech = self._parse_speech(speech_obj)
                    if speech:
                        speech.sequence = idx + 1  # Add sequence order
                        speeches.append(speech)
                except Exception as e:
                    logger.warning(f"Error parsing speech: {e}")
            
            debate.speeches = speeches
            logger.info(f"Parsed debate {debate.debate_number} with {len(speeches)} speeches")
            
            return debate
            
        except Exception as e:
            logger.error(f"Error parsing debate with speeches: {e}")
            return None
    
    def _parse_speech(self, data: Dict[str, Any]) -> Optional[SpeechData]:
        """Parse speech data from API response."""
        try:
            # Get speech ID
            speech_id = data.get("id")
            if not speech_id:
                return None
            
            # Extract politician info
            politician = data.get("politician", {})
            politician_id = None
            if politician:
                politician_url = politician.get("url")
                if politician_url:
                    # URL format: /politicians/{id}/
                    parts = politician_url.strip("/").split("/")
                    if len(parts) >= 2:
                        politician_id = int(parts[-1])
            
            # Get speech content
            content_en = data.get("content_en") or data.get("content")
            content_fr = data.get("content_fr")
            
            # Parse time if available
            time_str = data.get("time")
            speech_time = datetime.fromisoformat(time_str.replace("Z", "+00:00")) if time_str else None
            
            # Get speaker info
            speaker_name = data.get("h1_en") or data.get("h1")
            speaker_role = data.get("h2_en") or data.get("h2")
            
            return SpeechData(
                speech_id=str(speech_id),
                politician_id=politician_id,
                content_en=content_en,
                content_fr=content_fr,
                speech_time=speech_time,
                speaker_name=speaker_name,
                speaker_role=speaker_role
            )
            
        except Exception as e:
            logger.error(f"Error parsing speech data: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_latest_debates(self, limit: int = 50) -> List[DebateData]:
        """
        Fetch most recent debates across all sessions.
        
        Args:
            limit: Maximum number of debates to fetch
            
        Returns:
            List of recent DebateData objects
        """
        debates = []
        url = f"{self.api_base_url}/debates/"
        params = {
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching {limit} latest debates")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for debate_obj in data.get("objects", []):
                try:
                    session_info = debate_obj.get("session", {})
                    parliament = session_info.get("parliamentnum", 44)
                    session = session_info.get("sessnum", 1)
                    
                    debate = self._parse_debate(debate_obj, parliament, session)
                    if debate:
                        debates.append(debate)
                except Exception as e:
                    logger.error(f"Error parsing debate: {e}")
        
        logger.info(f"Fetched {len(debates)} latest debates")
        return debates
