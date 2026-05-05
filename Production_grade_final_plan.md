# Production Grade Final Plan

## 1. Executive Goal

Product complete for ARES means the repository becomes a dependable model promotion control plane: it can evaluate candidate models against governed golden sets, compare them to active champions, make explainable gate decisions, persist every decision, monitor production drift on a schedule, trigger alerting, support rollback, expose operator workflows through the API and dashboard, and provide enough client tooling and documentation for another team to adopt it without reading the source first.

Production grade means ARES can be deployed and operated safely outside a demo environment. The project must have durable database migrations, reversible champion state, production data ingestion for drift checks, scoped and rotating API keys, persistent audit logs, explicit incident runbooks, Prometheus/Grafana-ready observability, backup and restore validation, load-tested API and worker paths, Kubernetes or Helm deployment artifacts, and CI/CD gates that prove these properties on every change.

Top 0.01% quality means the system feels like an industry reference implementation:

- Architecture: clear boundaries between evaluators, gates, persistence, API, dashboard, workers, data contracts, deployment, and observability.
- Code: small modules, typed interfaces, no hidden side effects, no dead scaffolding, no fake production claims, and no duplicated gate or evaluator logic.
- Testing: unit, integration, e2e, contract, property, mutation, security, performance, migration, drift, rollback, plugin, and dashboard coverage for critical behavior.
- Documentation: runbooks, ADRs, API docs, deployment guides, tuning guides, troubleshooting guides, role-specific contributor guides, and evidence-backed release criteria.
- UX: Streamlit dashboard remains an operator tool, but becomes dense, reliable, polished, stateful, accessible, and visually consistent.
- Observability: metrics, logs, traces, alerts, dashboards, SLOs, and incident workflows are implemented together, not described separately.
- Security: no hardcoded secrets, scoped API keys with expiration and rotation, audit trails, dependency scanning, image scanning, secure headers, rate-limit analytics, and least-privilege deployment.
- Scalability: evaluation jobs, drift jobs, API reads, dashboard queries, artifacts, and database access have explicit limits, pagination, queues, indexes, and load-test evidence.

## 2. Current State Summary

The current checkout already has a substantial foundation. Verified evidence includes:

- Core Python package under `ares/` with FastAPI, SQLAlchemy/Alembic, evaluators, metrics, gate rules, database CRUD, cache wrapper, feature flags, notifiers, observability hooks, and Celery task scaffold.
- API routes for health, evaluations, champions, gate config/simulation, and drift reports in `ares/api/routers/`.
- Versioned application routes under `/api/v1`, plus `/health/live`, `/health/ready`, `/health`, `/health/pool`, and `/metrics`.
- DB models for evaluation runs, model champions, drift reports, API keys, webhooks, and audit logs.
- Alembic migrations through `120cb49ea4a3_add_audit_logs_table.py`, with migration tests present.
- Evaluation CLI in `scripts/run_evaluation.py` that validates golden-set data, evaluates models, applies gate decisions, persists runs, writes JSON output, and optionally logs MLflow artifacts.
- Golden-set validation in `ares/golden_set.py` and DVC wiring in `dvc.yaml`.
- Gate decision logic in `ares/gate/rules_engine.py` and narrative generation in `ares/gate/decision.py`.
- Evaluator surfaces for classification, regression, and detection under `ares/evaluators/`.
- Drift metric functions for KL divergence and PSI under `ares/metrics/drift.py`.
- A production data source interface in `ares/drift_sources.py`, currently backed only by `LocalFileDataSource`.
- API-key authentication with env-backed keys, DB-backed hashed keys, scopes, constant-time env-key comparison, and rate limiting.
- Audit middleware and `AuditLog` model for mutation logging.
- Prometheus counters/gauges/histograms in `ares/observability/metrics.py` and optional OpenTelemetry setup in `ares/observability/telemetry.py`.
- Docker Compose stack with Postgres, Redis, MinIO, MLflow, API, worker, and Streamlit dashboard.
- Dockerfiles for API, worker, eval image, and dashboard.
- GitHub Actions workflows: `quality.yml`, `regression_gate.yml`, `drift_monitor.yml`, and `build-eval-image.yml`.
- Streamlit dashboard pages for leaderboard, drill-down, drift monitor, model comparison, promotion workflow, and alerts.
- Test tree with 41 Python test files and 212 collected tests from `python -m pytest --collect-only -q -o addopts=`.
- Existing coverage artifact `reports/coverage.xml`, with root line-rate `0.89` and package line-rate `0.9135`; current full test pass was not re-run for this plan.
- Graphify artifacts under `graphify-out/`, including `graphify-out/core/GRAPH_REPORT.md`, `graphify-out/core/graph.json`, and `graphify-out/core/graph.html`.
- Graphify core report identified central hubs: `ClassificationEvaluator`, `BaseEvaluator`, `RegressionEvaluator`, `export()`, `compare_with_champion()`, `ChampionResponse`, `evaluate()`, `Base`, `LocalFileDataSource`, and `DriftReportResponse`.
- Documentation exists for README, contributing, security, migration policy, migration rollback, backup/restore, screenshots, agent workflow, Streamlit ADR, completion reports, and prior implementation plans.

Existing strengths:

- The repository has a real product shape, not just a scaffold.
- The gate, evaluator, API, persistence, dashboard, Docker, CI, and docs layers are already connected.
- The test suite now covers many critical paths, including auth, API, migrations, evaluator behavior, gate decisions, drift metrics, and dashboard importability.
- The project already enforces Ruff, Mypy, Pytest coverage, Docker Compose config validation, DVC dry-run, and compile checks through `scripts/verify_repo.py`.
- The README accurately describes many current surfaces and command paths.

Important current weaknesses:

- Production drift automation is workflow/sample-file oriented, not a true production ingestion and scheduling system.
- `scripts/backup.py` and `scripts/restore.py` are metadata-manifest placeholders, not real backup/restore orchestration.
- Rollback exists as `scripts/rollback.py` and champion history APIs, but lacks a first-class rollback record, approval policy, validation workflow, and post-rollback verification.
- The Celery worker currently returns a queued payload and does not execute the real evaluation workflow.
- API key lifecycle lacks expiration, rotation endpoints, last-used tracking, and explicit revocation audit UX.
- Observability has baseline metrics and optional tracing, but lacks alert rules, Grafana dashboards, business metric completeness, log redaction policy, and trace coverage.
- Kubernetes/Helm deployment artifacts are absent.
- Dashboard has useful pages but still needs production polish, consistent information architecture, real screenshots, operator flows, and stronger state handling.
- Documentation is uneven: some docs are thin, stale, or have formatting artifacts; migration rollback docs list only older migrations.
- Graphify command is not on PATH, but the local Graphify package under `skills/graphify-5` works when run with `PYTHONPATH`.

## 3. Missing Systems and Features

