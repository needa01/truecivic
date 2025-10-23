"""
GraphQL Schema
==============
Strawberry GraphQL schema aligned with the production SQLAlchemy models.

Responsibility: GraphQL type definitions and resolvers.
"""

from datetime import datetime
from typing import List, Optional

import strawberry  # type: ignore[import]
from strawberry.types import Info  # type: ignore[import]

from src.db.models import (
    BillModel,
    CommitteeModel,
    DebateModel,
    PoliticianModel,
    SpeechModel,
    VoteModel,
    VoteRecordModel,
)


# --------------------------------------------------------------------------- #
# GraphQL Types
# --------------------------------------------------------------------------- #


@strawberry.type
class Bill:
    """Bill GraphQL type that mirrors the persisted schema."""

    id: int
    jurisdiction: str
    number: str
    parliament: int
    session: int
    title_en: str
    title_fr: Optional[str]
    short_title_en: Optional[str]
    short_title_fr: Optional[str]
    law_status: Optional[str]
    legisinfo_status: Optional[str]
    introduced_date: Optional[datetime]
    royal_assent_date: Optional[datetime]
    royal_assent_chapter: Optional[str]
    legisinfo_summary_en: Optional[str]
    legisinfo_summary_fr: Optional[str]
    subject_tags: Optional[List[str]]
    committee_studies: Optional[List[str]]
    sponsor_politician_id: Optional[int]
    sponsor_politician_name: Optional[str]
    source_openparliament: bool
    source_legisinfo: bool
    last_fetched_at: Optional[datetime]
    last_enriched_at: Optional[datetime]

    @strawberry.field
    async def sponsor(self, info: Info) -> Optional["Politician"]:
        """Resolve the sponsor politician for this bill."""
        if self.sponsor_politician_id is None:
            return None

        from api.graphql.resolvers import get_politician_loader

        loader = get_politician_loader(info.context["db"])
        politician = await loader.load(self.sponsor_politician_id)
        return Politician.from_model(politician) if politician else None

    @strawberry.field
    async def votes(self, info: Info) -> List["Vote"]:
        """Resolve votes tied to this bill."""
        from api.graphql.resolvers import get_votes_by_bill_loader

        loader = get_votes_by_bill_loader(info.context["db"])
        votes = await loader.load(self.id)
        return [Vote.from_model(vote) for vote in votes]

    @classmethod
    def from_model(cls, model: BillModel) -> "Bill":
        """Convert SQLAlchemy model to GraphQL type."""
        return cls(
            id=model.id,
            jurisdiction=model.jurisdiction,
            number=model.number,
            parliament=model.parliament,
            session=model.session,
            title_en=model.title_en,
            title_fr=model.title_fr,
            short_title_en=model.short_title_en,
            short_title_fr=model.short_title_fr,
            law_status=model.law_status,
            legisinfo_status=model.legisinfo_status,
            introduced_date=model.introduced_date,
            royal_assent_date=model.royal_assent_date,
            royal_assent_chapter=model.royal_assent_chapter,
            legisinfo_summary_en=model.legisinfo_summary_en,
            legisinfo_summary_fr=model.legisinfo_summary_fr,
            subject_tags=model.subject_tags,
            committee_studies=model.committee_studies,
            sponsor_politician_id=model.sponsor_politician_id,
            sponsor_politician_name=model.sponsor_politician_name,
            source_openparliament=model.source_openparliament,
            source_legisinfo=model.source_legisinfo,
            last_fetched_at=model.last_fetched_at,
            last_enriched_at=model.last_enriched_at,
        )


