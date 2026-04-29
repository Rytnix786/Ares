# Database Migration Rollback Procedures

This document describes the procedures for rolling back Alembic migrations in Ares.

## Prerequisites

- Alembic installed and configured
- Database connection configured in `ares.config.py`
- Backup of database before running migrations (recommended)

## Rollback Procedure

### 1. Check Current Migration Version

```bash
alembic current
```

This shows the current revision hash.

### 2. View Migration History

```bash
alembic history
```

This shows all migrations with their revision hashes and order.

### 3. Rollback to Previous Version

To rollback to the previous migration:

```bash
alembic downgrade -1
```

To rollback to a specific revision:

```bash
alembic downgrade <revision_hash>
```

To rollback to the base (no migrations applied):

```bash
alembic downgrade base
```

### 4. Verify Rollback

After rollback, verify the database schema:

```bash
alembic current
```

Check that the current revision matches the expected version.

### 5. Re-apply Migrations (if needed)

To re-apply migrations after rollback:

```bash
alembic upgrade head
```

## Specific Migration Rollbacks

### Adding a New Table

When rolling back a migration that adds a table:

1. **Rollback**: `alembic downgrade -1`
2. **Verify**: Table should be dropped
3. **Data loss**: All data in the table is lost on rollback

### Adding Columns to Existing Table

When rolling back a migration that adds columns:

1. **Rollback**: `alembic downgrade -1`
2. **Verify**: Columns should be removed
3. **Data loss**: Data in the columns is lost on rollback

### Changing Column Type

When rolling back a migration that changes column types:

1. **Rollback**: `alembic downgrade -1`
2. **Verify**: Column type should revert
3. **Data loss**: Possible data truncation or loss if new type was more restrictive

### Adding Indexes

When rolling back a migration that adds indexes:

1. **Rollback**: `alembic downgrade -1`
2. **Verify**: Indexes should be dropped
3. **Data loss**: No data loss, but query performance may degrade

## Best Practices

1. **Always backup before migration**: Create a database backup before running any migration
2. **Test rollback in staging**: Test rollback procedures in staging before production
3. **Use transactions**: Migrations should be wrapped in transactions for atomicity
4. **Document breaking changes**: Document any migrations that cannot be safely rolled back
5. **Monitor for errors**: Watch for errors during rollback and handle appropriately

## Emergency Rollback

If a migration fails and leaves the database in an inconsistent state:

1. **Check current state**: `alembic current`
2. **Force stamp**: If needed, force stamp the version to match reality:
   ```bash
   alembic stamp <revision_hash>
   ```
3. **Manual intervention**: Manually fix the schema if automatic rollback fails
4. **Restore from backup**: If all else fails, restore from the pre-migration backup

## Testing Rollbacks

Before deploying to production, test rollback in development:

```bash
# Apply migration
alembic upgrade +1

# Verify migration worked
alembic current

# Rollback
alembic downgrade -1

# Verify rollback worked
alembic current

# Re-apply to ensure forward migration still works
alembic upgrade +1
```

## Current Migrations

As of the current version, the following migrations exist:

1. `initial` - Initial schema with evaluation_runs and model_champions tables
2. `add_mlflow_status` - Added mlflow_status, mlflow_error, artifact_uri to evaluation_runs

## Future Migrations

When adding new migrations, ensure:

- Downgrade method is implemented
- Downgrade is tested
- Any data loss is documented
- Rollback procedure is updated if needed
