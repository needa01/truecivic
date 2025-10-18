# TrueCivic - Complete Implementation Plan

**Last Updated**: October 17, 2025  
**Current Status**: Phase E (API) 100% Complete | Railway Worker Blocked  
**Overall Progress**: 37% (59/160 tasks)

---

## 📊 Executive Summary

### ✅ Completed Phases

**Phase A: Foundations** - 85% Complete (17/20 tasks)
- ✅ Railway infrastructure (6 services operational)
- ✅ PostgreSQL 17.6 + pgvector 0.8.1
- ✅ Redis 8.2.1, Kafka, MinIO (3 buckets)
- ⚠️ Missing: ADRs, CONTRIBUTING.md, pre-commit hooks

**Phase B: Schema & Migrations** - 70% Complete (14/20 tasks)
- ✅ 8 core tables (bills, politicians, votes, committees, debates, speeches)
- ✅ Alembic migrations (revision 7bd692ce137c)
- ⚠️ Missing: Materialized views, personalization tables

**Phase C: Orchestrator** - 60% Complete (12/20 tasks)
- ✅ Prefect 3.4.24 with 4 flow deployments
- ✅ Hourly/daily schedules configured
- ⚠️ Missing: Multi-jurisdiction support, sensors, lineage tracking

**Phase D: Adapters & ETL** - 40% Complete (8/20 tasks)
- ✅ LEGISinfo adapter (bills, politicians)
- ⚠️ Missing: Vote records, committee meetings, speech extraction

**Phase E: API** - **100% Complete** (20/20 tasks) ✅
- ✅ 9 REST routers (bills, politicians, votes, debates, committees, feeds, search, graph, preferences)
- ✅ GraphQL with Strawberry (8 DataLoaders)
- ✅ Rate limiting (Redis-based)
- ✅ Full-text search (PostgreSQL GIN indexes)
- ✅ RSS feeds (8 types)
- ✅ Graph API (bill-centric & politician-centric)
- **Total**: 2,771 lines across 3 commits

### 🚨 Critical Blocker

**Railway Worker Service FAILED**
- ❌ `intuitive-flow` trying to run non-existent frontend
- ❌ No Prefect Worker running on Railway
- ❌ ETL data not persisting to production database
- **Action Required**: Follow `docs/RAILWAY_WORKER_SETUP.md`

### ⏳ Remaining Phases

- **Phase F**: Frontend (10% - 2/20 tasks)
- **Phase G**: RAG & Ranking (0% - 0/20 tasks)
- **Phase H**: Hardening & Launch (5% - 1/20 tasks)

---

## 🎯 Implementation Roadmap

### **PRIORITY 1: CRITICAL - Fix Railway Worker (1 hour)**

**Status**: BLOCKING all ETL operations

**Tasks:**
1. ✅ Create `railway-worker.dockerfile` (done)
2. ✅ Create `prefect.yaml` deployments (done)
3. ⏳ Configure Railway service (manual Railway dashboard steps)
4. ⏳ Deploy Prefect flows to Railway
5. ⏳ Test end-to-end ETL pipeline
6. ⏳ Verify data persists to production database

**Guide**: See `docs/RAILWAY_WORKER_SETUP.md` for step-by-step instructions

**Success Criteria:**
- ✅ Worker service shows RUNNING in Railway
- ✅ `prefect deployment ls` shows 4 deployments
- ✅ Manual flow run completes successfully
- ✅ Database query returns bills: `SELECT COUNT(*) FROM bills;` > 0

---

### **PRIORITY 2: HIGH - Complete Phase D Adapters (Week 1)**

**Goal**: Populate missing data (vote records, committees, speeches)

#### Task D1: Vote Records Adapter (2 days)

**File**: `src/adapters/openparliament_votes.py`

**Current State:**
- ✅ Vote metadata fetched (date, result, counts)
- ❌ Individual MP votes NOT fetched

**Implementation:**

```python
# Add to openparliament_votes.py

async def fetch_vote_records(self, vote_id: int) -> List[VoteRecordData]:
    """Fetch individual MP votes for a specific vote.
    
    OpenParliament API: GET /votes/{id}/votemembers/
    Returns list of {politician_id, vote_position: 'Yea'|'Nay'|'Paired'}
    """
    url = f"{self.base_url}/votes/{vote_id}/votemembers/"
    response = await self.session.get(url)
    data = await response.json()
    
    vote_records = []
    for record in data.get("objects", []):
        vote_records.append(VoteRecordData(
            vote_id=vote_id,
            politician_id=record["politician_id"],
            vote_position=record["vote_position"],  # 'Yea', 'Nay', 'Paired'
        ))
    
    return vote_records

# Update fetch_votes() to also fetch vote records
async def fetch_votes_with_records(self, limit: int = 50) -> Tuple[List[VoteData], List[VoteRecordData]]:
    votes = await self.fetch_votes(limit)
    
    all_records = []
    for vote in votes:
        records = await self.fetch_vote_records(vote.id)
        all_records.extend(records)
    
    return votes, all_records
```

