# Running Parliament Explorer

Operational guide and task tracking for development and deployment.

## 🎯 Current Status

- [ ] **Phase A**: Foundations (Week 1)
- [ ] **Phase B**: Schema & Migrations (Week 2)
- [ ] **Phase C**: Orchestrator (Week 3)
- [ ] **Phase D**: Adapters & ETL (Weeks 4-5)
- [ ] **Phase E**: API (Week 6)
- [ ] **Phase F**: Frontend (Weeks 7-8)
- [ ] **Phase G**: Summaries & Ranking (Week 9)
- [ ] **Phase H**: Hardening & Launch (Week 10)

---

## 📋 Master Task List

### Phase A: Foundations (Week 1)

#### Railway Infrastructure
- [ ] **A1.1** Create Railway project and configure services
  - [ ] Provision Postgres with pgvector plugin
  - [ ] Provision Redis instance
  - [ ] Set up MinIO service (or use Railway storage + S3 API)
  - [ ] Configure private networking between services
  - [ ] Set up public domains for API and Frontend
  - [ ] Configure egress allowlist for Parliament endpoints

- [ ] **A1.2** Environment configuration
  - [ ] Create `.env.example` with all required variables
  - [ ] Document secret generation procedures
  - [ ] Set Railway environment variables for all services
  - [ ] Configure volume mounts for Dagster and MinIO

- [ ] **A1.3** MinIO bucket structure
  - [ ] Create `parl-raw` bucket with jurisdiction prefixes
  - [ ] Create `parl-processed` bucket with entity prefixes
  - [ ] Create `backups` bucket for DB dumps
  - [ ] Set bucket policies and lifecycle rules
  - [ ] Create access keys for services

#### Documentation & Standards
- [ ] **A1.4** Write Architecture Decision Records (ADRs)
  - [ ] ADR-001: Multi-jurisdiction data model design
  - [ ] ADR-002: Natural key strategy and ID conventions
  - [ ] ADR-003: RSS anti-spam limits and caching policy
  - [ ] ADR-004: Device-level personalization without auth
  - [ ] ADR-005: Dagster orchestration patterns
  - [ ] ADR-006: Vector search and embedding strategy

- [ ] **A1.5** Project scaffolding
  - [ ] Initialize Git repository with branch protection
  - [ ] Set up Python project structure and `pyproject.toml`
  - [ ] Initialize Next.js frontend with TypeScript
  - [ ] Configure linting (ruff, eslint) and formatting (black, prettier)
  - [ ] Set up pre-commit hooks
  - [ ] Create `CONTRIBUTING.md` with code standards

---

### Phase B: Schema & Migrations (Week 2)

#### Database Schema
- [ ] **B2.1** Core tables with jurisdiction support
  - [ ] Create `jurisdiction` table (slug, name, type, status)
  - [ ] Create `party` table (jurisdiction, name, abbrev, color)
  - [ ] Create `riding` table (jurisdiction, name, province, geom optional)
  - [ ] Create `mp` table (jurisdiction, member_id, party_id, riding_id, dates, photo)
  - [ ] Add unique constraints: `(jurisdiction, natural_id)`

- [ ] **B2.2** Legislative entities
  - [ ] Create `bill` table (jurisdiction, number, parliament, session, chamber, legisinfo_id, title_en/fr, status, stage, dates, tags, urls)
  - [ ] Create `vote` table (jurisdiction, chamber, vote_id, bill_id, date, result, aggregates)
  - [ ] Create `vote_record` table (vote_id, mp_id, position)
  - [ ] Create `committee` table (jurisdiction, abbr, name, url)
  - [ ] Create `committee_meeting` table (committee_id, date, evidence_url, topics)
  - [ ] Create `debate` table (jurisdiction, hansard_id, sitting_date, chamber, url)
  - [ ] Create `speech` table (debate_id, mp_id, language, text, offset, sequence)

