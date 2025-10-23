"""
GraphQL Resolvers and DataLoaders
==================================
Query resolvers and DataLoaders for N+1 prevention.

Features:
    - DataLoaders for efficient batched loading
    - Query functions for list endpoints
    - Prevents N+1 query problem

Responsibility: GraphQL data fetching and batching
"""

from typing import List, Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.dataloader import DataLoader

from src.db.models import (
    BillModel,
    PoliticianModel,
    VoteModel,
    VoteRecordModel,
    CommitteeModel,
    DebateModel,
    SpeechModel
)


# DataLoader factory functions
def get_bill_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for bills by ID"""
    
    async def load_bills(ids: List[int]) -> List[Optional[BillModel]]:
        query = select(BillModel).where(BillModel.id.in_(ids))
        result = await db.execute(query)
        bills = result.scalars().all()
        
        # Create map for ordering
        bill_map = {bill.id: bill for bill in bills}
        return [bill_map.get(id) for id in ids]
    
    return DataLoader(load_fn=load_bills)


def get_politician_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for politicians by ID"""
    
    async def load_politicians(ids: List[int]) -> List[Optional[PoliticianModel]]:
        query = select(PoliticianModel).where(PoliticianModel.id.in_(ids))
        result = await db.execute(query)
        politicians = result.scalars().all()
        
        politician_map = {p.id: p for p in politicians}
        return [politician_map.get(id) for id in ids]
    
    return DataLoader(load_fn=load_politicians)


def get_vote_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for votes by ID"""
    
    async def load_votes(ids: List[int]) -> List[Optional[VoteModel]]:
        query = select(VoteModel).where(VoteModel.id.in_(ids))
        result = await db.execute(query)
        votes = result.scalars().all()
        
        vote_map = {v.id: v for v in votes}
        return [vote_map.get(id) for id in ids]
    
    return DataLoader(load_fn=load_votes)


def get_debate_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for debates by ID"""
    
    async def load_debates(ids: List[int]) -> List[Optional[DebateModel]]:
        query = select(DebateModel).where(DebateModel.id.in_(ids))
        result = await db.execute(query)
        debates = result.scalars().all()
        
        debate_map = {d.id: d for d in debates}
        return [debate_map.get(id) for id in ids]
    
    return DataLoader(load_fn=load_debates)


def get_votes_by_bill_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for votes by bill_id"""
    
    async def load_votes_by_bill(bill_ids: List[int]) -> List[List[VoteModel]]:
        query = select(VoteModel).where(VoteModel.bill_id.in_(bill_ids))
        result = await db.execute(query)
        votes = result.scalars().all()
        
        # Group by bill_id
        votes_by_bill: Dict[int, List[VoteModel]] = {}
        for vote in votes:
            if vote.bill_id not in votes_by_bill:
                votes_by_bill[vote.bill_id] = []
            votes_by_bill[vote.bill_id].append(vote)
        
        return [votes_by_bill.get(bill_id, []) for bill_id in bill_ids]
    
    return DataLoader(load_fn=load_votes_by_bill)


def get_bills_by_sponsor_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for bills by sponsor_id"""
    
    async def load_bills_by_sponsor(sponsor_ids: List[int]) -> List[List[BillModel]]:
        query = select(BillModel).where(BillModel.sponsor_politician_id.in_(sponsor_ids))
        result = await db.execute(query)
        bills = result.scalars().all()
        
        # Group by sponsor_id
        bills_by_sponsor: Dict[int, List[BillModel]] = {}
        for bill in bills:
            sponsor_id = bill.sponsor_politician_id
            if sponsor_id is None:
                continue
            if sponsor_id not in bills_by_sponsor:
                bills_by_sponsor[sponsor_id] = []
            bills_by_sponsor[sponsor_id].append(bill)
        
        return [bills_by_sponsor.get(sponsor_id, []) for sponsor_id in sponsor_ids]
    
    return DataLoader(load_fn=load_bills_by_sponsor)


