# Operator Guide

Operators deploy, configure, monitor, and recover ARES.

## Deploy

- Local: Docker Compose.
- Production reference: `deploy/helm/ares`.
- Validate: `helm template`, `kubeconform`, `/health/ready`, `/metrics`.

## Operate

- Monitor Grafana dashboard from `deploy/observability/grafana-dashboard.json`.
- Load Prometheus rules from `deploy/observability/prometheus-rules.yaml`.
- Follow `docs/runbooks/operator-incident-response.md` for incidents.

## Secure

- Use scoped API keys with TTL and rotation.
- Use external secret management for Kubernetes.
- Run security gates from `.github/workflows/security.yml`.