- [ ] **B2.3** Documents and embeddings
  - [ ] Create `document` table (jurisdiction, entity_type, ref_id, version, language, source_url, sha256, text_content)
  - [ ] Enable pgvector extension
  - [ ] Create `embedding` table (document_id, chunk_id, vector, token_count, start_char, end_char)
  - [ ] Create HNSW index on `embedding.vector`
  - [ ] Create GIN indexes on `to_tsvector` for full-text search

- [ ] **B2.4** Ranking and provenance
  - [ ] Create `ranking` table (jurisdiction, entity_type, ref_id, score, explain_json, computed_at)
  - [ ] Create `provenance` table (jurisdiction, entity_type, ref_id, source_url, fetched_at, sha256, content_type, schema_version)
  - [ ] Add indexes on provenance fingerprints

- [ ] **B2.5** Personalization
  - [ ] Create `ignored_bill` table (anon_id, jurisdiction, bill_id, created_at)
  - [ ] Create `personalized_feed_token` table (token, anon_id, created_at, last_used)
  - [ ] Add indexes for fast lookups

- [ ] **B2.6** Materialized views for feeds
  - [ ] Create `mv_feed_all` view (all entities with update timestamp)
  - [ ] Create `mv_feed_bills_latest` view
  - [ ] Create `mv_feed_bills_by_tag` view
  - [ ] Create refresh functions and indexes
  - [ ] Create search materialized view with hybrid scoring

- [ ] **B2.7** Migrations
  - [ ] Set up Alembic with multi-head support
  - [ ] Write initial migration with all schemas
  - [ ] Create migration testing framework
  - [ ] Document rollback procedures

---

### Phase C: Orchestrator (Week 3)

#### Dagster Setup
- [ ] **C3.1** Dagster project initialization
  - [ ] Create Dagster project structure
  - [ ] Configure `dagster.yaml` for Railway
  - [ ] Set up workspace with code locations
  - [ ] Configure sensor and schedule definitions
  - [ ] Set up resources (Postgres, Redis, MinIO)

- [ ] **C3.2** Asset parameterization
  - [ ] Create `JurisdictionConfig` for asset parameterization
  - [ ] Implement `@asset` decorator patterns for multi-jurisdiction
  - [ ] Create asset groups by entity type
  - [ ] Define asset dependencies and lineage
  - [ ] Implement partition mapping for jurisdiction

- [ ] **C3.3** MinIO integration
  - [ ] Create `MinIOResource` with bucket operations
  - [ ] Implement manifest generation (JSON metadata per fetch)
  - [ ] Create provenance hash recording
  - [ ] Implement artifact versioning
  - [ ] Add checksum validation on read

- [ ] **C3.4** Schedules (Eastern Time)
  - [ ] Schedule: `ca-federal-legisinfo` @ 06:00 ET
  - [ ] Schedule: `ca-federal-hansard` @ 06:15 ET
  - [ ] Schedule: `ca-federal-committees` @ 06:15 ET
  - [ ] Schedule: `ca-federal-normalize` @ 06:45 ET
  - [ ] Schedule: `ca-federal-embeddings` @ 07:00 ET
  - [ ] Schedule: `ca-federal-rankings` @ 07:00 ET
  - [ ] Schedule: `ca-federal-feed-refresh` @ 07:15 ET
  - [ ] Create schedule builder for future jurisdictions (20-min offsets)

- [ ] **C3.5** Sensors and triggers
  - [ ] Sensor: detect LEGISinfo data changes (fingerprint delta)
  - [ ] Sensor: detect Hansard updates
  - [ ] Sensor: trigger downstream on source change
  - [ ] Implement backoff and retry logic
  - [ ] Add sensor logging and alerting

- [ ] **C3.6** Idempotency and lineage
  - [ ] Implement upsert patterns with `ON CONFLICT`
  - [ ] Record asset run metadata in Postgres
  - [ ] Create lineage tracking table
  - [ ] Implement run deduplication
  - [ ] Add dry-run mode for testing