@strawberry.type
class Politician:
    """Politician GraphQL type."""

    id: int
    name: str
    given_name: Optional[str]
    family_name: Optional[str]
    gender: Optional[str]
    email: Optional[str]
    image_url: Optional[str]
    current_party: Optional[str]
    current_riding: Optional[str]
    current_role: Optional[str]
    parl_mp_id: Optional[str]
    last_fetched_at: datetime

    @strawberry.field
    async def sponsored_bills(self, info: Info, limit: int = 10) -> List[Bill]:
        """Resolve bills sponsored by this politician."""
        from api.graphql.resolvers import get_bills_by_sponsor_loader

        loader = get_bills_by_sponsor_loader(info.context["db"])
        bills = await loader.load(self.id)
        return [Bill.from_model(bill) for bill in bills[:limit]]

    @strawberry.field
    async def votes(self, info: Info, limit: int = 10) -> List["VoteRecord"]:
        """Resolve vote records for this politician."""
        from api.graphql.resolvers import get_vote_records_by_politician_loader

        loader = get_vote_records_by_politician_loader(info.context["db"])
        vote_records = await loader.load(self.id)
        return [VoteRecord.from_model(record) for record in vote_records[:limit]]

    @classmethod
    def from_model(cls, model: PoliticianModel) -> "Politician":
        return cls(
            id=model.id,
            name=model.name,
            given_name=model.given_name,
            family_name=model.family_name,
            gender=model.gender,
            email=model.email,
            image_url=model.image_url,
            current_party=model.current_party,
            current_riding=model.current_riding,
            current_role=model.current_role,
            parl_mp_id=model.parl_mp_id,
            last_fetched_at=model.last_fetched_at,
        )


@strawberry.type
class Vote:
    """Vote GraphQL type."""

    id: int
    jurisdiction: str
    vote_id: str
    parliament: int
    session: int
    vote_number: int
    chamber: str
    vote_date: datetime
    vote_description_en: Optional[str]
    vote_description_fr: Optional[str]
    bill_id: Optional[int]
    result: str
    yeas: int
    nays: int
    abstentions: int

    @strawberry.field
    async def bill(self, info: Info) -> Optional[Bill]:
        """Resolve the bill associated with this vote, if any."""
        if self.bill_id is None:
            return None

        from api.graphql.resolvers import get_bill_loader

        loader = get_bill_loader(info.context["db"])
        bill = await loader.load(self.bill_id)
        return Bill.from_model(bill) if bill else None

    @strawberry.field
    async def records(self, info: Info) -> List["VoteRecord"]:
        """Resolve detailed vote records (individual MP votes)."""
        from api.graphql.resolvers import get_vote_records_by_vote_loader

        loader = get_vote_records_by_vote_loader(info.context["db"])
        vote_records = await loader.load(self.id)
        return [VoteRecord.from_model(record) for record in vote_records]

    @classmethod
    def from_model(cls, model: VoteModel) -> "Vote":
        return cls(
            id=model.id,
            jurisdiction=model.jurisdiction,
            vote_id=model.vote_id,
            parliament=model.parliament,
            session=model.session,
            vote_number=model.vote_number,
            chamber=model.chamber,
            vote_date=model.vote_date,
            vote_description_en=model.vote_description_en,
            vote_description_fr=model.vote_description_fr,
            bill_id=model.bill_id,
            result=model.result,
            yeas=model.yeas,
            nays=model.nays,
            abstentions=model.abstentions,
        )


@strawberry.type
class VoteRecord:
    """Individual MP vote record."""

    id: int
    vote_id: int
    politician_id: int
    vote_position: str
    created_at: datetime

    @strawberry.field
    async def politician(self, info: Info) -> Optional[Politician]:
        from api.graphql.resolvers import get_politician_loader

        loader = get_politician_loader(info.context["db"])
        politician = await loader.load(self.politician_id)
        return Politician.from_model(politician) if politician else None

    @classmethod
    def from_model(cls, model: VoteRecordModel) -> "VoteRecord":
        return cls(
            id=model.id,
            vote_id=model.vote_id,
            politician_id=model.politician_id,
            vote_position=model.vote_position,
            created_at=model.created_at,
        )


