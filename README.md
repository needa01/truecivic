# Parliament Explorer

A production-grade system for ingesting, indexing, and exploring Canadian Parliament data with multi-jurisdiction support from day one.

## 🎯 Product Vision

Parliament Explorer provides a mobile-first interface to explore federal Parliament data (Bills, MPs, Committees, Debates, Votes) with plans to expand to Senate and provincial legislatures. The system delivers:

- **Real-time bill tracking** with grounded AI summaries and source citations
- **Interactive graph visualization** showing relationships between bills, MPs, committees, and debates
- **Personalized RSS/Atom feeds** with device-level filtering (no authentication required)
- **Public REST + GraphQL APIs** for third-party integrations
- **Mobile-first responsive UI** with organic and hierarchical graph views

## 🏗️ Architecture

### Core Services (Railway)

1. **Postgres** (pgvector) - Primary OLTP + vector search
2. **Redis** - Caching, rate limiting, personalization tokens
3. **MinIO** - Raw/processed artifacts, DB backups
4. **Dagster** - Orchestration (webserver + daemon + worker)
5. **API** - REST + GraphQL + RSS/Atom endpoints
6. **Summarizer** - RAG pipeline for bill summaries
7. **Frontend** - Next.js mobile-first application

### Key Design Principles

- **Multi-jurisdiction from day one**: Namespaced data model supports federal House, Senate, and provinces without schema changes
- **Device-level personalization**: No user accounts; filtering via anonymous device IDs
- **RSS-first syndication**: No webhooks; all feeds via cacheable GET endpoints with strict anti-spam limits
- **Grounded AI**: All summaries include source citations with self-check guardrails
- **Idempotent ETL**: Natural-key-based upserts with provenance tracking

## 🚀 Getting Started

See [RUNNING.md](./RUNNING.md) for detailed setup and development instructions.

### Quick Start

```powershell
# Clone and enter directory
cd c:\Users\boredbedouin\Desktop\truecivic

# Set up Python environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Set up Node environment
cd frontend
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env with your Railway service URLs

# Run migrations
alembic upgrade head

# Start Dagster
dagster dev

# Start API (separate terminal)
cd api
uvicorn main:app --reload

# Start Frontend (separate terminal)
cd frontend
npm run dev
```

## 📊 Data Model

### Jurisdictions

- **Namespace format**: `ca-federal`, `ca-federal-senate`, `ca-on`, `ca-bc`
- **Primary keys**: All tables include `jurisdiction` + `chamber` (optional) + natural ID
- **Unique constraints**: `(jurisdiction, chamber?, natural_id)`

### Core Entities

- **MPs**: Members, parties, ridings, photos
- **Bills**: Full legislative lifecycle tracking
- **Votes**: Vote records with individual MP positions
- **Committees**: Meetings, evidence, topics
- **Debates**: Hansard transcripts with speeches
- **Documents**: Versioned full-text with embeddings
- **Rankings**: Computed relevance scores

## 🔌 API Overview

### REST Endpoints

```
/{jurisdiction}/v1/bills              # List bills with filters
/{jurisdiction}/v1/bills/{id}         # Bill details + summary
/{jurisdiction}/v1/graph              # Graph neighborhoods
/{jurisdiction}/v1/search             # Hybrid search
/{jurisdiction}/v1/preferences/ignore # Manage device ignores
```

### GraphQL

```graphql
query {
  bills(jurisdiction: "ca-federal", filter: {status: ACTIVE}) {
    id
    title
    status
    supporters {
      mp { name party }
    }
  }
}
```

### RSS/Atom Feeds

```
/{jurisdiction}/feeds/all.xml                  # All updates
/{jurisdiction}/feeds/bills/latest.xml         # Recent bills
/{jurisdiction}/feeds/bills/tag/{tag}.xml      # By topic
/{jurisdiction}/feeds/bill/{bill_id}.xml       # Single bill
/{jurisdiction}/feeds/mp/{mp_id}.xml           # MP activity
/{jurisdiction}/feeds/committee/{id}.xml       # Committee
/{jurisdiction}/feeds/search/{hash}.xml        # Saved search
/{jurisdiction}/feeds/p/{token}.xml            # Personalized
```

**Rate Limits**: 60 req/hour per IP; personalized feeds 30 req/hour per token

## 🛡️ Security & Privacy

- **No user PII**: Only anonymous device IDs for personalization
- **Cookie policy**: Essential only, `HttpOnly`, `SameSite=Lax`
- **Secrets management**: Railway environment variables, quarterly rotation
- **Network security**: Private service mesh; egress allowlist to Parliament sources
- **Backups**: Nightly Postgres dumps to MinIO; weekly restore tests

## 📈 Observability

### SLOs

- API p95 latency: <250ms (cached), <500ms (uncached)
- Data freshness: <60 minutes from source to site
- Feed cache hit rate: ≥70%

### Monitoring

- API latency, error rate, cache metrics
- ETL run durations and failures
- Feed build times and eviction counts
- Rate limit events and 429 responses

## 🗂️ Project Structure

```
parliament-explorer/
├── api/                    # FastAPI REST + GraphQL + RSS
├── frontend/               # Next.js mobile-first UI
├── dagster/                # Orchestration assets
├── summarizer/             # RAG pipeline
├── adapters/               # Data source adapters
│   ├── legisinfo/         # Federal bills
│   ├── hansard/           # Debates
│   └── committees/        # Committee data
├── models/                 # Shared data models
├── migrations/             # Alembic migrations
├── tests/                  # Test suites
└── docs/                   # ADRs and runbooks
```

## 📝 Documentation

- [RUNNING.md](./RUNNING.md) - Development setup and operations
- [docs/adr/](./docs/adr/) - Architecture decision records
- [docs/runbooks/](./docs/runbooks/) - Operational procedures

## 🧪 Testing

```powershell
# Unit tests
pytest tests/unit

# Integration tests
pytest tests/integration

# Feed validation
pytest tests/feeds

# Frontend tests
cd frontend
npm test
```

## 🚢 Deployment

Deployed to Railway with automatic deployments from `main` branch.

### Production Checklist

- [ ] All secrets rotated
- [ ] SBOM generated and scanned
- [ ] Backup/restore tested
- [ ] Load tests passed
- [ ] SLO alerts configured
- [ ] Status page live

## 📜 License

[Specify license]

## 🤝 Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development workflow and code standards.

## 📧 Contact

[Project contact information]