---

### Phase D: Adapters & ETL (Weeks 4-5)

#### Source Adapters
- [ ] **D4.1** LEGISinfo adapter (federal bills)
  - [ ] Create HTTP client with retry/backoff
  - [ ] Implement bill list scraper
  - [ ] Implement bill detail scraper
  - [ ] Parse sponsors, status, readings, committees
  - [ ] Extract full-text URLs
  - [ ] Handle English/French versions
  - [ ] Write unit tests with fixtures
  - [ ] Write integration tests with mock responses

- [ ] **D4.2** Hansard adapter (debates)
  - [ ] Create Hansard XML parser
  - [ ] Extract debate metadata
  - [ ] Parse speech segments with MP attribution
  - [ ] Handle language tagging
  - [ ] Extract topics and bill references
  - [ ] Store raw XML in MinIO
  - [ ] Write tests with sample Hansard files

- [ ] **D4.3** Committee adapter
  - [ ] Scrape committee list
  - [ ] Parse meeting notices
  - [ ] Extract evidence URLs
  - [ ] Link meetings to bills
  - [ ] Store meeting transcripts
  - [ ] Write tests

- [ ] **D4.4** Vote adapter
  - [ ] Scrape vote list by session
  - [ ] Parse vote results and individual records
  - [ ] Link votes to bills
  - [ ] Calculate party aggregates
  - [ ] Write tests

- [ ] **D4.5** MP and Party adapter
  - [ ] Scrape current MP list
  - [ ] Extract party affiliations
  - [ ] Download MP photos to MinIO
  - [ ] Track membership changes over time
  - [ ] Write tests

#### Normalization & Loading
- [ ] **D4.6** Normalization pipeline
  - [ ] Create `Normalizer` base class
  - [ ] Implement bill normalizer (raw → schema)
  - [ ] Implement debate normalizer
  - [ ] Implement committee normalizer
  - [ ] Implement vote normalizer
  - [ ] Add validation with Pydantic models
  - [ ] Write normalization tests

- [ ] **D4.7** Upsert logic
  - [ ] Create `Upserter` with `ON CONFLICT` patterns
  - [ ] Implement bill upsert with natural key
  - [ ] Implement MP upsert with membership tracking
  - [ ] Implement debate and speech upsert
  - [ ] Implement committee and meeting upsert
  - [ ] Implement vote and vote_record upsert
  - [ ] Add constraint violation handling
  - [ ] Log upsert stats (inserted, updated, skipped)

- [ ] **D4.8** Backfill baseline
  - [ ] Create backfill script for 44th Parliament
  - [ ] Backfill bills (all statuses)
  - [ ] Backfill votes
  - [ ] Backfill Hansard debates
  - [ ] Backfill committees
  - [ ] Verify data integrity post-backfill
  - [ ] Document backfill procedures

- [ ] **D4.9** Integrity checks
  - [ ] Implement foreign key validation checks
  - [ ] Check bill → MP sponsor links
  - [ ] Check vote → bill links
  - [ ] Check debate → MP speaker links
  - [ ] Implement orphan detection
  - [ ] Create data quality dashboard in Dagster

---

### Phase E: API (Week 6)

#### REST Endpoints
- [ ] **E5.1** FastAPI project setup
  - [ ] Initialize FastAPI app with CORS
  - [ ] Set up dependency injection for DB/Redis
  - [ ] Configure logging and tracing
  - [ ] Set up Pydantic response models
  - [ ] Add OpenAPI customization

- [ ] **E5.2** Bill endpoints
  - [ ] `GET /{jurisdiction}/v1/bills` - list with filters (status, chamber, tags, party_support, sort, limit, offset)
  - [ ] `GET /{jurisdiction}/v1/bills/{id}` - detail with summary, committees, debates, supporters/opponents
  - [ ] Apply device ignores via `X-Anon-Id` header
  - [ ] Implement caching with Redis
  - [ ] Add rate limiting
  - [ ] Write API tests

