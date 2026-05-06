# Secrets Guide

This guide documents the secrets and environment variable surface that is actually referenced by:

- `docker-compose.yml`
- `deploy/helm/ares/values.yaml`
- `deploy/helm/ares/templates/config.yaml`
- `deploy/helm/ares/templates/api.yaml`
- `deploy/helm/ares/templates/dashboard.yaml`
- `deploy/helm/ares/templates/workloads.yaml`
- `ares/api/auth.py`
- `.github/workflows/security.yml`
- `scripts/manage_api_keys.py`

It is intentionally non-vendor-locked.
The repo defaults to a standard Kubernetes Secret plus Helm values, but the same env surface can be injected
through External Secrets, Sealed Secrets, SOPS, Vault, cloud secret managers, or another platform-native system.

## Secret Injection Strategy in the Current Helm Chart

The current chart does not inject individual keys with `secretKeyRef`.
It injects a whole Secret with `envFrom.secretRef`.

The exact template pattern in `deploy/helm/ares/templates/api.yaml` is:

```yaml
envFrom:
  - configMapRef: {name: {{ include "ares.fullname" . }}-config}
  - secretRef: {name: {{ include "ares.secretName" . }}}
```

The same `envFrom.secretRef` pattern appears in:

- `deploy/helm/ares/templates/api.yaml`
- `deploy/helm/ares/templates/dashboard.yaml`
- `deploy/helm/ares/templates/workloads.yaml`

The exact secret name helper is:

```yaml
{{- define "ares.secretName" -}}{{ .Values.secrets.existingSecret }}{{- end -}}
```

Operational consequence:

- the chart expects one existing Secret whose name is supplied by `secrets.existingSecret`
- that Secret must contain the keys the workloads need at runtime
- if you prefer per-key `secretKeyRef`, that is a future chart refinement, not the current repo behavior

## Environment Variables Used by the Current Deployment Surface

The table below lists the env vars that are directly referenced by the current compose, Helm, and auth surfaces.

| Variable | Source | Used by | Required for | Notes |
|---|---|---|---|---|
| `POSTGRES_USER` | `docker-compose.yml` | `db` | local Postgres container | compose only |
| `POSTGRES_PASSWORD` | `docker-compose.yml` | `db` | local Postgres container | compose only |
| `POSTGRES_DB` | `docker-compose.yml` | `db` | local Postgres container | compose only |
| `MINIO_ROOT_USER` | `docker-compose.yml` | `minio` | local MinIO container | compose only |
| `MINIO_ROOT_PASSWORD` | `docker-compose.yml` | `minio` | local MinIO container | compose only |
| `DATABASE_URL` | `docker-compose.yml`, Helm Secret | API, worker, dashboard, migration job | required runtime secret | also required by auth and DB-backed key paths |
| `REDIS_URL` | `docker-compose.yml`, Helm Secret | API, worker, dashboard | required runtime secret for Redis-enabled flows | Secret in chart |
| `MLFLOW_TRACKING_URI` | `docker-compose.yml`, `values.yaml` ConfigMap | API, worker, dashboard | MLflow integration | ConfigMap value in chart |
| `AWS_ACCESS_KEY_ID` | `docker-compose.yml` | `mlflow` locally; also used by backup and MinIO flows elsewhere in repo | object-store credentials when applicable | not templated in Helm chart today |
| `AWS_SECRET_ACCESS_KEY` | `docker-compose.yml` | `mlflow` locally; also used by backup and MinIO flows elsewhere in repo | object-store credentials when applicable | not templated in Helm chart today |
| `AWS_ENDPOINT_URL` | `docker-compose.yml` | API, worker, dashboard, `mlflow` | MinIO or S3-compatible endpoint | compose surface is explicit |
| `ARES_API_URL` | `docker-compose.yml` | API, worker, dashboard | internal service URL wiring | compose surface only |
| `ARES_DASHBOARD_URL` | `docker-compose.yml` | API, worker, dashboard | dashboard URL wiring | compose surface only |
| `ENVIRONMENT` | `values.yaml`, `config.yaml` | API runtime config | environment mode | ConfigMap value in chart |
| `ARES_ALLOWED_ORIGINS` | `values.yaml`, `config.yaml` | CORS middleware in `ares/api/main.py` | optional browser allowlist | empty by default |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `values.yaml`, `config.yaml` | telemetry setup | optional OTEL export | ConfigMap value in chart |
| `ARES_API_KEYS` | Helm Secret, `ares/api/auth.py` | env-backed auth keys | required outside development unless DB keys are enough and fallback is available | secret |
| `API_KEY_HASH_SECRET` | Helm Secret, `ares/api/auth.py` | DB-backed API key hashing | required for DB-backed key lifecycle | secret |

