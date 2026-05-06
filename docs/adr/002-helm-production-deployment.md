# ARES Helm Deployment ADR

## Status
Accepted for the Phase 3 production reference deployment.

## Decision
ARES ships a Helm chart under `deploy/helm/ares` as the production Kubernetes reference. Docker Compose remains the local development stack.

## Rationale
Helm gives operators repeatable rendering, environment-specific values, Kubernetes-native health probes, and a single place to wire API, worker, scheduler, dashboard, migrations, secrets, resources, and observability hooks.

## Consequences
- Secrets are referenced from Kubernetes Secrets by default. The chart can create demo secrets only when explicitly enabled.
- API, worker, scheduler, and dashboard use non-root security contexts and bounded resources.
- The migration Job is a deploy-time hook and can be disabled for externally managed migrations.
- Prometheus ServiceMonitor support is optional so the chart works without the Prometheus Operator.
