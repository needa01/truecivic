"""
Graph API Endpoints
===================
Generate graph data for relationship visualization.

Endpoints:
    - GET /api/v1/ca/graph - Get graph neighborhood around a focus entity
    - GET /api/v1/ca/graph/bill/{bill_id} - Bill-centric graph
    - GET /api/v1/ca/graph/politician/{politician_id} - Politician-centric graph
    - GET /api/v1/ca/graph/committee/{committee_id} - Committee-centric graph

Responsibility: Build node/edge graphs for D3.js/vis.js visualization
"""

from typing import Optional, List, Dict, Any, Literal
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel, Field

from src.db.session import get_db
from src.db.models import (
    BillModel, 
    PoliticianModel, 
    VoteModel, 
    VoteRecordModel,
    CommitteeModel,
    DebateModel,
    SpeechModel
)


router = APIRouter()


# Response Models
class GraphNode(BaseModel):
    """Graph node representing an entity"""
    id: str = Field(..., description="Unique node ID (type:id)")
    type: str = Field(..., description="Node type: bill, politician, committee, vote, debate")
    label: str = Field(..., description="Display label")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node data")
    size: Optional[int] = Field(None, description="Visual size hint")
    color: Optional[str] = Field(None, description="Visual color hint")


class GraphEdge(BaseModel):
    """Graph edge representing a relationship"""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type: sponsored, voted_on, spoke_about, member_of")
    label: Optional[str] = Field(None, description="Edge label")
    weight: Optional[float] = Field(1.0, description="Edge weight for layout")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GraphResponse(BaseModel):
    """Graph data response"""
    focus: str = Field(..., description="Focus entity ID")
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    depth: int = Field(..., description="Graph depth traversed")
    node_count: int = Field(..., description="Total nodes")
    edge_count: int = Field(..., description="Total edges")


# Graph Builders
async def build_bill_graph(
    session: AsyncSession,
    bill_id: int,
    depth: int = 2
) -> GraphResponse:
    """
    Build graph centered on a bill.
    
    Includes:
    - Bill node
    - Sponsor politician
    - Votes on this bill
    - Politicians who voted
    - Committees that reviewed it
    - Debates mentioning it
    """
    nodes = []
    edges = []
    
    # Get bill
    bill = await session.get(BillModel, bill_id)
    if not bill:
        return GraphResponse(
            focus=f"bill:{bill_id}",
            nodes=[],
            edges=[],
            depth=0,
            node_count=0,
            edge_count=0
        )
    
    # Add bill node
    bill_node_id = f"bill:{bill.id}"
    nodes.append(GraphNode(
        id=bill_node_id,
        type="bill",
        label=f"{bill.number}: {bill.title_en or bill.title_fr or 'Untitled'}",
        metadata={
            "number": bill.number,
            "status": bill.law_status,
            "parliament": bill.parliament,
            "session": bill.session
        },
        size=30,
        color="#4CAF50"
    ))
    
    # Add sponsor if exists
    if bill.sponsor_politician_id:
        sponsor = await session.get(PoliticianModel, bill.sponsor_politician_id)
        if sponsor:
            sponsor_node_id = f"politician:{sponsor.id}"
            nodes.append(GraphNode(
                id=sponsor_node_id,
                type="politician",
                label=sponsor.name,
                metadata={
                    "party": sponsor.party,
                    "riding": sponsor.riding_name
                },
                size=20,
                color="#2196F3"
            ))
            edges.append(GraphEdge(
                source=sponsor_node_id,
                target=bill_node_id,
                type="sponsored",
                label="sponsored"
            ))
    
    # Get votes on this bill
    votes_query = select(VoteModel).where(VoteModel.bill_id == bill.id)
    votes_result = await session.execute(votes_query)
    votes = votes_result.scalars().all()
    
    for vote in votes:
        vote_node_id = f"vote:{vote.id}"
        nodes.append(GraphNode(
            id=vote_node_id,
            type="vote",
            label=f"Vote: {vote.result}",
            metadata={
                "date": str(vote.date),
                "result": vote.result,
                "yea_total": vote.yea_total,
                "nay_total": vote.nay_total
            },
            size=15,
            color="#FF9800"
        ))
        edges.append(GraphEdge(
            source=bill_node_id,
            target=vote_node_id,
            type="voted_on",
            label="voted on"
        ))
        
        # Add top voters if depth > 1
        if depth > 1:
            vote_records_query = select(VoteRecordModel).where(
                VoteRecordModel.vote_id == vote.id
            ).limit(10)
            vote_records_result = await session.execute(vote_records_query)
            vote_records = vote_records_result.scalars().all()
            
            for record in vote_records:
                if record.politician_id:
                    politician = await session.get(PoliticianModel, record.politician_id)
                    if politician:
                        pol_node_id = f"politician:{politician.id}"
                        # Add politician node if not exists
                        if not any(n.id == pol_node_id for n in nodes):
                            nodes.append(GraphNode(
                                id=pol_node_id,
                                type="politician",
                                label=politician.name,
                                metadata={"party": politician.party},
                                size=10,
                                color="#2196F3"
                            ))
                        # Add edge
                        edges.append(GraphEdge(
                            source=pol_node_id,
                            target=vote_node_id,
                            type="voted",
                            label=record.vote,
                            metadata={"vote": record.vote}
                        ))
    
    return GraphResponse(
        focus=bill_node_id,
        nodes=nodes,
        edges=edges,
        depth=depth,
        node_count=len(nodes),
        edge_count=len(edges)
    )


