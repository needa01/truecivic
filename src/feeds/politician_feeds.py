"""
Politician Feed Builders
=========================
Feed builders for MP activity feeds.

Responsibility: Generate RSS/Atom feeds for individual MP activities
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .feed_builder import FeedBuilder, GuidBuilder, FeedFormat
from ..db.models import PoliticianModel, BillModel, VoteRecordModel, SpeechModel


class MPActivityFeedBuilder(FeedBuilder):
    """
    Feed builder for MP activity.
    
    Aggregates bills sponsored, votes cast, and speeches given by an MP.
    """
    
    def __init__(self, mp_id: int, mp_name: str, feed_url: str, base_link: str = "https://truecivic.ca"):
        """
        Initialize MP activity feed builder.
        
        Args:
            mp_id: Politician ID
            mp_name: Politician name
            feed_url: URL of this feed
            base_link: Base URL for links
        """
        super().__init__(
            title=f"TrueCivic - {mp_name} Activity",
            description=f"Recent parliamentary activity by {mp_name}",
            feed_url=feed_url,
            link=f"{base_link}/politicians/{mp_id}",
            language="en-CA"
        )
        self.mp_id = mp_id
        self.mp_name = mp_name
        self.base_link = base_link
    
    def add_bill_sponsored_entry(
        self,
        bill_id: int,
        bill_number: str,
        bill_title: str,
        introduced_date: datetime,
        summary: Optional[str] = None
    ):
        """Add bill sponsorship to feed"""
        guid = GuidBuilder.for_bill_sponsored(self.mp_id, bill_id)
        link = f"{self.base_link}/bills/{bill_id}"
        
        content = f"<p><strong>Bill Sponsored:</strong> {bill_number}</p>"
        if summary:
            content += f"<p>{summary}</p>"
        
        self.add_entry(
            title=f"Sponsored: {bill_number} - {bill_title}",
            link=link,
            description=content,
            content=content,
            pub_date=introduced_date,
            guid=guid,
            categories=["bill", "sponsorship"]
        )
    
    def add_vote_entry(
        self,
        vote_id: int,
        bill_number: str,
        vote_position: str,
        vote_date: datetime,
        bill_title: Optional[str] = None
    ):
        """Add vote record to feed"""
        guid = GuidBuilder.for_mp_vote(self.mp_id, vote_id)
        link = f"{self.base_link}/votes/{vote_id}"
        
        position_emoji = {
            "Yea": "✅",
            "Nay": "❌",
            "Paired": "↔️"
        }.get(vote_position, "•")
        
        title_text = f"{position_emoji} Voted {vote_position}: {bill_number}"
        if bill_title:
            title_text += f" - {bill_title}"
        
        content = f"<p><strong>Vote Position:</strong> {vote_position}</p>"
        content += f"<p><strong>Bill:</strong> {bill_number}</p>"
        if bill_title:
            content += f"<p>{bill_title}</p>"
        
        self.add_entry(
            title=title_text,
            link=link,
            description=content,
            content=content,
            pub_date=vote_date,
            guid=guid,
            categories=["vote", vote_position.lower()]
        )
    
    def add_speech_entry(
        self,
        speech_id: int,
        debate_id: int,
        speech_date: datetime,
        excerpt: str,
        chamber: Optional[str] = None
    ):
        """Add speech to feed"""
        guid = GuidBuilder.for_mp_speech(self.mp_id, speech_id)
        link = f"{self.base_link}/debates/{debate_id}#speech-{speech_id}"
        
        # Truncate excerpt
        if len(excerpt) > 300:
            excerpt = excerpt[:297] + "..."
        
        chamber_text = f" in the {chamber}" if chamber else ""
        
        self.add_entry(
            title=f"Speech{chamber_text}",
            link=link,
            description=excerpt,
            content=f"<p>{excerpt}</p>",
            pub_date=speech_date,
            guid=guid,
            categories=["speech", chamber.lower() if chamber else "debate"]
        )
    
    async def build_from_db(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> str:
        """
        Build feed from database for MP activity.
        
        Args:
            db: Database session
            limit: Max entries per category
            
        Returns:
            RSS/Atom feed XML
        """
        # Get bills sponsored
        bills_query = select(BillModel).where(
            BillModel.sponsor_id == self.mp_id
        ).order_by(BillModel.introduced_date.desc()).limit(limit)
        
        bills_result = await db.execute(bills_query)
        bills = bills_result.scalars().all()
        
        for bill in bills:
            if bill.introduced_date:
                self.add_bill_sponsored_entry(
                    bill_id=bill.id,
                    bill_number=bill.number,
                    bill_title=bill.title_en or bill.title_fr or "Untitled",
                    introduced_date=bill.introduced_date,
                    summary=bill.summary_en or bill.summary_fr
                )
        
        # Get votes with bills (join query)
        votes_query = text("""
            SELECT vr.id, vr.vote_id, vr.vote_position, v.date, b.number, b.title_en
            FROM vote_records vr
            JOIN votes v ON vr.vote_id = v.id
            LEFT JOIN bills b ON v.bill_id = b.id
            WHERE vr.politician_id = :mp_id
            ORDER BY v.date DESC
            LIMIT :limit
        """)
        
        votes_result = await db.execute(votes_query, {"mp_id": self.mp_id, "limit": limit})
        votes = votes_result.fetchall()
        
        for vote in votes:
            if vote.date:
                self.add_vote_entry(
                    vote_id=vote.vote_id,
                    bill_number=vote.number or "Unknown Bill",
                    vote_position=vote.vote_position or "Unknown",
                    vote_date=vote.date,
                    bill_title=vote.title_en
                )
        
        # Get speeches
        speeches_query = text("""
            SELECT s.id, s.debate_id, s.content_en, d.date, d.chamber
            FROM speeches s
            JOIN debates d ON s.debate_id = d.id
            WHERE s.politician_id = :mp_id
            ORDER BY d.date DESC
            LIMIT :limit
        """)
        
        speeches_result = await db.execute(speeches_query, {"mp_id": self.mp_id, "limit": limit // 2})
        speeches = speeches_result.fetchall()
        
        for speech in speeches:
            if speech.date and speech.content_en:
                self.add_speech_entry(
                    speech_id=speech.id,
                    debate_id=speech.debate_id,
                    speech_date=speech.date,
                    excerpt=speech.content_en,
                    chamber=speech.chamber
                )
        
        return self.build_xml(format=FeedFormat.RSS)
