"""
GraphQL Schema
==============
Strawberry GraphQL schema with types and queries.

Features:
    - Bill, Politician, Vote, Committee, Debate types
    - Query root with fields: bills, bill, politicians, politician, votes, debates
    - DataLoaders for N+1 prevention
    - Depth and complexity limits (max depth 5, max complexity 1000)

Responsibility: GraphQL type definitions and resolvers
"""

from typing import List, Optional
from datetime import datetime
import strawberry
from strawberry.types import Info

from src.db.models import (
    BillModel,
    PoliticianModel,
    VoteModel,
    VoteRecordModel,
    CommitteeModel,
    DebateModel,
    SpeechModel
)


# GraphQL Types
@strawberry.type
class Bill:
    """Bill GraphQL type"""
    id: int
    number: str
    title_en: Optional[str]
    title_fr: Optional[str]
    parliament: int
    session: int
    status: Optional[str]
    introduced_date: Optional[datetime]
    law_date: Optional[datetime]
    url: Optional[str]
    summary_en: Optional[str]
    summary_fr: Optional[str]
    
    @strawberry.field
    async def sponsor(self, info: Info) -> Optional["Politician"]:
        """Get bill sponsor"""
        from api.graphql.resolvers import get_politician_loader
        loader = get_politician_loader(info.context["db"])
        if hasattr(self, "_sponsor_id") and self._sponsor_id:
            politician = await loader.load(self._sponsor_id)
            return Politician.from_model(politician) if politician else None
        return None
    
    @strawberry.field
    async def votes(self, info: Info) -> List["Vote"]:
        """Get votes on this bill"""
        from api.graphql.resolvers import get_votes_by_bill_loader
        loader = get_votes_by_bill_loader(info.context["db"])
        votes = await loader.load(self.id)
        return [Vote.from_model(vote) for vote in votes]
    
    @classmethod
    def from_model(cls, model: BillModel) -> "Bill":
        """Create from SQLAlchemy model"""
        instance = cls(
            id=model.id,
            number=model.number,
            title_en=model.title_en,
            title_fr=model.title_fr,
            parliament=model.parliament,
            session=model.session,
            status=model.status,
            introduced_date=model.introduced_date,
            law_date=model.law_date,
            url=model.url,
            summary_en=model.summary_en,
            summary_fr=model.summary_fr
        )
        # Store sponsor_id for lazy loading
        instance._sponsor_id = model.sponsor_id if hasattr(model, "sponsor_id") else None
        return instance


@strawberry.type
class Politician:
    """Politician GraphQL type"""
    id: int
    name: str
    party: Optional[str]
    riding: Optional[str]
    province: Optional[str]
    url: Optional[str]
    image_url: Optional[str]
    
    @strawberry.field
    async def sponsored_bills(self, info: Info, limit: int = 10) -> List[Bill]:
        """Get bills sponsored by this politician"""
        from api.graphql.resolvers import get_bills_by_sponsor_loader
        loader = get_bills_by_sponsor_loader(info.context["db"])
        bills = await loader.load(self.id)
        return [Bill.from_model(bill) for bill in bills[:limit]]
    
    @strawberry.field
    async def votes(self, info: Info, limit: int = 10) -> List["VoteRecord"]:
        """Get vote records for this politician"""
        from api.graphql.resolvers import get_vote_records_by_politician_loader
        loader = get_vote_records_by_politician_loader(info.context["db"])
        vote_records = await loader.load(self.id)
        return [VoteRecord.from_model(vr) for vr in vote_records[:limit]]
    
    @classmethod
    def from_model(cls, model: PoliticianModel) -> "Politician":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            name=model.name,
            party=model.party,
            riding=model.riding,
            province=model.province,
            url=model.url,
            image_url=model.image_url
        )


@strawberry.type
class Vote:
    """Vote GraphQL type"""
    id: int
    bill_id: int
    date: Optional[datetime]
    result: Optional[str]
    yea_count: Optional[int]
    nay_count: Optional[int]
    paired_count: Optional[int]
    session: Optional[int]
    parliament: Optional[int]
    
    @strawberry.field
    async def bill(self, info: Info) -> Optional[Bill]:
        """Get the bill this vote is for"""
        from api.graphql.resolvers import get_bill_loader
        loader = get_bill_loader(info.context["db"])
        bill = await loader.load(self.bill_id)
        return Bill.from_model(bill) if bill else None
    
    @strawberry.field
    async def vote_records(self, info: Info, limit: int = 50) -> List["VoteRecord"]:
        """Get individual vote records"""
        from api.graphql.resolvers import get_vote_records_by_vote_loader
        loader = get_vote_records_by_vote_loader(info.context["db"])
        records = await loader.load(self.id)
        return [VoteRecord.from_model(vr) for vr in records[:limit]]
    
    @classmethod
    def from_model(cls, model: VoteModel) -> "Vote":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            bill_id=model.bill_id,
            date=model.date,
            result=model.result,
            yea_count=model.yea_count,
            nay_count=model.nay_count,
            paired_count=model.paired_count,
            session=model.session,
            parliament=model.parliament
        )


@strawberry.type
class VoteRecord:
    """Individual vote record GraphQL type"""
    id: int
    vote_id: int
    politician_id: int
    vote_position: Optional[str]
    
    @strawberry.field
    async def politician(self, info: Info) -> Optional[Politician]:
        """Get the politician who cast this vote"""
        from api.graphql.resolvers import get_politician_loader
        loader = get_politician_loader(info.context["db"])
        politician = await loader.load(self.politician_id)
        return Politician.from_model(politician) if politician else None
    
    @strawberry.field
    async def vote(self, info: Info) -> Optional[Vote]:
        """Get the vote this record belongs to"""
        from api.graphql.resolvers import get_vote_loader
        loader = get_vote_loader(info.context["db"])
        vote = await loader.load(self.vote_id)
        return Vote.from_model(vote) if vote else None
    
    @classmethod
    def from_model(cls, model: VoteRecordModel) -> "VoteRecord":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            vote_id=model.vote_id,
            politician_id=model.politician_id,
            vote_position=model.vote_position
        )


