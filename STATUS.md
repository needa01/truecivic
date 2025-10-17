# Parliament Explorer - Project Status

**Last Updated**: January 17, 2025  
**Phase**: Discovery & Setup  
**Status**: 🟢 On Track - Phase 0 Complete

---

## 📍 Current State

### ✅ Phase 0 Complete - Discovery & Data Source Mapping

1. **P0.1: OpenParliament API Exploration** ✅
   - Explored all endpoints (bills, MPs, votes, debates, committees)
   - Mapped schemas and identified 10 entity types
   - Confirmed 90% data coverage
   - Documented gaps: subject tags, committee details, royal assent

2. **P0.2: Official Source Comparison** ✅
   - Explored LEGISinfo (parl.ca/legisinfo)
   - Explored Parliament.ca Committee pages
   - Analyzed Hansard structure (covered by OpenParliament)
   - Created source comparison matrix
   - **Document**: `exploration/P0.2_SOURCE_COMPARISON.md`

3. **P0.3: Adapter Strategy Defined** ✅
   - Designed `BaseAdapter` protocol with unified `AdapterResponse[T]`
   - Defined rate limiting strategy (token bucket)
   - Defined error handling and retry logic
   - Planned merge strategy for enrichment
   - **Document**: `exploration/P0.3_ADAPTER_STRATEGY.md`

4. **Documentation Created**
   - `README.md` - Project overview and quickstart
   - `RUNNING.md` - Full task breakdown (8 phases, 80+ tasks)
   - `TASKLIST.md` - Focused current tasks (updated with P0.2/P0.3 completion)
   - `exploration/FINDINGS.md` - OpenParliament API analysis
   - `exploration/P0.2_SOURCE_COMPARISON.md` - Multi-source comparison
   - `exploration/P0.3_ADAPTER_STRATEGY.md` - Adapter architecture
   - `exploration/README.md` - Exploration guide
   - `requirements.txt` - Initial dependencies

---

## 📊 Data Source Analysis Summary

### OpenParliament API Coverage

| Entity | Coverage | Notes |
|--------|----------|-------|
| **Bills** | 90% | Missing: subject tags, committee details |
| **MPs** | 95% | Complete profiles with history |
| **Votes** | 100% | Full voting records + individual ballots |
| **Debates** | 85% | Hansard available, need detail exploration |
| **Committees** | 50% | Names only, need meeting/evidence data |

### What We'll Scrape from LEGISinfo
- Bill subject tags and classification
- Bill-committee relationships
- Royal assent tracking
- Detailed bill timeline

---

## 🎯 Next Steps (Priority Order)

### 1. Design Phase (Next 1-2 Days)

**Database Schema Design**
- [ ] Design `bill` table based on OpenParliament + enrichment needs
- [ ] Design `mp`, `party`, `riding` tables
- [ ] Design `vote` and `vote_record` tables
- [ ] Design `debate` and `speech` tables
- [ ] Design `committee` and `committee_meeting` tables
- [ ] Design `document` and `embedding` tables
- [ ] Design `provenance` tracking table
- [ ] Add jurisdiction fields to all tables
- [ ] Create initial Alembic migration

**Adapter Interface**
- [ ] Define base `Adapter` abstract class
- [ ] Define `AdapterResponse` data model
- [ ] Define `EntityType` enum
- [ ] Design error handling and retry strategy
- [ ] Design rate limiting approach
- [ ] Design caching strategy

### 2. Foundation Phase (Next 3-5 Days)

**Local Development Environment**
- [ ] Create `docker-compose.yml` (Postgres, Redis, MinIO)
- [ ] Test local service startup
- [ ] Initialize database with migrations
- [ ] Create MinIO buckets
- [ ] Test end-to-end connectivity

**OpenParliament Adapter**
- [ ] Implement `OpenParliamentClient` with retry/backoff
- [ ] Implement bill adapter with pagination
- [ ] Implement MP adapter
- [ ] Implement vote adapter
- [ ] Implement debate adapter
- [ ] Implement committee adapter
- [ ] Add comprehensive tests with fixtures from exploration
- [ ] Add rate limiting (conservative: 60 req/min)

### 3. ETL Foundation (Next Week)

**Basic Dagster Setup**
- [ ] Initialize Dagster project
- [ ] Create jurisdiction-parameterized assets
- [ ] Implement bill fetch asset
- [ ] Implement normalization asset
- [ ] Implement upsert logic
- [ ] Test end-to-end flow: fetch → normalize → upsert
- [ ] Add provenance tracking

---

## 🗂️ Project Structure

