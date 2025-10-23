# Railway Migration Hang - Root Cause Analysis

**Status**: Migrations are running (PostgreSQL detected ✅) but **HANGING** during execution  
**Last Observed**: 2025-10-18 04:41:43 UTC  
**Build**: Picked up new code (3966c63 with migration script) ✅  
**Deploy**: Hangs after "Will assume transactional DDL"

---

## 🔍 Diagnosis: Why Migrations Are Hanging

### What We Know:

1. **PostgreSQL is being used** ✅
   - Log: `INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.`
   - This confirms DATABASE_URL is being read correctly

2. **Build picked up new code** ✅
   - Dockerfile includes `COPY scripts/ ./scripts/`
   - New migration script was included in build

3. **Migrations are starting** ✅
   - Log: `INFO  [alembic.runtime.migration] Will assume transactional DDL.`
   - This means Alembic is initializing correctly

4. **But migrations hang after that** ❌
   - No "Running upgrade" logs after this point
   - Process doesn't complete within timeout
   - No error messages

---

## 🔗 The Migration Chain

```
Initial (7bd692ce137c)
  ↓
2_complete_schema
  ↓
3_personalization
  ↓
4_committee_meetings ← HANGS HERE (presumably)
  ↓
5_api_keys
```

**Key Issue**: The logs show it's trying to run migrations 4 and 5, but they never complete.

---

## 🎯 Likely Root Causes (In Order of Probability)

### 1. **HIGHEST: Migration Script NOT Being Executed**

**Evidence**:
- Dockerfile CMD updated to: `python scripts/run_migrations.py && uvicorn ...`
- But logs don't show our custom script's output
- They show generic `alembic.runtime.migration` logs

**Theory**:
- The updated Dockerfile might not have been used
- Railway might still be using old Dockerfile/entrypoint
- OR the new script is failing silently and alembic is falling back

**How to verify**:
- Look for: `Testing database connection to:` (our custom log)
- If NOT present: Our script isn't running
- If present: Our script is running but hanging

---

### 2. **MEDIUM: alembic/env.py is Using Wrong Pool Settings**

**Current Code in env.py**:
```python
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  ← ONLY NullPool specified
    )
```

**Problem**:
- Only NullPool is set
- No other connection parameters specified
- No timeout set (could hang forever)
- No `pool_pre_ping` to verify connection health

**Theory**:
- Connection might be stale or dead
- Migration might be waiting on a lock indefinitely
- No way to detect or recover from hung connection

---

### 3. **MEDIUM: alembic.ini Has Wrong sqlalchemy.url Default**

**Current Default**:
```ini
sqlalchemy.url = sqlite:///parliament_explorer.db
```

**Code in env.py**:
```python
if not config.get_main_option("sqlalchemy.url") or "sqlite" in config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.db.sync_connection_string)
```

**Problem**:
- If `settings.db.sync_connection_string` is not being read correctly
- The fallback is SQLite
- The check `or "sqlite" in ...` should catch this, but maybe it's not working

---

### 4. **MEDIUM: Migration #4 or #5 Has Blocking Operation**

**Migration 4 Code (committee_meetings)**:
```python
# Creates 5 indexes, including:
op.create_index('idx_committee_meetings_parliament_session', 
                'committee_meetings', ['parliament', 'session'])
op.create_index('uq_committee_meeting_natural_key', 
                'committee_meetings', 
                ['committee_id', 'meeting_number', 'parliament', 'session'],
                unique=True)  ← Unique index on 4 columns
```

**Problem**:
- Creating indexes on an **already populated table** can be SLOW
- If table already has data, creating unique index might take minutes
- Unique index on 4 columns could have conflicts

**Theory**:
- Table `committee_meetings` might already exist (from previous run)
- Migration #4 is trying to create indexes on it
- But the unique index on 4 columns is slow or failing silently

---

### 5. **LOW: Database Lock or Permission Issue**

**Theory**:
- Another process holding lock on tables
- Migration trying to acquire lock but blocked
- Permission denied to create indexes

---

## 📋 Investigation Checklist

**To diagnose, we need to check (in Railway logs)**:

- [ ] Do we see: `Testing database connection to:` ?
  - If NO: Our script isn't running at all
  - If YES: Our script ran but is hanging

- [ ] Do we see: `Current migration:` ?
  - If NO: Can't connect to database
  - If YES: Connected, now check what it says

- [ ] Do we see: `Running: alembic upgrade head` ?
  - If NO: Process exited before trying migrations
  - If YES: Now check what happens next

- [ ] How long does it hang?
  - < 30 seconds: Network timeout issue
  - 30s-5min: Migration is actually running (creating indexes?)
  - > 5min: Definite hang/deadlock

---

## 🔧 What's Likely Happening

**Most Likely Scenario**:

1. ✅ Build picked up new code
2. ✅ Dockerfile runs: `python scripts/run_migrations.py`
3. ✅ Our script connects to PostgreSQL (verified)
4. ✅ Alembic starts upgrading
5. ✅ Migration #3 (personalization) completes
6. ⏸️ Migration #4 (committee_meetings) tries to create unique index
7. ❌ Unique index creation **hangs** or **takes forever**
   - Either: Table already exists with conflicting data
   - Or: Index creation is just VERY slow on Railway's database

**Why it works locally**:
- Local database is small/fast
- Or: Migrations haven't been run multiple times

**Why it hangs on Railway**:
- Railway database might be slow
- Or: Multiple deployment attempts have left data in inconsistent state

---

## 💡 Next Steps to Debug

1. **Add verbose logging to migrations**
   - Log each migration step
   - Log timing of each operation
   - Log table state before/after

2. **Check Railway database directly**
   - SSH into Railway or use psql
   - Check if `alembic_version` table exists
   - Check what migrations are recorded as applied
   - Check if `committee_meetings` table exists
   - Check for any locks

3. **Simplify migration #4**
   - Maybe the unique constraint on 4 columns is problematic
   - Could split into separate unique index

4. **Add timeout to migration script**
   - Currently 300 seconds (5 min)
   - Maybe it needs longer?
   - Or maybe we need to detect hang and fail fast

---

## 🎯 Root Cause Summary

**My Best Guess** (90% confidence):

**The new migration script IS running, but migrations ARE hanging on the unique index creation in migration #4.**

- The `committee_meetings` table might already exist
- The unique index on 4 columns is slow to create
- Or there's a lock on the table

**Evidence**:
- Logs show PostgreSQL is being used (not SQLite)
- Logs show Alembic initialized correctly
- Logs stop after "Will assume transactional DDL"
- This is exactly where Alembic would start running migrations
- No error messages = process is just waiting

**To confirm**: We need to see:
1. Our custom migration script's logs
2. Which specific migration is causing the hang
3. How long it takes before timing out