| Category | Missing Item | Why It Matters | Risk If Ignored | Priority | Difficulty | Dependencies | Definition of Done |
|---|---|---|---|---|---|---|---|
| Core product features | Automated production drift scheduler | Drift checks must run without GitHub Actions or manual scripts | Drift regressions are discovered late or never | P0 | Medium | Production data source, drift report DB, alerts | Configurable scheduler runs drift jobs, persists reports, emits alerts, and has tests |
| Core product features | Production data ingestion interface beyond local CSV | Real monitoring needs prediction streams or warehouse/object-store inputs | Drift monitor remains demo-only | P0 | High | Data contracts, credentials, validation | Pluggable sources for file, object store, warehouse, and API push with schema validation |
| Core product features | Champion rollback/version control workflow | Operators need safe recovery after bad promotion | Bad champion remains active or rollback is unaudited | P0 | Medium | Champion history, audit logs, API auth | Rollback API/CLI/dashboard flow records reason, actor, target, validation, and audit entry |
| Backend/API | API client library | CI, notebooks, and production systems need stable integration | Users copy curl/httpx snippets and drift from API contracts | P1 | Medium | OpenAPI schemas, auth model | Typed Python client package with tests and examples |
| Backend/API | Pagination and filtering on list endpoints | Evaluation and drift history will grow | Dashboard/API become slow and memory-heavy | P1 | Medium | DB indexes, schemas | Cursor or offset pagination, filters, tests, docs |
| Backend/API | Production error taxonomy with remediation | Errors exist but status mapping/remediation is incomplete | Operators see generic failures and cannot act quickly | P0 | Medium | Exceptions, API schemas, CLI payloads | All user-facing errors include code, category, status, remediation, request ID |
| Backend/API | Async evaluation API and job status | Long evaluations should not block API requests | API timeouts and poor scaling | P1 | High | Real Celery workflow, persistence | Submit/status/result/cancel endpoints backed by worker execution |
| Dashboard/frontend | Dashboard production polish | Operators need scannable, reliable workflows | Tool feels unfinished and slows incident response | P1 | Medium | Stable API/data models | Polished layout, filters, comparison UX, rollback UX, alert UX, loading/error states, screenshots |
| Dashboard/frontend | Operator flows for rollback, drift triage, key management | Production tasks need safe UI support | CLI-only operations are error-prone | P1 | Medium | APIs for rollback, drift, keys | UI flows with confirmations, audit context, and tests |
| Data/model evaluation | Evaluator plugin system | Teams need custom model types without editing core code | Core becomes cluttered with model-specific code | P1 | High | BaseEvaluator, packaging policy | Entry-point plugin registry, manifests, sandbox checks, plugin tests |
| Data/model evaluation | Multi-model comparison | Promotion often compares several candidates | Engineers run repeated manual comparisons | P1 | Medium | Evaluation persistence, gate engine | API/CLI/dashboard compare N candidates with winner/risk summary |
| Data/model evaluation | Model card generation | Governance needs standardized model evidence | Promotion evidence remains fragmented | P1 | Medium | Evaluation result, champion history, artifacts | Markdown/JSON model card generated from run, gate, drift, dataset, and lineage |
| Drift monitoring | Slice-specific drift and performance trending | Overall metrics can hide subgroup failure | Critical segment degradation is missed | P1 | High | Slice metrics schema, trend tables | Time-series slice tables, trend APIs, dashboard charts, alert thresholds |
| Drift monitoring | Alert delivery beyond workflow artifact | Operators need notification when thresholds breach | Alerts stay inside reports/dashboard | P0 | Medium | Notifiers, webhooks, scheduler | Slack/webhook/GitHub alert rules with dedupe and tests |
| Champion management | Promotion approval policy | Production promotion should be gated by role/criteria | Unauthorized or accidental promotions | P1 | Medium | Auth scopes, audit logs | Configurable approval modes and scoped mutation checks |
| Plugin/extensibility | Pluggable gate decision engine | Gate rules will vary by organization/model class | Core rules become rigid or over-complicated | P2 | High | GateDecision interface, config schema | Gate engine registry with built-in default and tested custom rule plugins |
| Security | API key expiration/rotation | Current keys can be created/revoked but not expired/rotated fully | Long-lived credentials and weak auditability | P0 | Medium | ApiKey model, auth dependency, CLI | `expires_at`, `last_used_at`, rotation CLI/API, audit logs, tests |
| Security | Security headers/CORS/deployment hardening | Public hosting needs defensive defaults | Misconfiguration and browser/API exposure | P1 | Medium | FastAPI middleware, config | Security headers, strict CORS config, docs, tests |
| Security | Dependency/image/secrets scanning gates | Production release needs automated checks | Vulnerable dependencies/images reach release | P1 | Medium | CI workflows | pip-audit/Bandit/Semgrep/Trivy/gitleaks or equivalents in CI |
| Observability | Prometheus alert rules | Metrics are useful only if alerts exist | Failures require manual dashboard watching | P0 | Medium | Metrics naming, deployment | Alert rules for availability, error rate, gate failures, drift, auth, rate limits |
| Observability | Grafana dashboard | Operators need shared system view | Metrics are hard to interpret | P1 | Medium | Prometheus metrics | Provisioned dashboard JSON with API, gate, drift, worker, DB panels |
| Observability | Distributed tracing coverage | Cross-service latency needs request flow | Root-cause analysis is slower | P1 | Medium | OTEL config | API, worker, evaluator, DB, external calls traced with request/run IDs |
| Testing | Contract tests | Client/dashboard/API must stay aligned | API changes break consumers silently | P1 | Medium | OpenAPI schema, client lib | Generated schema diff and client contract tests in CI |
| Testing | Mutation/property tests | Gate and drift math need stronger invariants | Subtle logic bugs pass example tests | P2 | Medium | Hypothesis, mutmut/cosmic-ray | Property tests for metrics/gates and mutation score threshold |
| CI/CD | Release workflow | Versioned releases should be reproducible | Manual releases produce inconsistent artifacts | P1 | Medium | build-pkg, Docker image | Tagged release workflow builds package, image, SBOM, changelog |
| Deployment | Kubernetes or Helm | Docker Compose is not production deployment | Users cannot deploy cleanly to clusters | P0 | High | Secrets, migrations, probes | Helm chart or manifests for API, worker, dashboard, scheduler, jobs, services |
| Deployment | Secrets management strategy | Compose env defaults are not production secret management | Secrets leak or rotate poorly | P0 | Medium | Helm/K8s, docs | External Secrets/Sealed Secrets/SOPS strategy documented and templated |
| Documentation | Operator incident runbook | Operators need exact actions during incidents | Recovery depends on source-code reading | P0 | Medium | Alerts, rollback, backup | Runbook for drift, failed gate, bad promotion, API outage, DB/Redis failure |
| Documentation | Configuration tuning guide | Gate/drift thresholds are safety-critical | Teams tune blindly and overfit thresholds | P1 | Medium | Gate simulation, threshold simulator | Practical guide with examples, anti-patterns, and validation workflow |
| Developer experience | Contributor guides by role | Different contributors need different paths | Onboarding remains slow | P2 | Low | Existing contributing docs | Role guides for evaluator, gate, dashboard, docs, deployment contributors |
| Operator experience | Sandbox demo deployment | Reviewers need a live demo | Project looks static despite working code | P2 | Medium | Demo data, deployment | Public or local one-command sandbox with seeded data |
| Performance/scalability | Load testing | API/worker capacity is unproven | Production limits unknown | P0 | Medium | Locust/k6, seeded data | Baselines for API, evaluation, dashboard reads, DB pool, Redis |
| Open-source readiness | Real screenshots and docs polish | Current assets include placeholders | Project presentation undersells implementation quality | P1 | Low | Running demo stack | Captured screenshots, clean Markdown, updated stale docs |

## 4. Skill Usage Strategy

The active Codex environment exposes only system skills such as `imagegen`, `openai-docs`, `plugin-creator`, `skill-creator`, `skill-installer`, and GitHub plugin skills. For this repository, the more relevant skills are present as repository-local skill packs under `skills/` and should be used as planning and review guides during implementation. They are not installed as active Codex skills in this session, so implementation agents should reference their `SKILL.md` files directly or install them intentionally before use.

| Skill/Tool | Purpose | Where to Use It | Expected Output | How It Improves the Plan |
|---|---|---|---|---|
| `graphify` (`skills/graphify-5`) | Architecture/dependency graph, community hubs, path queries | Phase 0 and before cross-module changes | Updated `graphify-out/core/*`, query notes, hub/risk map | Prevents blind edits and identifies coupling around evaluators, gates, champions, and API |
| `code-review-and-quality` | Five-axis review: correctness, readability, architecture, security, performance | End of every feature slice and before merge | Findings with severity, file references, required fixes | Keeps features small, reviewable, and production-grade |
| `source-driven-development` | Evidence-first implementation discipline | Any task touching unclear or legacy areas | Evidence map from current source to planned changes | Prevents invented features and stale documentation claims |
| `api-and-interface-design` | Stable API contracts and schema design | API client, async evaluation jobs, rollback, plugin contracts | API contract notes, schema review, versioning impact | Avoids breaking clients and keeps OpenAPI usable |
| `frontend-ui-engineering` | Production UI patterns, state, layout, accessibility | Dashboard production polish and operator flows | UI review checklist, page-level acceptance findings | Makes Streamlit dashboard useful and coherent for operators |
| `ui-ux-pro-max` | High-polish dashboard UX critique | Final dashboard review and screenshot capture | Visual/UX audit with layout, hierarchy, color, density findings | Pushes the dashboard from functional to polished |
| `documentation-and-adrs` | ADRs, runbooks, public docs | Runbooks, deployment docs, API docs, ADRs | Updated docs and ADRs with context/tradeoffs | Keeps future engineers from reverse-engineering decisions |
| `security-and-hardening` | Threat modeling, auth, secrets, input validation | API keys, audit logs, webhooks, deployment, headers | Threat model, security checklist, CI security gates | Reduces credential, auth, and deployment risk |
| `test-driven-development` | Red/green/refactor and regression tests | Every behavior change | Failing tests first, then passing implementation | Prevents untested critical paths |
| `performance-optimization` | Measurement-first optimization | Load tests, dashboard scaling, API pagination, worker throughput | Baseline report and regression budgets | Ensures scaling work is evidence-based |
| `ci-cd-and-automation` | CI workflow and release gate design | GitHub Actions, release workflow, image scanning, Helm validation | Updated pipeline design and gate matrix | Makes production-readiness enforceable |
| `deprecation-and-migration` | Safe schema/API evolution | Migrations, API versions, rollout/backfill work | Migration plan with up/down/backfill/rollback | Reduces production schema risk |
| `shipping-and-launch` | Release readiness and launch checklist | Final release candidate phase | Launch checklist and go/no-go evidence | Prevents premature production claims |
| GitHub plugin skills (`github:*`) | PR, CI, issue, and review workflow support | If publishing changes or fixing remote CI | PR summary, CI log triage, review response | Useful only when GitHub-hosted workflow is in scope |
| `imagegen` | Generate bitmap visuals | Optional README/social/demo visuals only | Real visual assets, not diagrams better handled in Markdown | Not needed for code; useful for polished marketing assets |

### Skill Execution Order