- [ ] **E5.3** Graph endpoints
  - [ ] `GET /{jurisdiction}/v1/graph` - neighborhoods with query params (focus, id, depth, layout)
  - [ ] Implement node/edge builders for typed graph
  - [ ] Support organic (force-directed) and hierarchical layouts
  - [ ] Apply device ignores
  - [ ] Cache graph neighborhoods
  - [ ] Write graph tests

- [ ] **E5.4** Search endpoints
  - [ ] `GET /{jurisdiction}/v1/search` - hybrid BM25 + vector rerank
  - [ ] Implement query parsing and filter extraction
  - [ ] Execute BM25 via materialized view
  - [ ] Rerank top-K with vector similarity
  - [ ] Return entity references with snippets
  - [ ] Apply device ignores
  - [ ] Write search tests

- [ ] **E5.5** Preferences endpoints
  - [ ] `POST /{jurisdiction}/v1/preferences/ignore` - add ignore (bill/mp/committee)
  - [ ] `DELETE /{jurisdiction}/v1/preferences/ignore` - remove ignore
  - [ ] `GET /{jurisdiction}/v1/preferences/ignored` - list ignored items
  - [ ] Validate `anon_id` format
  - [ ] Write preference tests

- [ ] **E5.6** Rate limiting middleware
  - [ ] Implement Redis-based rate limiter
  - [ ] Anonymous: 600 req/day per IP
  - [ ] Burst: 60 req/min per IP
  - [ ] Entity detail: 120 req/hour
  - [ ] Graph: 60 req/hour
  - [ ] Search: 120 req/hour
  - [ ] Return standard rate limit headers
  - [ ] Return 429 with `Retry-After` on limit
  - [ ] Write rate limit tests

#### GraphQL
- [ ] **E5.7** GraphQL setup
  - [ ] Add Strawberry GraphQL to FastAPI
  - [ ] Define types: MP, Bill, Vote, Committee, Debate, Edge, Graph
  - [ ] Implement resolvers with DataLoaders for N+1 prevention
  - [ ] Add query depth and complexity limits
  - [ ] Apply device ignores in resolvers
  - [ ] Write GraphQL tests

#### RSS/Atom Feeds
- [ ] **E5.8** Feed generation infrastructure
  - [ ] Create `FeedBuilder` base class (RSS 2.0 + Atom support)
  - [ ] Implement GUID generation: `{jurisdiction}:{entity_type}:{id}:{event}:{date}`
  - [ ] Implement item deduplication within window
  - [ ] Add citations to descriptions with "Read full bill" links
  - [ ] Set `Cache-Control`, `ETag`, `Last-Modified` headers
  - [ ] Support 304 Not Modified responses

- [ ] **E5.9** Feed endpoints
  - [ ] `GET /{jurisdiction}/feeds/all.xml` - all updates (50 items, TTL 5 min)
  - [ ] `GET /{jurisdiction}/feeds/bills/latest.xml` - recent bills
  - [ ] `GET /{jurisdiction}/feeds/bills/tag/{tag}.xml` - by topic
  - [ ] `GET /{jurisdiction}/feeds/bill/{bill_id}.xml` - single bill timeline
  - [ ] `GET /{jurisdiction}/feeds/mp/{mp_id}.xml` - MP activity
  - [ ] `GET /{jurisdiction}/feeds/committee/{id}.xml` - committee updates
  - [ ] `GET /{jurisdiction}/feeds/search/{hash}.xml` - saved search results
  - [ ] `GET /{jurisdiction}/feeds/p/{token}.xml` - personalized feed with ignores
  - [ ] Mirror all as `.atom` endpoints