**Database Changes:**
- ✅ `vote_records` table already exists (5 columns, 3 indexes)
- ⏳ Add repository method: `VoteRecordRepository.upsert_many()`

**Integration:**
- Update `src/prefect_flows/vote_flows.py` (create if not exists)
- Add schedule: `cron: "30 * * * *"` (hourly, 30 minutes after bills)

**Estimated Lines**: ~200 lines (adapter + repository + flow)

**Success Criteria:**
- ✅ Vote records fetched for all votes
- ✅ Database query: `SELECT COUNT(*) FROM vote_records;` > 0
- ✅ Can query: "How did MP John Doe vote on Bill C-15?"

#### Task D2: Committee Meetings Adapter (2 days)

**File**: `src/adapters/openparliament_committees.py` (create new)

**API Endpoints:**
- `GET /committees/` - List of committees
- `GET /committees/{id}/meetings/` - Meeting list
- `GET /committees/meetings/{id}/` - Meeting details with witnesses

**Implementation:**

```python
# src/adapters/openparliament_committees.py

from dataclasses import dataclass
from typing import List
import aiohttp

@dataclass
class CommitteeData:
    id: int
    name_en: str
    name_fr: str
    acronym: str
    chamber: str  # 'House of Commons', 'Senate'
    url: str

@dataclass
class CommitteeMeetingData:
    id: int
    committee_id: int
    date: str  # ISO 8601
    number: int
    title_en: str
    title_fr: str
    witnesses: List[str]  # List of witness names
    url: str

class OpenParliamentCommitteeAdapter:
    def __init__(self, session: aiohttp.ClientSession):
        self.base_url = "https://api.openparliament.ca"
        self.session = session
    
    async def fetch_committees(self) -> List[CommitteeData]:
        """Fetch all active committees."""
        url = f"{self.base_url}/committees/"
        response = await self.session.get(url)
        data = await response.json()
        
        committees = []
        for obj in data.get("objects", []):
            committees.append(CommitteeData(
                id=obj["id"],
                name_en=obj["name"]["en"],
                name_fr=obj["name"]["fr"],
                acronym=obj["acronym"],
                chamber=obj["chamber"],
                url=obj["url"],
            ))
        
        return committees
    
    async def fetch_committee_meetings(
        self, 
        committee_id: int, 
        limit: int = 50
    ) -> List[CommitteeMeetingData]:
        """Fetch meetings for a specific committee."""
        url = f"{self.base_url}/committees/{committee_id}/meetings/"
        response = await self.session.get(url, params={"limit": limit})
        data = await response.json()
        
        meetings = []
        for obj in data.get("objects", []):
            meetings.append(CommitteeMeetingData(
                id=obj["id"],
                committee_id=committee_id,
                date=obj["date"],
                number=obj["number"],
                title_en=obj.get("title_en", ""),
                title_fr=obj.get("title_fr", ""),
                witnesses=obj.get("witnesses", []),
                url=obj["url"],
            ))
        
        return meetings
```

**Database Changes:**
- ✅ `committees` table exists (10 columns, 3 indexes)
- ⏳ Create migration for `committee_meetings` table (pending)
- ⏳ Add repository: `CommitteeRepository`, `CommitteeMeetingRepository`

**Prefect Flow:**
- Create `src/prefect_flows/committee_flows.py`
- Add deployment: `fetch-committees-daily` (cron: "0 4 * * *")

**Estimated Lines**: ~250 lines (adapter + repository + flow)

**Success Criteria:**
- ✅ All committees fetched and stored
- ✅ Committee meetings with witnesses populated
- ✅ RSS feed: `/feeds/committee/{id}.xml` shows actual data

#### Task D3: Speech Extraction from Debates (3 days)

**File**: `src/adapters/openparliament_debates.py` (extend existing)

**Current State:**
- ✅ Debate metadata fetched
- ❌ Individual speeches NOT extracted

**Implementation:**