1. Run Graphify first:
   - PowerShell command from repo root:
     ```powershell
     $env:PYTHONPATH='H:\Projects\Ares\skills\graphify-5'
     python -m graphify query "What modules connect evaluation, gate decisions, champions, drift, API, dashboard, and observability?" --graph graphify-out/core/graph.json --budget 3500
     ```
   - Update graph artifacts after major architecture changes with `python -m graphify update ares`.
   - Output should be an updated architecture map and a list of high-coupling modules.
2. Use `source-driven-development` to map each feature to existing files and confirm evidence before editing.
3. Use `api-and-interface-design` before changing schemas, endpoints, client contracts, async job APIs, rollback APIs, plugin interfaces, or gate engine contracts.
4. Use `deprecation-and-migration` before schema changes, especially API key lifecycle, audit logs, slice trends, scheduler runs, and rollback records.
5. Use `test-driven-development` before implementation of every behavior change.
6. Use `security-and-hardening` before finalizing API keys, auth scopes, audit logs, webhooks, secret handling, deployment, and CI security scans.
7. Use `frontend-ui-engineering` and `ui-ux-pro-max` only after backend contracts for dashboard features are stable.
8. Use `performance-optimization` once APIs and workers have realistic data flows; measure before optimizing.
9. Use `ci-cd-and-automation` to wire new checks into GitHub Actions after local tests exist.
10. Use `code-review-and-quality` after each slice and again before release.
11. Use `documentation-and-adrs` after behavior stabilizes, before release.
12. Use `shipping-and-launch` for the final production-grade release checklist.

## 5. Implementation Roadmap

### Phase 0 — Repository Re-Understanding and Planning Lock

Objective: Freeze the true baseline before implementation begins.

Tasks:

- Re-read `README.md`, `plan.md`, `ares-remaining-gaps-implementation-plan-v3-2c73ea.md`, completion reports, `docs/`, `SECURITY.md`, `CONTRIBUTING.md`, workflows, Docker files, scripts, API, dashboard, tests, and migrations.
- Run Graphify query/update on `ares/`, `dashboard/`, `scripts/`, and docs.
- Produce a current architecture map showing evaluator, gate, API, DB, dashboard, worker, drift, and observability boundaries.
- Re-run `python -m pytest --collect-only -q -o addopts=`.
- Run `python scripts/verify_repo.py` only when the environment has DVC, Docker, and dependencies ready.
- Record current test pass/coverage from a fresh run, not from stale reports.
- Convert this plan into issue-sized tasks with owners and dependencies.

Implementation order:

1. Evidence refresh.
2. Graphify refresh.
3. Test/coverage baseline.
4. Risk register.
5. Task inventory.
6. Scope lock.

Files/modules likely affected: `Production_grade_final_plan.md`, `docs/`, issue tracker; no application code.

Skills/tools to use: `graphify`, `source-driven-development`, `planning-and-task-breakdown`, `code-review-and-quality`.

Tests required: collection-only baseline and full `scripts/verify_repo.py` if local services are ready.

Documentation required: updated architecture map, risk register, dependency map.

Acceptance criteria:

- Every claimed completed feature is backed by a file path or test.
- Every missing feature has a priority, dependency, and definition of done.
- Current verification results are recorded with exact commands and dates.

Risks:

- Existing docs are partly stale.
- Existing coverage artifacts may not match current code.
- Graphify repo-wide graph includes noisy `skills/` content; prefer scoped core graph for implementation.

Completion checklist:

- [ ] Current docs inventory complete.
- [ ] Graphify map reviewed.
- [ ] Verification baseline recorded.
- [ ] Risk register created.
- [ ] Task inventory approved.

### Phase 1 — Critical Production Gaps

Objective: Make the system operable and recoverable in a real production environment.

Tasks:

- Implement automated production drift monitoring scheduler.
- Implement production data ingestion interface for drift checks.
- Implement champion rollback/version control as first-class API/CLI/dashboard workflow.
- Write operator incident response runbook.
- Complete audit logging persistence with retention, query, and failure policy.
- Add API key expiration, last-used tracking, and rotation workflow.
- Add basic alerting rules and alert delivery.
- Complete production-ready error taxonomy with remediation messages.

Implementation order:

1. Data model migrations for scheduler runs, production data sources, rollback records, API key fields, audit retention metadata, and alert events.
2. Drift ingestion interface and scheduler.
3. Error taxonomy and remediation payloads.
4. API key lifecycle.
5. Rollback workflow.
6. Alert rules and delivery.
7. Operator runbooks.
8. Verification and review.

Files/modules likely affected:

- `ares/models/`, `alembic/versions/`, `ares/db/`
- `ares/drift_sources.py`, `scripts/run_drift_check.py`, new scheduler module
- `ares/api/routers/`, `ares/api/schemas/`, `ares/api/auth.py`
- `ares/api/middleware/audit.py`, `ares/exceptions.py`
- `ares/notifier/`, `dashboard/pages/`, `dashboard/api_client.py`
- `docs/`

Skills/tools to use: `deprecation-and-migration`, `api-and-interface-design`, `security-and-hardening`, `test-driven-development`, `documentation-and-adrs`, `code-review-and-quality`.

Tests required:

- Migration up/down tests.
- Drift scheduler unit and integration tests.
- Production data source contract tests.
- Rollback API/CLI/dashboard tests.
- API key expiration/rotation tests.
- Audit persistence tests.
- Alert rule tests.
- Error taxonomy snapshot tests.

Documentation required:

- Operator incident runbook.
- API key rotation guide.
- Drift scheduler setup.
- Rollback procedure.
- Alerting guide.
- Error catalog.

Acceptance criteria:

- A production deployment can detect drift, alert, and preserve the report without GitHub Actions.
- A bad champion can be rolled back with audit evidence and validation.
- Expired/revoked keys cannot mutate or read protected resources.
- Operators have exact steps for the top failure modes.

Risks:

- Scheduler design can conflict with future Kubernetes CronJob design.
- API key changes can break current env-key compatibility.
- Rollback must not bypass gate/audit requirements.

Completion checklist:

- [ ] Drift scheduler implemented.
- [ ] Production ingestion sources implemented.
- [ ] Rollback records and workflow implemented.
- [ ] API key lifecycle implemented.
- [ ] Alert rules implemented.
- [ ] Error taxonomy implemented.
- [ ] Runbooks completed.
- [ ] Full verification passed.

### Phase 2 — Product Completeness

Objective: Complete product workflows that users expect from a serious model promotion gate.

Tasks:

- Evaluator plugin system.
- Slice-specific performance trending.
- Multi-model comparison.
- Dashboard UX improvements.
- API client library.
- Model card generation.
- Configuration tuning guide.
- Better troubleshooting docs.

Implementation order:

1. Stabilize extension interfaces.
2. Add plugin registry and contracts.
3. Add slice trend data model and APIs.
4. Add multi-model comparison and model cards.
5. Add Python API client.
6. Polish dashboard workflows against stable APIs.
7. Write tuning/troubleshooting docs.

Files/modules likely affected:

- `ares/evaluators/`, new `ares/plugins/`
- `ares/gate/`, `ares/api/schemas/`, `ares/api/routers/`
- `ares/models/`, `ares/db/`, `alembic/versions/`
- `dashboard/`
- new client package, for example `ares_client/`
- `docs/`

Skills/tools to use: `api-and-interface-design`, `frontend-ui-engineering`, `ui-ux-pro-max`, `documentation-and-adrs`, `test-driven-development`, `code-review-and-quality`.

Tests required:

- Plugin loading tests.
- Plugin isolation and failure tests.
- Slice trend integration tests.
- Multi-model comparison tests.
- Client contract tests.
- Dashboard state tests.
- Model card golden-file tests.

Documentation required:

- Evaluator plugin authoring guide.
- API client guide.
- Model card guide.
- Configuration tuning guide.
- Dashboard operator guide.

Acceptance criteria:

- A custom evaluator can be added without editing core evaluator modules.
- Operators can view trends and compare multiple candidates.
- A generated model card is attached to promotion evidence.
- Client library covers main API workflows.

Risks:

- Plugin abstraction can over-generalize too early.
- Slice trend schema can grow quickly without retention policy.
- Dashboard polish before API stability causes rework.

Completion checklist:

- [ ] Plugin system implemented.
- [ ] Slice trending implemented.
- [ ] Multi-model comparison implemented.
- [ ] Dashboard polished.
- [ ] API client published locally.
- [ ] Model card generation implemented.
- [ ] Tuning/troubleshooting docs completed.

### Phase 3 — Enterprise Production Readiness

Objective: Make ARES deployable, observable, secure, and supportable in enterprise infrastructure.

Tasks:

- Kubernetes manifests or Helm chart.
- Secrets management strategy.
- Backup/restore validation.
- SLOs and SLIs.
- Prometheus alert rules.
- Grafana dashboard.
- Distributed tracing.
- Load testing.
- Security test suite.
- Deployment guide.

Implementation order:

