# Backup Restore Incident Runbook

## Scenario

Use this runbook when:

- the ARES PostgreSQL database is corrupted
- required records were deleted or lost
- the active database must be rebuilt from a known-good backup

This runbook assumes you already have a timestamped backup directory created by `scripts/backup.py`.

## Immediate Safety Checks

Before restoring:

1. Confirm the incident scope and record the backup directory you intend to use.
2. Confirm `DATABASE_URL` points to the intended restore target.
3. Confirm `AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`, and `AWS_SECRET_ACCESS_KEY` point to the intended MinIO deployment.
4. Confirm `pg_dump` and `psql` are available on the restore host.
5. Stop or isolate writers if possible so the restored database is not immediately modified by active traffic.

Example environment:

```powershell
$env:DATABASE_URL="postgresql+asyncpg://ares:ares@localhost:55432/ares"
$env:AWS_ENDPOINT_URL="http://localhost:9000"
$env:AWS_ACCESS_KEY_ID="minioadmin"
$env:AWS_SECRET_ACCESS_KEY="minioadmin"
$env:AWS_REGION="us-east-1"
```

## Restore Commands

Run from the repository root.

1. Identify the backup directory:

```powershell
Get-ChildItem backups
```

2. Start the restore:

```powershell
python scripts/restore.py --backup-dir backups/20260507T143500Z/
```

3. Confirm the restore messages:

```text
Checksum verified: backups\20260507T143500Z\postgres.sql.gz
Database recreated and restored
Artifacts restored: backups\20260507T143500Z\artifacts
Alembic upgrade head completed
```

## Estimated RTO

Expected restore time depends on:

- database size
- number and size of artifacts in `ares-artifacts`
- disk throughput
- local network speed to MinIO

Practical guidance:

- small local development restores are usually minutes
- larger production-like restores may take materially longer as dump size and artifact volume grow

Do not treat this as a fixed SLA without measuring your actual environment.

## Post-Restore Smoke Tests

### 1. Verify row counts

```powershell
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from evaluation_runs;"
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from model_champions;"
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from drift_reports;"
psql -h localhost -p 55432 -U ares -d ares -c "select count(*) from audit_logs;"
```

### 2. Verify Alembic state

```powershell
python -m alembic current
```

### 3. Verify champion read path

```powershell
curl -H "X-API-Key: $env:ARES_API_KEYS" http://localhost:8000/api/v1/champions/default-model
```

### 4. Verify drift report read path

```powershell
curl -H "X-API-Key: $env:ARES_API_KEYS" "http://localhost:8000/api/v1/drift/reports?limit=5"
```

### 5. Verify artifact presence

Use the MinIO console or an S3-compatible client to confirm expected objects exist again under `ares-artifacts`.

### 6. Verify service health

```powershell
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

If these checks fail:

- do not resume write traffic
- inspect the restore host logs
- inspect the chosen backup directory contents
- verify the restore target and credentials were correct