```python
# Add to openparliament_debates.py

@dataclass
class SpeechData:
    id: int
    debate_id: int
    politician_id: Optional[int]
    speaker_name: str
    time: str  # HH:MM:SS
    content_en: str
    content_fr: Optional[str]
    h_id: str  # Hansard ID for permalinks

class OpenParliamentDebateAdapter:
    # ... existing code ...
    
    async def fetch_speeches_for_debate(
        self, 
        debate_id: int
    ) -> List[SpeechData]:
        """Extract individual speeches from a debate transcript.
        
        OpenParliament API: GET /debates/{id}/speeches/
        Returns list of speeches with politician attribution
        """
        url = f"{self.base_url}/debates/{debate_id}/speeches/"
        response = await self.session.get(url)
        data = await response.json()
        
        speeches = []
        for obj in data.get("objects", []):
            speeches.append(SpeechData(
                id=obj["id"],
                debate_id=debate_id,
                politician_id=obj.get("politician_id"),
                speaker_name=obj["speaker"]["name"],
                time=obj["time"],
                content_en=obj["content"]["en"],
                content_fr=obj["content"].get("fr"),
                h_id=obj["h_id"],
            ))
        
        return speeches
    
    async def fetch_debates_with_speeches(
        self, 
        limit: int = 10
    ) -> Tuple[List[DebateData], List[SpeechData]]:
        """Fetch debates and extract all speeches."""
        debates = await self.fetch_debates(limit)
        
        all_speeches = []
        for debate in debates:
            speeches = await self.fetch_speeches_for_debate(debate.id)
            all_speeches.extend(speeches)
        
        return debates, all_speeches
```

**Database Changes:**
- ✅ `speeches` table exists (10 columns, 3 indexes)
- ⏳ Add repository method: `SpeechRepository.upsert_many()`

**Prefect Flow:**
- Update `src/prefect_flows/debate_flows.py`
- Add deployment: `fetch-debates-daily` (cron: "0 5 * * *")

**Estimated Lines**: ~180 lines (adapter extension + repository + flow)

**Success Criteria:**
- ✅ Speeches extracted from all debates
- ✅ Politician attribution linked correctly
- ✅ MP activity feed shows speeches: `/feeds/mp/{id}.xml`

---

### **PRIORITY 3: HIGH - Build Frontend (Phase F) (Week 2-3)**

**Goal**: Create production-ready Next.js frontend with graph visualization

#### Task F1: Frontend Setup & Core Layout (1 day)

**Already Complete:**
- ✅ Next.js 14 initialized in `web/` directory
- ✅ TypeScript configured
- ✅ Tailwind CSS with truecivic design system

**Missing Components:**

```bash
# Install additional dependencies
cd web/
npm install @tanstack/react-query zustand reactflow recharts lucide-react
npm install @radix-ui/react-dropdown-menu @radix-ui/react-dialog
npm install d3 @types/d3
```

**Files to Create:**

1. **Layout with Navigation** - `web/src/components/layout/Layout.tsx`
2. **Header with Search** - `web/src/components/layout/Header.tsx`
3. **Footer** - `web/src/components/layout/Footer.tsx`
4. **Navigation Menu** - `web/src/components/layout/Nav.tsx`

**Estimated Lines**: ~400 lines (layout components)

#### Task F2: Bill List & Detail Pages (2 days)

**Pages:**

1. **Bill List Page** - `web/src/app/bills/page.tsx`
   - Search bar with autocomplete
   - Filters: parliament, session, status, tag
   - Pagination (20 per page)
   - Bill cards with status indicators

2. **Bill Detail Page** - `web/src/app/bills/[id]/page.tsx`
   - Bill metadata (number, title, sponsor, status)
   - Timeline (introduction → readings → votes → royal assent)
   - Graph canvas (embedded, toggle full-screen)
   - Related bills sidebar
   - Subscribe to RSS button
   - Ignore button (device-level preference)

**Components:**

1. **BillCard** - `web/src/components/bills/BillCard.tsx`
2. **BillTimeline** - `web/src/components/bills/BillTimeline.tsx`
3. **BillFilters** - `web/src/components/bills/BillFilters.tsx`
4. **StatusBadge** - `web/src/components/shared/StatusBadge.tsx`

**API Integration:**

```typescript
// web/src/lib/api/bills.ts

import { useQuery } from '@tanstack/react-query';

export interface Bill {
  id: number;
  number: string;
  title_en: string;
  title_fr: string;
  sponsor: Politician;
  status: string;
  parliament: number;
  session: number;
  introduced_date: string;
  url: string;
}

export const useBills = (filters: BillFilters) => {
  return useQuery({
    queryKey: ['bills', filters],
    queryFn: async () => {
      const params = new URLSearchParams(filters);
      const res = await fetch(`/api/v1/ca/bills?${params}`);
      return res.json();
    },
  });
};

export const useBill = (id: number) => {
  return useQuery({
    queryKey: ['bill', id],
    queryFn: async () => {
      const res = await fetch(`/api/v1/ca/bills/${id}`);
      return res.json();
    },
  });
};
```