1. Deployment model and ADR.
2. Helm/manifests for API, worker, dashboard, scheduler, migration job, services, probes.
3. Secret strategy and templates.
4. Real backup/restore scripts and validation.
5. SLO/SLI definitions.
6. Prometheus rules and Grafana dashboard.
7. Distributed tracing instrumentation.
8. Load/security test suites.
9. Deployment docs.

Files/modules likely affected:

- new `deploy/helm/` or `deploy/kubernetes/`
- `docker/`, `.github/workflows/`
- `scripts/backup.py`, `scripts/restore.py`
- `ares/observability/`, `ares/api/`, `ares/worker/`
- `docs/`

Skills/tools to use: `ci-cd-and-automation`, `security-and-hardening`, `performance-optimization`, `documentation-and-adrs`, `shipping-and-launch`.

Tests required:

- Helm template validation.
- Kubeconform/kubeval.
- Secret reference checks.
- Backup/restore integration tests.
- k6/Locust load tests.
- Trivy/pip-audit/Bandit/Semgrep/gitleaks CI gates.

Documentation required:

- Deployment guide.
- Secrets guide.
- Backup/restore runbook.
- Observability guide.
- SLO guide.
- Security guide.

Acceptance criteria:

- A fresh cluster can deploy ARES from documented commands.
- Migrations run safely as a job.
- Alerts and dashboards work against metrics.
- Backup/restore is validated in CI or staging.
- Load and security gates are enforced.

Risks:

- Helm chart can drift from Docker Compose if not tested.
- Secrets management differs by organization; provide a reference strategy, not a hardcoded vendor lock.
- Load tests must use realistic data sizes to be meaningful.

Completion checklist:

- [ ] Helm/manifests complete.
- [ ] Secrets strategy complete.
- [ ] Backup/restore validated.
- [ ] SLOs/SLIs defined.
- [ ] Alerts and dashboards provisioned.
- [ ] Tracing complete.
- [ ] Load/security gates complete.
- [ ] Deployment docs complete.

### Phase 4 — Top 0.01% Excellence

Objective: Add advanced extensibility, scale, evidence, and contributor experience that make ARES exceptional.

Tasks:

- Pluggable gate decision engine.
- Event-driven evaluation workflow.
- Threshold simulation and optimization.
- Distributed evaluation for large datasets.
- Mutation testing.
- Contract testing.
- Property-based testing.
- Interactive architecture explorer.
- Sandbox demo deployment.
- Contributor guides by role.

Implementation order:

1. Gate engine interface and registry.
2. Event model and workflow engine.
3. Threshold simulation optimizer.
4. Distributed evaluation execution.
5. Advanced test suites.
6. Architecture explorer based on Graphify artifacts.
7. Sandbox deployment.
8. Contributor role guides.

Files/modules likely affected:

- `ares/gate/`, `ares/evaluators/`, `ares/worker/`, `ares/api/`
- `dashboard/`
- `graphify-out/` or new `docs/architecture/`
- `tests/`, `.github/workflows/`, `docs/`

Skills/tools to use: `graphify`, `api-and-interface-design`, `performance-optimization`, `test-driven-development`, `ci-cd-and-automation`, `documentation-and-adrs`, `shipping-and-launch`.

Tests required:

- Gate plugin contract tests.
- Event workflow integration tests.
- Threshold optimizer property tests.
- Distributed evaluation tests.
- Mutation and contract gates.
- Sandbox smoke checks.

Documentation required:

- Gate plugin guide.
- Event workflow docs.
- Threshold optimization guide.
- Architecture explorer guide.
- Sandbox demo docs.
- Role-specific contributor docs.

Acceptance criteria:

- Advanced features are optional, stable, and documented.
- Core default behavior remains simple.
- Contributors can extend ARES without reading unrelated modules.

Risks:

- Advanced features can bloat core abstractions.
- Distributed evaluation can make local development harder if not optional.
- Architecture explorer must be generated, not hand-maintained.

Completion checklist:

- [ ] Gate engine plugins complete.
- [ ] Event-driven workflow complete.
- [ ] Threshold optimizer complete.
- [ ] Distributed evaluation complete.
- [ ] Advanced tests wired into CI.
- [ ] Architecture explorer complete.
- [ ] Sandbox demo complete.
- [ ] Contributor guides complete.

## 6. Detailed Feature Implementation Plans

### Automated drift scheduler

- Problem: `scripts/run_drift_check.py` and `.github/workflows/drift_monitor.yml` exist, but production drift checks depend on GitHub Actions or manual script execution.
- Goal: Run drift checks inside the deployed system on a configured cadence.
- User/operator value: Operators get timely drift detection without relying on CI.
- Technical approach: Add a scheduler service using Celery Beat, APScheduler, or Kubernetes CronJob. Keep scheduler execution behind a common `DriftJobRunner` so Compose, worker, and K8s can share logic.
- Architecture impact: Adds a scheduling boundary between production data sources, drift metrics, drift report persistence, and alert delivery.
- Files/modules likely affected: `ares/drift_sources.py`, new `ares/drift/runner.py`, new `ares/scheduler/`, `ares/models/`, `ares/db/`, `scripts/run_drift_check.py`, `docker-compose.yml`, Helm/manifests.
- Data model changes: `drift_jobs`, `drift_job_runs`, optional `alert_events`.
- API changes: `GET/POST /api/v1/drift/jobs`, `GET /api/v1/drift/jobs/{id}/runs`.
- Dashboard/UI changes: Drift job status, last run, next run, failures, alert state.
- Configuration changes: cadence, lookback window, source type, thresholds, alert channels.
- Security considerations: scheduler credentials must be least privilege; source credentials must not appear in logs.
- Observability requirements: metrics for run count, duration, failures, stale jobs, alert count.
- Tests required: unit runner tests, scheduler integration tests, duplicate-run lock tests, failure and retry tests.
- Documentation required: scheduler setup and operations guide.
- Step-by-step implementation sequence:
  1. Extract drift logic from `scripts/run_drift_check.py` into reusable runner.
  2. Add job/run models and migration.
  3. Add scheduler lock to prevent duplicate runs.
  4. Add APIs and dashboard status.
  5. Add alert dispatch on threshold breach.
  6. Add Compose/K8s wiring.
  7. Add tests and docs.
- Definition of done: Scheduled drift checks run without GitHub Actions, persist results, alert on breaches, expose status, and pass tests.

### Production data ingestion interface

- Problem: `ProductionDataSource` exists, but only `LocalFileDataSource` is implemented.
- Goal: Support real production predictions from API push, object store, warehouse, or event stream.
- User/operator value: ARES can monitor deployed models, not just sample CSVs.
- Technical approach: Define source registry and typed contracts: `fetch_recent_predictions(model_name, window)` returns validated dataframe or batch object. Add implementations for local file, S3/MinIO object prefix, HTTP push endpoint, and optional SQL warehouse.
- Architecture impact: Drift monitoring becomes source-agnostic.
- Files/modules likely affected: `ares/drift_sources.py`, new `ares/drift/contracts.py`, `ares/api/routers/drift.py`, `data/schemas/`, `docs/`.
- Data model changes: `production_prediction_batches` or source references; source configuration table if managed through API.
- API changes: `POST /api/v1/drift/predictions` for push ingestion; source management endpoints if needed.
- Dashboard/UI changes: source health, last batch, schema failures.
- Configuration changes: source type, paths, credentials references, retention.
- Security considerations: validate payload size, schema, timestamps, and model names; never log raw predictions by default.
- Observability requirements: ingestion count, rejected rows, source latency, stale-source alerts.
- Tests required: schema contract tests, source adapter tests, API payload size tests, stale source tests.
- Documentation required: production prediction schema and source setup guide.
- Step-by-step implementation sequence:
  1. Formalize required drift prediction schema.
  2. Add source registry.
  3. Add source adapters.
  4. Add push ingestion endpoint.
  5. Add source validation and retention.
  6. Wire scheduler to source registry.
  7. Test and document.
- Definition of done: At least two production-ready source types work, invalid data is rejected safely, and drift scheduler consumes sources through the same interface.

### Champion rollback/version control

- Problem: Champion history and previous champion endpoint exist, and `scripts/rollback.py` promotes previous champion, but rollback is not a governed workflow.
- Goal: Make rollback auditable, safe, validated, and operator-visible.
- User/operator value: Operators can recover from bad promotions quickly and safely.
- Technical approach: Add `ChampionRollback` records, rollback API, CLI, dashboard flow, validation checks, and post-rollback smoke verification.
- Architecture impact: Champion management becomes a governed lifecycle instead of simple promotion rows.
- Files/modules likely affected: `ares/models/`, `ares/db/crud.py`, `ares/api/routers/champions.py`, `ares/api/schemas/champion.py`, `scripts/rollback.py`, `dashboard/pages/05_promotion_workflow.py`.
- Data model changes: `champion_rollbacks` with source champion, target champion, actor, reason, validation status, timestamps.
- API changes: `POST /api/v1/champions/{model_name}/rollback`, `GET /api/v1/champions/{model_name}/rollbacks`.
- Dashboard/UI changes: rollback action with confirmation, reason, impact preview, recent rollbacks.
- Configuration changes: optional require-admin-scope, require-passed-run, require-validation-before-activate.
- Security considerations: rollback requires `admin` or dedicated `champion:rollback` scope.
- Observability requirements: rollback success/failure counter, audit log, alert event.
- Tests required: rollback transaction tests, concurrent rollback tests, audit tests, CLI tests, dashboard import/state tests.
- Documentation required: rollback runbook.
- Step-by-step implementation sequence:
  1. Add rollback model and migration.
  2. Add transactional rollback CRUD with row lock.
  3. Add API and schema.
  4. Update CLI.
  5. Add dashboard workflow.
  6. Add audit/alerts/metrics.
  7. Add tests and docs.
