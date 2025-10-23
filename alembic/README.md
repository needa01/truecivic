# Database Migrations with Alembic

This directory contains database migrations managed by [Alembic](https://alembic.sqlalchemy.org/).

## Overview

Alembic provides version control for your database schema, allowing you to:
- Track schema changes over time
- Apply or rollback migrations
- Manage schema evolution across environments (dev, staging, prod)

## Migration Commands

### Check Current Version
```bash
python -m alembic current
```

### View Migration History
```bash
python -m alembic history
```

### Apply All Pending Migrations (Upgrade to Latest)
```bash
python -m alembic upgrade head
```

### Rollback to Previous Version
```bash
python -m alembic downgrade -1
```

### Rollback to Base (Empty Database)
```bash
python -m alembic downgrade base
```

### Create a New Migration (Auto-generate from Model Changes)
```bash
python -m alembic revision --autogenerate -m "description of changes"
```

### Create a Blank Migration (Manual)
```bash
python -m alembic revision -m "description of changes"
```

## Migration Workflow

### 1. **Making Schema Changes**
   - Edit models in `src/db/models.py`
   - Run auto-generate to create a migration:
     ```bash
     python -m alembic revision --autogenerate -m "add column xyz to bills"
     ```
   - Review the generated migration in `alembic/versions/`
   - Edit if needed (Alembic may miss some changes)

### 2. **Applying Migrations**
   - **Development**: `python -m alembic upgrade head`
   - **Production**: Same command, but ensure you've tested in staging first

### 3. **Testing Migrations**
   - Always test downgrade/upgrade cycle:
     ```bash
     python -m alembic downgrade -1
     python -m alembic upgrade head
     ```
   - Verify data integrity after migration

## Database Configuration

Alembic automatically uses your project's database configuration from `src/config.py`:

- **Local (PostgreSQL + pgvector)**: Controlled via `.env.local`
- **Production (PostgreSQL)**: Uses environment variables:
  - `DB_DRIVER=postgresql+psycopg`
  - `DB_HOST`, `DB_PORT`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`

## Important Notes

### Async vs Sync Drivers

- **Application code** uses async drivers (`postgresql+asyncpg`)
- **Migrations** use the sync driver (`postgresql+psycopg`)
- The `DatabaseConfig.sync_connection_string` property handles this conversion

### Auto-generation Limitations

Alembic's auto-generate detects:

- ✅ New tables and columns
- ✅ Removed tables and columns
- ✅ Changed column types
- ✅ Added/removed indexes

But may miss:

- ⚠️ Changes to column constraints
- ⚠️ Changes to server defaults
- ⚠️ Renamed columns (appears as drop + add)

Always review generated migrations!

### Production Best Practices

1. **Never** edit an already-applied migration
2. **Always** test migrations in staging before production
3. **Backup** database before running migrations in production
4. **Review** auto-generated migrations for accuracy
5. **Test** downgrade path in case rollback is needed

## Initial Migration

The initial migration (`7bd692ce137c`) creates:

- **bills** table with 26 columns, 11 indexes, and natural key constraint
- **politicians** table with 14 columns, 6 indexes
- **fetch_logs** table with 10 columns, 5 indexes

Run `python -m alembic upgrade head` to initialize a fresh database.

## Troubleshooting

### "FAILED: Can't locate revision identified by '...'"

- Your database's migration version doesn't match available migrations
- Solution: Use `python -m alembic stamp head` to force set current version (⚠️ dangerous)

### "Target database is not up to date"

- Run `python -m alembic upgrade head` to apply pending migrations

### Auto-generate Creates No Changes

- Database schema already matches models
- Or Alembic can't connect to database (check connection string)

### SSL/TLS Certificate Error on Windows

- Install with: `pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org alembic`