**Estimated Lines**: ~800 lines (2 pages + 4 components + API hooks)

#### Task F3: Graph Canvas with D3.js (3 days)

**Component**: `web/src/components/graph/GraphCanvas.tsx`

**Features:**
- Force-directed layout (D3.js force simulation)
- Hierarchical layout (D3.js tree)
- Layout toggle (button in toolbar)
- Depth selector (1-3 levels)
- Type filters (bills, politicians, committees)
- Node click → open detail modal
- Node hover → show preview tooltip
- Zoom & pan (D3.js zoom behavior)
- Mobile-friendly (touch gestures)

**Implementation:**

```typescript
// web/src/components/graph/GraphCanvas.tsx

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { useGraphData } from '@/lib/api/graph';

interface GraphCanvasProps {
  entityId: number;
  entityType: 'bill' | 'politician';
  depth?: number;
  layout?: 'force' | 'hierarchical';
}

export function GraphCanvas({ 
  entityId, 
  entityType, 
  depth = 2, 
  layout = 'force' 
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const { data: graphData } = useGraphData(entityType, entityId, depth);
  
  useEffect(() => {
    if (!svgRef.current || !graphData) return;
    
    const svg = d3.select(svgRef.current);
    const width = svg.node()!.clientWidth;
    const height = svg.node()!.clientHeight;
    
    // Force-directed layout
    if (layout === 'force') {
      const simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.edges).id(d => d.id))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));
      
      // Render nodes and edges
      // ... (D3 rendering logic)
    }
    
    // Hierarchical layout
    if (layout === 'hierarchical') {
      const root = d3.hierarchy(graphData);
      const treeLayout = d3.tree().size([width, height]);
      treeLayout(root);
      
      // Render tree
      // ... (D3 tree rendering logic)
    }
    
    // Zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.5, 3])
      .on('zoom', (event) => {
        svg.select('g').attr('transform', event.transform);
      });
    
    svg.call(zoom);
    
  }, [graphData, layout, depth]);
  
  return <svg ref={svgRef} className="w-full h-full" />;
}
```

**Estimated Lines**: ~600 lines (graph canvas + toolbar + controls)

#### Task F4: Search Page (1 day)

**Page**: `web/src/app/search/page.tsx`

**Features:**
- Search bar with query highlighting
- Result snippets with excerpts (ts_headline from API)
- Filters: entity type (bills, politicians, debates)
- Pagination
- Search history (localStorage)
- Empty state with suggestions

**Estimated Lines**: ~350 lines (page + search results component)

#### Task F5: Politician Pages (1 day)

**Pages:**

1. **Politician List** - `web/src/app/politicians/page.tsx`
2. **Politician Detail** - `web/src/app/politicians/[id]/page.tsx`

**Components:**

1. **PoliticianCard** - `web/src/components/politicians/PoliticianCard.tsx`
2. **ActivityTimeline** - `web/src/components/politicians/ActivityTimeline.tsx`

**Estimated Lines**: ~450 lines

#### Task F6: Settings & Preferences Page (1 day)

**Page**: `web/src/app/settings/page.tsx`

**Features:**
- Ignored bills list (with X-Anon-Id from localStorage)
- Language toggle (English/French)
- Personalized feed token display
- RSS subscription guide
- Data freshness status

**Estimated Lines**: ~300 lines

**Total Frontend Estimate**: ~2,900 lines across 6 tasks

---

### **PRIORITY 4: MEDIUM - Complete Phase B Schema (Week 3)**

**Goal**: Add missing tables for personalization and materialized views

#### Task B1: Personalization Tables (1 day)

**Migration**: `migrations/versions/004_personalization.py`

```python
"""Add personalization tables

Revision ID: 004_personalization
Revises: 003_full_text_search
Create Date: 2025-10-17
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Ignored bills table
    op.create_table(
        'ignored_bills',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('anon_id', sa.String(64), nullable=False, index=True),
        sa.Column('bill_id', sa.Integer(), sa.ForeignKey('bills.id'), nullable=False),
        sa.Column('ignored_at', sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint('anon_id', 'bill_id', name='uq_ignored_bill'),
    )
    
    # Personalized feed tokens
    op.create_table(
        'personalized_feed_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token', sa.String(64), nullable=False, unique=True, index=True),
        sa.Column('anon_id', sa.String(64), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('last_accessed', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('access_count', sa.Integer(), default=0),
    )

def downgrade():
    op.drop_table('personalized_feed_tokens')
    op.drop_table('ignored_bills')
```

