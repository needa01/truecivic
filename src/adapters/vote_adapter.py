"""
Vote Adapter for OpenParliament API.

Fetches parliamentary vote data including vote results and individual MP voting records.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.models.adapter_models import VoteData, VoteRecordData
from src.adapters.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class VoteAdapter(BaseAdapter):
    """Adapter for fetching vote data from OpenParliament API."""
    
    def __init__(self, api_base_url: str = "https://api.openparliament.ca"):
        super().__init__(api_base_url)
        self.source_name = "openparliament_votes"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_votes_for_session(
        self,
        parliament: int,
        session: int,
        limit: int = 500
    ) -> List[VoteData]:
        """
        Fetch all votes for a given parliament session.
        
        Args:
            parliament: Parliament number (e.g., 44)
            session: Session number (e.g., 1)
            limit: Results per page
            
        Returns:
            List of VoteData objects
        """
        votes = []
        url = f"{self.api_base_url}/votes/"
        params = {
            "session": f"{parliament}-{session}",
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching votes for Parliament {parliament}, Session {session}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(url, params=params if url == f"{self.api_base_url}/votes/" else None)
                response.raise_for_status()
                data = response.json()
                
                for vote_obj in data.get("objects", []):
                    try:
                        vote = self._parse_vote(vote_obj, parliament, session)
                        if vote:
                            votes.append(vote)
                    except Exception as e:
                        logger.error(f"Error parsing vote {vote_obj.get('number')}: {e}")
                
                # Get next page
                url = data.get("pagination", {}).get("next_url")
                if url:
                    url = f"{self.api_base_url}{url}" if url.startswith("/") else url
                params = None  # Only use params on first request
        
        logger.info(f"Fetched {len(votes)} votes for {parliament}-{session}")
        return votes
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_vote_detail(self, vote_url: str) -> Optional[VoteData]:
        """
        Fetch detailed vote information including individual ballots.
        
        Args:
            vote_url: API URL for the vote
            
        Returns:
            VoteData with ballot records
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(vote_url)
            response.raise_for_status()
            data = response.json()
            
            # Parse vote with ballots
            return self._parse_vote_with_ballots(data)
    
    def _parse_vote(self, data: Dict[str, Any], parliament: int, session: int) -> Optional[VoteData]:
        """Parse vote data from API response."""
        try:
            # Extract vote details
            number = data.get("number")
            if not number:
                return None
            
            # Parse date
            date_str = data.get("date")
            vote_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else None
            
            # Determine result
            result = data.get("result", "Unknown")
            
            # Get vote counts
            vote_total = data.get("vote_total", {})
            yeas = vote_total.get("yea", 0)
            nays = vote_total.get("nay", 0)
            paired = vote_total.get("paired", 0)
            
            # Extract bill reference
            bill = data.get("bill")
            bill_number = None
            if bill:
                bill_number = bill.get("number")
            
            # Get description
            description_en = data.get("description_en") or data.get("description")
            description_fr = data.get("description_fr")
            
            return VoteData(
                vote_id=f"ca-federal-{parliament}-{session}-vote-{number}",
                parliament=parliament,
                session=session,
                vote_number=number,
                chamber="House",  # OpenParliament is primarily House of Commons
                vote_date=vote_date,
                vote_description_en=description_en,
                vote_description_fr=description_fr,
                bill_number=bill_number,
                result=result,
                yeas=yeas,
                nays=nays,
                abstentions=paired,  # Paired votes are similar to abstentions
                vote_records=[]  # Will be populated separately if needed
            )
            
        except Exception as e:
            logger.error(f"Error parsing vote data: {e}")
            return None
    
    def _parse_vote_with_ballots(self, data: Dict[str, Any]) -> Optional[VoteData]:
        """Parse vote data with individual ballot records."""
        try:
            # Parse basic vote info
            parliament = data.get("session", {}).get("parliamentnum")
            session = data.get("session", {}).get("sessnum")
            
            vote = self._parse_vote(data, parliament, session)
            if not vote:
                return None
            
            # Parse ballot records
            ballots = data.get("ballots", {}).get("objects", [])
            vote_records = []
            
            for ballot in ballots:
                try:
                    politician_url = ballot.get("politician_url")
                    ballot_vote = ballot.get("ballot")
                    
                    # Extract politician ID from URL
                    politician_id = None
                    if politician_url:
                        # URL format: /politicians/{id}/
                        parts = politician_url.strip("/").split("/")
                        if len(parts) >= 2:
                            politician_id = int(parts[-1])
                    
                    if politician_id and ballot_vote:
                        record = VoteRecordData(
                            politician_id=politician_id,
                            vote_position=ballot_vote.title()  # Y -> Yea, N -> Nay
                        )
                        vote_records.append(record)
                
                except Exception as e:
                    logger.warning(f"Error parsing ballot: {e}")
            
            vote.vote_records = vote_records
            logger.info(f"Parsed vote {vote.vote_number} with {len(vote_records)} ballot records")
            
            return vote
            
        except Exception as e:
            logger.error(f"Error parsing vote with ballots: {e}")
            return None
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def fetch_latest_votes(self, limit: int = 50) -> List[VoteData]:
        """
        Fetch most recent votes across all sessions.
        
        Args:
            limit: Maximum number of votes to fetch
            
        Returns:
            List of recent VoteData objects
        """
        votes = []
        url = f"{self.api_base_url}/votes/"
        params = {
            "limit": limit,
            "format": "json"
        }
        
        logger.info(f"Fetching {limit} latest votes")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            for vote_obj in data.get("objects", []):
                try:
                    # Extract parliament and session from vote
                    session_info = vote_obj.get("session", {})
                    parliament = session_info.get("parliamentnum", 44)
                    session = session_info.get("sessnum", 1)
                    
                    vote = self._parse_vote(vote_obj, parliament, session)
                    if vote:
                        votes.append(vote)
                except Exception as e:
                    logger.error(f"Error parsing vote: {e}")
        
        logger.info(f"Fetched {len(votes)} latest votes")
        return votes
