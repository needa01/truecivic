"""
Bill Feed Builders
==================
Specialized feed builders for bill-related feeds.

Responsibility: Generate RSS/Atom feeds for bills from materialized views
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .feed_builder import FeedBuilder, GuidBuilder, FeedFormat
from ..db.models import BillModel


class BillsFeedBuilder(FeedBuilder):
    """
    Feed builder for bills.
    
    Generates feeds from bills data with proper metadata and formatting.
    """
    
    def __init__(self, feed_url: str, base_link: str = "https://truecivic.ca"):
        """
        Initialize bills feed builder.
        
        Args:
            feed_url: URL of this feed
            base_link: Base URL for bill links
        """
        super().__init__(
            title="TrueCivic - Latest Parliamentary Bills",
            description="Recent bills introduced in the Parliament of Canada",
            feed_url=feed_url,
            link=base_link,
            language="en-CA"
        )
        self.base_link = base_link
    
    def add_bill_entry(
        self,
        bill_id: int,
        number: str,
        title_en: str,
        title_fr: Optional[str],
        introduced_date: datetime,
        parliament: int,
        session: int,
        law_status: Optional[str],
        legisinfo_status: Optional[str],
        sponsor_name: Optional[str] = None,
        subject_tags: Optional[List[str]] = None,
        summary_en: Optional[str] = None,
        jurisdiction: str = "ca"
    ) -> None:
        """
        Add a bill entry to the feed.
        
        Args:
            bill_id: Database ID
            number: Bill number (e.g., C-123)
            title_en: English title
            title_fr: French title
            introduced_date: Date introduced
            parliament: Parliament number
            session: Session number
            law_status: Law status
            legisinfo_status: LEGISinfo status
            sponsor_name: Bill sponsor
            subject_tags: List of tags
            summary_en: Bill summary
            jurisdiction: Jurisdiction code
        """
        # Build GUID
        guid = GuidBuilder.build(
            jurisdiction=jurisdiction,
            entity_type="bill",
            entity_id=bill_id,
            event="introduced",
            date=introduced_date
        )
        
        # Build link
        link = f"{self.base_link}/bills/{number}"
        
        # Build description
        description_parts = []
        
        if summary_en:
            description_parts.append(summary_en[:300])
        else:
            description_parts.append(f"{title_en}")
        
        if law_status:
            description_parts.append(f"<br/><strong>Law Status:</strong> {law_status}")
        elif legisinfo_status:
            description_parts.append(f"<br/><strong>Status:</strong> {legisinfo_status}")
        
        if sponsor_name:
            description_parts.append(f"<br/><strong>Sponsor:</strong> {sponsor_name}")
        
        description_parts.append(
            f"<br/><strong>Parliament:</strong> {parliament}-{session}"
        )
        
        description = ' '.join(description_parts)
        
        # Build categories
        categories = subject_tags if subject_tags else []
        
        # Add entry
        self.add_entry(
            title=f"{number}: {title_en}",
            link=link,
            description=description,
            guid=guid,
            pub_date=introduced_date,
            author=sponsor_name,
            categories=categories,
            bill_number=number,
            parliament=parliament,
            session=session
        )


class LatestBillsFeedBuilder(BillsFeedBuilder):
    """Feed builder for latest bills (uses mv_feed_bills_latest)"""
    
    @classmethod
    async def from_materialized_view(
        cls,
        session: AsyncSession,
        feed_url: str,
        limit: int = 50
    ) -> "LatestBillsFeedBuilder":
        """
        Create feed from mv_feed_bills_latest materialized view.
        
        Args:
            session: Database session
            feed_url: URL of this feed
            limit: Maximum number of entries
        
        Returns:
            Populated feed builder
        """
        builder = cls(feed_url=feed_url)
        
        # Query materialized view
        result = await session.execute(text(f"""
            SELECT 
                id, 
                number, 
                title_en, 
                title_fr, 
                introduced_date, 
                parliament, 
                session,
                law_status,
                legisinfo_status,
                updated_at
            FROM mv_feed_bills_latest
            ORDER BY introduced_date DESC
            LIMIT {limit}
        """))
        
        rows = result.fetchall()
        
        for row in rows:
            builder.add_bill_entry(
                bill_id=row.id,
                number=row.number,
                title_en=row.title_en,
                title_fr=row.title_fr,
                introduced_date=row.introduced_date,
                parliament=row.parliament,
                session=row.session,
                law_status=row.law_status,
                legisinfo_status=row.legisinfo_status
            )
        
        return builder


class BillsByTagFeedBuilder(BillsFeedBuilder):
    """Feed builder for bills filtered by tag (uses mv_feed_bills_by_tag)"""
    
    def __init__(self, tag: str, feed_url: str, base_link: str = "https://truecivic.ca"):
        """
        Initialize tag-filtered bills feed.
        
        Args:
            tag: Tag to filter by
            feed_url: URL of this feed
            base_link: Base URL for bill links
        """
        super().__init__(feed_url=feed_url, base_link=base_link)
        
        # Update metadata for tag-specific feed
        self.fg.title(f"TrueCivic - Bills Tagged: {tag}")
        self.fg.description(f"Parliamentary bills tagged with '{tag}'")
        self.tag = tag
    
    @classmethod
    async def from_materialized_view(
        cls,
        session: AsyncSession,
        tag: str,
        feed_url: str,
        limit: int = 50
    ) -> "BillsByTagFeedBuilder":
        """
        Create feed from mv_feed_bills_by_tag materialized view.
        
        Args:
            session: Database session
            tag: Tag to filter by
            feed_url: URL of this feed
            limit: Maximum number of entries
        
        Returns:
            Populated feed builder
        """
        builder = cls(tag=tag, feed_url=feed_url)
        
        # Query materialized view
        result = await session.execute(text("""
            SELECT 
                id, 
                number, 
                title_en, 
                introduced_date, 
                parliament, 
                session,
                law_status,
                updated_at
            FROM mv_feed_bills_by_tag
            WHERE tag = :tag
            ORDER BY introduced_date DESC
            LIMIT :limit
        """), {"tag": tag, "limit": limit})
        
        rows = result.fetchall()
        
        for row in rows:
            builder.add_bill_entry(
                bill_id=row.id,
                number=row.number,
                title_en=row.title_en,
                title_fr=None,
                introduced_date=row.introduced_date,
                parliament=row.parliament,
                session=row.session,
                law_status=row.law_status,
                legisinfo_status=None,
                subject_tags=[tag]
            )
        
        return builder


class AllEntitiesFeedBuilder(FeedBuilder):
    """
    Unified feed for all entities (bills, votes, debates).
    
    Uses mv_feed_all materialized view.
    """
    
    def __init__(self, feed_url: str, base_link: str = "https://truecivic.ca"):
        """
        Initialize unified feed builder.
        
        Args:
            feed_url: URL of this feed
            base_link: Base URL for entity links
        """
        super().__init__(
            title="TrueCivic - All Parliamentary Activity",
            description="Recent bills, votes, and debates from the Parliament of Canada",
            feed_url=feed_url,
            link=base_link,
            language="en-CA"
        )
        self.base_link = base_link
    
    @classmethod
    async def from_materialized_view(
        cls,
        session: AsyncSession,
        feed_url: str,
        limit: int = 100
    ) -> "AllEntitiesFeedBuilder":
        """
        Create feed from mv_feed_all materialized view.
        
        Args:
            session: Database session
            feed_url: URL of this feed
            limit: Maximum number of entries
        
        Returns:
            Populated feed builder
        """
        builder = cls(feed_url=feed_url)
        
        # Query unified view
        result = await session.execute(text(f"""
            SELECT 
                entity_type,
                entity_id,
                jurisdiction,
                event_date,
                event_type,
                title,
                description,
                parliament,
                session,
                updated_at
            FROM mv_feed_all
            ORDER BY event_date DESC, updated_at DESC
            LIMIT {limit}
        """))
        
        rows = result.fetchall()
        
        for row in rows:
            # Build GUID
            guid = GuidBuilder.build(
                jurisdiction=row.jurisdiction,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                event=row.event_type,
                date=row.event_date
            )
            
            # Build link based on entity type
            if row.entity_type == 'bill':
                link = f"{builder.base_link}/bills/{row.title}"  # title is bill number
            elif row.entity_type == 'vote':
                link = f"{builder.base_link}/votes/{row.entity_id}"
            elif row.entity_type == 'debate':
                link = f"{builder.base_link}/debates/{row.entity_id}"
            else:
                link = builder.base_link
            
            # Build title
            if row.entity_type == 'bill':
                title = f"Bill {row.title}: {row.description}"
            elif row.entity_type == 'vote':
                title = f"{row.title}: {row.description}"
            elif row.entity_type == 'debate':
                title = f"Debate: {row.title}"
            else:
                title = row.title
            
            # Build description
            description = f"{row.description}<br/>"
            description += f"<strong>Type:</strong> {row.entity_type.capitalize()}<br/>"
            description += f"<strong>Parliament:</strong> {row.parliament}-{row.session}"
            
            # Add entry
            builder.add_entry(
                title=title,
                link=link,
                description=description,
                guid=guid,
                pub_date=row.event_date,
                categories=[row.entity_type, row.event_type],
                entity_type=row.entity_type,
                entity_id=row.entity_id
            )
        
        return builder