- [ ] **E5.10** Feed caching and limits
  - [ ] Implement Redis cache with TTL per feed scope
  - [ ] Rebuild only if `MAX(updated_at)` changed
  - [ ] Enforce rebuild cap: ≤12/hour per jurisdiction per scope
  - [ ] Queue additional rebuilds for next window
  - [ ] Per-IP limit: 60 req/hour (burst 10)
  - [ ] Per-token limit: 30 req/hour (burst 10)
  - [ ] Global limit: 1,000 responses/hour per instance
  - [ ] Return 429 with `Retry-After` on limit
  - [ ] Fallback to stale cache on 503
  - [ ] Add `robots.txt` with `Crawl-delay: 60` for `/feeds/`

- [ ] **E5.11** Feed validation and testing
  - [ ] Validate RSS 2.0 against spec
  - [ ] Validate Atom 1.0 against spec
  - [ ] Test GUID uniqueness and stability
  - [ ] Test cache behavior (hit, miss, stale)
  - [ ] Test rate limits and 429 responses
  - [ ] Test 304 Not Modified
  - [ ] Load test feed endpoints

---

### Phase F: Frontend (Weeks 7-8)

#### Next.js Setup
- [ ] **F6.1** Project initialization
  - [ ] Initialize Next.js 14+ with App Router
  - [ ] Configure TypeScript strict mode
  - [ ] Set up Tailwind CSS with mobile-first utilities
  - [ ] Configure environment variables for API base URL
  - [ ] Set up SWR or React Query for data fetching
  - [ ] Add PWA manifest for mobile

- [ ] **F6.2** Layout and navigation
  - [ ] Create root layout with jurisdiction switcher
  - [ ] Implement mobile navigation drawer
  - [ ] Create breadcrumb component
  - [ ] Add "Last Updated" banner component
  - [ ] Create loading and error boundaries
  - [ ] Implement dark mode toggle (optional)

#### Core Pages
- [ ] **F6.3** Home page
  - [ ] Feed widgets (latest bills, active votes)
  - [ ] Top bills by ranking
  - [ ] Quick filters (status, chamber, tags)
  - [ ] Subscribe to feeds CTAs
  - [ ] Mobile-optimized cards

- [ ] **F6.4** Bills index page
  - [ ] Sortable table/list view (rank, updated, introduced)
  - [ ] Filters: status, chamber, tags, party support
  - [ ] Pagination or infinite scroll
  - [ ] Bulk actions: Ignore, Save View, Share, Subscribe
  - [ ] Mobile-optimized filters drawer

- [ ] **F6.5** Bill detail page
  - [ ] Summary section (grounded, with citations)
  - [ ] Key facts card (introduced date, topics, status/reading)
  - [ ] Supporters/opponents tabs with MP cards
  - [ ] Committee trail timeline
  - [ ] Debates timeline with speeches
  - [ ] Source links (LEGISinfo, full text)
  - [ ] Mobile graph drawer toggle
  - [ ] Ignore button
  - [ ] Subscribe to bill feed button

- [ ] **F6.6** Graph canvas
  - [ ] Implement force-directed (organic) layout with D3.js or vis.js
  - [ ] Implement hierarchical layout
  - [ ] Toggle between layouts
  - [ ] Depth selector (1-3)
  - [ ] Type filters (bill, MP, committee, debate)
  - [ ] Node click → detail panel or navigate
  - [ ] Deep drills: MP → sponsored bills → committees
  - [ ] Save graph view
  - [ ] Mobile drawer for graph on small screens
  - [ ] Export graph as image

- [ ] **F6.7** Search page
  - [ ] Omnibox with autocomplete
  - [ ] Grouped results by entity type
  - [ ] Result snippets with highlights
  - [ ] Filter by type, jurisdiction, date range
  - [ ] "Save as feed" button per query
  - [ ] Mobile-optimized results

