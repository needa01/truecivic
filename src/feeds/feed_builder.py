"""
Feed Builder Infrastructure
===========================
Base classes and utilities for building RSS 2.0 and Atom feeds.

Responsibility: Generate RFC-compliant RSS/Atom feeds from database entities
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from feedgen.feed import FeedGenerator
from feedgen.entry import FeedEntry

from ..config import settings


class FeedFormat(str, Enum):
    """Supported feed formats"""
    RSS = "rss"
    ATOM = "atom"


class FeedBuilder:
    """
    Base class for building RSS/Atom feeds.
    
    Handles feed metadata, entry generation, and format serialization.
    Each feed type (bills, votes, debates) should subclass this.
    
    Example:
        builder = FeedBuilder(
            title="Latest Bills",
            description="Recent parliamentary bills",
            feed_url="https://truecivic.ca/feeds/bills/latest.xml"
        )
        builder.add_entry(
            title="Bill C-123",
            link="https://truecivic.ca/bills/C-123",
            description="Summary...",
            guid="ca:bill:12345"
        )
        xml = builder.generate(FeedFormat.RSS)
    """
    
    def __init__(
        self,
        title: str,
        description: str,
        feed_url: str,
        link: Optional[str] = None,
        language: str = "en-CA",
        author_name: str = "TrueCivic",
        author_email: str = "info@truecivic.ca"
    ):
        """
        Initialize feed builder.
        
        Args:
            title: Feed title
            description: Feed description
            feed_url: URL of the feed itself (self link)
            link: URL of the website (defaults to feed_url)
            language: Feed language code
            author_name: Feed author name
            author_email: Feed author email
        """
        self.fg = FeedGenerator()
        
        # Required metadata
        self.fg.title(title)
        self.fg.description(description)
        self.fg.link(href=link or feed_url, rel='alternate')
        self.fg.link(href=feed_url, rel='self')
        self.fg.language(language)
        
        # Author info
        self.fg.author({'name': author_name, 'email': author_email})
        
        # Generator info
        self.fg.generator('TrueCivic Feed Generator', uri='https://truecivic.ca')
        
        # Set update time to now (timezone-aware UTC)
        self.fg.lastBuildDate(datetime.now(timezone.utc))
        
        self._entries: List[FeedEntry] = []
    
    def add_entry(
        self,
        title: str,
        link: str,
        description: str,
        guid: str,
        pub_date: Optional[datetime] = None,
        author: Optional[str] = None,
        categories: Optional[List[str]] = None,
        content: Optional[str] = None,
        **kwargs
    ) -> FeedEntry:
        """
        Add an entry to the feed.
        
        Args:
            title: Entry title
            link: URL to the full content
            description: Short summary
            guid: Globally unique identifier (format: jurisdiction:type:id[:event])
            pub_date: Publication date (defaults to now)
            author: Author name
            categories: List of categories/tags
            content: Full content (optional, for Atom)
            **kwargs: Additional metadata
        
        Returns:
            The created FeedEntry
        """
        entry = self.fg.add_entry()
        
        # Required fields
        entry.title(title)
        entry.link(href=link)
        entry.description(description)
        entry.guid(guid, permalink=False)  # GUID is not necessarily a URL
        
        # Optional fields
        if pub_date:
            # Ensure timezone-aware
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
            entry.pubDate(pub_date)
        else:
            entry.pubDate(datetime.now(timezone.utc))
        
        if author:
            entry.author({'name': author})
        
        if categories:
            for category in categories:
                entry.category(term=category)
        
        if content:
            entry.content(content, type='html')
        
        # Store custom metadata
        entry._custom_metadata = kwargs
        
        self._entries.append(entry)
        return entry
    
    def generate(self, format: FeedFormat = FeedFormat.RSS) -> str:
        """
        Generate the feed in the specified format.
        
        Args:
            format: Output format (RSS or Atom)
        
        Returns:
            XML string of the feed
        """
        if format == FeedFormat.RSS:
            return self.fg.rss_str(pretty=True).decode('utf-8')
        elif format == FeedFormat.ATOM:
            return self.fg.atom_str(pretty=True).decode('utf-8')
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def get_entry_count(self) -> int:
        """Get the number of entries in the feed"""
        return len(self._entries)
    
    def clear_entries(self) -> None:
        """Remove all entries from the feed"""
        self._entries.clear()
        # Reset feedgen entries
        self.fg.entry([], replace=True)


class GuidBuilder:
    """
    Utility class for building consistent GUIDs.
    
    GUID Format: {jurisdiction}:{entity_type}:{id}[:{event}][:{date}]
    
    Examples:
        ca:bill:12345
        ca:vote:67890:result
        ca:debate:11111:2024-01-15
    """
    
    @staticmethod
    def build(
        jurisdiction: str,
        entity_type: str,
        entity_id: int,
        event: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> str:
        """
        Build a consistent GUID for feed entries.
        
        Args:
            jurisdiction: Jurisdiction code (e.g., 'ca')
            entity_type: Type of entity (e.g., 'bill', 'vote', 'debate')
            entity_id: Unique ID of the entity
            event: Optional event name (e.g., 'introduced', 'voted', 'debated')
            date: Optional date for time-based events
        
        Returns:
            GUID string
        """
        parts = [jurisdiction, entity_type, str(entity_id)]
        
        if event:
            parts.append(event)
        
        if date:
            parts.append(date.strftime('%Y-%m-%d'))
        
        return ':'.join(parts)


class FeedCache:
    """
    Simple in-memory cache for generated feeds.
    
    Caches feeds for 5 minutes to reduce database load.
    In production, this should use Redis.
    """
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize feed cache.
        
        Args:
            ttl_seconds: Time-to-live in seconds (default: 5 minutes)
        """
        self._cache: Dict[str, tuple[str, datetime]] = {}
        self._ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[str]:
        """
        Get cached feed if not expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached feed XML or None if expired/missing
        """
        if key not in self._cache:
            return None
        
        content, cached_at = self._cache[key]
        age = (datetime.now(timezone.utc) - cached_at).total_seconds()
        
        if age > self._ttl:
            # Expired
            del self._cache[key]
            return None
        
        return content
    
    def set(self, key: str, content: str) -> None:
        """
        Cache a feed.
        
        Args:
            key: Cache key
            content: Feed XML content
        """
        self._cache[key] = (content, datetime.now(timezone.utc))
    
    def clear(self) -> None:
        """Clear all cached feeds"""
        self._cache.clear()
    
    def size(self) -> int:
        """Get number of cached feeds"""
        return len(self._cache)


# Global cache instance
feed_cache = FeedCache(ttl_seconds=300)  # 5 minutes
