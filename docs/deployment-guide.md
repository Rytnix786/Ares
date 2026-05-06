# Deployment Guide

This guide documents the Phase 3 deployment surface that is actually present in the repository today.
It is written for a fresh Kubernetes cluster and uses only repo-verified Helm values, templates, probe paths,
workflow behavior, Dockerfiles, and local compose commands.

The authoritative deployment assets are:

- `deploy/helm/ares/values.yaml`
- `deploy/helm/ares/templates/api.yaml`
- `deploy/helm/ares/templates/dashboard.yaml`
- `deploy/helm/ares/templates/workloads.yaml`
- `deploy/helm/ares/templates/config.yaml`
- `.github/workflows/deployment.yml`
- `.github/workflows/build-eval-image.yml`
- `docker-compose.yml`
- `docker/entrypoint.api.sh`

## Prerequisites

Make sure the operator workstation or CI runner has:

- Docker with `docker compose`
- `kubectl`
- Helm 3
- access to a Kubernetes cluster and a target namespace
- a pre-created Kubernetes Secret for ARES runtime secrets

The deployment surfaces in this repo expect the following environment values to exist somewhere in your
cluster secret or local runtime:

- `DATABASE_URL`
- `REDIS_URL`
- `ARES_API_KEYS`
- `API_KEY_HASH_SECRET`
- `ENVIRONMENT`
- `MLFLOW_TRACKING_URI`
- `OTEL_EXPORTER_OTLP_ENDPOINT`
- `ARES_ALLOWED_ORIGINS`

The chart also assumes image repositories and tags are set through Helm values:

- `image.repository`
- `image.tag`
- `dashboard.image.repository`
- `dashboard.image.tag`

## Step 1: Build and Push Docker Images

The repo has four Dockerfiles under `docker/`:

- `docker/Dockerfile.api`
- `docker/Dockerfile.dashboard`
- `docker/Dockerfile.eval`
- `docker/Dockerfile.worker`

The only committed image push workflow in the repo today is the eval-image workflow in
`.github/workflows/build-eval-image.yml`. Its exact build-and-push surface is:

```yaml
- uses: docker/build-push-action@v5
  with:
    context: .
    file: docker/Dockerfile.eval
    push: true
    tags: ghcr.io/rytnix786/ares/ares-eval:latest
```

That means the repo currently provides a verified push path for the eval image, not a full push workflow
for API, dashboard, or worker images.

For API, worker, and dashboard, the repo does provide verified local build definitions through
`docker-compose.yml`, which points to these Dockerfiles:

- API: `docker/Dockerfile.api`
- worker: `docker/Dockerfile.worker`
- dashboard: `docker/Dockerfile.dashboard`

Use the compose-defined build surface locally:

```bash
docker compose config
docker compose up -d
```

If you need cluster-ready images for the Helm chart, publish image repositories and tags that match the
chart values:

- `image.repository` and `image.tag` for API, worker, scheduler, and migration job
- `dashboard.image.repository` and `dashboard.image.tag` for the Streamlit dashboard

Current repo limitation:

- the repository does not yet ship a committed GitHub Actions workflow that pushes API, worker, or dashboard
  images the way `build-eval-image.yml` pushes the eval image

## Step 2: Helm Install

The chart lives at `deploy/helm/ares`.

The deployment gate workflow renders it with this exact repo command:

```bash
helm template ares deploy/helm/ares --set secrets.existingSecret=ares-secrets > rendered-ares.yaml
```

That same workflow validates the rendered manifests with:

```bash
kubeconform -strict -ignore-missing-schemas rendered-ares.yaml
```

For a real install, the existing Kubernetes deployment guide in this repo uses:

```bash
helm upgrade --install ares deploy/helm/ares \
  --namespace ares --create-namespace \
  --set secrets.existingSecret=ares-secrets \
  --set config.environment=production \
  --set serviceMonitor.enabled=true
```

The chart values that matter most during install are:

- `image.repository`
- `image.tag`
- `dashboard.image.repository`
- `dashboard.image.tag`
- `secrets.existingSecret`
- `config.environment`
- `config.allowedOrigins`
- `config.otelExporterOtlpEndpoint`
- `config.mlflowTrackingUri`
- `service.type`
- `serviceMonitor.enabled`
- `networkPolicy.enabled`