```
truecivic/
├── .env.example              ✅ Template for environment variables
├── .env.local                ✅ Local development config
├── .env.production           ✅ Production config template
├── .gitignore                ✅ Comprehensive ignore rules
├── README.md                 ✅ Project overview
├── RUNNING.md                ✅ Full task breakdown
├── TASKLIST.md               ✅ Current focused tasks
├── requirements.txt          ✅ Python dependencies
│
├── exploration/              ✅ API testing (gitignored)
│   ├── README.md             ✅ Exploration guide
│   ├── FINDINGS.md           ✅ API analysis summary
│   ├── 00_quick_api_test.py  ✅ Quick API test
│   ├── 01_openparliament_api_explorer.py  ✅ Full API explorer
│   ├── 02_data_structure_analysis.py      ✅ Schema analyzer
│   └── outputs/              ✅ Sample API responses
│
├── api/                      📁 FastAPI service (TODO)
├── dagster/                  📁 Orchestration (TODO)
├── frontend/                 📁 Next.js app (TODO)
├── adapters/                 📁 Data source adapters (TODO)
├── models/                   📁 Shared data models (TODO)
├── tests/                    📁 Test suites (TODO)
└── docs/
    └── adr/                  📁 Architecture decisions (TODO)
```

---

## 💡 Key Insights from Exploration

### API Characteristics
- **Response Time**: ~320ms average
- **Format**: Requires `?format=json` parameter
- **Pagination**: Standard `limit`/`offset`
- **Search**: Full-text search via `?q=` parameter
- **No Auth**: Public read-only access
- **Rate Limits**: Undocumented (need testing under load)

### Data Quality
- ✅ High quality structured data
- ✅ Bilingual support (EN/FR)
- ✅ Historical tracking (MP tenure, past bills)
- ✅ Rich relationships (bills→votes, MPs→speeches)
- ⚠️  Some fields sparse (committee meetings, bill topics)

### Design Implications
1. **Natural Keys**: Use source IDs (`legisinfo_id`, session+number)
2. **Bilingual Storage**: Store EN/FR in separate columns
3. **Historical Data**: Support start/end dates for memberships
4. **Nullable Fields**: Design for optional enrichment data
5. **Provenance**: Track source and fetch timestamp for all data

---

## 🚀 Development Workflow

### Running Exploration Scripts

```powershell
# Quick API test
python exploration/00_quick_api_test.py

# Full exploration
python exploration/01_openparliament_api_explorer.py

# Analyze responses
python exploration/02_data_structure_analysis.py

# View findings
cat exploration/FINDINGS.md
```

### Next Commands (After Setup)

```powershell
# Start local services
docker-compose up -d

# Run migrations
alembic upgrade head

# Test adapter
pytest tests/adapters/test_openparliament.py

# Run Dagster
dagster dev
```

---

## 📈 Progress Tracking

### Phase 0: Discovery ✅ COMPLETE (Oct 17)
- [x] API exploration
- [x] Schema analysis
- [x] Data source decision
- [x] Project scaffolding

### Phase 1: Design (Oct 18-19)
- [ ] Database schema
- [ ] Adapter interface
- [ ] Initial migrations

### Phase 2: Foundation (Oct 20-24)
- [ ] Local dev environment
- [ ] OpenParliament adapter
- [ ] Basic ETL pipeline

### Phase 3: Core Features (Oct 25 - Nov 7)
- [ ] Full ETL with Dagster
- [ ] LEGISinfo enrichment
- [ ] API service
- [ ] Frontend basics

---

## 🎓 Lessons Learned

1. **Always explore APIs first** - Saved weeks of scraping work
2. **Test with real requests** - Documentation was sparse but API is functional
3. **Structure matters** - Good project structure makes phases clearer
4. **Gitignore exploration** - Allows messy testing without polluting repo

---

## 📞 Quick Links

- **OpenParliament API**: https://api.openparliament.ca/
- **LEGISinfo**: https://www.parl.ca/legisinfo
- **Exploration Outputs**: `exploration/outputs/`
- **Main Tasks**: `RUNNING.md`
- **Focused Tasks**: `TASKLIST.md`

---

## 🔔 Blockers & Risks

### Current Blockers
None - all initial exploration complete.

### Known Risks
1. **Rate Limits**: OpenParliament limits are undocumented
   - **Mitigation**: Conservative limits (60/min), monitoring
   
2. **API Changes**: No versioning visible
   - **Mitigation**: Cache raw responses, version adapters
   
3. **Data Freshness**: Update frequency unknown
   - **Mitigation**: Track timestamps, poll frequently

---

**Status**: Ready to move to design phase. All initial questions answered.