- Definition of done: Rollback is an explicit API/CLI/dashboard operation with audit evidence and validation.

### Operator runbook

- Problem: Docs exist but incident response is thin and incomplete.
- Goal: Provide exact operational procedures for common production incidents.
- User/operator value: Operators can act without reading source code.
- Technical approach: Create `docs/runbooks/operator-incident-response.md` and link it from README and deployment docs.
- Architecture impact: None in code, but locks operator contracts.
- Files/modules likely affected: `docs/runbooks/`, `README.md`, `docs/backup-restore.md`, `docs/migration-rollback.md`.
- Data model changes: None.
- API changes: None.
- Dashboard/UI changes: Link runbook from dashboard sidebar/help.
- Configuration changes: Document required env vars and alert channels.
- Security considerations: Avoid embedding secrets; describe secure access.
- Observability requirements: Map each alert to symptoms, queries, dashboards, and actions.
- Tests required: docs link check and command smoke tests where possible.
- Documentation required: runbook itself.
- Step-by-step implementation sequence:
  1. List top incidents: drift alert, bad promotion, failed evaluation, API outage, DB outage, Redis outage, MLflow outage, key compromise.
  2. For each, define detection, severity, immediate action, diagnosis, rollback, communication, postmortem.
  3. Add command snippets verified against actual CLI/API.
  4. Link from dashboard and README.
- Definition of done: Every P0 alert has a matching runbook entry and verified command path.

### Audit log persistence

- Problem: `AuditLog` and middleware exist, but retention, querying, security, and failure semantics are incomplete.
- Goal: Make audit logs durable, queryable, and production-safe.
- User/operator value: Security and operations teams can investigate mutations.
- Technical approach: Fix schema type issues, add query APIs, retention policy, redaction, and dashboards.
- Architecture impact: Audit becomes a first-class operational data set.
- Files/modules likely affected: `ares/models/audit_log.py`, `ares/api/middleware/audit.py`, `ares/api/routers/`, `dashboard/`, `docs/`.
- Data model changes: fix `status_code` to integer, add actor key id, resource id, event type, retention metadata.
- API changes: `GET /api/v1/audit/events` with filters and pagination.
- Dashboard/UI changes: audit page or admin panel.
- Configuration changes: retention days, redacted fields, audit failure policy.
- Security considerations: audit API requires admin scope; payload hashes only, no secret payloads.
- Observability requirements: audit write failures and latency metrics.
- Tests required: mutation audit tests, redaction tests, query authorization tests, migration tests.
- Documentation required: audit logging policy.
- Step-by-step implementation sequence:
  1. Add migration for missing audit fields.
  2. Update middleware to capture principal key ID and event type.
  3. Add redaction and payload hash rules.
  4. Add admin query API.
  5. Add retention job.
  6. Add tests/docs.
- Definition of done: Mutations create secure audit events, audit data is queryable by admins, and retention is documented.

### API key expiration and rotation

- Problem: DB-backed API keys support create/list/revoke, but lack expiration and rotation workflow.
- Goal: Implement full lifecycle controls.
- User/operator value: Safer long-running production deployments.
- Technical approach: Extend `ApiKey` with `expires_at`, `last_used_at`, `rotated_from_key_id`, and metadata; update auth and CLI/API.
- Architecture impact: Auth becomes stateful and auditable.
- Files/modules likely affected: `ares/models/api_key.py`, `ares/db/crud_api_keys.py`, `ares/api/auth.py`, `scripts/manage_api_keys.py`, tests, docs.
- Data model changes: new columns and indexes.
- API changes: optional admin endpoints for create, rotate, revoke, list.
- Dashboard/UI changes: key lifecycle admin page if dashboard admin scope is in product scope.
- Configuration changes: default TTL, max TTL, warning window.
- Security considerations: never return raw key after creation; hash using configured secret; update last-used without timing leaks.
- Observability requirements: auth failures, expired key attempts, rotation count, last-used updates.
- Tests required: expired key rejection, rotation overlap, revoke, env-key compatibility, DB precedence.
- Documentation required: key rotation guide.
- Step-by-step implementation sequence:
  1. Add migration.
  2. Update model/CRUD.
  3. Update auth dependency.
  4. Update CLI.
  5. Add optional API endpoints.
  6. Add audit/metrics.
  7. Add tests/docs.
- Definition of done: Keys can be created, rotated, expired, revoked, audited, and tested without breaking env-key compatibility.

### Evaluator plugin system

- Problem: Evaluators exist but extension requires modifying the core package.
- Goal: Load custom evaluators through a stable plugin contract.
- User/operator value: Teams can add model-specific evaluation without forking ARES.
- Technical approach: Use Python entry points plus local plugin manifests. Define `EvaluatorPlugin` metadata and factory returning `BaseEvaluator`.
- Architecture impact: Evaluator extension moves from core modules to registry.
- Files/modules likely affected: `ares/evaluators/`, new `ares/plugins/`, `pyproject.toml`, docs, tests.
- Data model changes: optional `evaluator_name` and `evaluator_version` on evaluation run metadata.
- API changes: `GET /api/v1/evaluators` if needed.
- Dashboard/UI changes: display evaluator name/version on run detail.
- Configuration changes: `evaluator.plugin`, plugin allowlist, plugin config block.
- Security considerations: plugins are trusted code; document install trust boundary and optional allowlist.
- Observability requirements: plugin load failures and evaluation metrics by plugin.
- Tests required: entry-point fake plugin tests, config selection tests, plugin failure tests.
- Documentation required: plugin authoring guide.
- Step-by-step implementation sequence:
  1. Define plugin protocol.
  2. Build registry and discovery.
  3. Adapt CLI to use registry.
  4. Add sample plugin.
  5. Add tests.
  6. Document.
- Definition of done: A sample external plugin can be installed and used without editing core code.

### Slice performance trending

- Problem: Slice metrics are stored per run, but not modeled as time-series trend data.
- Goal: Track slice performance over time by model, run, metric, and slice.
- User/operator value: Operators can detect slow degradation in critical slices.
- Technical approach: Normalize slice metrics into a `slice_metric_points` table at evaluation persistence time.
- Architecture impact: Dashboard and alerts stop parsing large JSON for trend queries.
- Files/modules likely affected: `ares/models/`, `ares/db/`, `scripts/run_evaluation.py`, `ares/api/routers/`, `dashboard/pages/`.
- Data model changes: `slice_metric_points` with model, run, slice, metric, value, critical flag, timestamp.
- API changes: `GET /api/v1/slices/trends`.
- Dashboard/UI changes: trend charts, filters, critical slice cards.
- Configuration changes: retention and alert thresholds.
- Security considerations: model names and slice names should be validated and paginated.
- Observability requirements: trend write failures and query latency.
- Tests required: persistence tests, API trend tests, dashboard data shaping tests.
- Documentation required: slice monitoring guide.
- Step-by-step implementation sequence:
  1. Add model/migration.
  2. Write extraction function from `slice_metrics`.
  3. Persist points on evaluation run creation.
  4. Add trend API.
  5. Add dashboard charts.
  6. Add alerts.
  7. Test/docs.
- Definition of done: Critical slice history is queryable and visible without JSON parsing.

### Dashboard production polish

- Problem: Dashboard pages are functional but still lack final operator-grade polish.
- Goal: Make dashboard dense, predictable, useful under incidents, and visually consistent.
- User/operator value: Operators can triage quickly.
- Technical approach: Stabilize page IA, shared components, filters, loading/error states, and action confirmations.
- Architecture impact: Dashboard remains Streamlit per ADR but gains stronger component discipline.
- Files/modules likely affected: `dashboard/app.py`, `dashboard/pages/`, `dashboard/components/`, `dashboard/api_client.py`, `docs/screenshots.md`.
- Data model changes: none directly.
- API changes: depends on stable backend endpoints for rollback, trends, audit, keys.
- Dashboard/UI changes: page-level redesign, filters, details drawers/expanders, status chips, trend charts, rollback confirmation, alert triage.
- Configuration changes: dashboard refresh defaults and API settings.
- Security considerations: never expose API key value after entry; protect admin-only actions.
- Observability requirements: dashboard API call failures and latency logs if feasible.
- Tests required: Streamlit import tests, page smoke tests, API client tests, screenshot checklist.
- Documentation required: dashboard operator guide and real screenshots.
- Step-by-step implementation sequence:
  1. Freeze backend contracts.
  2. Audit dashboard with `frontend-ui-engineering` and `ui-ux-pro-max`.
  3. Standardize layout/components.
  4. Add operator workflows.
  5. Add tests.
  6. Capture screenshots.