- [ ] **F6.8** Settings page
  - [ ] Ranking sliders (relevance weights)
  - [ ] Ignored items manager (list + remove)
  - [ ] Language toggle (EN/FR)
  - [ ] Personalized feed token display and regenerate
  - [ ] RSS subscription guide
  - [ ] Data freshness status

#### Components
- [ ] **F6.9** Reusable components
  - [ ] MP card with photo, party color, riding
  - [ ] Bill card with status badge, tags, summary snippet
  - [ ] Committee card
  - [ ] Timeline component for events
  - [ ] Tag pills
  - [ ] Share modal
  - [ ] Subscribe modal with feed URL and QR code
  - [ ] Loading skeletons

- [ ] **F6.10** Mobile optimization
  - [ ] Test on iOS Safari and Chrome Android
  - [ ] Lighthouse CI: performance ≥90, accessibility ≥90
  - [ ] Touch-friendly buttons (min 44px)
  - [ ] Swipe gestures for drawers
  - [ ] Optimize images with Next.js Image
  - [ ] Lazy load below-the-fold content

---

### Phase G: Summaries & Ranking (Week 9)

#### RAG Pipeline
- [ ] **G7.1** Embedding generation
  - [ ] Choose embedding model (OpenAI, Cohere, or local)
  - [ ] Implement chunking strategy (500 tokens, 100 overlap)
  - [ ] Create `EmbeddingService` with batch processing
  - [ ] Store embeddings in `embedding` table
  - [ ] Create Dagster asset for embedding materialization
  - [ ] Schedule daily embedding updates

- [ ] **G7.2** Retrieval and summarization
  - [ ] Implement vector similarity search (top-K chunks)
  - [ ] Create prompt template for bill summary with citations
  - [ ] Integrate LLM (OpenAI GPT-4, Anthropic Claude, or local)
  - [ ] Implement self-check: verify claims against sources
  - [ ] Format summary with inline citations
  - [ ] Store summaries in `document` table
  - [ ] Cache summaries with invalidation on bill updates

- [ ] **G7.3** Guardrails
  - [ ] Implement hallucination detection
  - [ ] Validate citation references (chunk IDs exist)
  - [ ] Flag low-confidence summaries for review
  - [ ] Add fallback to extractive summary if generative fails
  - [ ] Log guardrail failures for analysis

- [ ] **G7.4** Summary UI integration
  - [ ] Display summary on bill detail page
  - [ ] Show inline citation links (click → source)
  - [ ] Add "Summary generated from..." disclaimer
  - [ ] Allow user feedback (helpful/not helpful)
  - [ ] Show summary date and trigger re-summarization if stale

#### Ranking System
- [ ] **G7.5** Ranking computation
  - [ ] Define ranking factors (recency, activity, controversy, user signals)
  - [ ] Implement scoring algorithm
  - [ ] Store scores in `ranking` table with explainability JSON
  - [ ] Create Dagster asset for daily ranking materialization
  - [ ] Expose ranking in bill list API

- [ ] **G7.6** Personalized ranking
  - [ ] Implement sliders in Settings for user-defined weights
  - [ ] Store weights in Redis by `anon_id`
  - [ ] Recompute personalized ranking on-the-fly or cache per profile
  - [ ] Apply personalized ranking to bill lists and feeds

---

### Phase H: Hardening & Launch (Week 10)

#### Testing & QA
- [ ] **H8.1** Load testing
  - [ ] Set up Locust or k6 for load tests
  - [ ] Test API endpoints at 100 req/s
  - [ ] Test feed endpoints at peak RSS polling load
  - [ ] Test graph endpoints at concurrent load
  - [ ] Verify rate limits trigger correctly
  - [ ] Verify cache hit rates under load
  - [ ] Document performance benchmarks

- [ ] **H8.2** Integration testing
  - [ ] End-to-end tests: bill creation → display → feed
  - [ ] Test personalization flow: ignore → verify absence
  - [ ] Test jurisdiction switching
  - [ ] Test feed subscription and polling
  - [ ] Test graph navigation and deep drills
  - [ ] Test search relevance with golden queries

