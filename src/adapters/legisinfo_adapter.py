"""
LEGISinfo scraper adapter for enriching bill data.

Scrapes additional metadata from LEGISinfo that's not available in OpenParliament:
- Subject tags and policy areas
- Committee studies and reports
- Royal assent details (date and chapter number)
- Related bill linkages

Responsibility: Scrape and normalize enrichment data from LEGISinfo HTML pages
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import re
import httpx
from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter
from ..models.bill import Bill
from ..models.adapter_models import AdapterResponse, AdapterError


class LEGISinfoAdapter(BaseAdapter[Dict[str, Any]]):
    """
    Adapter for scraping bill enrichment data from LEGISinfo.
    
    Key features:
    - Scrapes HTML pages (no official API)
    - Extracts subject tags and policy areas
    - Extracts committee information
    - Extracts royal assent details
    - Rate limited to 0.5 requests/second (gentle scraping)
    
    Example:
        adapter = LEGISinfoAdapter()
        response = await adapter.fetch(legisinfo_id=12345)
    """
    
    BASE_URL = "https://www.parl.ca/legisinfo/en/bill"
    
    def __init__(self):
        """Initialize LEGISinfo scraper adapter"""
        super().__init__(
            source_name="legisinfo_scraper",
            rate_limit_per_second=0.5,  # 0.5 req/sec = very gentle
            max_retries=3,
            timeout_seconds=30
        )
        
        # Initialize HTTP client with browser-like headers
        self.client = httpx.AsyncClient(
            timeout=self.timeout_seconds,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
            },
            follow_redirects=True
        )
    
    async def fetch(
        self,
        legisinfo_id: int,
        **kwargs: Any
    ) -> AdapterResponse[Dict[str, Any]]:
        """
        Fetch enrichment data for a bill from LEGISinfo.
        
        Args:
            legisinfo_id: LEGISinfo bill ID (e.g., 12345)
            **kwargs: Additional parameters (ignored)
        
        Returns:
            AdapterResponse containing enrichment data dict
        """
        self._reset_metrics()
        start_time = datetime.utcnow()
        errors: List[AdapterError] = []
        
        self.logger.info(f"Fetching LEGISinfo data for bill ID: {legisinfo_id}")
        
        try:
            # Build URL
            url = f"{self.BASE_URL}/{legisinfo_id}"
            
            # Apply rate limiting
            await self.rate_limiter.acquire()
            
            self.logger.debug(f"GET {url}")
            
            # Make request
            response = await self._request_with_retries(self.client.get, url)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Normalize the page content
            data = self.normalize(soup)
            
            self.logger.info(
                f"Successfully scraped LEGISinfo data for bill {legisinfo_id}"
            )
            
            # Build success response
            return self._build_success_response(
                data=[data],  # Wrap in list for consistency
                errors=errors,
                start_time=start_time,
                cache_ttl_seconds=24 * 3600  # Cache for 24 hours
            )
        
        except httpx.HTTPError as e:
            # Network/HTTP error
            self.logger.error(
                f"HTTP error fetching LEGISinfo {legisinfo_id}: {e}",
                exc_info=True
            )
            return self._build_failure_response(
                error=e,
                start_time=start_time,
                retryable=True
            )
        
        except Exception as e:
            # Unexpected error (parsing, etc.)
            self.logger.error(
                f"Unexpected error scraping LEGISinfo {legisinfo_id}: {e}",
                exc_info=True
            )
            return self._build_failure_response(
                error=e,
                start_time=start_time,
                retryable=False
            )
    
    def normalize(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract enrichment data from LEGISinfo HTML page.
        
        Args:
            soup: BeautifulSoup parsed HTML
        
        Returns:
            Dict containing enrichment fields
        """
        data: Dict[str, Any] = {
            "subject_tags": [],
            "committee_studies": [],
            "royal_assent_date": None,
            "royal_assent_chapter": None,
            "related_bill_numbers": [],
        }
        
        # Extract subject tags
        data["subject_tags"] = self._extract_subject_tags(soup)
        
        # Extract committee studies
        data["committee_studies"] = self._extract_committee_studies(soup)
        
        # Extract royal assent information
        royal_assent = self._extract_royal_assent(soup)
        if royal_assent:
            data["royal_assent_date"] = royal_assent.get("date")
            data["royal_assent_chapter"] = royal_assent.get("chapter")
        
        # Extract related bills
        data["related_bill_numbers"] = self._extract_related_bills(soup)
        
        return data
    
    def _extract_subject_tags(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract subject tags and policy areas.
        
        Looks for sections like "Subject" or "Policy area" in the page.
        """
        tags: List[str] = []
        
        # Find subject section
        # Common patterns: <h3>Subject</h3>, <dt>Policy area</dt>
        subject_headers = soup.find_all(['h3', 'h4', 'dt'], string=re.compile(
            r'Subject|Policy [Aa]rea|Theme',
            re.IGNORECASE
        ))
        
        for header in subject_headers:
            # Get the next sibling or parent's next sibling
            content = None
            
            if header.name == 'dt':
                # Definition list: <dt>Subject</dt><dd>Tags here</dd>
                content = header.find_next_sibling('dd')
            else:
                # Heading: <h3>Subject</h3><div>Tags here</div>
                content = header.find_next_sibling(['div', 'p', 'ul'])
            
            if content:
                # Extract text, split by common separators
                text = content.get_text(separator=';', strip=True)
                # Split by semicolon, comma, or bullet points
                raw_tags = re.split(r'[;,]|\n', text)
                tags.extend([
                    tag.strip()
                    for tag in raw_tags
                    if tag.strip() and len(tag.strip()) > 2
                ])
        
        # Remove duplicates, preserve order
        seen = set()
        unique_tags = []
        for tag in tags:
            if tag not in seen:
                seen.add(tag)
                unique_tags.append(tag)
        
        return unique_tags
    
    def _extract_committee_studies(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract committee names that studied the bill.
        
        Looks for committee links or references in the page.
        """
        committees: List[str] = []
        
        # Find committee section
        committee_headers = soup.find_all(['h3', 'h4', 'dt'], string=re.compile(
            r'Committee|Standing Committee',
            re.IGNORECASE
        ))
        
        for header in committee_headers:
            # Find committee links or text
            parent_section = header.find_parent(['section', 'div']) or header
            
            # Look for links containing "committee"
            committee_links = parent_section.find_all(
                'a',
                href=re.compile(r'committee', re.IGNORECASE)
            )
            
            for link in committee_links:
                committee_name = link.get_text(strip=True)
                if committee_name and len(committee_name) > 3:
                    committees.append(committee_name)
        
        # Remove duplicates
        return list(set(committees))
    
    def _extract_royal_assent(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract royal assent date and chapter number.
        
        Looks for "Royal Assent" section with date and chapter info.
        """
        royal_assent_headers = soup.find_all(['h3', 'h4', 'dt', 'strong'], string=re.compile(
            r'Royal Assent',
            re.IGNORECASE
        ))
        
        for header in royal_assent_headers:
            # Get the associated content
            parent = header.find_parent(['div', 'section', 'dl'])
            if not parent:
                parent = header.find_next_sibling(['div', 'dd', 'p'])
            
            if parent:
                text = parent.get_text(separator=' ', strip=True)
                
                # Extract date (various formats)
                # Example: "2023-06-22", "June 22, 2023", "22/06/2023"
                date_match = re.search(
                    r'(\d{4}-\d{2}-\d{2})|'  # ISO format
                    r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4})|'  # "June 22, 2023"
                    r'(\d{1,2}/\d{1,2}/\d{4})',  # "22/06/2023"
                    text
                )
                
                # Extract chapter number
                # Example: "S.C. 2023, c. 15", "Chapter 15"
                chapter_match = re.search(
                    r'[Cc](?:hapter|\.)?\s*(\d+)',
                    text
                )
                
                if date_match or chapter_match:
                    return {
                        "date": self._parse_date(date_match.group(0)) if date_match else None,
                        "chapter": chapter_match.group(1) if chapter_match else None,
                    }
        
        return None
    
    def _extract_related_bills(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract related bill numbers (amendments, companion bills, etc.).
        
        Looks for bill number patterns (C-123, S-45) in related sections.
        """
        related: List[str] = []
        
        # Find related bills section
        related_headers = soup.find_all(['h3', 'h4', 'dt'], string=re.compile(
            r'Related|Former|Amended|Companion',
            re.IGNORECASE
        ))
        
        for header in related_headers:
            # Get parent section
            parent = header.find_parent(['div', 'section']) or header
            
            # Find all text in this section
            text = parent.get_text(separator=' ', strip=True)
            
            # Extract bill numbers (C-123, S-45, etc.)
            bill_pattern = r'\b[CS]-\d+[A-Z]?\b'
            matches = re.findall(bill_pattern, text)
            related.extend(matches)
        
        # Remove duplicates
        return list(set(related))
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse various date formats to datetime.
        
        Supports:
        - ISO: 2023-06-22
        - Long: June 22, 2023
        - Short: 22/06/2023
        """
        if not date_str:
            return None
        
        # Try ISO format
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass
        
        # Try long format
        try:
            return datetime.strptime(date_str, "%B %d, %Y")
        except ValueError:
            pass
        
        # Try short format (DD/MM/YYYY - Canadian convention)
        try:
            return datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            pass
        
        self.logger.warning(f"Could not parse date: {date_str}")
        return None
    
    async def close(self):
        """Close HTTP client connection"""
        await self.client.aclose()