- Definition of done: Dashboard supports core operator decisions without source-code knowledge and has real screenshot assets.

### API client library

- Problem: Users rely on curl/scripts instead of a stable client.
- Goal: Provide a typed Python client for core workflows.
- User/operator value: Easier integration into CI, notebooks, and services.
- Technical approach: Add `ares_client/` package or `ares.client` module with sync/async clients, typed request/response models, retry/timeouts, and auth handling.
- Architecture impact: API contract becomes consumer-tested.
- Files/modules likely affected: new client package, `pyproject.toml`, docs, tests.
- Data model changes: none.
- API changes: none; may expose OpenAPI schema as source of truth.
- Dashboard/UI changes: none.
- Configuration changes: base URL, API key, timeout, retry policy.
- Security considerations: never log API keys; support env loading carefully.
- Observability requirements: client request IDs and retries in logs.
- Tests required: mocked HTTP tests, contract tests against FastAPI test client, type tests.
- Documentation required: client quickstart and examples.
- Step-by-step implementation sequence:
  1. Define client API surface.
  2. Implement auth and request wrapper.
  3. Add methods for evaluations, champions, drift, gate, keys, audit.
  4. Add contract tests.
  5. Document examples.
- Definition of done: Client covers main API workflows and contract tests fail on incompatible schema changes.

### Kubernetes/Helm deployment

- Problem: Docker Compose exists; Kubernetes/Helm is absent.
- Goal: Provide a production deployment reference.
- User/operator value: Teams can deploy ARES to a cluster with repeatable manifests.
- Technical approach: Prefer Helm chart with templates for API, worker, scheduler, dashboard, migration job, services, ingress, secrets, config maps, HPA, PDB.
- Architecture impact: Separates production deployment from local Compose.
- Files/modules likely affected: new `deploy/helm/ares/`, `.github/workflows/`, docs.
- Data model changes: none.
- API changes: none.
- Dashboard/UI changes: none.
- Configuration changes: Helm values for URLs, images, resources, secrets, ingress, probes.
- Security considerations: non-root containers, read-only root filesystem where possible, resource limits, network policies.
- Observability requirements: ServiceMonitor/PodMonitor options.
- Tests required: `helm template`, schema validation, kubeconform, smoke tests.
- Documentation required: Kubernetes deployment guide.
- Step-by-step implementation sequence:
  1. Write deployment ADR.
  2. Add chart skeleton.
  3. Add API/worker/dashboard/scheduler/migration resources.
  4. Add secrets strategy.
  5. Add probes/resources/security contexts.
  6. Add CI validation.
  7. Write docs.
- Definition of done: Chart renders and validates, and docs describe a production-like deployment.

### Prometheus/Grafana observability

- Problem: Metrics endpoint exists, but alert rules and dashboards are missing.
- Goal: Provide production monitoring assets.
- User/operator value: Operators can detect and diagnose failures.
- Technical approach: Define metric catalog, add missing business metrics, Prometheus rules, and Grafana dashboard JSON.
- Architecture impact: Observability becomes part of release artifact.
- Files/modules likely affected: `ares/observability/metrics.py`, `deploy/observability/`, Helm chart, docs.
- Data model changes: none.
- API changes: none.
- Dashboard/UI changes: none.
- Configuration changes: alert thresholds and labels.
- Security considerations: avoid high-cardinality or sensitive labels.
- Observability requirements: API latency/error, gate decisions, drift alerts, auth failures, rate limits, audit failures, worker jobs, DB pool.
- Tests required: metrics exposure tests and alert rule lint.
- Documentation required: observability guide.
- Step-by-step implementation sequence:
  1. Define metric names and labels.
  2. Add missing metrics.
  3. Add tests.
  4. Add Prometheus rules.
  5. Add Grafana JSON.
  6. Wire Helm options.
  7. Document.
- Definition of done: A new deployment has working `/metrics`, alert rules, and Grafana dashboard.

### Security hardening

- Problem: Security baseline exists, but production hardening is incomplete.
- Goal: Reduce auth, secret, deployment, dependency, and webhook risk.
- User/operator value: Safer deployment and easier security review.
- Technical approach: Threat model, secure headers, strict CORS, key lifecycle, secret scanning, dependency/image scanning, webhook signing, audit API, least-privilege deploy.
- Architecture impact: Security becomes enforced by code and CI.
- Files/modules likely affected: `ares/api/main.py`, `ares/api/auth.py`, `ares/notifier/webhook.py`, `.github/workflows/`, Docker/Helm, docs.
- Data model changes: API key fields, audit fields.
- API changes: admin security endpoints if needed.
- Dashboard/UI changes: admin views if in scope.
- Configuration changes: allowed origins, security header policy, key TTL.
- Security considerations: this feature is security itself.
- Observability requirements: auth failures, forbidden requests, key expiry, suspicious rate-limit hits.
- Tests required: authz tests, CORS/header tests, secret scan, dependency scan, image scan.
- Documentation required: security hardening guide.
- Step-by-step implementation sequence:
  1. Run security review.
  2. Add headers/CORS config.
  3. Complete key lifecycle.
  4. Harden webhook signatures.
  5. Add scans to CI.
  6. Add deployment security contexts.
  7. Document.
- Definition of done: Security controls are implemented, tested, and enforced by CI.

### Load/performance testing

- Problem: Performance tests exist but are benchmark-style and not production capacity tests.
- Goal: Establish capacity and latency budgets.
- User/operator value: Teams understand sizing and failure limits.
- Technical approach: Add k6 or Locust scenarios for API reads, evaluate compare, drift report writes, dashboard data APIs, and worker jobs.
- Architecture impact: Adds performance gates and sizing docs.
- Files/modules likely affected: `tests/performance/`, new `load/`, `.github/workflows/`, docs.
- Data model changes: none unless indexes are added from findings.
- API changes: pagination may be required.
- Dashboard/UI changes: query optimizations if needed.
- Configuration changes: benchmark dataset sizes and thresholds.
- Security considerations: load tests must use test credentials and isolated DB.
- Observability requirements: collect metrics during tests.
- Tests required: load scenarios and threshold assertions.
- Documentation required: performance baseline report.
- Step-by-step implementation sequence:
  1. Define SLO budgets.
  2. Seed realistic data.
  3. Add load scenarios.
  4. Measure baseline.
  5. Fix bottlenecks.
  6. Add CI/staging gate.
  7. Document sizing.
- Definition of done: Load tests produce repeatable capacity evidence and enforce budgets.

### Model card generation

- Problem: Promotion evidence exists across JSON, DB, dashboard, and MLflow, but not as a standardized model card.
- Goal: Generate model cards for candidate and champion decisions.
- User/operator value: Governance and review are easier.
- Technical approach: Generate Markdown and JSON model cards from evaluation run, champion comparison, gate config, dataset metadata, drift status, and artifacts.
- Architecture impact: Promotion evidence gets a stable artifact.
- Files/modules likely affected: new `ares/model_cards.py`, `scripts/run_evaluation.py`, `ares/api/routers/evaluations.py`, docs.
- Data model changes: optional `model_card_uri` on evaluation run metadata.
- API changes: `GET /api/v1/evaluations/{run_id}/model-card`.
- Dashboard/UI changes: download/view model card.
- Configuration changes: template path and required fields.
- Security considerations: redact sensitive metadata.
- Observability requirements: generation failures.
- Tests required: golden-file tests, API tests.
- Documentation required: model card schema/template guide.
- Step-by-step implementation sequence:
  1. Define model card schema.
  2. Implement renderer.
  3. Generate from CLI/API.
  4. Store artifact URI.
  5. Add dashboard/download.
  6. Test/docs.
- Definition of done: Every promotion-grade evaluation can produce a complete model card.

### Error taxonomy and remediation messages

- Problem: `ares/exceptions.py` is rich, but API/CLI errors do not consistently include remediation and correct status mapping.
- Goal: Standardize all user-facing errors.
- User/operator value: Faster debugging and cleaner integrations.
- Technical approach: Add error catalog with code, category, HTTP status, operator message, remediation, retryability.
- Architecture impact: Errors become a stable public contract.
- Files/modules likely affected: `ares/exceptions.py`, `ares/api/schemas/error.py`, `ares/api/main.py`, CLI scripts, docs.
- Data model changes: optional error category columns where useful.
- API changes: consistent `ErrorResponse`.
- Dashboard/UI changes: render remediation in error states.
- Configuration changes: none.
- Security considerations: do not leak internals.
- Observability requirements: error counter by code/category.
- Tests required: snapshot tests for error responses and CLI failure JSON.
- Documentation required: error catalog.
- Step-by-step implementation sequence:
  1. Define catalog.
  2. Map exceptions to status/retryability/remediation.
  3. Update API handler.
  4. Update CLI failure payloads.
  5. Update dashboard error rendering.
  6. Test/docs.
- Definition of done: Every expected failure path returns actionable, stable error details.

### Pluggable gate engine