- [ ] **H8.3** Security testing
  - [ ] Run OWASP ZAP or Burp Suite scan
  - [ ] Verify input validation on all endpoints
  - [ ] Test SQL injection resistance
  - [ ] Test XSS protection
  - [ ] Verify CORS configuration
  - [ ] Test rate limit bypass attempts
  - [ ] Verify secret redaction in logs

- [ ] **H8.4** Failover and resilience
  - [ ] Test Postgres failover (if using HA setup)
  - [ ] Test Redis failover
  - [ ] Test MinIO unavailability (graceful degradation)
  - [ ] Test Dagster run failures and retries
  - [ ] Test API 503 fallback to stale cache
  - [ ] Document recovery procedures

#### Backup & Recovery
- [ ] **H8.5** Backup automation
  - [ ] Create nightly Postgres dump script
  - [ ] Upload dumps to MinIO `backups` bucket
  - [ ] Implement retention policy (30 days, weekly archives)
  - [ ] Create weekly restore test job
  - [ ] Document backup locations and encryption

- [ ] **H8.6** Runbooks
  - [ ] Write runbook: Restore from backup
  - [ ] Write runbook: Dagster run failure investigation
  - [ ] Write runbook: Feed outage response
  - [ ] Write runbook: Rate limit tuning
  - [ ] Write runbook: Scaling API instances
  - [ ] Write runbook: Secret rotation

#### Observability
- [ ] **H8.7** Dashboards
  - [ ] Create Grafana/Railway dashboard: API latency (p50, p95, p99)
  - [ ] Dashboard: Error rate by endpoint
  - [ ] Dashboard: Cache hit/miss rates
  - [ ] Dashboard: Rate limit events (429 responses)
  - [ ] Dashboard: Dagster run durations and failures
  - [ ] Dashboard: Feed build times and eviction counts
  - [ ] Dashboard: Database size and growth
  - [ ] Dashboard: MinIO storage usage

- [ ] **H8.8** Alerts
  - [ ] Alert: Dagster run failure (critical path assets)
  - [ ] Alert: Feed error rate >5% over 15 min
  - [ ] Alert: Cache hit rate <40% over 30 min
  - [ ] Alert: API p95 latency >1s over 5 min
  - [ ] Alert: Database storage >80%
  - [ ] Alert: Ingestion freshness >2 hours
  - [ ] Configure alert channels (email, Slack, PagerDuty)

- [ ] **H8.9** Status page
  - [ ] Create public status page
  - [ ] Show last Dagster materialization per jurisdiction
  - [ ] Show feed cache health
  - [ ] Show ingestion freshness (time since last update)
  - [ ] Show incident history
  - [ ] Subscribe to status updates

#### Compliance & Documentation
- [ ] **H8.10** Security compliance
  - [ ] Generate SBOM for all services
  - [ ] Run Snyk or Dependabot for vulnerability scanning
  - [ ] Address critical and high CVEs
  - [ ] Rotate all secrets (DB passwords, API keys)
  - [ ] Document secret rotation schedule (quarterly)
  - [ ] Review and update egress allowlist

- [ ] **H8.11** Privacy & legal
  - [ ] Add cookie consent banner (if collecting analytics)
  - [ ] Write privacy policy (no PII, anonymous device IDs)
  - [ ] Write terms of service
  - [ ] Add data deletion endpoint (delete `anon_id` data)
  - [ ] Add robots.txt with feed crawl delay
  - [ ] Add sitemap.xml

- [ ] **H8.12** Launch readiness
  - [ ] Verify all acceptance criteria (see below)
  - [ ] Conduct launch rehearsal with rollback test
  - [ ] Prepare launch announcement (blog, social, API docs)
  - [ ] Set up user feedback channels
  - [ ] Schedule post-launch retrospective

