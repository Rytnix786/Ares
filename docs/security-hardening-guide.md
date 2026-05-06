# Security Hardening Guide

Phase 3 security hardening is enforced through application defaults, Helm security contexts, webhook signatures, and CI gates.

## Application controls

- Security headers are enabled by default with `ARES_SECURITY_HEADERS_ENABLED=true`.
- Browser origins are denied unless explicitly configured through `ARES_ALLOWED_ORIGINS`.
- API keys retain scoped DB-backed lifecycle support and env-key compatibility.
- Webhooks use timestamped HMAC signatures:
  - `x-ares-timestamp`
  - `x-ares-signature: v1=<sha256>`

Receivers should reject signatures older than five minutes and use constant-time comparison.

## Deployment controls

The Helm chart defaults to:

- non-root pods (`runAsNonRoot`, UID/GID `10001`);
- dropped Linux capabilities;
- no privilege escalation;
- read-only root filesystem where supported;
- bounded resources;
- NetworkPolicy enabled;
- externally managed Kubernetes Secret by default.

## CI controls

`.github/workflows/security.yml` runs:

- Bandit for Python static analysis;
- pip-audit for dependency vulnerabilities;
- detect-secrets for secret scanning;
- Trivy for image scanning.

## Local operator checklist

```bash
python -m pip install bandit pip-audit detect-secrets
bandit -q -r ares scripts -x tests
pip-audit --strict
detect-secrets scan --all-files --force-use-all-plugins
```

For image scans:

```bash
docker build -f Dockerfile -t ares-api:local .
trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 ares-api:local
```

## Threat model summary

| Threat | Control |
|---|---|
| Stolen API key | scopes, expiration, rotation, audit logs, auth failure metrics |
| Replay webhook | timestamped HMAC signatures |
| Browser/API exposure | explicit CORS allowlist and secure headers |
| Secret leakage | external secret strategy and detect-secrets CI |
| Vulnerable dependencies/images | pip-audit and Trivy CI |
| Over-privileged pods | non-root, no escalation, dropped capabilities, NetworkPolicy |