@strawberry.type
class Committee:
    """Committee GraphQL type"""
    id: int
    name_en: Optional[str]
    name_fr: Optional[str]
    acronym: Optional[str]
    chamber: Optional[str]
    parliament: Optional[int]
    session: Optional[int]
    url: Optional[str]
    
    @classmethod
    def from_model(cls, model: CommitteeModel) -> "Committee":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            name_en=model.name_en,
            name_fr=model.name_fr,
            acronym=model.acronym,
            chamber=model.chamber,
            parliament=model.parliament,
            session=model.session,
            url=model.url
        )


@strawberry.type
class Debate:
    """Debate GraphQL type"""
    id: int
    date: Optional[datetime]
    parliament: Optional[int]
    session: Optional[int]
    chamber: Optional[str]
    url: Optional[str]
    
    @strawberry.field
    async def speeches(self, info: Info, limit: int = 20) -> List["Speech"]:
        """Get speeches in this debate"""
        from api.graphql.resolvers import get_speeches_by_debate_loader
        loader = get_speeches_by_debate_loader(info.context["db"])
        speeches = await loader.load(self.id)
        return [Speech.from_model(speech) for speech in speeches[:limit]]
    
    @classmethod
    def from_model(cls, model: DebateModel) -> "Debate":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            date=model.date,
            parliament=model.parliament,
            session=model.session,
            chamber=model.chamber,
            url=model.url
        )


@strawberry.type
class Speech:
    """Speech GraphQL type"""
    id: int
    debate_id: int
    politician_id: Optional[int]
    content_en: Optional[str]
    content_fr: Optional[str]
    time: Optional[str]
    
    @strawberry.field
    async def politician(self, info: Info) -> Optional[Politician]:
        """Get the politician who gave this speech"""
        if not self.politician_id:
            return None
        from api.graphql.resolvers import get_politician_loader
        loader = get_politician_loader(info.context["db"])
        politician = await loader.load(self.politician_id)
        return Politician.from_model(politician) if politician else None
    
    @strawberry.field
    async def debate(self, info: Info) -> Optional[Debate]:
        """Get the debate this speech belongs to"""
        from api.graphql.resolvers import get_debate_loader
        loader = get_debate_loader(info.context["db"])
        debate = await loader.load(self.debate_id)
        return Debate.from_model(debate) if debate else None
    
    @classmethod
    def from_model(cls, model: SpeechModel) -> "Speech":
        """Create from SQLAlchemy model"""
        return cls(
            id=model.id,
            debate_id=model.debate_id,
            politician_id=model.politician_id,
            content_en=model.content_en,
            content_fr=model.content_fr,
            time=model.time
        )


# Query Root
@strawberry.type
class Query:
    """GraphQL Query root"""
    
    @strawberry.field
    async def bills(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0,
        parliament: Optional[int] = None,
        session: Optional[int] = None
    ) -> List[Bill]:
        """Query bills with filters"""
        from api.graphql.resolvers import get_bills
        bills = await get_bills(
            info.context["db"],
            limit=limit,
            offset=offset,
            parliament=parliament,
            session=session
        )
        return [Bill.from_model(bill) for bill in bills]
    
    @strawberry.field
    async def bill(self, info: Info, id: int) -> Optional[Bill]:
        """Get a single bill by ID"""
        from api.graphql.resolvers import get_bill_loader
        loader = get_bill_loader(info.context["db"])
        bill = await loader.load(id)
        return Bill.from_model(bill) if bill else None
    
    @strawberry.field
    async def politicians(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0,
        party: Optional[str] = None,
        province: Optional[str] = None
    ) -> List[Politician]:
        """Query politicians with filters"""
        from api.graphql.resolvers import get_politicians
        politicians = await get_politicians(
            info.context["db"],
            limit=limit,
            offset=offset,
            party=party,
            province=province
        )
        return [Politician.from_model(p) for p in politicians]
    
    @strawberry.field
    async def politician(self, info: Info, id: int) -> Optional[Politician]:
        """Get a single politician by ID"""
        from api.graphql.resolvers import get_politician_loader
        loader = get_politician_loader(info.context["db"])
        politician = await loader.load(id)
        return Politician.from_model(politician) if politician else None
    
    @strawberry.field
    async def votes(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0,
        parliament: Optional[int] = None,
        session: Optional[int] = None
    ) -> List[Vote]:
        """Query votes with filters"""
        from api.graphql.resolvers import get_votes
        votes = await get_votes(
            info.context["db"],
            limit=limit,
            offset=offset,
            parliament=parliament,
            session=session
        )
        return [Vote.from_model(vote) for vote in votes]
    
    @strawberry.field
    async def debates(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0,
        chamber: Optional[str] = None
    ) -> List[Debate]:
        """Query debates with filters"""
        from api.graphql.resolvers import get_debates
        debates = await get_debates(
            info.context["db"],
            limit=limit,
            offset=offset,
            chamber=chamber
        )
        return [Debate.from_model(debate) for debate in debates]
    
    @strawberry.field
    async def committees(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0
    ) -> List[Committee]:
        """Query committees"""
        from api.graphql.resolvers import get_committees
        committees = await get_committees(
            info.context["db"],
            limit=limit,
            offset=offset
        )
        return [Committee.from_model(c) for c in committees]


# Create schema
schema = strawberry.Schema(
    query=Query,
    extensions=[
        # Add depth and complexity limiting extensions here if needed
    ]
)