---

## ✅ Acceptance Criteria by Surface

### ETL
- [x] Daily runs succeed for all scheduled assets
- [x] Delta runs detect and ingest changed bills/debates
- [x] Provenance recorded for all fetches
- [x] Re-runs are idempotent (no duplicates)
- [x] Data quality checks pass (no orphans, all FKs valid)

### API
- [x] All endpoints return within SLO (p95 <250ms cached, <500ms uncached)
- [x] Device ignores applied to lists, detail, graph, search
- [x] 100% schema coverage for `ca-federal`
- [x] Rate limits enforced correctly (429 with Retry-After)
- [x] GraphQL depth and complexity limits active

### Feeds
- [x] All feed endpoints exist and validate against RSS 2.0 / Atom 1.0
- [x] Cache headers present (ETag, Last-Modified, Cache-Control)
- [x] Rate limits enforced (per-IP, per-token, global)
- [x] Personalized feeds reflect device ignores
- [x] GUID stability verified (same event = same GUID)
- [x] Feed items include citations and source links

### Frontend
- [x] Mobile Lighthouse scores ≥90 (performance, accessibility)
- [x] Jurisdiction switcher works across all pages
- [x] Graph toggle (organic/hierarchical) functions correctly
- [x] Deep drills work (MP → bills → committees)
- [x] Subscribe buttons generate correct feed URLs
- [x] Settings: ignored items manager functional
- [x] Settings: personalized feed token display and regenerate

### Security
- [x] All secrets rotated within past 90 days
- [x] SBOM generated for all services
- [x] No critical or high CVEs unresolved
- [x] Input validation on all endpoints
- [x] Logs redact sensitive data (tokens, PII)

### Observability
- [x] Dashboards populated with live data
- [x] Alerts tested and routing correctly
- [x] Status page accurate and public
- [x] Runbooks documented and accessible

---

## 🚀 Development Workflow

### Local Development

1. **Start dependencies** (Postgres, Redis, MinIO)
   ```powershell
   docker-compose up -d
   ```

2. **Run migrations**
   ```powershell
   alembic upgrade head
   ```

3. **Start Dagster**
   ```powershell
   dagster dev
   ```

4. **Start API**
   ```powershell
   cd api
   uvicorn main:app --reload --port 8000
   ```

5. **Start Frontend**
   ```powershell
   cd frontend
   npm run dev
   ```

### Testing

```powershell
# Python tests
pytest tests/ -v --cov

# Frontend tests
cd frontend
npm test
npm run test:e2e

# Feed validation
python scripts/validate_feeds.py

# Load tests
locust -f tests/load/locustfile.py
```

### Deployment

```powershell
# Deploy to Railway (auto from main branch)
git push origin main

# Manual deployment
railway up

# Run migrations on Railway
railway run alembic upgrade head
```

---

## 📊 Current Metrics (Update Weekly)

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| API p95 latency | <250ms | — | 🔴 |
| Feed cache hit rate | ≥70% | — | 🔴 |
| Data freshness | <60min | — | 🔴 |
| Test coverage | ≥80% | — | 🔴 |
| Lighthouse score | ≥90 | — | 🔴 |
| Open CVEs (critical) | 0 | — | 🔴 |

---

## 🐛 Known Issues

- [ ] Issue: [Description]
  - Impact: [High/Medium/Low]
  - Workaround: [If applicable]
  - ETA: [Target resolution date]

---

## 📝 Notes

- Use this document to track progress and blockers
- Update task checkboxes as work completes
- Add new tasks under appropriate phase as scope evolves
- Link to PRs and commits for traceability
- Review and update metrics weekly

---

## 🔗 Quick Links

- **Railway Dashboard**: [URL]
- **Dagster UI**: [URL]
- **API Docs**: [URL]/docs
- **Status Page**: [URL]/status
- **Grafana**: [URL]
- **MinIO Console**: [URL]