**Models**: Add to `src/db/models.py`

**Estimated Lines**: ~120 lines (migration + models)

#### Task B2: Materialized Views for Feeds (1 day)

**Migration**: `migrations/versions/005_materialized_views.py`

```sql
-- Materialized view for latest bills feed
CREATE MATERIALIZED VIEW mv_feed_bills_latest AS
SELECT 
    b.id,
    b.number,
    b.title_en,
    b.title_fr,
    b.introduced_date,
    b.status,
    p.name as sponsor_name,
    b.updated_at
FROM bills b
LEFT JOIN politicians p ON b.sponsor_id = p.id
WHERE b.introduced_date >= NOW() - INTERVAL '30 days'
ORDER BY b.introduced_date DESC;

-- Index for fast access
CREATE INDEX idx_mv_feed_bills_latest_date ON mv_feed_bills_latest(introduced_date DESC);

-- Materialized view for bills by tag
CREATE MATERIALIZED VIEW mv_feed_bills_by_tag AS
SELECT 
    unnest(b.tags) as tag,
    b.id,
    b.number,
    b.title_en,
    b.introduced_date,
    b.status
FROM bills b
WHERE array_length(b.tags, 1) > 0
ORDER BY tag, b.introduced_date DESC;

-- Index for tag lookups
CREATE INDEX idx_mv_feed_bills_by_tag_tag ON mv_feed_bills_by_tag(tag);
```

**Refresh Schedule**: Add to Prefect

```python
# src/prefect_flows/maintenance_flows.py

from prefect import flow, task
from sqlalchemy import text
from src.db.session import async_session_factory

@task
async def refresh_materialized_view(view_name: str):
    """Refresh a single materialized view."""
    async with async_session_factory() as session:
        await session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
        await session.commit()

@flow(name="refresh-materialized-views")
async def refresh_views_flow():
    """Refresh all feed materialized views hourly."""
    views = [
        "mv_feed_bills_latest",
        "mv_feed_bills_by_tag",
    ]
    
    for view in views:
        await refresh_materialized_view(view)
```

**Deployment**: Add to `prefect.yaml`

```yaml
- name: refresh-views-hourly
  entrypoint: src/prefect_flows/maintenance_flows.py:refresh_views_flow
  work_pool:
    name: default-agent-pool
  schedule:
    cron: "15 * * * *"  # Hourly at :15
    timezone: "UTC"
  tags:
    - production
    - maintenance
    - hourly
```

**Estimated Lines**: ~200 lines (migration + flow + deployment)

---

### **PRIORITY 5: MEDIUM - Complete Phase G (RAG & Ranking) (Week 4)**

**Status**: 0% complete, complex ML integration

#### Task G1: Embedding Generation (2 days)

**Goal**: Generate pgvector embeddings for semantic search

**Implementation:**

1. **Choose Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
   - 384 dimensions
   - Fast inference
   - Suitable for semantic similarity

2. **Embedding Service** - `src/services/embedding_service.py`

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List

class EmbeddingService:
    def __init__(self):
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.model.encode(texts)
        return embeddings.tolist()
```

3. **Database Schema** - Add to migration

```python
# Update bills table to add embedding column
op.add_column('bills', sa.Column('title_embedding', Vector(384), nullable=True))
op.create_index('idx_bills_title_embedding', 'bills', ['title_embedding'], 
                postgresql_using='ivfflat', 
                postgresql_ops={'title_embedding': 'vector_cosine_ops'})
```

4. **Prefect Flow** - `src/prefect_flows/embedding_flows.py`

```python
@flow(name="generate-embeddings-daily")
async def generate_embeddings_flow():
    """Generate embeddings for new bills without embeddings."""
    async with async_session_factory() as session:
        # Fetch bills without embeddings
        result = await session.execute(
            select(BillModel).where(BillModel.title_embedding.is_(None))
        )
        bills = result.scalars().all()
        
        service = EmbeddingService()
        
        for bill in bills:
            text = f"{bill.title_en} {bill.summary_en or ''}"
            embedding = service.generate_embedding(text)
            bill.title_embedding = embedding
        
        await session.commit()
```

**Estimated Lines**: ~300 lines (service + migration + flow)

#### Task G2: Hybrid Search (BM25 + Vector) (2 days)

**Goal**: Combine full-text search with semantic similarity

**Implementation:**

```python
# src/services/search_service.py

