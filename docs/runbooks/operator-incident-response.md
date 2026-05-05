# Operator Incident Response Runbook

This runbook covers the Phase 1 production-critical ARES incidents. Do not paste secrets into tickets, chat, logs, or screenshots.

## Common first steps

1. Identify request/run/job IDs from API response headers, dashboard, or logs.
2. Check health:
   ```bash
   curl -H "X-API-Key: $ARES_API_KEY" $ARES_API_ORIGIN/health/ready
   curl -H "X-API-Key: $ARES_API_KEY" $ARES_API_ORIGIN/api/v1/drift/jobs
   ```
3. Check recent alerts:
   ```bash
   curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/alerts/events?status=open"
   ```
4. Check audit evidence:
   ```bash
   curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/audit/events?limit=50"
   ```

## Drift alert

Detection: an open `drift_threshold_breach` alert exists or a drift report has `is_alerting=true`.

Immediate actions:

1. Acknowledge the alert:
   ```bash
   curl -X PATCH -H "X-API-Key: $ARES_API_KEY" -H "Content-Type: application/json" \
     -d '{"status":"acknowledged","actor":"oncall"}' \
     "$ARES_API_ORIGIN/api/v1/alerts/events/$ALERT_ID"
   ```
2. Inspect the related drift run and report.
3. Compare live prediction source schema to the documented prediction contract: `timestamp`, `model_name`, and either `confidence` or `prediction`.
4. If the current champion is unsafe, follow the bad promotion rollback procedure.

Resolution:

1. Fix source data or roll back the champion.
2. Re-run the drift job:
   ```bash
   curl -X POST -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/drift/jobs/$JOB_ID/run"
   ```
3. Resolve the alert only after the report is no longer alerting.

## Bad promotion

Detection: performance regression, drift after promotion, incident report, or failed smoke verification.

Immediate actions:

1. Preview rollback:
   ```bash
   python scripts/rollback.py --model-name default-model --reason "incident INC-123" --dry-run
   ```
2. Execute rollback:
   ```bash
   python scripts/rollback.py --model-name default-model --reason "incident INC-123"
   ```
3. Verify active champion:
   ```bash
   curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/champions/default-model"
   ```
4. Verify audit and rollback history:
   ```bash
   curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/champions/default-model/history"
   curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/audit/events?resource_type=champion"
   ```

Rules:

- Rollback requires `admin` scope.
- Rollback target must exist, match the model, and have passed the gate.
- Always record an incident ID or clear reason.

## API key compromise

Immediate actions:

1. Revoke the key:
   ```bash
   python scripts/manage_api_keys.py revoke $KEY_ID --revoked-by oncall --reason "compromise INC-123"
   ```
2. Rotate dependent services to a new key:
   ```bash
   python scripts/manage_api_keys.py create --name service-name --scopes read,write --ttl-days 30
   ```
3. Review audit events for the key/user.

## API outage

1. Check `/health/live`, `/health/ready`, `/health/pool`.
2. Check DB/Redis/container status in Compose or Kubernetes.
3. If DB is unavailable, stop mutation traffic and preserve logs.
4. After recovery, run `python scripts/verify_repo.py` or targeted health checks before declaring resolved.

## DB outage

1. Freeze promotions, rollbacks, key changes, and drift writes.
2. Verify DB connectivity and migrations.
3. Restore from backup only after validating the backup artifact and getting operator approval.
4. Re-run health and audit checks after restore.

## Redis/worker outage

1. API read paths may continue, but async jobs and scheduler execution may stall.
2. Check worker logs and queue depth.
3. Re-run missed drift jobs after recovery.

## MLflow/object store outage

1. Evaluation may complete with degraded artifact logging depending on configuration.
2. Check evaluation records for `mlflow_status` and artifact URI.
3. Do not promote if required evidence artifacts are missing for the target environment.

## Post-incident checklist

- Alert acknowledged and resolved.
- Root cause documented.
- Audit events preserved.
- Rollback/promotion state verified.
- Follow-up tests/docs/tasks created.
