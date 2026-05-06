# Kubernetes Deployment Guide

ARES ships a production reference Helm chart in `deploy/helm/ares`.

## Render locally

```bash
helm template ares deploy/helm/ares \
  --set image.repository=ghcr.io/your-org/ares-api \
  --set image.tag=v1.0.0 \
  --set dashboard.image.repository=ghcr.io/your-org/ares-dashboard \
  --set dashboard.image.tag=v1.0.0
```

## Secrets strategy

Use an externally managed Kubernetes Secret by default:

```bash
kubectl create secret generic ares-secrets \
  --from-literal=DATABASE_URL='postgresql+asyncpg://...' \
  --from-literal=REDIS_URL='redis://...' \
  --from-literal=ARES_API_KEYS='admin-key' \
  --from-literal=API_KEY_HASH_SECRET='long-random-secret'
```

For production, prefer External Secrets, Sealed Secrets, SOPS, or the platform secret manager. Do not commit rendered secrets.

## Install

```bash
helm upgrade --install ares deploy/helm/ares \
  --namespace ares --create-namespace \
  --set secrets.existingSecret=ares-secrets \
  --set config.environment=production \
  --set serviceMonitor.enabled=true
```

## Workloads

The chart renders:

- API Deployment and Service with `/health/live`, `/health/ready`, and `/metrics` probes.
- Dashboard Deployment and Service.
- Worker Deployment.
- Drift scheduler Deployment.
- Alembic migration Job as a Helm pre-install/pre-upgrade hook.
- Optional ServiceMonitor and default NetworkPolicy.

## Validation

1. `helm template ares deploy/helm/ares` renders without errors.
2. Apply to a staging namespace.
3. Verify `kubectl rollout status deployment/ares-ares-api`.
4. Check `/health/ready` and `/metrics` through port-forward or ingress.
5. Run a rollback drill using the champion rollback API/CLI before production promotion.