class SearchService:
    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        weights: dict = {'bm25': 0.7, 'vector': 0.3}
    ) -> List[BillModel]:
        """
        Hybrid search combining BM25 (keyword) and vector (semantic) search.
        
        Score = (weights['bm25'] * bm25_score) + (weights['vector'] * vector_score)
        """
        # Generate query embedding
        embedding_service = EmbeddingService()
        query_embedding = embedding_service.generate_embedding(query)
        
        async with async_session_factory() as session:
            # Full-text search (BM25-like)
            tsquery = func.plainto_tsquery('english', query)
            bm25_results = await session.execute(
                select(
                    BillModel.id,
                    func.ts_rank(BillModel.search_vector, tsquery).label('bm25_score')
                )
                .where(BillModel.search_vector.op('@@')(tsquery))
            )
            
            # Vector similarity search
            vector_results = await session.execute(
                select(
                    BillModel.id,
                    BillModel.title_embedding.cosine_distance(query_embedding).label('vector_distance')
                )
                .where(BillModel.title_embedding.is_not(None))
                .order_by('vector_distance')
                .limit(limit * 2)
            )
            
            # Merge results with weighted scoring
            # ... (combine scores and rank)
            
            return merged_results
```

**Estimated Lines**: ~250 lines (hybrid search service)

#### Task G3: LLM Summary Generation (3 days)

**Goal**: Generate AI summaries with citations

**Implementation:**

1. **Choose LLM**: OpenAI GPT-4 or Anthropic Claude
   - Budget: $0.01 per summary (reasonable for MVP)
   - Alternative: Self-hosted LLaMA 3.1 (more cost-effective at scale)

2. **Summary Service** - `src/services/summary_service.py`

```python
from openai import AsyncOpenAI
from typing import List

