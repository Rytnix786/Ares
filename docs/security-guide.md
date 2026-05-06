# Security Guide

This guide documents the security controls that are actually visible in the current repository.
It covers auth, API key lifecycle, audit logging, CI scanners, Kubernetes hardening defaults, and known risks.

Primary sources for this guide:

- `ares/api/auth.py`
- `ares/models/api_key.py`
- `ares/api/routers/api_keys.py`
- `scripts/manage_api_keys.py`
- `ares/api/middleware/audit.py`
- `ares/api/routers/audit.py`
- `.github/workflows/security.yml`
- `deploy/helm/ares/values.yaml`
- `deploy/helm/ares/templates/api.yaml`
- `deploy/helm/ares/templates/dashboard.yaml`
- `deploy/helm/ares/templates/workloads.yaml`
- `ares/api/main.py`

## Threat Model Summary

The repository's current security model is built around these assumptions:

- API access is key-based, not anonymous
- write and admin operations must be scope-gated
- auditability matters for mutations
- dependency, secret, and image scanning should run in CI
- Kubernetes workloads should run with least privilege by default

The most relevant threats in the current codebase are:

- stolen or reused API keys
- over-privileged operational keys
- missing or weak audit trails for mutations
- secret leakage through config or committed files
- vulnerable Python or container dependencies
- excessive Kubernetes runtime privileges

## Authentication Model

The auth entrypoint is `require_api_key()` in `ares/api/auth.py`.

There are two active key sources:

1. DB-backed managed keys
2. environment-backed keys from `ARES_API_KEYS`

### DB-backed key path

When `X-API-Key` is provided, the auth layer first tries the DB-backed lifecycle path:

- hash the presented key with `hash_api_key()`
- query `get_active_api_key_by_hash(...)`
- if found, record usage with `record_api_key_usage(...)`
- bind an `APIKeyPrincipal` with `source="db"`

The hash function uses:

- HMAC-SHA256
- secret key material from `API_KEY_HASH_SECRET`
- truncation to `settings.API_KEY_HASH_PREFIX_LENGTH`

### Env-key path

If the DB-backed path does not authenticate the key, auth falls back to `ARES_API_KEYS`.

Important behaviors:

- in `development`, if no `ARES_API_KEYS` are configured, the API creates a synthetic development principal
- outside development, missing `ARES_API_KEYS` produces `503 API keys are not configured`
- invalid keys produce `401 Invalid API key`

### Constant-time comparison

The env-key path uses `hmac.compare_digest(...)` for constant-time comparison.

That matters because:

- it avoids naive string-equality timing differences
- it is the only constant-time key comparison in the env-backed path

### Scope enforcement

Scope checks are implemented with `require_scope(scope)`.

`APIKeyPrincipal.has_scope(...)` grants access when:

- the explicit scope is present
- or the key has the `admin` scope

Insufficient scope returns `403` with:

- error code `INSUFFICIENT_SCOPE`
- the required scope
- the provided scopes

Auth failures also increment the metric `ares_auth_failures_total` with reasons such as:

- `not_configured`
- `invalid_key`
- `insufficient_scope`

## API Key Lifecycle

The lifecycle model is stored in `ares/models/api_key.py`.

Tracked fields include:

- `id`
- `key_hash`
- `name`
- `scopes`
- `rate_limit`
- `is_active`
- `created_at`
- `revoked_at`
- `expires_at`
- `last_used_at`
- `use_count`
- `revoked_by`
- `revocation_reason`
- `rotated_from_key_id`
- `rotated_to_key_id`
- `rotation_grace_expires_at`
- `updated_at`

### Create

The CLI surface in `scripts/manage_api_keys.py` provides:

```bash
python scripts/manage_api_keys.py create --name production-admin --scopes read,write
```

The admin API also provides:

- `POST /api/v1/admin/api-keys`

Create semantics in the current repo:

- raw key can be user-provided or generated
- hash is derived with `hash_api_key(...)`
- TTL defaults to `settings.API_KEY_DEFAULT_TTL_DAYS`
- TTL must be between `1` and `settings.API_KEY_MAX_TTL_DAYS`

### Rotate

The CLI surface is:

```bash
python scripts/manage_api_keys.py rotate <KEY_ID> --grace-days 0
```

The admin API surface is:

- `POST /api/v1/admin/api-keys/{key_id}/rotate`

Rotation semantics in the current repo:

- a new raw key is created or accepted
- the replacement key can override name, scopes, rate limit, and expiry
- the relationship between old and new keys is stored
- an overlap window can be expressed through `rotation_grace_expires_at`

### Revoke

The CLI surface is:

```bash
python scripts/manage_api_keys.py revoke <KEY_ID> --reason "rotation complete"
```

The admin API surface is:

- `POST /api/v1/admin/api-keys/{key_id}/revoke`

Revocation semantics in the current repo:

