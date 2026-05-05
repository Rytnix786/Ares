# Phase 1 Operations Guide

Phase 1 adds the production-critical control-plane workflows required before ARES can be operated outside a demo environment.

## Drift scheduler and ingestion

Production predictions can be ingested through two supported paths:

1. API push:
   ```bash
   curl -X POST -H "X-API-Key: $ARES_API_KEY" -H "Content-Type: application/json" \
     -d '{"model_name":"default-model","records":[{"timestamp":"2026-05-05T00:00:00Z","model_name":"default-model","confidence":0.91}]}' \
     "$ARES_API_ORIGIN/api/v1/drift/predictions"
   ```
2. Configured source jobs:
   ```bash
   curl -X POST -H "X-API-Key: $ARES_API_KEY" -H "Content-Type: application/json" \
     -d '{"model_name":"default-model","job_name":"hourly","source_type":"local_file","source_config":{"path":"data/sample_predictions"},"reference_config":{"path":"data/golden_set/val.csv"},"thresholds":{"features":["confidence"],"psi":0.2,"kl_divergence":0.1,"interval_minutes":60}}' \
     "$ARES_API_ORIGIN/api/v1/drift/jobs"
   curl -X POST -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/drift/jobs/$JOB_ID/run"
   ```

Prediction records must include `timestamp`, `model_name`, and either `confidence` or `prediction`. Job source types currently supported are `local_file` and `object_prefix`/`object_store`.

## Alerts

Drift threshold breaches create `alert_events` records. Operators can list, acknowledge, and resolve alerts:

```bash
curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/alerts/events?status=open"
curl -X PATCH -H "X-API-Key: $ARES_API_KEY" -H "Content-Type: application/json" \
  -d '{"status":"acknowledged","actor":"oncall"}' \
  "$ARES_API_ORIGIN/api/v1/alerts/events/$ALERT_ID"
```

## Champion rollback

Rollback is a first-class governed action, not a re-promotion workaround:

```bash
python scripts/rollback.py --model-name default-model --reason "incident INC-123" --dry-run
python scripts/rollback.py --model-name default-model --reason "incident INC-123"
```

The API endpoint is `POST /api/v1/champions/{model_name}/rollback` and requires admin scope.

## API key lifecycle

Admin API-key operations are available under `/api/v1/admin/api-keys` and through `scripts/manage_api_keys.py`.

```bash
python scripts/manage_api_keys.py create --name ci --scopes read,write --ttl-days 30
python scripts/manage_api_keys.py rotate $KEY_ID --grace-days 1 --ttl-days 30
python scripts/manage_api_keys.py revoke $KEY_ID --revoked-by oncall --reason "compromise INC-123"
```

The raw key is returned only at create/rotate time. Store it in a secret manager immediately.

## Audit logs

Mutation requests are audit logged with request ID, user, endpoint, method, payload hash, status, resource metadata where available, and error information. Query and retention endpoints require admin scope:

```bash
curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/audit/events?limit=100"
curl -X DELETE -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/audit/events/retention?retention_days=365"
```

## Error payloads

ARES domain errors now return machine-readable code, category, remediation, retryability, request ID, and details. Operators should include `request_id` and `error_code` in incident reports.