Auth-specific interpretation from `ares/api/auth.py`:

- if `ARES_API_KEYS` is empty and `ENVIRONMENT` is `development`, the API falls back to a synthetic development principal
- if `ARES_API_KEYS` is empty outside development, auth returns `503 API keys are not configured`
- `API_KEY_HASH_SECRET` is used by `hash_api_key()` to derive the DB lookup hash for managed keys

## Kubernetes Secret Creation

The current repo already shows the baseline secret creation pattern in `docs/kubernetes-deployment.md`:

```bash
kubectl create secret generic ares-secrets \
  --from-literal=DATABASE_URL='postgresql+asyncpg://...' \
  --from-literal=REDIS_URL='redis://...' \
  --from-literal=ARES_API_KEYS='admin-key' \
  --from-literal=API_KEY_HASH_SECRET='long-random-secret'
```

The chart expects that secret name here:

```bash
helm upgrade --install ares deploy/helm/ares \
  --namespace ares --create-namespace \
  --set secrets.existingSecret=ares-secrets \
  --set config.environment=production
```

If you use an external secret system, keep the same key names so the workloads can still resolve them through
the current `envFrom.secretRef` templates.

## Never-Commit Rules

The repo already protects common local secret files in `.gitignore`:

- `.env`
- `docker-compose.override.yml`
- `.venv/`
- `.gstack/`
- generated reports under `reports/`

Minimum operator rules:

1. Never commit `.env`.
2. Never commit rendered Kubernetes Secret manifests.
3. Never commit copied production credentials into docs, screenshots, notebooks, or JSON fixtures.
4. Never commit API keys printed by `scripts/manage_api_keys.py`.
5. Never store cluster secrets in PR descriptions or issue comments.

Recommended repo-aligned additions when working locally:

- keep per-developer overrides in `docker-compose.override.yml`
- keep cluster-specific values files outside the repo root or in an ignored path
- use platform secret managers instead of long-lived plaintext files

## Key Rotation Procedure

The DB-backed key lifecycle surface is implemented in `scripts/manage_api_keys.py`.
The exact subcommands currently present are:

- `create`
- `list`
- `revoke`
- `rotate`

Create a new managed key:

```bash
python scripts/manage_api_keys.py create --name production-admin --scopes read,write
```

List keys:

```bash
python scripts/manage_api_keys.py list
```

Rotate an existing key:

```bash
python scripts/manage_api_keys.py rotate <KEY_ID> --grace-days 0
```

Revoke a key:

```bash
python scripts/manage_api_keys.py revoke <KEY_ID> --reason "rotation complete"
```

What rotation does in the current repo:

- generates or accepts a new raw key
- hashes it with `API_KEY_HASH_SECRET`
- preserves DB lifecycle metadata
- records `rotated_from_key_id` and `rotated_to_key_id`
- supports a `--grace-days` overlap window

Operational rotation sequence:

1. Create or rotate a replacement key.
2. Update the client or automation that uses the old key.
3. Confirm requests succeed with the new key.
4. Revoke the old key if no grace period is required.
5. Review audit and auth-failure signals after rotation.

## Env-Key vs Managed DB-Key

There are two live auth paths in the repo today:

- env-backed keys from `ARES_API_KEYS`
- DB-backed managed keys that are looked up by hashed key prefix

Use env-backed keys when:

- bootstrapping a fresh environment
- operating in a small local or staging environment
- you need a simple fallback path before DB-managed keys are provisioned

Use DB-backed keys when:

- you need expiry, last-used tracking, rotation, revocation, and usage counts
- you want admin lifecycle operations through the CLI or admin API endpoints

## CI Secret Scanning

The secret-scanning command in `.github/workflows/security.yml` is:

```bash
detect-secrets scan --all-files --force-use-all-plugins --exclude-files '(^\.git/|^reports/|^docs/screenshots/)' > reports-detect-secrets.json
```

The same workflow also installs the scanner with:

```bash
python -m pip install bandit pip-audit detect-secrets
```

This CI gate does not replace local discipline.
Run the same command locally before shipping docs, config changes, values files, or scripts that might
accidentally include credentials.

## Accepted Current Limitations

The current chart secret model is intentionally simple, but it has limits:

- it uses `envFrom.secretRef` rather than per-key mapping
- it assumes `DATABASE_URL`, `REDIS_URL`, `ARES_API_KEYS`, and `API_KEY_HASH_SECRET` are all present in one Secret
- it does not yet template object-store credentials such as `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`
- it relies on operator discipline and CI scanning rather than a full repo-enforced secret management framework

Document these limits clearly in deployment reviews instead of hiding them behind generic "best practice" language.
