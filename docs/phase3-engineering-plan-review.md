# Phase 3 Engineering Plan Review

This review follows the intent of `gstack-main/plan-eng-review/SKILL.md`: lock architecture, data flow, edge cases, tests, and performance before more deployment code.

## Scope locked from `Production_grade_final_plan.md`

Phase 3 completion covers:

1. Kubernetes/Helm production reference with API, worker, scheduler, dashboard, migration job, services, ingress, secrets, ConfigMaps, HPA/PDB, probes, security contexts, ServiceMonitor, validation, and docs.
2. Prometheus/Grafana assets with low-cardinality business and platform metrics, alert rules, dashboard JSON, lint/parse tests, and operator guide.
3. Security hardening with secure headers/CORS, key lifecycle continuity, webhook signature hardening, dependency/secret/image scan CI gates, least-privilege deployment defaults, threat model, and docs.
4. Load/performance testing with reproducible scenarios, SLO budgets, seed assumptions, CI/staging gate, and baseline report.
5. Supportability with runbook alignment, deployment validation checklist, rollback drill guidance, and local evidence.

## Architecture decisions

- Keep Docker Compose as local/dev, Helm as production reference.
- Keep app runtime code minimal: only add security/config/metrics code that Helm, alerts, or tests need.
- Prefer static deploy/observability artifacts plus tests over adding runtime dependencies.
- Security scans are CI workflows and docs, not mandatory local verifier dependencies, so contributors without Docker/Trivy can still run `scripts/verify_repo.py`.
- `/land-and-deploy` and `/canary` are not executed without a staging cluster/URL. Provide scripts/checklists that operators can run in staging.

## Deployment data flow

```mermaid
flowchart LR
  User[Operator / CI] --> Helm[helm upgrade --install]
  Helm --> Migrate[Alembic migration Job]
  Helm --> API[ARES API Deployment]
  Helm --> Worker[Celery Worker]
  Helm --> Scheduler[Drift Scheduler]
  Helm --> Dashboard[Streamlit Dashboard]
  API --> DB[(Postgres)]
  Worker --> Redis[(Redis)]
  Scheduler --> API
  API --> Metrics[/metrics]
  Metrics --> Prometheus[Prometheus Rules]
  Prometheus --> Grafana[Grafana Dashboard]
```

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Chart renders invalid Kubernetes | Add schema-like values tests plus `helm template` docs/CI gate. |
| Alerts reference missing metrics | Add metrics definitions/tests and align rule names. |
| Security scans block contributors locally | Put scans in CI workflow and document optional local commands. |
| Helm demo secrets accidentally used in prod | Default `createDemoSecret=false`, document external secret managers. |
| Load tests run against production | Docs and scripts require explicit base URL/API key and call out isolated staging. |
| Canary/deploy claims are fake | Do not claim deployment. Provide runbook/checklist and validate local assets only. |

## Required validation

- Full `python scripts/verify_repo.py` must pass.
- New tests must parse Helm/observability/security/load assets.
- Security headers and CORS parsing must be tested.
- CI workflows must be YAML-parseable.
- Documentation must name exact files and commands.

## Implementation order

1. Finish Helm templates: ingress, HPA, PDB, optional service account, NetworkPolicy refinement, values schema/readme.
2. Finish observability: metric catalog, rule/dashboard alignment, docs and tests.
3. Finish security: webhook HMAC config/tests/docs and CI scan workflow.
4. Finish load/performance: k6 scenario, Python smoke validator, baseline docs, CI workflow.
5. Finish supportability: runbook/deployment checklist links.
6. Run full verifier and commit locally.