- Problem: Gate logic is centralized in `ares/gate/rules_engine.py`.
- Goal: Allow alternate decision policies without cluttering default rules.
- User/operator value: Teams can enforce organization-specific promotion policy.
- Technical approach: Define `GateEngine` protocol, default implementation, registry, and config selection.
- Architecture impact: Gate decision becomes extensible like evaluators.
- Files/modules likely affected: `ares/gate/`, `ares/config.py`, `ares.api.routers.gate`, tests/docs.
- Data model changes: store `gate_engine_name` and version in gate snapshot.
- API changes: list engines and simulate with engine override if authorized.
- Dashboard/UI changes: display engine/version.
- Configuration changes: `gate.engine`.
- Security considerations: gate plugins are trusted code and should be allowlisted.
- Observability requirements: decisions by engine/version.
- Tests required: default parity tests, custom engine tests, plugin failure tests.
- Documentation required: gate engine plugin guide.
- Step-by-step implementation sequence:
  1. Extract current rules into default engine.
  2. Define protocol and registry.
  3. Add config selection.
  4. Add tests proving default behavior unchanged.
  5. Add sample custom engine.
  6. Document.
- Definition of done: Default behavior is preserved, and a custom gate engine can be loaded through config.

### Event-driven evaluation workflow

- Problem: The worker scaffold does not run the real evaluation workflow.
- Goal: Support async, event-driven evaluations at production scale.
- User/operator value: API-triggered evaluations become reliable and observable.
- Technical approach: Add job/event tables, task queue execution, idempotency, status transitions, retries, and result callbacks.
- Architecture impact: Evaluation flow becomes API -> job -> worker -> DB/artifacts -> notifications.
- Files/modules likely affected: `ares/worker/tasks.py`, `scripts/run_evaluation.py`, `ares/api/routers/`, `ares/models/`, `ares/db/`.
- Data model changes: `evaluation_jobs`, `evaluation_events`.
- API changes: submit/status/cancel endpoints.
- Dashboard/UI changes: job status and queue view.
- Configuration changes: queue backend, concurrency, retry policy.
- Security considerations: submitted model paths and artifact references must be validated.
- Observability requirements: queue depth, job duration, retries, failures.
- Tests required: eager worker tests, integration tests with Redis where available, idempotency tests.
- Documentation required: async evaluation guide.
- Step-by-step implementation sequence:
  1. Extract reusable evaluation service from CLI.
  2. Add job/event models.
  3. Implement Celery task.
  4. Add APIs.
  5. Add dashboard.
  6. Add tests/docs.
- Definition of done: API-submitted evaluations execute asynchronously and produce the same persisted results as CLI.

### Threshold simulation/optimization

- Problem: Gate simulation endpoint exists for overrides, but optimization is manual.
- Goal: Help users choose thresholds from historical runs.
- User/operator value: Safer tuning with evidence.
- Technical approach: Add offline simulator over historical runs with objectives, false-pass/false-fail analysis, and suggested threshold ranges.
- Architecture impact: Gate config becomes tunable through historical evidence.
- Files/modules likely affected: `ares/gate/`, `ares/api/routers/gate.py`, dashboard, docs.
- Data model changes: optional simulation run records.
- API changes: `POST /api/v1/gate/optimize`.
- Dashboard/UI changes: threshold simulator page.
- Configuration changes: optimization objectives and constraints.
- Security considerations: write/admin scope for saved recommendations.
- Observability requirements: simulation duration/failures.
- Tests required: optimizer unit/property tests and API tests.
- Documentation required: threshold tuning guide.
- Step-by-step implementation sequence:
  1. Define optimization objective.
  2. Build simulator over stored runs.
  3. Add API.
  4. Add dashboard controls.
  5. Add docs and guardrails.
- Definition of done: Users can simulate and compare threshold sets before changing production config.

### Sandbox demo mode

- Problem: Demo scripts and placeholder screenshots exist, but no complete sandbox experience.
- Goal: Provide one-command seeded demo or hosted sandbox.
- User/operator value: Reviewers can evaluate the product quickly.
- Technical approach: Add `make demo` or `scripts/start_demo.py`, seed data, verify API/dashboard, and capture screenshots.
- Architecture impact: No production path change; improves onboarding.
- Files/modules likely affected: `Makefile`, `make.cmd`, `scripts/seed_demo_data.py`, `docs/screenshots.md`, README.
- Data model changes: none.
- API changes: none.
- Dashboard/UI changes: demo mode banner if needed.
- Configuration changes: demo env defaults.
- Security considerations: demo keys must be clearly non-production.
- Observability requirements: demo smoke output.
- Tests required: demo smoke test in CI if feasible.
- Documentation required: sandbox demo guide.
- Step-by-step implementation sequence:
  1. Define demo command.
  2. Seed champion/evaluations/drift.
  3. Verify API and dashboard.
  4. Capture screenshots.
  5. Document.
- Definition of done: A new user can run one command and see a realistic ARES dashboard.

## 7. Clean Code and No-Clutter Rules

- No unnecessary abstractions: add plugin/engine interfaces only where real extension points exist.
- No duplicate logic: gate decisions, evaluator execution, drift computation, API serialization, and auth checks must have one source of truth.
- No dead code: remove obsolete plans, stale examples, unused helper paths, and fake TODO scaffolds once replacements exist.
- No untested critical paths: promotion, rollback, auth, drift alerts, scheduler locks, migrations, backup/restore, and gate rules require tests.
- No silent failures: degradations must be logged, metered, and reflected in user/operator output.
- No unclear naming: names must reveal domain meaning, not implementation convenience.
- No giant files: split modules once they mix unrelated responsibilities.
- No hidden side effects: config loading, DB writes, network calls, and scheduler behavior must be explicit.
- No hardcoded secrets: dev defaults belong in `.env.example` only, never production docs.
- No fake production-readiness: README/docs may only claim features that exist and have verification evidence.
- No documentation claims without implementation evidence.

Module boundaries:

- `ares/evaluators/`: model loading, prediction, metric computation, plugin registry.
- `ares/gate/`: decision policy, gate snapshots, simulation, optimization.
- `ares/drift/` or `ares/drift_sources.py`: production prediction sources and drift runners.
- `ares/db/`: persistence and transactions only.
- `ares/api/`: schemas, routers, auth, middleware.
- `ares/worker/`: async execution only; no duplicated CLI logic.
- `dashboard/`: operator UI only; no business logic that belongs in API/core.
- `scripts/`: thin CLI wrappers around importable services.
- `deploy/`: production deployment artifacts.
- `docs/`: evidence-backed docs and runbooks.

Naming:

- Use domain names: `ChampionRollback`, `DriftJobRun`, `SliceMetricPoint`, `GateEngine`.
- Avoid generic `data`, `result`, `payload` where a specific name exists.

Error handling:

- All domain errors use `AresException` subclasses.
- API errors include code, message, remediation, retryability, request ID.
- CLI errors write valid JSON when they promise output files.

Logging:

- Include request ID, run ID, model name, job ID, and actor where applicable.
- Never log raw API keys, secrets, or raw prediction payloads.

Configuration:

- Every production behavior must be configurable through typed settings or `ares.config.yaml`.
- Reject unsafe production defaults at startup.

Dependency management:

- Keep optional heavy ML dependencies optional.
- Add new dependencies only with a concrete feature owner and CI coverage.

Type hints:

- Public functions, service boundaries, and plugin contracts must be typed.
- Avoid broad `Any` across API/service boundaries.

Testing:

- Tests assert behavior, not implementation details.
- Add regression tests before fixing bugs.
- Keep slow tests marked and isolated.

Documentation:

- Update docs in the same PR as behavior.
- Docs must include commands, expected outputs, and operational caveats.

API design:

- Versioned routes remain under `/api/v1`.
- Breaking changes require `/api/v2` or compatibility shims.
- Add pagination before unbounded data can grow.

Dashboard design:

- Prioritize dense, scannable operator workflows.
- Avoid marketing-style layouts.
- Use consistent page structure, compact charts, clear state, and safe action confirmations.

## 8. Testing and Quality Strategy

