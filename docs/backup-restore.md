# Backup and Restore

This runbook covers the normal operator flow for creating and restoring an ARES backup with:

- a PostgreSQL logical dump written as `postgres.sql.gz`
- a local filesystem snapshot of the MinIO `ares-artifacts` bucket
- a manifest containing the backup timestamp, dump path, artifact path, table row counts, and SHA-256 checksum

## Prerequisites

Before running backup or restore, make sure the host has:

- `DATABASE_URL` set to a PostgreSQL database
- `AWS_ENDPOINT_URL` set to the S3-compatible MinIO endpoint
- `AWS_ACCESS_KEY_ID` set to the MinIO access key
- `AWS_SECRET_ACCESS_KEY` set to the MinIO secret key
- `AWS_REGION` set if your MinIO deployment expects a non-default region
- optional `ARES_BACKUP_BUCKET` if you need a bucket name other than `ares-artifacts`
- `pg_dump` available on `PATH`
- `psql` available on `PATH`
- `python -m alembic` working from the repository root

Current local Compose notes:

- local Compose does **not** pre-create `ares-artifacts`
- the backup script expects the bucket to exist and be readable
- the restore script can create the bucket if it does not already exist

Example environment:

```powershell
$env:DATABASE_URL="postgresql+asyncpg://ares:ares@localhost:55432/ares"
$env:AWS_ENDPOINT_URL="http://localhost:9000"
$env:AWS_ACCESS_KEY_ID="minioadmin"
$env:AWS_SECRET_ACCESS_KEY="minioadmin"
$env:AWS_REGION="us-east-1"
```

## Create a Backup

Run:

```powershell
python scripts/backup.py --output-dir backups/
```

What it does:

- creates a timestamped folder like `backups/20260507T143500Z/`
- runs `pg_dump` and compresses the output into `postgres.sql.gz`
- downloads the `ares-artifacts` bucket into `artifacts/`
- counts rows in `evaluation_runs`, `model_champions`, `drift_reports`, and `audit_logs`
- writes `manifest.json`
- prints the backup location and checksum

Example output:

```text
Backup directory: backups\20260507T143500Z
Postgres dump: backups\20260507T143500Z\postgres.sql.gz
Artifacts path: backups\20260507T143500Z\artifacts
SHA256: 4f8c6af4d2d6b9d76b4f1d0ec3efb8b9e4bb4f76d5b5af67b7260fd7d8f4ef2f
```

Example manifest:

```json
{
  "db_row_counts": {
    "audit_logs": 0,
    "champions": 1,
    "drift_reports": 2,
    "evaluation_runs": 3
  },
  "minio_sync_path": "artifacts",
  "pg_dump_path": "postgres.sql.gz",
  "sha256": "4f8c6af4d2d6b9d76b4f1d0ec3efb8b9e4bb4f76d5b5af67b7260fd7d8f4ef2f",
  "timestamp": "20260507T143500Z"
}
```

## Restore a Backup

Run from the repository root:

```powershell
python scripts/restore.py --backup-dir backups/20260507T143500Z/
```

What it does:

- loads `manifest.json`
- verifies the SHA-256 checksum for `postgres.sql.gz`
- drops and recreates the database named by `DATABASE_URL`
- restores the SQL dump with `psql`
- uploads files from the backup `artifacts/` snapshot into `ares-artifacts`
- runs `python -m alembic upgrade head`

Example output:

```text
Checksum verified: backups\20260507T143500Z\postgres.sql.gz
Database recreated and restored
Artifacts restored: backups\20260507T143500Z\artifacts
Alembic upgrade head completed
```

Warning:

- restore is destructive
- it targets the database named by `DATABASE_URL`
- use a dedicated restore target when rehearsing or validating backups

## Verify the Restore

After restore completes, verify both data and service readiness.

### 1. Spot-check table counts

```powershell
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from evaluation_runs;"
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from model_champions;"
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from drift_reports;"
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from audit_logs;"
```

Compare the counts with `manifest.json`.

### 2. Verify Alembic state

```powershell
python -m alembic current
```

Expected result:

- the database is at `head`

### 3. Verify artifacts are back in MinIO

Check through the MinIO console or a client of your choice that objects under `ares-artifacts` are present again.

### 4. Verify ARES health

If the API is running:

```powershell
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

If you have an API key and want to verify a read path:

```powershell
curl -H "X-API-Key: $env:ARES_API_KEYS" http://localhost:8000/api/v1/champions/default-model
curl -H "X-API-Key: $env:ARES_API_KEYS" http://localhost:8000/api/v1/drift/reports
```

## Scheduling Guidance

Example cron entry for a nightly backup:

```cron
0 2 * * * cd /opt/ares && /usr/bin/python scripts/backup.py --output-dir /var/backups/ares >> /var/log/ares-backup.log 2>&1
```

Recommended retention approach:

- keep each timestamped backup directory intact
- rotate by whole timestamp folder, not by individual files
- retain enough history to cover operator error, delayed corruption discovery, and audit requirements

Example retention policy:

- daily backups retained for 14 days
- weekly backups retained for 8 weeks
- monthly backups retained for 6 months