Example override pattern grounded in `deploy/helm/ares/values.yaml`:

```bash
helm upgrade --install ares deploy/helm/ares \
  --namespace ares --create-namespace \
  --set image.repository=ghcr.io/example/ares-api \
  --set image.tag=latest \
  --set dashboard.image.repository=ghcr.io/example/ares-dashboard \
  --set dashboard.image.tag=latest \
  --set secrets.existingSecret=ares-secrets \
  --set config.environment=production \
  --set config.mlflowTrackingUri=http://mlflow:5000 \
  --set serviceMonitor.enabled=true \
  --set networkPolicy.enabled=true
```

## Step 3: Migration Job

The migration workload is defined in `deploy/helm/ares/templates/workloads.yaml` as a Kubernetes Job with:

- `helm.sh/hook: pre-install,pre-upgrade`
- `helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded`

Its exact command is:

```yaml
command: ["alembic", "upgrade", "head"]
```

This means Helm runs the migration job automatically during install and upgrade.
There is no separate user-invoked Helm hook command committed in this repo.

After install or upgrade, verify the hook-created job:

```bash
kubectl -n ares get jobs
kubectl -n ares logs job/ares-ares-migrate
```

The API container startup path also runs migrations before launching uvicorn.
That behavior comes from `docker/entrypoint.api.sh`:

```sh
alembic upgrade head
exec uvicorn ares.api.main:app --host 0.0.0.0 --port 8000
```

## Step 4: Verify Deployment

The API deployment in `deploy/helm/ares/templates/api.yaml` exposes:

- readiness probe path `/health/ready`
- liveness probe path `/health/live`
- service port `80` targeting container port `8000`

Use these repo-aligned verification commands:

```bash
kubectl -n ares rollout status deployment/ares-ares-api
kubectl -n ares rollout status deployment/ares-ares-dashboard
kubectl -n ares get pods,svc,jobs
kubectl -n ares get deployment ares-ares-api -o yaml
kubectl -n ares get deployment ares-ares-dashboard -o yaml
```

If you want to check probe-backed health endpoints through a port-forward:

```bash
kubectl -n ares port-forward svc/ares-ares-api 8000:80
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/metrics
```

If `serviceMonitor.enabled=true`, the chart also renders a `ServiceMonitor` in
`deploy/helm/ares/templates/observability-network.yaml` that scrapes `/metrics` on the API service port.

## Step 5: Smoke Test

The repo exposes these verified API surfaces:

- `GET /health/live`
- `GET /health/ready`
- `GET /api/v1/champions/{model_name}`
- `GET /api/v1/drift/reports`
- `GET /api/v1/evaluations/`

Minimal smoke test:

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
```

Read-path smoke test with an API key:

```bash
curl -H "X-API-Key: dev-key-1" http://127.0.0.1:8000/api/v1/evaluations/
curl -H "X-API-Key: dev-key-1" http://127.0.0.1:8000/api/v1/champions/default-model
curl -H "X-API-Key: dev-key-1" http://127.0.0.1:8000/api/v1/drift/reports
```

Use an admin-scoped key if you also need to verify audit or managed API-key endpoints.

## Rollback Procedure

Helm rollback is the chart-level rollback surface for this repo.

Inspect history:

```bash
helm history ares -n ares
```

Rollback to a previous revision:

```bash
helm rollback ares <REVISION> -n ares
```

After rollback, re-run the same verification steps:

```bash
kubectl -n ares rollout status deployment/ares-ares-api
curl http://127.0.0.1:8000/health/ready
curl http://127.0.0.1:8000/metrics
```

## Docker Compose Alternative for Local Deploy

For local deployment, the verified repo path is still `docker-compose.yml`.

The local quickstart already uses:

```bash
docker compose up -d
python -m alembic upgrade head
python scripts/seed_champion.py
```

Compose starts:

- Postgres
- Redis
- MinIO
- MinIO init container
- MLflow
- API
- worker
- dashboard

Use it when:

- you need a local functional stack
- you want to rehearse API and dashboard behavior without a cluster
- you are validating probe paths, env wiring, or Helm-equivalent runtime assumptions

Do not treat Compose as production deployment.
The production-grade cluster surface in this repo is the Helm chart under `deploy/helm/ares`.