| Test Category | What to Test | Why It Matters | Suggested Tools | Where Tests Should Live | Acceptance Criteria |
|---|---|---|---|---|---|
| Unit tests | Evaluators, gates, metrics, serializers, config, auth helpers | Fast feedback for core logic | Pytest, pytest-mock | `tests/unit/` | Critical modules >= 90% line coverage; branch cases covered |
| Integration tests | API + DB + migrations + auth + drift + rollback | Proves components work together | Pytest, httpx, SQLAlchemy test DB | `tests/integration/` | All core flows pass against migrated DB |
| End-to-end tests | CLI evaluation to DB to API/dashboard-visible result | Proves user workflows | Pytest subprocess, Docker Compose where needed | `tests/e2e/` | Promotion-grade workflow passes with artifacts |
| Security tests | Auth scopes, expired keys, CORS, headers, webhooks, scans | Prevents high-risk regressions | Pytest, Bandit, Semgrep, pip-audit, Trivy, gitleaks | `tests/security/` and CI | Security gates pass; expected auth failures are tested |
| Contract tests | OpenAPI, client library, dashboard API shapes | Prevents consumer breakage | Schemathesis, openapi-python-client, snapshot tests | `tests/contract/` | Client/dashboard contracts fail on incompatible API changes |
| Mutation tests | Gate rules, drift metrics, auth decisions | Finds weak assertions | mutmut or cosmic-ray | CI scheduled job | Mutation score threshold set and tracked |
| Property-based tests | Drift math, threshold rules, slice aggregation | Catches edge cases | Hypothesis | `tests/property/` | Invariants hold across generated inputs |
| Load/performance tests | API, DB pool, worker, scheduler, dashboard read patterns | Establishes production limits | k6, Locust, pytest-benchmark | `tests/performance/`, `load/` | Budgets for p95/p99 latency and throughput enforced |
| Dashboard tests | Page imports, API client states, data transforms, screenshot smoke | Prevents UI regressions | Streamlit AppTest, Playwright if feasible | `tests/integration/test_dashboard.py`, `tests/dashboard/` | All pages render with seeded data and error states |
| Migration tests | Up/down, data preservation, branch consistency | Prevents schema incidents | Alembic, Pytest | `tests/integration/test_migrations.py` | Every migration has tested upgrade/downgrade where safe |
| Worker/Celery tests | Job execution, retries, idempotency, cancellation | Async flow reliability | Celery eager mode, Redis integration | `tests/integration/test_worker.py` | Worker produces same persisted result as CLI |
| API concurrency/rate-limit tests | Concurrent promotion, rollback, rate limits | Prevents races and abuse | pytest-asyncio, httpx, xdist | `tests/integration/` | Locks prevent duplicate active champions; rate limits enforce |
| Drift detection tests | Source adapters, schema validation, thresholds, alerts | Monitoring correctness | Pytest, fixtures, fake object store | `tests/unit/`, `tests/integration/` | Bad schema rejected; threshold breaches alert |
| Rollback tests | API/CLI/dashboard transaction and audit | Recovery confidence | Pytest, httpx | `tests/integration/`, `tests/e2e/` | Rollback changes active champion and writes audit/rollback record |
| Plugin loading tests | Evaluator/gate discovery, versioning, failure isolation | Extensibility reliability | importlib.metadata monkeypatching | `tests/unit/test_plugins.py` | Bad plugin fails safely; good plugin executes |

Quality gates:

- `python scripts/verify_repo.py` remains the canonical local gate.
- CI must run lint, type check, unit/integration/e2e as appropriate, coverage, Docker config, DVC dry-run, compile, security scans, and deployment validation.
- Coverage target for production-grade release: repository line coverage >= 92%, critical modules >= 95%, and no uncovered critical paths.
- Performance gates must use budgets, not just benchmark output.

## 9. Production Readiness Checklist

Reliability:

- [ ] Drift scheduler runs with duplicate-run protection.
- [ ] Worker executes real evaluation jobs with retries and idempotency.
- [ ] Rollback workflow is tested end to end.
- [ ] Health/readiness probes cover DB, Redis, object store, and dependencies.
- [ ] Migrations are tested up/down and run as deployment jobs.

Security:

- [ ] API keys expire, rotate, revoke, and update last-used metadata.
- [ ] Admin-only operations require admin or dedicated scopes.
- [ ] Security headers and CORS are configured.
- [ ] Secrets are externalized through deployment secret strategy.
- [ ] Dependency, image, and secret scans run in CI.
- [ ] Webhooks are signed and replay-resistant if used externally.

Observability:

- [ ] Metric catalog documented.
- [ ] Prometheus alert rules exist.
- [ ] Grafana dashboard exists.
- [ ] Logs include request/run/job IDs.
- [ ] Traces cover API, worker, DB, and external calls.
- [ ] Alerts map to runbook entries.

Scalability:

- [ ] API list endpoints are paginated.
- [ ] Dashboard queries are bounded.
- [ ] DB indexes support common queries.
- [ ] Worker concurrency is configurable.
- [ ] Load-test budgets are recorded.

Deployment:

- [ ] Helm/manifests exist and validate in CI.
- [ ] Containers run as non-root where possible.
- [ ] Resource requests/limits are set.
- [ ] Migration job is separate from API startup for production.
- [ ] Rollback of deployment and schema is documented.

Data integrity:

- [ ] Golden-set checksums are enforced for promotion-grade runs.
- [ ] Evaluation idempotency is preserved.
- [ ] Champion active uniqueness is enforced.
- [ ] Backup/restore scripts validate real DB/artifact state.
- [ ] Drift inputs are schema-validated.

Model governance:

- [ ] Model cards are generated.
- [ ] Promotion, rollback, and threshold changes are audited.
- [ ] Gate config snapshots include engine/version.
- [ ] Slice trends and drift reports are retained by policy.

Operator experience:

- [ ] Incident runbook covers all P0 alerts.
- [ ] Dashboard supports drift triage, rollback, comparison, and audit review.
- [ ] CLI commands print actionable failures.
- [ ] Error messages include remediation.

Developer experience:

- [ ] API client exists.
- [ ] Plugin authoring guide exists.
- [ ] Role-specific contributor guides exist.
- [ ] One-command demo exists.

Documentation:

- [ ] README claims match implementation.
- [ ] Stale docs are updated or removed.
- [ ] Migration docs list current migrations.
- [ ] Deployment, security, observability, and runbook docs are complete.

Compliance readiness:

- [ ] Audit retention policy exists.
- [ ] Access control model is documented.
- [ ] Model card evidence is reproducible.
- [ ] Security review evidence is stored.

## 10. Final Release Criteria

ARES can be called production-grade only when all criteria below are true:

- Test coverage: repository line coverage >= 92%, critical modules >= 95%, no uncovered promotion/rollback/auth/drift/scheduler paths.
- Workflows: quality, regression gate, drift monitor, eval-image build, security scan, Helm validation, and release workflows pass on main.
- Docs: README, deployment guide, operator runbook, security guide, observability guide, API client guide, plugin guide, configuration tuning guide, troubleshooting guide, and migration/rollback docs are current.
- Dashboards/alerts: Prometheus rules and Grafana dashboard are shipped and mapped to runbook entries.
- Security controls: expiring/rotating API keys, scoped auth, audit logs, security headers, CORS, secret management, dependency/image/secrets scans are in place.
- Deployment validation: Helm/manifests deploy API, worker, dashboard, scheduler, migration job, secrets, probes, resources, and observability hooks.
- Rollback validation: champion rollback is tested through API, CLI, dashboard, audit log, and post-rollback verification.
- Performance benchmarks: API, dashboard read paths, scheduler, worker, and DB pool pass documented p95/p99 and throughput budgets on seeded realistic data.
- Operator runbook validation: runbook commands are executed in staging or a sandbox and outputs are captured.
- Release artifact integrity: package, Docker images, SBOM, changelog, and version tags are produced by automation.

## 11. Suggested Execution Order

1. Refresh baseline: Graphify, docs inventory, test/coverage run, risk register.
2. Fix stale docs and remove misleading production claims so implementation starts from truthful documentation.
3. Add missing data models and migrations for scheduler runs, source configs, rollback records, API key lifecycle, alert events, slice trends, and audit enhancements.
4. Extract reusable services from scripts before adding APIs or workers.
5. Implement production data ingestion and drift scheduler before dashboard drift polish.
6. Implement alert rules and operator runbook immediately after scheduler alerts exist.
7. Implement API key expiration/rotation and audit persistence before external deployment work.
8. Implement champion rollback as API/CLI workflow before dashboard rollback controls.
9. Implement error taxonomy before broad dashboard and client work.
10. Add evaluator plugin system and gate engine contracts before adding many custom evaluator/gate examples.
11. Add slice trending and multi-model comparison before dashboard production polish.
12. Add API client after API contracts stabilize.
13. Add model card generation after evaluation, gate, drift, and champion data models are stable.
14. Add Helm/Kubernetes after runtime services and scheduler shape are stable.
15. Add Prometheus/Grafana and tracing after final metric names and deployment labels are stable.
16. Add load tests after pagination, indexes, worker, and scheduler are implemented.
17. Add security scans and hardening before release candidate.
18. Polish dashboard after backend APIs/data models are stable.
19. Finalize docs only after behavior is implemented and verified.
20. Run final code review, security review, performance review, and shipping checklist.

Do not:

- Polish dashboard before API/data models are stable.
- Finalize docs before behavior exists.
- Run final security review before auth/audit/deployment changes are complete.
- Claim production-readiness before rollback, drift scheduler, observability, deployment, backup/restore, and runbooks exist.

## 12. Final Summary

Implement Phase 1 first. The highest production value comes from production drift scheduling, real production data ingestion, governed champion rollback, API key lifecycle, audit persistence, alert rules, error taxonomy, and operator runbooks.

The project becomes exceptional when extension points, trend analytics, client tooling, model cards, Kubernetes deployment, observability assets, load/security gates, and polished dashboard workflows are all implemented with evidence-backed docs.

Do not skip rollback, observability, runbooks, security hardening, backup/restore validation, or deployment validation. Those are the line between a strong demo/reference project and a production-grade system.