@strawberry.type
class Committee:
    """Committee GraphQL type."""

    id: int
    jurisdiction: str
    committee_code: str
    name_en: Optional[str]
    name_fr: Optional[str]
    chamber: Optional[str]
    committee_type: Optional[str]
    website_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, model: CommitteeModel) -> "Committee":
        return cls(
            id=model.id,
            jurisdiction=model.jurisdiction,
            committee_code=model.committee_code,
            name_en=model.name_en,
            name_fr=model.name_fr,
            chamber=model.chamber,
            committee_type=model.committee_type,
            website_url=model.website_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


@strawberry.type
class Debate:
    """Debate GraphQL type."""

    id: int
    jurisdiction: str
    hansard_id: str
    parliament: int
    session: int
    sitting_date: datetime
    chamber: Optional[str]
    debate_type: Optional[str]
    document_url: Optional[str]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def speeches(self, info: Info) -> List["Speech"]:
        from api.graphql.resolvers import get_speeches_by_debate_loader

        loader = get_speeches_by_debate_loader(info.context["db"])
        speeches = await loader.load(self.id)
        return [Speech.from_model(speech) for speech in speeches]

    @classmethod
    def from_model(cls, model: DebateModel) -> "Debate":
        return cls(
            id=model.id,
            jurisdiction=model.jurisdiction,
            hansard_id=model.hansard_id,
            parliament=model.parliament,
            session=model.session,
            sitting_date=model.sitting_date,
            chamber=model.chamber,
            debate_type=model.debate_type,
            document_url=model.document_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


@strawberry.type
class Speech:
    """Speech GraphQL type."""

    id: int
    debate_id: int
    politician_id: Optional[int]
    speaker_name: str
    speaker_display_name: str
    sequence: int
    language: Optional[str]
    text_content: str
    timestamp_start: Optional[str]
    timestamp_end: Optional[str]
    created_at: datetime

    @strawberry.field
    async def politician(self, info: Info) -> Optional[Politician]:
        if self.politician_id is None:
            return None

        from api.graphql.resolvers import get_politician_loader

        loader = get_politician_loader(info.context["db"])
        politician = await loader.load(self.politician_id)
        return Politician.from_model(politician) if politician else None

    @classmethod
    def from_model(cls, model: SpeechModel) -> "Speech":
        return cls(
            id=model.id,
            debate_id=model.debate_id,
            politician_id=model.politician_id,
            speaker_name=model.speaker_name,
            speaker_display_name=model.speaker_display_name,
            sequence=model.sequence,
            language=model.language,
            text_content=model.text_content,
            timestamp_start=model.timestamp_start,
            timestamp_end=model.timestamp_end,
            created_at=model.created_at,
        )


# --------------------------------------------------------------------------- #
# Query Root
# --------------------------------------------------------------------------- #


@strawberry.type
class Query:
    """GraphQL Query root."""

    @strawberry.field
    async def bills(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0,
        parliament: Optional[int] = None,
        session: Optional[int] = None,
    ) -> List[Bill]:
        """Query bills with optional filters."""
        from api.graphql.resolvers import get_bills

        bills = await get_bills(
            info.context["db"],
            limit=limit,
            offset=offset,
            parliament=parliament,
            session=session,
        )
        return [Bill.from_model(bill) for bill in bills]

    @strawberry.field
    async def bill(self, info: Info, id: int) -> Optional[Bill]:
        """Fetch a single bill."""
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
        riding: Optional[str] = None,
    ) -> List[Politician]:
        """Query politicians with optional filters."""
        from api.graphql.resolvers import get_politicians

        politicians = await get_politicians(
            info.context["db"],
            limit=limit,
            offset=offset,
            party=party,
            riding=riding,
        )
        return [Politician.from_model(politician) for politician in politicians]

    @strawberry.field
    async def politician(self, info: Info, id: int) -> Optional[Politician]:
        """Fetch a single politician."""
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
        session: Optional[int] = None,
    ) -> List[Vote]:
        """Query votes with optional filters."""
        from api.graphql.resolvers import get_votes

        votes = await get_votes(
            info.context["db"],
            limit=limit,
            offset=offset,
            parliament=parliament,
            session=session,
        )
        return [Vote.from_model(vote) for vote in votes]

    @strawberry.field
    async def debates(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0,
        chamber: Optional[str] = None,
    ) -> List[Debate]:
        """Query debates."""
        from api.graphql.resolvers import get_debates

        debates = await get_debates(
            info.context["db"],
            limit=limit,
            offset=offset,
            chamber=chamber,
        )
        return [Debate.from_model(debate) for debate in debates]

    @strawberry.field
    async def committees(
        self,
        info: Info,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Committee]:
        """Query committees."""
        from api.graphql.resolvers import get_committees

        committees = await get_committees(
            info.context["db"],
            limit=limit,
            offset=offset,
        )
        return [Committee.from_model(committee) for committee in committees]


# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #


schema = strawberry.Schema(
    query=Query,
    extensions=[],  # Add depth/complexity limiting extensions here when ready
)
