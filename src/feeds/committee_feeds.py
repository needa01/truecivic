"""
Committee Feed Builders
=======================
Feed builders for committee activity feeds.

Responsibility: Generate RSS/Atom feeds for committee meetings and reports
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .feed_builder import FeedBuilder, GuidBuilder, FeedFormat
from ..db.models import CommitteeModel, BillModel


class CommitteeFeedBuilder(FeedBuilder):
    """
    Feed builder for committee activity.
    
    Generates feeds for committee meetings, reports, and proceedings.
    """
    
    def __init__(
        self,
        committee_id: int,
        committee_name: str,
        feed_url: str,
        base_link: str = "https://truecivic.ca"
    ):
        """
        Initialize committee feed builder.
        
        Args:
            committee_id: Committee ID
            committee_name: Committee name
            feed_url: URL of this feed
            base_link: Base URL for links
        """
        super().__init__(
            title=f"TrueCivic - {committee_name} Activity",
            description=f"Recent activity from the {committee_name}",
            feed_url=feed_url,
            link=f"{base_link}/committees/{committee_id}",
            language="en-CA"
        )
        self.committee_id = committee_id
        self.committee_name = committee_name
        self.base_link = base_link
    
    def add_meeting_entry(
        self,
        meeting_id: int,
        meeting_date: datetime,
        title: str,
        description: Optional[str] = None,
        witnesses: Optional[str] = None
    ):
        """Add committee meeting to feed"""
        guid = GuidBuilder.for_committee_meeting(self.committee_id, meeting_id)
        link = f"{self.base_link}/committees/{self.committee_id}/meetings/{meeting_id}"
        
        content = f"<p><strong>Meeting:</strong> {title}</p>"
        if description:
            content += f"<p>{description}</p>"
        if witnesses:
            content += f"<p><strong>Witnesses:</strong> {witnesses}</p>"
        
        self.add_entry(
            title=f"Meeting: {title}",
            link=link,
            description=content,
            content=content,
            pub_date=meeting_date,
            guid=guid,
            categories=["meeting", "committee"]
        )
    
    def add_report_entry(
        self,
        report_id: int,
        report_date: datetime,
        title: str,
        summary: Optional[str] = None
    ):
        """Add committee report to feed"""
        guid = GuidBuilder.for_committee_report(self.committee_id, report_id)
        link = f"{self.base_link}/committees/{self.committee_id}/reports/{report_id}"
        
        content = f"<p><strong>Report:</strong> {title}</p>"
        if summary:
            content += f"<p>{summary}</p>"
        
        self.add_entry(
            title=f"Report: {title}",
            link=link,
            description=content,
            content=content,
            pub_date=report_date,
            guid=guid,
            categories=["report", "committee"]
        )
    
    async def build_from_db(
        self,
        db: AsyncSession,
        limit: int = 50
    ) -> str:
        """
        Build feed from database for committee activity.
        
        Note: Currently a placeholder as committee_meetings and committee_reports
        tables don't exist yet. This will be implemented when Phase D adapters
        are complete.
        
        Args:
            db: Database session
            limit: Max entries
            
        Returns:
            RSS/Atom feed XML
        """
        # Placeholder: Once committee_meetings and committee_reports tables exist,
        # query them here
        
        # For now, return empty feed with just committee info
        return self.build_xml(format=FeedFormat.RSS)


class BillTimelineFeedBuilder(FeedBuilder):
    """
    Feed builder for single bill timeline.
    
    Tracks all events related to a specific bill (votes, speeches, committee hearings).
    """
    
    def __init__(
        self,
        bill_id: int,
        bill_number: str,
        bill_title: str,
        feed_url: str,
        base_link: str = "https://truecivic.ca"
    ):
        """
        Initialize bill timeline feed builder.
        
        Args:
            bill_id: Bill ID
            bill_number: Bill number
            bill_title: Bill title
            feed_url: URL of this feed
            base_link: Base URL for links
        """
        super().__init__(
            title=f"TrueCivic - {bill_number} Timeline",
            description=f"Timeline of events for {bill_number}: {bill_title}",
            feed_url=feed_url,
            link=f"{base_link}/bills/{bill_id}",
            language="en-CA"
        )
        self.bill_id = bill_id
        self.bill_number = bill_number
        self.bill_title = bill_title
        self.base_link = base_link
    
    def add_introduced_entry(
        self,
        introduced_date: datetime,
        sponsor_name: Optional[str] = None
    ):
        """Add bill introduction event"""
        guid = GuidBuilder.for_bill_event(self.bill_id, "introduced")
        link = f"{self.base_link}/bills/{self.bill_id}"
        
        content = f"<p><strong>Bill Introduced:</strong> {self.bill_number}</p>"
        if sponsor_name:
            content += f"<p><strong>Sponsor:</strong> {sponsor_name}</p>"
        
        self.add_entry(
            title=f"📄 {self.bill_number} Introduced",
            link=link,
            description=content,
            content=content,
            pub_date=introduced_date,
            guid=guid,
            categories=["bill", "introduced"]
        )
    
    def add_vote_entry(
        self,
        vote_id: int,
        vote_date: datetime,
        result: str,
        yea_count: int,
        nay_count: int
    ):
        """Add vote on bill"""
        guid = GuidBuilder.for_bill_vote(self.bill_id, vote_id)
        link = f"{self.base_link}/votes/{vote_id}"
        
        result_emoji = "✅" if result.lower() == "passed" else "❌"
        
        content = f"<p><strong>Vote Result:</strong> {result}</p>"
        content += f"<p><strong>Yea:</strong> {yea_count} | <strong>Nay:</strong> {nay_count}</p>"
        
        self.add_entry(
            title=f"{result_emoji} Vote: {result} ({yea_count}-{nay_count})",
            link=link,
            description=content,
            content=content,
            pub_date=vote_date,
            guid=guid,
            categories=["vote", result.lower()]
        )
    
    def add_committee_referral_entry(
        self,
        referral_date: datetime,
        committee_name: str
    ):
        """Add committee referral event"""
        guid = GuidBuilder.for_bill_event(self.bill_id, f"committee-{committee_name}")
        link = f"{self.base_link}/bills/{self.bill_id}"
        
        content = f"<p>Bill referred to <strong>{committee_name}</strong> for study</p>"
        
        self.add_entry(
            title=f"📋 Referred to {committee_name}",
            link=link,
            description=content,
            content=content,
            pub_date=referral_date,
            guid=guid,
            categories=["committee", "referral"]
        )
    
    def add_royal_assent_entry(
        self,
        assent_date: datetime
    ):
        """Add royal assent event"""
        guid = GuidBuilder.for_bill_event(self.bill_id, "royal-assent")
        link = f"{self.base_link}/bills/{self.bill_id}"
        
        content = f"<p><strong>{self.bill_number}</strong> received Royal Assent and is now law</p>"
        
        self.add_entry(
            title=f"👑 Royal Assent - Now Law",
            link=link,
            description=content,
            content=content,
            pub_date=assent_date,
            guid=guid,
            categories=["bill", "royal-assent", "law"]
        )
    
    async def build_from_db(
        self,
        db: AsyncSession
    ) -> str:
        """
        Build feed from database for bill timeline.
        
        Args:
            db: Database session
            
        Returns:
            RSS/Atom feed XML
        """
        # Get bill details
        bill_query = select(BillModel).where(BillModel.id == self.bill_id)
        bill_result = await db.execute(bill_query)
        bill = bill_result.scalar_one_or_none()
        
        if not bill:
            return self.build_xml(format=FeedFormat.RSS)
        
        # Add introduction
        if bill.introduced_date:
            sponsor_name = None
            if bill.sponsor_id:
                sponsor_query = text("SELECT name FROM politicians WHERE id = :id")
                sponsor_result = await db.execute(sponsor_query, {"id": bill.sponsor_id})
                sponsor_row = sponsor_result.fetchone()
                if sponsor_row:
                    sponsor_name = sponsor_row.name
            
            self.add_introduced_entry(
                introduced_date=bill.introduced_date,
                sponsor_name=sponsor_name
            )
        
        # Add votes
        votes_query = text("""
            SELECT id, date, result, yea_count, nay_count
            FROM votes
            WHERE bill_id = :bill_id
            ORDER BY date DESC
        """)
        
        votes_result = await db.execute(votes_query, {"bill_id": self.bill_id})
        votes = votes_result.fetchall()
        
        for vote in votes:
            if vote.date:
                self.add_vote_entry(
                    vote_id=vote.id,
                    vote_date=vote.date,
                    result=vote.result or "Unknown",
                    yea_count=vote.yea_count or 0,
                    nay_count=vote.nay_count or 0
                )
        
        # Add royal assent
        if bill.law_date:
            self.add_royal_assent_entry(assent_date=bill.law_date)
        
        return self.build_xml(format=FeedFormat.RSS)