def get_vote_records_by_vote_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for vote records by vote_id"""
    
    async def load_vote_records_by_vote(vote_ids: List[int]) -> List[List[VoteRecordModel]]:
        query = select(VoteRecordModel).where(VoteRecordModel.vote_id.in_(vote_ids))
        result = await db.execute(query)
        records = result.scalars().all()
        
        # Group by vote_id
        records_by_vote: Dict[int, List[VoteRecordModel]] = {}
        for record in records:
            if record.vote_id not in records_by_vote:
                records_by_vote[record.vote_id] = []
            records_by_vote[record.vote_id].append(record)
        
        return [records_by_vote.get(vote_id, []) for vote_id in vote_ids]
    
    return DataLoader(load_fn=load_vote_records_by_vote)


def get_vote_records_by_politician_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for vote records by politician_id"""
    
    async def load_vote_records_by_politician(politician_ids: List[int]) -> List[List[VoteRecordModel]]:
        query = select(VoteRecordModel).where(VoteRecordModel.politician_id.in_(politician_ids))
        result = await db.execute(query)
        records = result.scalars().all()
        
        # Group by politician_id
        records_by_politician: Dict[int, List[VoteRecordModel]] = {}
        for record in records:
            if record.politician_id not in records_by_politician:
                records_by_politician[record.politician_id] = []
            records_by_politician[record.politician_id].append(record)
        
        return [records_by_politician.get(politician_id, []) for politician_id in politician_ids]
    
    return DataLoader(load_fn=load_vote_records_by_politician)


def get_speeches_by_debate_loader(db: AsyncSession) -> DataLoader:
    """Create DataLoader for speeches by debate_id"""
    
    async def load_speeches_by_debate(debate_ids: List[int]) -> List[List[SpeechModel]]:
        query = select(SpeechModel).where(SpeechModel.debate_id.in_(debate_ids))
        result = await db.execute(query)
        speeches = result.scalars().all()
        
        # Group by debate_id
        speeches_by_debate: Dict[int, List[SpeechModel]] = {}
        for speech in speeches:
            if speech.debate_id not in speeches_by_debate:
                speeches_by_debate[speech.debate_id] = []
            speeches_by_debate[speech.debate_id].append(speech)
        
        return [speeches_by_debate.get(debate_id, []) for debate_id in debate_ids]
    
    return DataLoader(load_fn=load_speeches_by_debate)


# Query functions
async def get_bills(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    parliament: Optional[int] = None,
    session: Optional[int] = None
) -> List[BillModel]:
    """Get bills with filters"""
    query = select(BillModel)
    
    if parliament is not None:
        query = query.where(BillModel.parliament == parliament)
    if session is not None:
        query = query.where(BillModel.session == session)
    
    query = query.order_by(BillModel.introduced_date.desc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_politicians(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    party: Optional[str] = None,
    riding: Optional[str] = None
) -> List[PoliticianModel]:
    """Get politicians with filters"""
    query = select(PoliticianModel)
    
    if party:
        query = query.where(PoliticianModel.current_party == party)
    if riding:
        query = query.where(PoliticianModel.current_riding == riding)
    
    query = query.order_by(PoliticianModel.name)
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_votes(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    parliament: Optional[int] = None,
    session: Optional[int] = None
) -> List[VoteModel]:
    """Get votes with filters"""
    query = select(VoteModel)
    
    if parliament is not None:
        query = query.where(VoteModel.parliament == parliament)
    if session is not None:
        query = query.where(VoteModel.session == session)
    
    query = query.order_by(VoteModel.vote_date.desc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_debates(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0,
    chamber: Optional[str] = None
) -> List[DebateModel]:
    """Get debates with filters"""
    query = select(DebateModel)
    
    if chamber:
        query = query.where(DebateModel.chamber == chamber)
    
    query = query.order_by(DebateModel.date.desc())
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_committees(
    db: AsyncSession,
    limit: int = 20,
    offset: int = 0
) -> List[CommitteeModel]:
    """Get committees"""
    query = select(CommitteeModel)
    query = query.order_by(CommitteeModel.name_en)
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    return result.scalars().all()