async def build_politician_graph(
    session: AsyncSession,
    politician_id: int,
    depth: int = 2
) -> GraphResponse:
    """
    Build graph centered on a politician.
    
    Includes:
    - Politician node
    - Bills sponsored
    - Votes participated in
    - Committees member of
    - Speeches given
    """
    nodes = []
    edges = []
    
    # Get politician
    politician = await session.get(PoliticianModel, politician_id)
    if not politician:
        return GraphResponse(
            focus=f"politician:{politician_id}",
            nodes=[],
            edges=[],
            depth=0,
            node_count=0,
            edge_count=0
        )
    
    # Add politician node
    pol_node_id = f"politician:{politician.id}"
    nodes.append(GraphNode(
        id=pol_node_id,
        type="politician",
        label=politician.name,
        metadata={
            "party": politician.party,
            "riding": politician.riding_name,
            "url": politician.url
        },
        size=30,
        color="#2196F3"
    ))
    
    # Get sponsored bills
    bills_query = select(BillModel).where(
        BillModel.sponsor_politician_id == politician.id
    ).limit(20)
    bills_result = await session.execute(bills_query)
    bills = bills_result.scalars().all()
    
    for bill in bills:
        bill_node_id = f"bill:{bill.id}"
        nodes.append(GraphNode(
            id=bill_node_id,
            type="bill",
            label=f"{bill.number}",
            metadata={"status": bill.law_status},
            size=20,
            color="#4CAF50"
        ))
        edges.append(GraphEdge(
            source=pol_node_id,
            target=bill_node_id,
            type="sponsored",
            label="sponsored"
        ))
    
    # Get vote records (sample)
    vote_records_query = select(VoteRecordModel).where(
        VoteRecordModel.politician_id == politician.id
    ).limit(10)
    vote_records_result = await session.execute(vote_records_query)
    vote_records = vote_records_result.scalars().all()
    
    for record in vote_records:
        vote = await session.get(VoteModel, record.vote_id)
        if vote:
            vote_node_id = f"vote:{vote.id}"
            if not any(n.id == vote_node_id for n in nodes):
                nodes.append(GraphNode(
                    id=vote_node_id,
                    type="vote",
                    label=f"Vote: {vote.result}",
                    metadata={"date": str(vote.date)},
                    size=15,
                    color="#FF9800"
                ))
            edges.append(GraphEdge(
                source=pol_node_id,
                target=vote_node_id,
                type="voted",
                label=record.vote,
                metadata={"vote": record.vote}
            ))
    
    # Get speeches (sample)
    speeches_query = select(SpeechModel).where(
        SpeechModel.politician_id == politician.id
    ).limit(5)
    speeches_result = await session.execute(speeches_query)
    speeches = speeches_result.scalars().all()
    
    for speech in speeches:
        debate = await session.get(DebateModel, speech.debate_id)
        if debate:
            debate_node_id = f"debate:{debate.id}"
            if not any(n.id == debate_node_id for n in nodes):
                nodes.append(GraphNode(
                    id=debate_node_id,
                    type="debate",
                    label=f"Debate {debate.sitting_date}",
                    metadata={"date": str(debate.sitting_date)},
                    size=12,
                    color="#9C27B0"
                ))
            edges.append(GraphEdge(
                source=pol_node_id,
                target=debate_node_id,
                type="spoke_in",
                label="spoke in"
            ))
    
    return GraphResponse(
        focus=pol_node_id,
        nodes=nodes,
        edges=edges,
        depth=depth,
        node_count=len(nodes),
        edge_count=len(edges)
    )


# Endpoints
@router.get("/graph", response_model=GraphResponse)
async def get_graph(
    focus: Literal["bill", "politician", "committee"] = Query(..., description="Focus entity type"),
    id: int = Query(..., description="Entity ID"),
    depth: int = Query(2, ge=1, le=3, description="Graph depth (1-3)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get graph neighborhood around a focus entity.
    
    Args:
        focus: Entity type to center graph on
        id: Entity ID
        depth: How many relationship hops to traverse (1-3)
        db: Database session
        
    Returns:
        GraphResponse with nodes and edges for visualization
        
    Examples:
        - Bill graph: ?focus=bill&id=123&depth=2
        - Politician graph: ?focus=politician&id=456&depth=2
    """
    if focus == "bill":
        return await build_bill_graph(db, id, depth)
    elif focus == "politician":
        return await build_politician_graph(db, id, depth)
    else:
        # Committee graph not yet implemented
        return GraphResponse(
            focus=f"{focus}:{id}",
            nodes=[],
            edges=[],
            depth=0,
            node_count=0,
            edge_count=0
        )


@router.get("/graph/bill/{bill_id}", response_model=GraphResponse)
async def get_bill_graph(
    bill_id: int = Path(..., description="Bill ID"),
    depth: int = Query(2, ge=1, le=3),
    db: AsyncSession = Depends(get_db)
):
    """
    Get graph centered on a bill.
    
    Shows relationships between bill, sponsor, votes, and voters.
    
    Args:
        bill_id: Bill ID
        depth: Graph depth
        db: Database session
        
    Returns:
        GraphResponse with bill-centric graph
    """
    return await build_bill_graph(db, bill_id, depth)


@router.get("/graph/politician/{politician_id}", response_model=GraphResponse)
async def get_politician_graph(
    politician_id: int = Path(..., description="Politician ID"),
    depth: int = Query(2, ge=1, le=3),
    db: AsyncSession = Depends(get_db)
):
    """
    Get graph centered on a politician.
    
    Shows bills sponsored, votes, speeches, and committee memberships.
    
    Args:
        politician_id: Politician ID
        depth: Graph depth
        db: Database session
        
    Returns:
        GraphResponse with politician-centric graph
    """
    return await build_politician_graph(db, politician_id, depth)
