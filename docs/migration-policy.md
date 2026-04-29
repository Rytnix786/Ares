# Migration Policy

Production code must never call `Base.metadata.create_all()`. All schema changes go through Alembic. Add columns nullable first, backfill separately, then enforce not-null constraints in a later migration.

## Rollback Procedures

For detailed rollback procedures, see [migration-rollback.md](migration-rollback.md).

## Testing

All migrations must be tested with the up/down cycle before deployment. Run:
```bash
pytest tests/integration/test_migrations.py -v -m integration