- `is_active` can be turned off
- revocation actor and reason are stored
- revoked keys should no longer authenticate

### Expiry and usage tracking

The model tracks:

- `expires_at`
- `last_used_at`
- `use_count`

That gives the repo a real basis for:

- expiring stale keys
- detecting dormant keys
- reviewing operational key usage

## Audit Trail

Mutation auditing is implemented in `ares/api/middleware/audit.py`.

### What gets logged

Only mutation methods are audited automatically:

- `POST`
- `PUT`
- `DELETE`
- `PATCH`

Captured fields include:

- `request_id`
- `user`
- `endpoint`
- `method`
- `payload_hash`
- `result`
- `status_code`
- `audit_metadata`
- `api_key_id`
- `actor_type`
- `resource_type`
- `resource_id`
- `action`
- `correlation_id`
- `error_code`
- `duration_ms`

The middleware hashes payloads rather than storing the raw body as the primary audit payload.

### Success and failure behavior

On success:

- the request is processed
- a success audit row is written

On exception:

- the request error is re-raised
- an error audit row is attempted with error metadata

If the audit write itself fails:

- the metric `ares_audit_write_failures_total` is incremented
- a warning event `audit_log_write_failed` is emitted

### Who can query audit data

The audit API router is mounted at:

- `GET /api/v1/audit/events`
- `DELETE /api/v1/audit/events/retention`

Both endpoints require:

- `require_scope("admin")`

That means audit inspection and retention purges are admin-only in the current repo.

### Retention

Retention is an operator-controlled API action today, not a background policy engine.

The repo exposes:

```bash
curl -X DELETE -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/audit/events/retention?retention_days=365"
```

Current limitation:

- retention is driven by explicit operator calls
- there is no scheduler in the repo that enforces audit retention automatically

## Security CI Gates

The security workflow is `.github/workflows/security.yml`.

### Bandit

Install command:

```bash
python -m pip install bandit pip-audit detect-secrets
```

Scan command:

```bash
bandit -q -r ares scripts -x tests
```

What it checks:

- common Python security anti-patterns
- unsafe subprocess, weak cryptography, insecure defaults, and similar static findings

### pip-audit

Command:

```bash
pip-audit --strict
```

What it checks:

- known dependency vulnerabilities in the Python environment

### detect-secrets

Command:

```bash
detect-secrets scan --all-files --force-use-all-plugins --exclude-files '(^\.git/|^reports/|^docs/screenshots/)' > reports-detect-secrets.json
```

What it checks:

- likely committed credentials, tokens, and other secret-looking strings

### Trivy

The workflow's current image-scan step is:

```bash
docker build -f Dockerfile -t ares-api:ci .
```

followed by:

```yaml
uses: aquasecurity/trivy-action@0.24.0
with:
  image-ref: ares-api:ci
  severity: HIGH,CRITICAL
  ignore-unfixed: true
  exit-code: "1"
```

What it checks:

- HIGH and CRITICAL vulnerabilities in the built container image

Current repo limitation:

- the workflow command references `Dockerfile` at repo root, while the repo's Dockerfiles currently live under `docker/`
- this should be treated as a deployment-doc and CI-consistency issue until reconciled in code

## Kubernetes Security Contexts

The Helm defaults in `deploy/helm/ares/values.yaml` are:

### Pod security context

- `runAsNonRoot: true`
- `runAsUser: 10001`
- `fsGroup: 10001`

### Container security context

- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true`
- `capabilities.drop: ["ALL"]`

These values are applied to:

- API deployment
- dashboard deployment
- worker deployment
- scheduler deployment

The migration job does not currently render the same explicit container security context block in
`deploy/helm/ares/templates/workloads.yaml`.
That is a real chart limitation and should be documented as such.

## Related Runtime Security Controls

Other current controls visible in the repo:

- CORS is only enabled when `ARES_ALLOWED_ORIGINS` is configured
- security headers are added by `security_headers_middleware` when `ARES_SECURITY_HEADERS_ENABLED` is true
- every request gets an `X-Request-ID`
- Prometheus tracks auth and audit failure signals

The current default security headers include:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`

## Known Limitations and Accepted Risks

The repo has meaningful controls, but it is not a finished security platform.
These are the main verified gaps:

- env-key compatibility remains active, which is useful operationally but less governed than DB-managed keys
- the chart uses `envFrom.secretRef` rather than narrower per-key secret mapping
- object-store credentials are not templated into the current Helm chart
- audit retention is manual, not automated
- the migration job does not currently show the same explicit hardened container security context as the long-running deployments
- the Trivy build command in `security.yml` does not match the repo's `docker/` directory layout
- alerting on auth and audit problems exists, but no dedicated security incident automation exists in the repo

Treat these as accepted current risks, not hidden implementation details.
Document them during deployment reviews and use them to scope future hardening work.
