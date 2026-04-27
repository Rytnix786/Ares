# Migration Policy

Production code must never call `Base.metadata.create_all()`. All schema changes go through Alembic. Add columns nullable first, backfill separately, then enforce not-null constraints in a later migration.