class SummaryService:
    def __init__(self):
        self.client = AsyncOpenAI()
    
    async def generate_summary(
        self, 
        bill: BillModel, 
        debates: List[DebateModel],
        max_tokens: int = 500
    ) -> str:
        """Generate AI summary with citations."""
        
        prompt = f"""
        Summarize this Canadian bill in plain language for a general audience.
        
        Bill {bill.number}: {bill.title_en}
        Status: {bill.status}
        Sponsor: {bill.sponsor.name} ({bill.sponsor.party})
        
        Key Debates:
        {self._format_debates(debates)}
        
        Provide a 2-3 paragraph summary covering:
        1. What the bill does (main purpose)
        2. Key provisions and changes
        3. Current status and next steps
        
        Use clear, accessible language. Cite specific sections when relevant.
        Format citations as [Source: Debate on YYYY-MM-DD].
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,  # Lower temperature for factual summaries
        )
        
        summary = response.choices[0].message.content
        
        # Validate citations exist
        if not self._has_valid_citations(summary):
            raise ValueError("Summary missing required citations")
        
        return summary
```

3. **Guardrails** - Hallucination detection

```python
def _validate_summary_accuracy(self, summary: str, bill: BillModel) -> bool:
    """Check for hallucinations using fact-checking."""
    
    # Extract claims from summary
    claims = self._extract_claims(summary)
    
    # Verify each claim against bill text
    for claim in claims:
        if not self._verify_claim(claim, bill):
            logger.warning(f"Potential hallucination detected: {claim}")
            return False
    
    return True
```

**Estimated Lines**: ~400 lines (summary service + guardrails + tests)

#### Task G4: Ranking System (2 days)

**Goal**: Score and rank bills by relevance

**Implementation:**

```python
# src/services/ranking_service.py

class RankingService:
    FACTORS = {
        'recency': 0.25,        # Newer bills ranked higher
        'activity': 0.20,       # More votes/debates = higher rank
        'sponsor_influence': 0.15,  # Cabinet ministers = higher rank
        'media_mentions': 0.10,  # External mentions (future)
        'user_interest': 0.30,   # Views, subscriptions, interactions
    }
    
    def calculate_bill_score(self, bill: BillModel) -> float:
        """Calculate composite ranking score (0-100)."""
        
        # Recency score (0-1)
        days_old = (datetime.now() - bill.introduced_date).days
        recency = max(0, 1 - (days_old / 365))  # Decay over 1 year
        
        # Activity score (0-1)
        activity = min(1, (bill.vote_count + bill.debate_count) / 10)
        
        # Sponsor influence score (0-1)
        sponsor_influence = 1.0 if bill.sponsor.is_cabinet else 0.5
        
        # User interest score (0-1) - placeholder
        user_interest = 0.5  # TODO: Track actual engagement
        
        # Weighted sum
        score = (
            self.FACTORS['recency'] * recency +
            self.FACTORS['activity'] * activity +
            self.FACTORS['sponsor_influence'] * sponsor_influence +
            self.FACTORS['user_interest'] * user_interest
        ) * 100
        
        return score
    
    async def update_rankings_daily(self):
        """Recalculate all bill rankings."""
        async with async_session_factory() as session:
            bills = await session.execute(select(BillModel))
            
            for bill in bills.scalars():
                bill.ranking_score = self.calculate_bill_score(bill)
            
            await session.commit()
```

**Database Changes:**

```python
# Add ranking_score column to bills table
op.add_column('bills', sa.Column('ranking_score', sa.Float(), default=50.0))
op.create_index('idx_bills_ranking_score', 'bills', ['ranking_score'])
```

**Estimated Lines**: ~250 lines (ranking service + migration)

**Total Phase G Estimate**: ~1,400 lines across 4 tasks

---

### **PRIORITY 6: MEDIUM - Phase H Hardening (Week 5)**

**Goal**: Production-ready testing, monitoring, and deployment

#### Task H1: Comprehensive Testing (3 days)

**Test Coverage Target**: 80%

**Test Suites:**

1. **Unit Tests** - `tests/unit/`
   - Models (30 tests)
   - Repositories (40 tests)
   - Services (50 tests)
   - Adapters (40 tests)

2. **Integration Tests** - `tests/integration/`
   - API endpoints (60 tests)
   - GraphQL queries (30 tests)
   - ETL pipelines (20 tests)
   - Feeds (20 tests)

3. **Load Tests** - `tests/load/`
   - API stress test (10k req/min)
   - Database query performance
   - Redis cache hit rates
   - Feed generation latency

**Implementation:**

```python
# tests/integration/test_api_bills.py

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_bills_list(client: AsyncClient):
    """Test GET /api/v1/ca/bills"""
    response = await client.get("/api/v1/ca/bills?limit=10")
    
    assert response.status_code == 200
    data = response.json()
    assert "bills" in data
    assert len(data["bills"]) <= 10
    assert data["total"] >= 0

@pytest.mark.asyncio
async def test_get_bill_detail(client: AsyncClient):
    """Test GET /api/v1/ca/bills/{id}"""
    response = await client.get("/api/v1/ca/bills/1")
    
    assert response.status_code == 200
    bill = response.json()
    assert "id" in bill
    assert "number" in bill
    assert "title_en" in bill

@pytest.mark.asyncio
async def test_search_bills(client: AsyncClient):
    """Test GET /api/v1/ca/search"""
    response = await client.get("/api/v1/ca/search?q=climate&limit=5")
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert all("snippet" in r for r in data["results"])
```

**Estimated Lines**: ~2,000 lines (180 tests)

#### Task H2: Monitoring & Observability (2 days)

**Tools:**
- Prometheus (metrics)
- Grafana (dashboards)
- Railway built-in monitoring

**Metrics to Track:**

1. **API Metrics**
   - Request rate (req/sec)
   - Response time (p50, p95, p99)
   - Error rate (%)
   - Rate limit hits

2. **ETL Metrics**
   - Flow run duration
   - Bills fetched per run
   - API call failures
   - Data quality issues

3. **Database Metrics**
   - Query latency
   - Connection pool usage
   - Table sizes
   - Index hit rates

4. **Cache Metrics**
   - Redis hit/miss rates
   - Eviction rate
   - Memory usage

**Implementation:**

```python
# src/middleware/metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

rate_limit_hits = Counter(
    'rate_limit_hits_total',
    'Total rate limit hits',
    ['ip_hash', 'endpoint']
)

class MetricsMiddleware:
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
```

**Grafana Dashboard:**

```yaml
# grafana-dashboard.json (simplified)

{
  "title": "TrueCivic API Dashboard",
  "panels": [
    {
      "title": "API Request Rate",
      "targets": [
        "rate(http_requests_total[5m])"
      ]
    },
    {
      "title": "Response Time (p95)",
      "targets": [
        "histogram_quantile(0.95, http_request_duration_seconds)"
      ]
    },
    {
      "title": "Error Rate",
      "targets": [
        "rate(http_requests_total{status=~'5..'}[5m])"
      ]
    }
  ]
}
```

**Estimated Lines**: ~400 lines (metrics middleware + dashboard config)

#### Task H3: Documentation & Deployment (2 days)

**Documentation to Create:**

1. **API Reference** - `docs/API.md`
   - All endpoints with examples
   - GraphQL schema documentation
   - Rate limit policies
   - Authentication (if added)

2. **Deployment Guide** - `docs/DEPLOYMENT.md`
   - Railway setup instructions
   - Environment variables
   - Database migrations
   - Monitoring setup

3. **Developer Guide** - `docs/DEVELOPER.md`
   - Local development setup
   - Testing guidelines
   - Contribution workflow
   - Code style (already in copilot-instructions.md)

4. **User Guide** - `docs/USER_GUIDE.md`
   - How to use the website
   - RSS feed subscription
   - Graph visualization guide
   - Personalization features

**Estimated Lines**: ~1,200 lines (documentation)

**Total Phase H Estimate**: ~3,600 lines across 3 tasks

---

## 📈 Overall Timeline

### Week 1: Fix Blocker & Complete Phase D
- **Day 1**: Railway worker setup (manual) - 1 hour
- **Day 2-3**: Vote records adapter - 200 lines
- **Day 4-5**: Committee meetings adapter - 250 lines
- **Day 6-7**: Speech extraction - 180 lines

**Output**: 630 lines, full ETL pipeline operational

### Week 2-3: Build Frontend (Phase F)
- **Day 1**: Setup & layout - 400 lines
- **Day 2-3**: Bill list & detail pages - 800 lines
- **Day 4-6**: Graph canvas - 600 lines
- **Day 7**: Search page - 350 lines
- **Day 8**: Politician pages - 450 lines
- **Day 9**: Settings page - 300 lines

**Output**: 2,900 lines, production-ready UI

### Week 3: Complete Schema (Phase B)
- **Day 1**: Personalization tables - 120 lines
- **Day 2**: Materialized views - 200 lines

**Output**: 320 lines, full schema complete

### Week 4: RAG & Ranking (Phase G)
- **Day 1-2**: Embedding generation - 300 lines
- **Day 3-4**: Hybrid search - 250 lines
- **Day 5-7**: LLM summaries - 400 lines
- **Day 8-9**: Ranking system - 250 lines

**Output**: 1,400 lines, AI-powered features

### Week 5: Hardening (Phase H)
- **Day 1-3**: Comprehensive testing - 2,000 lines
- **Day 4-5**: Monitoring - 400 lines
- **Day 6-7**: Documentation - 1,200 lines

**Output**: 3,600 lines, production-ready

---

## 📊 Final Progress Summary

| Phase | Current | Target | Lines to Write |
|-------|---------|--------|----------------|
| **A: Foundations** | 85% | 100% | ~150 lines (ADRs, docs) |
| **B: Schema** | 70% | 100% | ~320 lines (tables, views) |
| **C: Orchestrator** | 60% | 100% | ~400 lines (schedules, sensors) |
| **D: Adapters/ETL** | 40% | 100% | ~630 lines (3 adapters) |
| **E: API** | **100%** | **100%** | ✅ **COMPLETE** |
| **F: Frontend** | 10% | 100% | ~2,900 lines (UI) |
| **G: RAG/Ranking** | 0% | 100% | ~1,400 lines (ML) |
| **H: Hardening** | 5% | 100% | ~3,600 lines (tests, docs) |
| **TOTAL** | **37%** | **100%** | **~9,400 lines** |

**Current**: 59/160 tasks complete  
**Target**: 160/160 tasks complete  
**Estimated Effort**: ~5 weeks of focused development

---

## 🚀 Next Steps

1. **IMMEDIATE**: Follow `docs/RAILWAY_WORKER_SETUP.md` to fix Railway worker service
2. **Week 1**: Complete Phase D adapters (vote records, committees, speeches)
3. **Week 2-3**: Build Phase F frontend with graph visualization
4. **Week 3**: Complete Phase B schema (personalization, materialized views)
5. **Week 4**: Implement Phase G (RAG pipeline and ranking system)
6. **Week 5**: Phase H hardening (testing, monitoring, documentation)

---

## 📞 Support & Resources

- **Repository**: https://github.com/monuit/truecivic
- **Railway Dashboard**: https://railway.app/dashboard
- **Prefect UI**: https://prefect-production-a5a7.up.railway.app
- **Gap Analysis**: `IMPLEMENTATION_GAP_ANALYSIS.md`
- **Current Status**: `STATUS.md`
- **Railway Worker Guide**: `docs/RAILWAY_WORKER_SETUP.md`

---

**Last Updated**: October 17, 2025  
**Status**: Phase E complete, Railway worker blocked, 5 weeks remaining  
**Progress**: 37% → 100% (target)
