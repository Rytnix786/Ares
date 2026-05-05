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
- API-key authentication with env-backed keys, DB-backed hashed keys, scopes, constant-time env-key comparison, expiration checks, rotation grace handling, last-used tracking, and rate limiting.
- Audit middleware and `AuditLog` model for mutation logging.
- Prometheus counters/gauges/histograms in `ares/observability/metrics.py` and optional OpenTelemetry setup in `ares/observability/telemetry.py`.
- Docker Compose stack with Postgres, Redis, MinIO, MLflow, API, worker, and Streamlit dashboard.
- Dockerfiles for API, worker, eval image, and dashboard.
- GitHub Actions workflows: `quality.yml`, `regression_gate.yml`, `drift_monitor.yml`, and `build-eval-image.yml`.
- Streamlit dashboard pages for leaderboard, drill-down, drift monitor, model comparison, promotion workflow, and alerts.
- Test tree with 42 Python test files and 220 tests in the final canonical `python scripts/verify_repo.py` run after Phase 0 coverage hardening.
- Fresh verification artifact `reports/coverage.xml` from `python scripts/verify_repo.py`; detailed terminal coverage reported 89.92%, satisfying the configured integer 90% gate.
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
- API key lifecycle primitives exist in the model/auth/CRUD layer, but admin-facing API/CLI/dashboard surfaces, TTL policy, audit UX, and operational documentation are incomplete.
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
| Security | API key lifecycle completion | Model/auth/CRUD support expiration, usage tracking, and rotation, but operator-facing workflows and policy controls are incomplete | Keys remain hard to operate safely at scale even though the primitives exist | P0 | Medium | ApiKey model, auth dependency, CLI/API/dashboard/admin docs | Lifecycle policy, rotate/revoke UX, audit visibility, tests, and docs are complete |
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

## 4. GStack Skill Integration Strategy

The repository contains a vendored GStack checkout at `gstack-main/`. For this plan, that directory is the operative GStack system even though its on-disk name is `gstack-main` rather than `gstack`. It is large (`701` tracked files in this checkout), so this section inventories the execution surfaces that matter to delivering ARES. GStack output is advisory and workflow-enforcing; ARES repository evidence remains the final authority.

### Purpose of GStack in the Production Plan

GStack should be used to make ARES implementation faster, cleaner, and safer by enforcing a structured order of work:

1. Understand the product and architecture before editing.
2. Challenge the plan before implementation hardens bad assumptions.
3. Review code, security, DX, QA, and release readiness with distinct specialist lenses.
4. Use the browser-backed QA and benchmark tooling only when the API/dashboard stack is actually running.
5. Treat all GStack outputs as inputs to repository-backed decisions, tests, and documentation.

GStack is most valuable for ARES in five ways:

- planning discipline for Phases 0-4;
- architecture and execution review before cross-module edits;
- browser-backed dashboard QA after the local stack is running;
- release/readiness verification late in the cycle;
- persistent learnings so repeated mistakes are not rediscovered every session.

### Full GStack Inventory

#### 4.1 Control documents, configs, and generated-skill system

| Item | Path | Purpose | Use when | Do not use when | Dependencies | Output | Related phase |
|---|---|---|---|---|---|---|---|
| GStack overview | `gstack-main/README.md` | Canonical skill catalog, install modes, and workflow order | Orienting new contributors to the vendored system | Deriving implementation facts about ARES itself | Bun/Node/Claude Code assumptions in the doc | Workflow map and command surface | Phase 0 |
| Architecture reference | `gstack-main/ARCHITECTURE.md` | Browser daemon, security model, template generation, eval/test architecture | Using `/browse`, `/qa`, `/pair-agent`, or security-sensitive browser work | Making ARES security claims without validating ARES code | Bun, Playwright, localhost daemon, extension | Design constraints and risk model | Phases 0-4 |
| Browser reference | `gstack-main/BROWSER.md` | Full `$B` command semantics | Preparing dashboard QA scripts or debugging browse failures | Planning non-browser backend work | Browse binary and daemon | Command-level reference | Phases 2-4 |
| Agent guidance | `gstack-main/AGENTS.md`, `gstack-main/CLAUDE.md` | Host-facing routing and usage posture | Understanding how GStack expects agents to invoke skills | Treating host instructions as ARES product requirements | Claude/OpenAI/OpenClaw host behavior | Invocation conventions | Phase 0 |
| Builder philosophy | `gstack-main/ETHOS.md`, `gstack-main/DESIGN.md` | Search-before-building and design posture | Phase 0 planning, dashboard quality framing | Replacing ARES acceptance criteria with ideology | None beyond Markdown | Review heuristics and non-functional expectations | Phases 0, 2, 4 |
| GBrain guides | `gstack-main/USING_GBRAIN_WITH_GSTACK.md`, `gstack-main/docs/gbrain-sync.md`, `gstack-main/docs/gbrain-sync-errors.md` | Persistent memory/search workflow | Long multi-session implementation where repo memory helps | If GBrain is not installed or trusted for this repo | GBrain CLI, optional Supabase/PGLite | Search guidance and sync workflow | Phases 0-4 |
| Skill generator | `gstack-main/SKILL.md`, `gstack-main/SKILL.md.tmpl`, per-skill `SKILL.md.tmpl`, `gstack-main/scripts/gen-skill-docs.ts` | Generated skill docs from templates and command metadata | Verifying skill docs are current before relying on them | Editing generated `SKILL.md` output by hand in GStack | Bun, source metadata, templates | Fresh generated skill docs | Phase 0 |
| Build/test config | `gstack-main/package.json`, `gstack-main/.github/workflows/*`, `gstack-main/actionlint.yaml`, `gstack-main/.gitlab-ci.yml` | Declares GStack binaries, tests, CI, and doc generation | Verifying what GStack itself can do and how it is validated | Assuming those pipelines validate ARES | Bun, Playwright, provider CLIs | Build/test commands and CI evidence | Phase 0 |
| Host and overlay configs | `gstack-main/hosts/*.ts`, `gstack-main/model-overlays/*.md`, `gstack-main/agents/openai.yaml`, `gstack-main/conductor.json` | Host-specific install/routing and model behavior overlays | Explaining how GStack targets Codex/OpenClaw/others | Using host wiring as a substitute for ARES design | Supported host CLIs | Host routing rules | Phase 0 |
| Design/reference docs | `gstack-main/docs/*`, especially `docs/skills.md`, `docs/OPENCLAW.md`, `docs/REMOTE_BROWSER_ACCESS.md`, `docs/domain-skills.md`, `docs/designs/*` | Deep-dive references for skills, remote browser access, domain skills, and design rationale | When a skill’s `SKILL.md` is ambiguous | Using design notes as proof of shipped behavior in ARES | Varies by document | Clarifying context, limits, and examples | Phases 0-4 |

#### 4.2 Workflow skills to use during ARES implementation

| Skill | Path | Purpose and problem solved | Use when | Do not use when | Inputs | Outputs | Dependencies / limitations / risks | ARES use case | Phase | Mode |
|---|---|---|---|---|---|---|---|---|---|---|
| `/office-hours` | `gstack-main/office-hours/SKILL.md` | Forces product/problem clarity before code | Starting a new phase or ambiguous feature | Scope is already locked and execution-only | Problem statement, user pain, constraints | Design doc / reframed problem statement | Can expand scope aggressively if not constrained | Reconfirm what “production-grade ARES” means before Phase 0 lock | 0 | Manual |
| `/plan-ceo-review` | `gstack-main/plan-ceo-review/SKILL.md` | Challenges product framing and scope | Before committing to a large roadmap slice | For small mechanical changes | Plan draft, goals, constraints | Scope challenges and recommended direction | Can bias toward expansion; must be checked against repo reality | Validate whether Phase 2/4 features are truly worth building | 0, 2, 4 | Manual |
| `/plan-eng-review` | `gstack-main/plan-eng-review/SKILL.md` | Architecture, data flow, edge-case, and test review | Before cross-module or migration-heavy work | After implementation is already complete | Plan, architecture context | Execution plan, diagrams, risk list, test plan | Advisory only; does not inspect runtime unless prompted | Scheduler, rollback, deployment, plugin architecture review | 0-4 | Manual |
| `/plan-design-review` | `gstack-main/plan-design-review/SKILL.md` | Reviews UX/design plans before implementation | Dashboard/operator workflow planning | Pure backend slices | UX goals, mockups/plans | Rated design feedback and required improvements | Interactive; not useful until UI scope is defined | Phase 2 dashboard IA before redesign work | 2 | Manual |
| `/plan-devex-review` | `gstack-main/plan-devex-review/SKILL.md` | Reviews developer/operator onboarding and TTHW | API client, docs, deploy UX, contributor guides | Backend-only internals with no user-facing workflow | Developer persona, docs/CLI plan | DX friction map and prioritized fixes | Time-consuming; use only for DX-heavy phases | Deployment docs, API client, sandbox demo, contributor guides | 2-4 | Manual |
| `/plan-tune` | `gstack-main/plan-tune/SKILL.md` | Tunes question sensitivity for GStack itself | Repeated use of interactive GStack reviews | ARES implementation tasks directly | Existing GStack question history | Preference updates | GStack-internal, not ARES-deliverable | Reduce review churn in long sessions | 0-4 | Optional manual |
| `/autoplan` | `gstack-main/autoplan/SKILL.md` | Runs CEO -> design -> eng -> DX review chain | Need a single reviewed plan artifact | Scope is tiny or already approved | Initial plan / feature request | Consolidated reviewed plan | May surface taste questions late; still needs repo verification | One-command preflight for major phase starts | 0-4 | Manual |
| `/design-consultation` | `gstack-main/design-consultation/SKILL.md` | Creates design system direction | Major UI/dashboard redesign planning | Backend and ops work | Product and visual context | `DESIGN.md`, design direction | Can overreach for utility dashboards | If ARES dashboard gets a deliberate visual-system refresh | 2 | Optional manual |
| `/review` | `gstack-main/review/SKILL.md` | Staff-level pre-landing review for structural bugs and unsafe diffs | End of each implementation slice | Before any code exists | Diff/branch | Findings, sometimes auto-fixes | Requires actual diff; can’t replace tests | Review migrations, auth, scheduler, deployment diffs | 1-4 | Manual before merge |
| `/codex` | `gstack-main/codex/SKILL.md` | Second-opinion review/challenge via Codex CLI | High-risk changes need model diversity | Codex CLI unavailable | Diff / prompt / review mode | Independent findings or consultation | Depends on Codex CLI; external toolchain | Challenge security, migration, and release plans | 1-4 | Manual or approval-gated |
| `/investigate` | `gstack-main/investigate/SKILL.md` | Root-cause debugging before fixing | Runtime failures or unexplained regressions | Pure feature building | Failing symptom, logs, error paths | Root-cause narrative, narrowed edit scope | Stops after repeated failed fixes; requires evidence | Debug scheduler, dashboard, or deployment failures during rollout | 1-4 | Manual |
| `/design-review` | `gstack-main/design-review/SKILL.md` | Live visual QA plus fix loop | Dashboard polish after APIs stabilize | Before dashboard contracts exist | Running UI, screenshots, code | Visual findings and fixes | Code-mutating; not for report-only audits | Final dashboard production polish | 2, 4 | Manual after approval |
| `/design-shotgun` | `gstack-main/design-shotgun/SKILL.md` | Generates multiple mockup variants | Exploring alternative dashboard layouts | Utility dashboard IA is still undefined or Streamlit constraints dominate | Design prompt, constraints | Comparison board and preferred variants | Image-heavy and can drift from actual framework | Explore ARES screenshots/marketing/demo page only | 2, 4 | Optional manual |
| `/design-html` | `gstack-main/design-html/SKILL.md` | Produces production HTML/CSS from approved designs | Static site, landing page, or docs microsite work | Streamlit page implementation, Python backend, or ops slices | Approved design/mocks | HTML/CSS artifacts | Not aligned with current Streamlit dashboard architecture | Likely not applicable unless ARES adds a separate static surface | 4 | Approval-only |
| `/devex-review` | `gstack-main/devex-review/SKILL.md` | Live onboarding/docs/CLI audit | API client, setup docs, contributor flows, demo flow | No runnable docs/CLI yet | Running docs/site/CLI | DX audit with measured TTHW | Needs a real runnable path | Audit quickstart, deploy guide, and demo setup | 2-4 | Manual |
| `/qa` | `gstack-main/qa/SKILL.md` | Browser-backed QA plus fix loop | Dashboard/API UI is running and fixes are in scope | Read-only audit only, or app not running | URL, expected workflows | Bugs, screenshots, fixes, regression intent | Code-mutating; requires running target | Test leaderboard, promotion, drift, and alert pages | 2-4 | Manual after approval |
| `/qa-only` | `gstack-main/qa-only/SKILL.md` | Browser-backed QA report only | Need a production-readiness dashboard bug report without editing | Backend-only slices | URL, expected workflows | Structured bug report with repro evidence | UI-focused; requires live target | Release-candidate dashboard validation | 2-4 | Manual |
| `/scrape` | `gstack-main/scrape/SKILL.md` | Extracts data from web pages | Pulling comparative deployment/docs data from external sites | Internal ARES code review work | URL/intent | JSON extraction | Not for mutation; external dependency | Optional competitive research for docs/deploy patterns | 0, 3 | Optional manual |
| `/skillify` | `gstack-main/skillify/SKILL.md` | Turns a successful scrape flow into a reusable browser skill | Repeatable external web extraction is needed | Core ARES build work | Prior scrape transcript | New browser-skill files | GStack-internal acceleration only | Not needed for ARES production features today | N/A | Optional manual |
| `/ship` | `gstack-main/ship/SKILL.md` | Pre-PR ship workflow | After a slice is implemented and locally verified | Before tests/review evidence exists | Branch, tests, docs, diff | Commit, push, PR workflow state | Assumes git/PR flow; not a substitute for local quality gates | Finalize each approved slice | 1-4 | Manual |
| `/land-and-deploy` | `gstack-main/land-and-deploy/SKILL.md` | Merge, deploy, wait, verify | Staging/prod deployment with verified CI | Local-only planning work | PR, deploy config, health URLs | Deploy verification | Needs configured platform; high-risk if premature | Final staged deployment after Phase 3/4 readiness | 3-4 | Approval-only |
| `/canary` | `gstack-main/canary/SKILL.md` | Post-deploy monitoring loop | After deploy to staging/prod | Before a deployment exists | URL, baseline, health surface | Canary evidence | Browser and runtime dependent | Verify ARES dashboard/API after release | 3-4 | Approval-only |
| `/landing-report` | `gstack-main/landing-report/SKILL.md` | Read-only ship queue dashboard | Many parallel workspaces or release branches | Single-branch solo work | Repo state | Queue snapshot | GStack workflow aid only | Useful if ARES work is split across many worktrees | 3-4 | Optional manual |
| `/document-release` | `gstack-main/document-release/SKILL.md` | Updates docs after shipping | Behavior has stabilized and docs need sync | Before implementation exists | Diff, docs | Updated docs list and drift findings | Must not invent features; repo evidence still required | Align README/runbooks/guides with shipped ARES behavior | 2-4 | Manual after code freeze |
| `/setup-deploy` | `gstack-main/setup-deploy/SKILL.md` | Configures deploy checks for GStack | Before using `/land-and-deploy` | If deployment remains manual/local | Deploy target, health URLs | Deploy config state | GStack-side configuration only | Prepare final deployment verification flow | 3 | Manual |
| `/gstack-upgrade` | `gstack-main/gstack-upgrade/SKILL.md` | Upgrades the vendored/global GStack tooling | GStack bugs block the workflow | ARES issue is unrelated to GStack | Existing install | Upgraded toolchain | Changes the tooling, not ARES | Use only if a GStack defect blocks ARES work | N/A | Approval-only |
| `/context-save` | `gstack-main/context-save/SKILL.md` | Saves in-progress execution context | Handoffs between long sessions | Short, self-contained edits | Current state and remaining work | Saved context snapshot | GStack-side state only | Preserve rollout state between production-plan phases | 0-4 | Optional manual |
| `/context-restore` | `gstack-main/context-restore/SKILL.md` | Restores saved context | Resuming multi-session work | Same-session work | Saved context | Restored plan/state | Requires prior saved context | Resume long ARES execution programs | 0-4 | Optional manual |
| `/learn` | `gstack-main/learn/SKILL.md` | Manages accumulated project learnings | Repeated issues or patterns are emerging | Single-shot tasks | Existing learnings | Search/prune/export results | Can become stale if not curated | Capture ARES-specific rollout rules and pitfalls | 0-4 | Optional manual |
| `/retro` | `gstack-main/retro/SKILL.md` | Weekly retrospective over work patterns | Multi-week delivery program | Single patch work | Git history and metrics | Retro report | Not a release gate | Review execution quality across phases | 4 | Optional manual |
| `/health` | `gstack-main/health/SKILL.md` | Composite code-quality dashboard | Need a quick health summary over lint/type/test status | Detailed failure diagnosis is needed | Existing project commands | Weighted health report | Wrapper only; underlying commands must work | Track repo quality trend between phases | 0-4 | Manual |
| `/benchmark` | `gstack-main/benchmark/SKILL.md` | Browser performance baseline/regression tool | Frontend/dashboard performance validation | No live UI or no comparable baseline | URL and benchmark scope | Perf baseline/report | Browser-centric, not backend load test | Measure dashboard render and navigation costs | 2-4 | Manual |
| `/benchmark-models` | `gstack-main/benchmark-models/SKILL.md` | Cross-model benchmark for GStack prompts | Comparing AI reviewer quality/cost | ARES product benchmarking | Prompt and providers | Model comparison table | GStack-tooling concern, not ARES runtime | Optional if choosing a review host strategy | N/A | Optional manual |
| `/cso` | `gstack-main/cso/SKILL.md` | Security audit with infra, supply-chain, OWASP, STRIDE framing | Security review after major backend/deploy/auth changes | Before architecture and auth decisions are visible in code/docs | Repo state, deploy context | Security findings with exploit framing | Advisory; findings must be validated in ARES | Phase 1 and 3 security gates | 1, 3, 4 | Manual before approval |
| `/setup-gbrain` | `gstack-main/setup-gbrain/SKILL.md` | Installs/configures GBrain memory/search | Long-running ARES execution with trusted memory | Memory should remain local/disabled | GBrain target and trust mode | GBrain installation and trust config | External system, privacy decision required | Optional acceleration for repeated repo search | 0 | Optional manual |
| `/sync-gbrain` | `gstack-main/sync-gbrain/SKILL.md` | Re-indexes repo into GBrain | Repo changed materially and GBrain is in use | GBrain is absent or denied | Repo path and sync mode | Updated index and guidance block | External system; index freshness matters | Keep ARES search/memory current between phases | 0-4 | Optional manual |
| `/browse` | `gstack-main/browse/SKILL.md` | Fast persistent browser surface | Dashboard QA, screenshot capture, docs verification | Pure backend work | URL and `$B` commands | Screenshots, DOM state, workflow evidence | Requires Bun/Playwright/browser daemon | Drive Streamlit dashboard and docs flows | 2-4 | Manual |
| `/open-gstack-browser` | `gstack-main/open-gstack-browser/SKILL.md` | Visible browser with sidebar and stealth | Interactive visual QA or browser handoff | Headless-only CI checks | Running browser session | Headed browser workspace | Operational convenience, not product evidence alone | Watch the dashboard and troubleshoot visually | 2-4 | Optional manual |
| `/setup-browser-cookies` | `gstack-main/setup-browser-cookies/SKILL.md` | Imports cookies into headless browse session | QA requires authenticated browser state | Local ARES dashboard has no auth or no browser login flow | Local browser cookie stores | Imported session cookies | Sensitive operation; local-machine only | Likely not needed until ARES gains browser auth | 2-4 | Approval-only |
| `/pair-agent` | `gstack-main/pair-agent/SKILL.md` | Shares browser access with another AI agent | Parallel browser testing or second-opinion QA | Single-agent review is sufficient | Existing browser session and peer agent | Scoped shared browser session | Remote/tunnel security and coordination overhead | Pair Codex/Claude/OpenClaw on the ARES dashboard | 2-4 | Optional manual |
| `/careful` | `gstack-main/careful/SKILL.md` | Warns before destructive operations | Prod-like deploy, DB, or git operations | Read-only analysis | Destructive command intent | Safety warning / confirmation gate | Advisory only | Use during deployment, migration, rollback work | 1, 3, 4 | Automatic/manual |
| `/freeze` | `gstack-main/freeze/SKILL.md` | Restricts edits to a directory | Narrow debugging or scoped edits | Cross-cutting refactors | Target directory | Edit-scope lock | Can slow legitimate cross-cutting work | Constrain migrations, dashboard, or docs-only edits | 0-4 | Manual |
| `/guard` | `gstack-main/guard/SKILL.md` | Combines careful + freeze | Highest-risk work | Wide exploratory refactors | Target directory and risky op context | Safety + scope guard | Same limitations as both underlying skills | Use around rollback/deploy/hotfix work | 1, 3, 4 | Manual |
| `/unfreeze` | `gstack-main/unfreeze/SKILL.md` | Clears freeze boundary | Scope must widen | Freeze is still protecting a risky task | Existing freeze state | Global edit access restored | None beyond losing protection | End scoped-debug sessions | 0-4 | Manual |
| `/make-pdf` | `gstack-main/make-pdf/SKILL.md` | Creates polished PDFs from Markdown | Release artifacts or stakeholder packets | Source-code implementation work | Markdown source | PDF artifact | Presentation aid only | Optional release packet for ARES docs | 4 | Optional manual |

#### 4.3 Supporting GStack toolchains, commands, and reusable processes

| Toolchain | Path | Purpose | Use when | Do not use when | Dependencies | Output | Limitations / risks | ARES mapping | Phase | Mode |
|---|---|---|---|---|---|---|---|---|---|---|
| Browse daemon and command runtime | `gstack-main/browse/src/*`, `browse/dist/*`, `browse/bin/*` | Persistent browser, command dispatch, refs, content security, tokenized tunnel support | Dashboard QA, screenshots, performance checks | Backend-only slices | Bun, Playwright, Chromium, localhost daemon | Browser state, screenshots, workflow evidence | Browser security and platform setup must work first | Dashboard QA, benchmark, canary | 2-4 | Manual |
| Browser extension and sidebar | `gstack-main/extension/*` | Headed browser sidepanel, inspector, activity stream | Interactive browser debugging or paired-agent work | Headless-only or CLI-only work | Browser extension load, local daemon | Visible browser UX and activity stream | Operational complexity, browser-only | Human-supervised dashboard review | 2-4 | Optional manual |
| Domain-skill example | `gstack-main/browser-skills/hackernews-frontpage/*` | Example codified browser skill lifecycle | Learning how `/scrape` and `/skillify` persist flows | ARES product work directly | Browse runtime | Example script/test/skill trio | Example only; unrelated to ARES domain | Reference for repeatable external scrape automation | 0 | Reference only |
| GBrain and memory CLIs | `gstack-main/bin/gstack-brain-*`, `bin/gstack-gbrain-*`, `lib/gbrain-sources.ts`, `lib/gstack-memory-helpers.ts` | Persistent learnings, repo sync, privacy/trust gates | Multi-session delivery where search/memory helps | Memory is disabled or not trusted | GBrain CLI, optional Supabase/PGLite | Searchable repo memory and synced learnings | Extra infrastructure and privacy decisions | Long-running ARES delivery acceleration | 0-4 | Optional manual |
| Config / analytics / telemetry CLIs | `gstack-main/bin/gstack-config`, `gstack-analytics`, `gstack-telemetry-*`, `gstack-security-dashboard`, `gstack-community-dashboard`, `supabase/*` | Operates GStack’s own telemetry/config/security surfaces | Debugging GStack itself or reviewing its privacy/security model | ARES feature development | Bun, local state, optional Supabase | Local dashboards, config state, attack logs | GStack-internal, not ARES product functionality | Only relevant if GStack behavior blocks ARES work | N/A | Optional manual |
| Review/planning support CLIs | `gstack-main/bin/gstack-diff-scope`, `gstack-patch-names`, `gstack-review-*`, `gstack-question-*`, `gstack-specialist-stats`, `gstack-builder-profile`, `gstack-developer-profile`, `scripts/question-registry.ts`, `scripts/psychographic-signals.ts` | Narrow diff scope, review logging, question tuning, persona helpers | Large review programs and repeated planning loops | Straightforward implementation tasks | Local repo state | Narrowed review scope and logged preferences | Process aids only | Use to keep large ARES reviews disciplined | 0-4 | Optional manual |
| Team/install lifecycle CLIs | `gstack-main/setup`, `bin/dev-setup`, `bin/dev-teardown`, `bin/gstack-team-init`, `bin/gstack-uninstall`, `bin/gstack-update-check`, `scripts/host-config.ts`, `scripts/discover-skills.ts` | Install/update/team bootstrap and host detection | Enabling or repairing GStack in the repo/toolchain | ARES runtime work | Git, Bun, host CLI layout | Installed/updated skill set | Tooling-only | Ensure GStack is usable before relying on it | 0 | Manual |
| Benchmark/eval harness | `gstack-main/bin/gstack-model-benchmark`, `scripts/eval-*.ts`, `test/helpers/*`, `test/skill-e2e*.ts`, `benchmark-models/SKILL.md` | Measures GStack prompt/model quality and validates skills | Verifying GStack workflow reliability | Measuring ARES model performance | Provider CLIs, Bun tests | GStack eval reports | Not ARES performance evidence | Confirms GStack workflow trustworthiness only | 0 | Optional manual |
| Skill health and doc freshness | `gstack-main/scripts/skill-check.ts`, `test/skill-validation.test.ts`, `test/gen-skill-docs.test.ts` | Validates that generated skills match the command surface | Before relying on vendored skills in a long program | ARES repo validation | Bun test harness | GStack skill health report | Validates GStack, not ARES | Preflight if GStack behavior looks inconsistent | 0 | Optional manual |
| Worktree helpers | `gstack-main/lib/worktree.ts`, `bin/gstack-repo-mode`, `landing-report/SKILL.md` | Coordinates multi-worktree execution and ship queues | Parallel ARES slices across worktrees | Single-worktree execution | Git worktrees | Worktree/queue visibility | Workflow aid only | Useful if several ARES phases run in parallel | 3-4 | Optional manual |

### GStack Execution Order

1. Repository understanding and architecture mapping:
   - Read `gstack-main/README.md`, `ARCHITECTURE.md`, `AGENTS.md`, and the relevant `SKILL.md` files.
   - Run `/office-hours` and `/plan-eng-review` against the current ARES roadmap only after repository evidence is gathered.
2. Gap validation:
   - Validate the roadmap against real ARES code, tests, docs, and workflows.
   - Use `/autoplan` or `/plan-ceo-review` only to sharpen priorities, not to invent features absent from the repository.
3. Code-quality review:
   - Use `/review` at the end of each implementation slice.
   - Use `/codex` as a second opinion for high-risk diffs.
4. Security review:
   - Use `/cso` after auth, audit, deployment, webhook, or secret-handling changes are visible in code and docs.
5. Frontend/dashboard review:
   - Use `/browse`, `/qa-only`, `/qa`, `/design-review`, and `/benchmark` only after the API/dashboard contracts and runtime stack are stable.
6. Documentation/runbook review:
   - Use `/plan-devex-review`, `/devex-review`, and `/document-release` after behavior exists and before release sign-off.
7. Testing and QA planning:
   - Use `/plan-eng-review` to pressure-test test plans before implementation and `/qa-only` for release-candidate visual validation.
8. Deployment validation:
   - Use `/setup-deploy`, `/land-and-deploy`, and `/canary` only after deployment artifacts, health endpoints, and rollback paths exist.
9. Final production-readiness review:
   - Use `/review`, `/codex`, `/cso`, `/devex-review`, `/qa-only`, and `/canary` as the final multi-angle release gate.

### Phase-by-Phase GStack Usage

| Phase | Goal | GStack skills/tools | Why use them | When to use | Expected output | Risks | Validation |
|---|---|---|---|---|---|---|---|
| Phase 0 | Re-understand repo and lock baseline | `/office-hours`, `/plan-eng-review`, `/autoplan`, `/health`, optional `/setup-gbrain` and `/sync-gbrain`; supporting docs `README.md`, `ARCHITECTURE.md`, `docs/skills.md` | Forces repository-backed planning discipline and identifies hidden assumptions early | After reading ARES docs/code/tests and before editing | Locked baseline, reviewed roadmap, current risk register, GStack usage plan | Over-expansion if planning skills are run before repository evidence is gathered | Reconcile every recommendation with ARES file paths, collected tests, and workflow files |
| Phase 1 | Close critical production gaps | `/plan-eng-review`, `/review`, `/codex`, `/cso`, `/investigate`, `/guard`, `/careful` | Highest-risk backend and security changes need architectural review, security challenge, and controlled execution | Before and after migrations, auth, scheduler, rollback, audit, alerting work | Architecture/test plan, review findings, security findings, narrowed debugging scope | Advisory output can be mistaken for proof | Validate via ARES tests, migration runs, and runtime probes |
| Phase 2 | Complete user-facing workflows and dashboard | `/plan-design-review`, `/plan-devex-review`, `/browse`, `/qa`, `/qa-only`, `/design-review`, `/benchmark`, `/document-release` | Stabilizes UX, developer/operator paths, and dashboard quality after backend contracts settle | Only after APIs/data models are stable and the stack is runnable | UX review, browser bug reports, fixes, perf baselines, synced docs | UI tools waste time if contracts are still moving | Validate against seeded dashboard data, screenshots, and integration tests |
| Phase 3 | Enterprise deployment, observability, supportability | `/plan-eng-review`, `/cso`, `/devex-review`, `/setup-deploy`, `/land-and-deploy`, `/canary`, `/document-release` | Reviews deployability, security posture, operator UX, and post-deploy health | After deploy artifacts, runbooks, and health endpoints exist | Deploy plan, security findings, DX findings, deploy verification, canary evidence | Deploy automation is dangerous before envs are hardened | Validate with staging deploy, health checks, alert tests, and rollback drills |
| Phase 4 | Top 0.01% excellence and release gate | `/plan-ceo-review`, `/plan-eng-review`, `/review`, `/codex`, `/cso`, `/qa-only`, `/benchmark`, `/devex-review`, `/document-release`, optional `/make-pdf` | Keeps advanced work optional, justified, and measurable while tightening the release candidate | After core production-grade behavior exists | Final review packet, bug list, perf data, docs sync, release notes/artifacts | Advanced tooling can distract from critical-path readiness | Validate against final release criteria in this document and captured evidence |

### GStack Usage Rules

- Do not use a skill blindly.
- Do not use a skill when its output is irrelevant to the current ARES phase.
- Do not let GStack output override repository evidence.
- Do not make code changes based only on skill output without validation.
- Do not introduce clutter, duplicated logic, or speculative abstractions because a skill suggested them.
- Every skill-generated recommendation must map to a concrete ARES task, test, benchmark, runbook step, or documented decision.
- Every major production change must have validation evidence from ARES commands, tests, runtime checks, screenshots, or deployment probes.
- `/qa`, `/design-review`, `/ship`, `/land-and-deploy`, `/canary`, `/setup-browser-cookies`, and `/gstack-upgrade` are never default-on for ARES; they require an explicit phase need and an operator decision.
- Browser-backed GStack tools are not substitutes for ARES integration tests, API tests, migration tests, or deployment validation.
- GStack security findings are hypotheses until reproduced against ARES code, config, or runtime.

### Approval Gate

- First produce the analysis.
- Then update only `Production_grade_final_plan.md`.
- Do not touch any other files.
- Do not implement source code until explicit approval is given.
- If GStack suggests edits outside the approved scope, reject them and keep the work inside this plan until the user changes the scope.

## Ruflo Integration Strategy

The repository also contains a local Ruflo checkout at `ruflo-main/`. Ruflo is an orchestration and workflow system, not ARES application logic. The repository evidence shows three distinct Ruflo surfaces that matter to this roadmap:

1. orchestration guidance (`README.md`, `AGENTS.md`, `.agents/*`, `docs/USERGUIDE.md`);
2. machine-readable capability inventory and verification (`verification-inventory.json`, `verification.md`, `bin/cli.js`, `package.json`);
3. reusable execution surfaces (CLI command families, plugins, hooks, agents, and local skills).

Ruflo must be used as planning, review, routing, and evidence-collection infrastructure. It must not be treated as proof that an ARES change is correct. Final authority remains ARES code, tests, lint/type checks, runtime probes, migration validation, and deployment evidence.

There are also version and branding mismatches inside `ruflo-main` that affect trust decisions:

- `package.json` reports version `3.6.30`;
- `docs/STATUS.md` still reports `ruflo@3.6.24`;
- `docs/USERGUIDE.md` describes "Ruflo v3.5";
- `AGENTS.md` and hooks examples use `claude-flow`, while other docs use `ruflo`.

Because of that drift, `verification-inventory.json`, `package.json`, and the local skill/config files should be treated as the strongest Ruflo evidence in this repo.

### Purpose of Ruflo in the Production Plan

Repository evidence supports using Ruflo in the ARES plan for these concrete reasons:

- planning quality: `ruflo-sparc`, `ruflo-goals`, and the enabled local `sparc-methodology` skill provide structured decomposition before risky implementation starts;
- repository understanding: `analyze`, `route`, `swarm`, `memory`, `graph-navigator`, and `researcher` surfaces help map dependencies, change risk, and prior patterns before editing;
- implementation sequencing: `AGENTS.md`, `.agents/config.toml`, and `plugin/hooks/hooks.json` define routing, hook, and swarm patterns that can enforce disciplined execution order;
- workflow automation: `hooks`, `workflow`, `autopilot`, and `ruflo-workflows` can automate task routing and progress tracking once the plan is already correct;
- code and review quality: `analyze`, `ruflo-jujutsu`, `reviewer`, `architect`, `security-auditor`, and the local review skills are useful after a scoped ARES slice exists;
- testing confidence: `ruflo-testgen` and `tester` can identify test gaps, but they do not replace `pytest`, `scripts/verify_repo.py`, dashboard checks, or migration tests;
- production-readiness validation: `deployment`, `doctor`, `verify`, `ruflo-observability`, `ruflo-security-audit`, and `observability-engineer` can challenge readiness claims after deployment artifacts and operational surfaces exist;
- developer speed: `memory`, `route`, `swarm`, and hooks can reduce repeated rediscovery and coordination overhead in long-running multi-phase work;
- clutter reduction: `AGENTS.md` explicitly frames Ruflo as the orchestrator and Codex as the executor, which is the right boundary for avoiding speculative abstractions or duplicate systems in ARES.

Ruflo should not be used to claim product behavior, coverage, security, or deployability by itself. It is a forcing function around execution quality.

### Full Ruflo Inventory

#### Control docs, configs, manifests, and trust surfaces

| Item | Path | Purpose | When to use | When not to use | Required inputs | Expected outputs | Dependencies | Limitations | Related phase | Validation required |
|---|---|---|---|---|---|---|---|---|---|---|
| Ruflo overview | `ruflo-main/README.md` | High-level capability map, install modes, plugin catalog, and CLI entrypoints | Initial capability discovery and naming alignment | Deriving ARES behavior or repository facts | None beyond file access | Top-level workflow map | Node 20+, npm/npx assumptions in the doc | Marketing-level counts drift from local inventory | Phase 0 | Cross-check plugin and command claims against `verification-inventory.json` |
| Codex execution contract | `ruflo-main/AGENTS.md` | Defines Ruflo as orchestrator and Codex as executor | Before using Ruflo in this repo | When deciding whether ARES code itself is correct | None | Execution boundary, command patterns, memory/swarm workflow | Node/npx; Claude Flow lineage | Uses `claude-flow` naming rather than `ruflo`; examples are orchestration-only | Phases 0-4 | Validate every recommended action against the actual ARES task and file set |
| Local agent config guide | `ruflo-main/.agents/README.md` | Explains `.agents/config.toml` and `$skill-name` invocation | Before relying on local Ruflo skills | When reviewing ARES runtime behavior | None | Skill/config loading model | Local `.agents` tree | Guidance only | Phase 0 | Confirm actual enabled skills in `.agents/config.toml` |
| Active local agent config | `ruflo-main/.agents/config.toml` | Defines model, approval, sandbox, MCP server, enabled skills, security flags, and swarm defaults | Determining which local Ruflo skills and constraints are actually active | As proof that ARES is secure or production-ready | None | Concrete execution defaults | `npx -y @claude-flow/cli@latest`, local skills, MCP support | This config is for Ruflo/Codex integration, not ARES deployment | Phases 0-4 | Treat as workflow config only; verify resulting recommendations against ARES repo evidence |
| User guide | `ruflo-main/docs/USERGUIDE.md` | Broad reference for architecture, security, deployment, config, and usage | Clarifying ambiguous capability names or setup expectations | As a source of truth over local inventory/manifests when they conflict | None | Detailed reference material | Node ecosystem, providers, plugins | Version label (`v3.5`) lags local package version | Phases 0-4 | Prefer local manifest/inventory evidence where counts or versions conflict |
| Status report | `ruflo-main/docs/STATUS.md` | Snapshot of Ruflo test/verification status and capability counts | Gauging maturity of Ruflo itself | Claiming current ARES quality or exact Ruflo version | None | Stated verification posture | Ruflo test harness | Stale version string (`3.6.24`) | Phase 0 | Treat as indicative only; confirm capability counts from inventory |
| Capability manifest | `ruflo-main/verification-inventory.json` | Machine-readable inventory of CLI commands, plugins, MCP tools, and agents | Main source for enumerating Ruflo capabilities | As direct proof that any capability is correctly configured in this repo | None | Inventory of command/plugin/agent surfaces | JSON parser only | Inventory does not prove local runtime health | Phases 0-4 | Validate runtime-critical capabilities with `doctor`, `verify`, or direct command tests before use |
| Witness manifest | `ruflo-main/verification.md` | Signed/witnessed proof package for Ruflo artifacts and fixes | Understanding Ruflo's provenance and trust model | Claiming that ARES has equivalent witness guarantees | None | Provenance and fix traceability context | Signing/witness workflow | About Ruflo artifacts, not ARES | Phase 0 | Use only to judge Ruflo trust posture, not ARES readiness |
| Package manifest | `ruflo-main/package.json` | Actual local package name/version, scripts, entrypoints, and dependency footprint | Determining local version and executable surface | Mapping ARES architecture | Node/npm ecosystem | CLI/bin/scripts/dependency metadata | Node 20+, npm | Does not describe ARES usage policy by itself | Phase 0 | Use with `bin/cli.js` and inventory to confirm executable surface |
| CLI entrypoint | `ruflo-main/bin/cli.js` | Entry binary that forwards into the v3 CLI | Verifying the local binary path | As proof that every subcommand works in this environment | Node runtime | CLI entrypoint path | Local `v3` implementation | Thin wrapper only | Phase 0 | Pair with `doctor` or help output before operational use |
| Plugin manifest | `ruflo-main/plugin/.claude-plugin/plugin.json` | Declares plugin capabilities (skills, commands, hooks, agents, MCP) | Understanding plugin packaging and host integration | As proof that ARES should enable the plugin automatically | Plugin host support | Plugin capability declaration | Claude plugin host assumptions | Packaging metadata only | Phase 0 | Confirm the commands/hooks exist locally before relying on them |
| Hook routing config | `ruflo-main/plugin/hooks/hooks.json` | Maps prompt/tool/session events to Ruflo hook commands | Workflow automation and routing design review | Before the plan is stable or in fully manual execution | Prompt text, tool events, session events | Routed tasks, metrics capture, session restore prompts | `npx claude-flow@alpha hooks ...` | Hook automation can add noise if enabled too early | Phases 0-4 | Only act on hook output after checking affected ARES files/tests directly |

#### Local Ruflo skills shipped in the repo

| Item | Path | Purpose | When to use | When not to use | Required inputs | Expected outputs | Dependencies | Limitations | Related phase | Validation required |
|---|---|---|---|---|---|---|---|---|---|---|
| Swarm orchestration skill | `ruflo-main/.agents/skills/swarm-orchestration/SKILL.md` | Decides when cross-file or cross-module work should use swarm coordination | New features, 3+ file changes, API changes, schema/perf/security work | Single-file fixes, docs-only, or simple config edits | Task description and file scope | Swarm setup and routing recommendation | Ruflo MCP/CLI, `.agents/config.toml` | Orchestration only; does not implement | Phases 0-4 | Apply only if the ARES slice truly spans modules and merits the overhead |
| Memory management skill | `ruflo-main/.agents/skills/memory-management/SKILL.md` | Stores, searches, and reuses prior task patterns | Long-running multi-session ARES delivery | One-shot read-only audits or ephemeral experiments | Search terms, pattern keys, namespaces | Search hits, stored patterns, memory stats | Memory subsystem / AgentDB features | Can preserve stale assumptions if not curated | Phases 0-4 | Revalidate stored patterns against the current repo before reusing them |
| SPARC methodology skill | `ruflo-main/.agents/skills/sparc-methodology/SKILL.md` | Structured Specification, Pseudocode, Architecture, Refinement, Completion workflow | Major production phases, module-boundary changes, integration work | Small bug fixes or pure docs work | Problem statement, architecture context, quality bar | Decomposed implementation plan and checkpoints | Hooks routing, agent spawning | Can over-process simple work | Phases 0-4 | Use only for slices that genuinely need architecture-level decomposition |
| Security audit skill | `ruflo-main/.agents/skills/security-audit/SKILL.md` | Security scanning and threat review for auth, data, DB, API, file, and external integration work | After sensitive ARES changes are visible in code/config/docs | Before the change exists or for unrelated UI polish | Changed files, architecture context, threat surface | Security findings and checks | Security CLI/plugin surfaces | Findings are advisory until reproduced | Phases 1, 3, 4 | Reproduce every finding with ARES code, config, or runtime evidence |
| Code-quality analyzer agent skill | `ruflo-main/.agents/skills/agent-analyze-code-quality/SKILL.md` | Read-only quality analysis via a `code-analyzer` specialist | End-of-slice review, debt assessment, refactor targeting | As justification for speculative redesign | Code paths, review scope | Structured code-quality report | Read/Grep/Glob/WebSearch-capable host | Report-only and heuristic | Phases 1-4 | Check every finding against actual diffs and local tests |
| Migration planner agent skill | `ruflo-main/.agents/skills/agent-migration-plan/SKILL.md` | Migration-oriented planning agent | Planning larger migration or command-to-agent conversion style work | As a substitute for Alembic design, rollout testing, or rollback validation | Migration objective and constraints | Migration strategy notes | Ruflo agent host | Geared toward Ruflo workflows, only partially relevant to ARES | Phases 1, 3 | Validate all DB-impacting recommendations with ARES schema history and migration tests |
| CI/CD GitHub ops agent skill | `ruflo-main/.agents/skills/agent-ops-cicd-github/SKILL.md` | CI/CD and deployment workflow review agent | Workflow hardening and deployment planning once artifacts exist | Before deployment surfaces exist or for local-only backend coding | Pipeline scope, workflow files, deployment target | CI/CD findings and change plan | GitHub/CI context | Requires approval for workflow/secret changes; review-only in this phase | Phases 3-4 | Confirm every recommendation against `.github/workflows`, deployment assets, and rollback steps |

#### Ruflo CLI command families relevant to ARES

The machine-readable inventory exposes many commands. The relevant ARES-facing command families are below.

| Command family | Source | Purpose | When to use | When not to use | Inputs | Outputs | Dependencies | Limitations | Related phase | Validation required |
|---|---|---|---|---|---|---|---|---|---|---|
| `init`, `doctor`, `status`, `start`, `mcp`, `config`, `providers`, `session` | `ruflo-main/verification-inventory.json`, `bin/cli.js`, `package.json` | Ruflo environment bootstrap, diagnostics, and session control | Before depending on local Ruflo execution | As evidence of ARES correctness | Local Ruflo install/config | Health status and configured runtime | Node 20+, package install, provider config | Tooling bootstrap only | Phase 0 | Confirm diagnostic results locally before relying on later Ruflo steps |
| `analyze`, `route`, `swarm`, `agent`, `task`, `workflow`, `guidance`, `hive-mind` | same | Architecture analysis, task routing, swarm coordination, and workflow execution | Planning cross-module or multi-step ARES work | Small isolated patches | Repo/diff scope, task text | Task graph, risk classification, routed work plan | Swarm/router support | Coordination can exceed the value of the task | Phases 0-4 | Validate output against ARES module boundaries and roadmap priorities |
| `memory`, `agentdb_*`, `search`, `store`, `download`, `publish`, `list`, `info` | same | Pattern/memory retrieval and registry interactions | Reusing internal execution patterns or searching prior solutions | For final validation of ARES behavior | Queries, keys, namespaces | Search hits, stored patterns, memory records | AgentDB/memory features | Memory can be stale; registry is external | Phases 0-4 | Recheck every reused pattern in the current repo |
| `security`, `claims`, `aidefence_*` | same | Threat scanning, policy checks, AI/PII safety, and access-control analysis | Sensitive auth, audit, secret, ingestion, and deployment work | As a substitute for app-level auth tests and manual review | Diff/path set, input payloads, policies | Security findings and scans | Security plugin/tool support | Generated findings require reproduction | Phases 1, 3, 4 | Reproduce with code, tests, and runtime probes |
| `deployment`, `process`, `daemon`, `performance`, `benchmark`, `verify` | same | Deployment coordination, process control, profiling, benchmarking, and artifact verification | After deploy/process/observability artifacts exist | Before deployment assets or performance targets exist | Deployment target, process state, benchmark scope | Deploy/health/perf reports | Ruflo runtime, target environment | Does not prove ARES production readiness on its own | Phases 3-4 | Validate with staging deploys, health endpoints, rollback drills, and ARES perf tests |
| `autopilot`, `progress`, `cleanup` | same | Persistent completion loops, progress reporting, and artifact cleanup | Long multi-slice execution programs | Narrow hand-reviewed tasks where persistence adds risk | Task source and current state | Progress reports and re-engagement behavior | AgentDB/autopilot support | Can hide execution drift if overused | Phases 2-4 | Keep disabled unless the phase has explicit automation needs and review checkpoints |
| `migrate` | same | V2-to-V3 Ruflo migration tooling | Only for Ruflo itself if its internals block ARES usage | Any ARES schema or app migration work | Ruflo migration scope | Ruflo migration result | Ruflo internals | Not relevant to ARES schema changes | N/A | Do not map to ARES database migrations |

#### Ruflo plugins relevant to ARES

| Plugin | Path evidence | Purpose | When to use | When not to use | Required inputs | Expected outputs | Dependencies | Limitations | Related phase | Validation required |
|---|---|---|---|---|---|---|---|---|---|---|
| `ruflo-core` | `verification-inventory.json`, `README.md` | Base commands, hooks, and orchestration patterns | Any Ruflo usage in this repo | Never as a substitute for ARES validation | Repo/task context | Routed tasks and base orchestration | CLI/MCP runtime | Infrastructure only | Phases 0-4 | Validate against ARES evidence |
| `ruflo-sparc` | same | Structured implementation decomposition | Before complex ARES changes | Tiny slices | Problem statement, architecture scope | Stepwise implementation plan | SPARC workflow | Can add overhead | Phases 0-4 | Compare to actual module layout and acceptance criteria |
| `ruflo-swarm` | same | Team/swarm coordination and worktree isolation | Parallel, cross-cutting work | Single-threaded or tiny tasks | Task graph and scope | Coordinated task plan | Swarm/runtime support | Coordination overhead | Phases 0-4 | Use only when slice breadth justifies it |
| `ruflo-goals` | same | Long-horizon planning and adaptive replanning | Multi-phase roadmap execution | Short isolated tasks | Objectives, constraints | Goal graph and phased plan | Goal-planning runtime | Planning bias if constraints are weak | Phases 0-4 | Reconcile with this document before acting |
| `ruflo-jujutsu` | same | Diff analysis, risk scoring, reviewer recommendations | End-of-slice code review and merge prep | Before a scoped diff exists | Diff/branch scope | Risk and reviewer suggestions | Git state | Review support only | Phases 1-4 | Confirm against actual changed files and tests |
| `ruflo-security-audit` | same | Security review, dependency scanning, CVE monitoring, policy gates | Sensitive backend/deploy/auth changes | Before security-relevant code exists | Changed files, config, dependencies | Security findings and risk notes | Security tooling | Must not override manual review and tests | Phases 1, 3, 4 | Reproduce findings directly |
| `ruflo-aidefence` | same | PII and prompt-injection style scanning | Log, input, or support-surface review | Irrelevant to current surface | Payloads or prompts | Safety findings | AIDefence tooling | AI-safety oriented; not a full appsec suite | Phases 1, 3 | Reconcile with ARES data flows |
| `ruflo-docs` | same | Documentation generation and drift detection | Runbook, guide, API-client, and troubleshooting docs review | Before implementation exists | Diff, docs scope | Drift findings and draft doc updates | Docs tooling | Can mirror stale assumptions if source behavior is wrong | Phases 2-4 | Verify against shipped behavior and commands |
| `ruflo-migrations` | same | Migration generation, validation, dry-run, rollback review | ARES DB and schema planning | As a replacement for Alembic or migration tests | Schema objective and DB context | Migration plan and validation steps | Migration tooling | Planning/review aid only | Phases 1, 3 | Validate against `alembic/versions` and real DB runs |
| `ruflo-observability` | same | Structured logs, tracing, and metrics review | Alerting, tracing, and SLO work | Before observability surfaces exist | Telemetry scope and deployment context | Observability recommendations | Observability tooling | Not specific to ARES stack by itself | Phases 1, 3, 4 | Validate against actual metrics/traces/log sinks |
| `ruflo-testgen` | same | Test gap detection and generated test proposals | After implementation scope is defined | As a substitute for hand-reviewed test design | Diff/scope | Test gap list and generated tests/proposals | Testgen tooling | Generated tests can be noisy | Phases 1-4 | Keep only tests that improve ARES coverage meaningfully |
| `ruflo-browser` | same | Playwright-backed browser automation | Dashboard and docs workflow validation | Backend-only work or non-runnable UI | URL, flow, credentials if any | UI bug reports, screenshots, interaction evidence | Browser runtime | UI-only and environment-sensitive | Phases 2-4 | Validate against the running Streamlit/dashboard stack |
| `ruflo-ddd` | same | Bounded-context and domain-model mapping | Evaluator plugin, event workflow, and API-client design | Small local code changes | Domain scope and module map | Context and aggregate suggestions | DDD tooling | Can over-abstract a simple Python service | Phases 2, 4 | Accept only if it simplifies current ARES boundaries |
| `ruflo-adr` | same | Architecture Decision Record lifecycle support | Major deployment, rollback, or architecture decisions | Minor edits | Decision prompt and context | ADR suggestions or lifecycle updates | ADR workflow | Documentation support only | Phases 0, 3, 4 | Verify the decision against code and ops constraints |
| `ruflo-workflows` | same | Multi-step workflow orchestration and templates | Repeated delivery/release procedures | One-off local execution | Workflow definition | Workflow skeletons and runs | Workflow runtime | Can hide missing manual validation | Phases 2-4 | Pair with explicit tests and checklists |
| `ruflo-agentdb`, `ruflo-rag-memory`, `ruflo-knowledge-graph` | same | Memory, graph retrieval, and semantic recall | Long-running repo understanding and historical pattern recall | Single short task or privacy-sensitive contexts | Queries and indexing scope | Retrieved context and graph results | AgentDB/vector features | Retrieval is advisory, not truth | Phases 0-4 | Validate retrieved context against present files |
| `ruflo-autopilot` | same | Persistent completion loop with learning and progress tracking | Large, repetitive, bounded execution programs | High-risk slices needing human checkpoints | Task source and loop settings | Progress tracking and re-engagement | AgentDB/autopilot support | Over-automation risk | Phases 2-4 | Require explicit phase-level checkpoints before enabling |
| `ruflo-plugin-creator`, `ruflo-cost-tracker`, `ruflo-daa`, `ruflo-federation`, `ruflo-ruvector`, `ruflo-ruvllm`, `ruflo-rvf`, `ruflo-wasm` | same | General Ruflo ecosystem capabilities | Only if ARES execution later has a concrete need | Current roadmap execution | Plugin-specific inputs | Tooling-specific outputs | Varies | Evidence insufficient for current ARES need beyond inventory description | N/A | Do not add to ARES scope without a justified roadmap task |
| `ruflo-market-data`, `ruflo-neural-trader`, `ruflo-iot-cognitum` | same | Domain-specific trading/IoT capabilities | Not applicable to ARES based on current repository evidence | Current ARES implementation | Domain-specific | Domain-specific | Domain-specific runtimes | Not directly relevant | N/A | Do not use in this project unless the roadmap changes materially |

#### Ruflo agents relevant to ARES

| Agent | Path evidence | Purpose | When to use | When not to use | Required inputs | Expected outputs | Dependencies | Limitations | Related phase | Validation required |
|---|---|---|---|---|---|---|---|---|---|---|
| `architect`, `domain-modeler`, `adr-architect` | `verification-inventory.json` | Architecture and module-boundary review | Phase starts and major design changes | Small implementation details | Architecture scope and constraints | Design notes, boundary suggestions, ADR guidance | Agent runtime | Review/planning only | Phases 0, 2, 3, 4 | Confirm against the current ARES package layout and plan |
| `researcher`, `graph-navigator`, `deep-researcher` | same | Dependency and context discovery | Repository understanding and gap analysis | Final validation | Query and repo scope | Dependency map and evidence summary | Agent runtime, memory/graph features | Can surface stale or irrelevant context | Phases 0-4 | Check each result in the repo |
| `reviewer`, `git-specialist`, `coder` | same | Diff review, git-risk assessment, and implementation support | End-of-slice review and execution assistance | As sole validation | Diff, task scope | Findings, risk notes, implementation suggestions | Agent runtime | Must not replace local tests | Phases 1-4 | Validate findings with commands and tests |
| `tester`, `migration-engineer`, `observability-engineer`, `security-auditor`, `safety-specialist` | same | Test design, migration review, telemetry design, and security challenge | Backend/security/deploy slices after scope is concrete | Before relevant code/config exists | Diff, schema, telemetry, threat surface | Test plans, migration notes, security findings | Agent runtime and related plugins | Generated output can overfit generic patterns | Phases 1, 3, 4 | Reproduce every recommendation locally |
| `browser-agent`, `docs-writer`, `workflow-specialist`, `goal-planner`, `session-specialist`, `autopilot-coordinator` | same | UI review, docs review, workflow planning, long-horizon tracking, and context continuity | Dashboard, docs, release, and long-running execution work | Backend-only narrow bug fixes | Running app/docs/workflow or phase plan | UI findings, docs drift notes, workflow plans, progress state | Browser/docs/workflow runtime | Environment-sensitive; some surfaces are convenience only | Phases 2-4 | Validate against live app, docs, and release evidence |

#### Supporting scripts and processes

| Item | Path | Purpose | When to use | When not to use | Required inputs | Expected outputs | Dependencies | Limitations | Related phase | Validation required |
|---|---|---|---|---|---|---|---|---|---|---|
| Installer | `ruflo-main/scripts/install.sh` | Installs Ruflo and optional MCP/doctor setup | If Ruflo is not usable locally and the plan explicitly chooses to use it | During ARES app implementation by default | Install mode flags | Installed Ruflo environment | Shell, curl, Node/npm | Changes the local toolchain; not an ARES artifact | Phase 0 | Confirm install state with `doctor` before relying on it |
| Capability inventory generator | `ruflo-main/scripts/inventory-capabilities.mjs` | Rebuilds capability inventory | If the manifest appears stale and Ruflo itself needs verification | Normal ARES planning work | Local Ruflo source tree | Refreshed inventory JSON | Node toolchain | Tooling maintenance only | Phase 0 | Use only for Ruflo verification, not ARES scope expansion |
| Witness regeneration and signing | `ruflo-main/scripts/regenerate-witness.mjs`, `sign-witness-from-inventory.mjs` | Regenerates and signs Ruflo witness material | Only if Ruflo trust artifacts themselves need maintenance | Any ARES implementation work | Ruflo inventory and signing context | Updated witness files | Node/signing setup | Not relevant to ARES product changes | N/A | Do not treat as ARES validation |
| Appliance verification | `ruflo-main/scripts/verify-appliance.sh` | Verifies self-contained Ruflo artifacts | Only if using Ruflo appliance workflows | Standard ARES roadmap execution | Appliance target | Appliance verification result | Shell/runtime tooling | Not directly relevant to ARES | N/A | Not directly applicable |
| `verification.md` and witness workflow | `ruflo-main/verification.md` plus supporting scripts | Provenance process | Trust review of Ruflo itself | Any claim about ARES releases | Witness context | Trust evidence | Signing workflow | Tooling-only | Phase 0 | Keep separate from ARES release evidence |
| `v3/`, `plugins/`, `plugin/`, `.claude-plugin/`, `tests/`, `v2/`, `ruflo/` trees | directory inventory | Internal implementation, compatibility, packaging, and secondary product surfaces | Deep Ruflo debugging only if Ruflo blocks ARES execution | Current ARES implementation planning | Internal Ruflo source context | Ruflo internal implementation detail | Large Node codebase | Evidence insufficient for ARES relevance beyond inventory-level understanding | N/A | Do not expand ARES scope based on these internals without a concrete blocker |

### Ruflo Execution Order

1. Repository and plan understanding
   - Use: `README.md`, `AGENTS.md`, `.agents/config.toml`, `verification-inventory.json`
   - Input: current ARES repo state and `Production_grade_final_plan.md`
   - Expected output: exact Ruflo surfaces relevant to ARES
   - Validation: confirm each named surface exists locally and is relevant to the current phase
   - Approval: not required
2. Ruflo capability discovery
   - Use: `verification-inventory.json`, `package.json`, `bin/cli.js`, `docs/USERGUIDE.md`
   - Input: command/plugin/agent names needed for the phase
   - Expected output: verified command families, plugins, agents, and known setup drift
   - Validation: prefer inventory/manifests over stale marketing counts
   - Approval: not required
3. Architecture and dependency analysis
   - Use: `analyze`, `route`, `architect`, `researcher`, `graph-navigator`, `ruflo-sparc`
   - Input: affected ARES modules, phase objective, current gaps
   - Expected output: module map, risk notes, task decomposition
   - Validation: compare with actual ARES package structure, tests, and workflows
   - Approval: not required for analysis; required before acting on broad refactor advice
4. Gap validation against the production plan
   - Use: `ruflo-goals`, `sparc-methodology`, `memory`, optional `ruflo-adr`
   - Input: this production plan plus verified repo gaps
   - Expected output: narrowed next slice and explicit acceptance criteria
   - Validation: reject any recommendation that adds speculative scope
   - Approval: not required
5. Task decomposition
   - Use: `swarm-orchestration`, `swarm`, `agent`, `task`, `workflow`
   - Input: approved implementation slice
   - Expected output: execution order, task split, review checkpoints
   - Validation: ensure the slice breadth justifies orchestration overhead
   - Approval: required before enabling persistent/autonomous loops
6. Code-quality review
   - Use: `analyze`, `ruflo-jujutsu`, `reviewer`, `agent-analyze-code-quality`
   - Input: scoped diff and changed file set
   - Expected output: risk score, reviewer focus areas, code-quality findings
   - Validation: check findings against diffs, tests, and local runtime
   - Approval: not required for review
7. Security review
   - Use: `security-audit`, `ruflo-security-audit`, `security`, `claims`, `aidefence_*`, `security-auditor`
   - Input: changed auth/data/deploy surfaces
   - Expected output: reproducible security findings and mitigations
   - Validation: reproduce in ARES code/config/runtime before accepting
   - Approval: not required for review; required for any high-impact remediation outside current slice
8. Frontend/dashboard review, if supported
   - Use: `ruflo-browser`, `browser-agent`
   - Input: running dashboard URL and operator flows
   - Expected output: screenshots, repro steps, UI bug list
   - Validation: confirm findings against the live Streamlit stack
   - Approval: required before acting on browser-driven code changes if the task was previously read-only
9. Documentation/runbook review
   - Use: `ruflo-docs`, `docs-writer`, `workflow-specialist`
   - Input: implemented behavior, commands, ops steps
   - Expected output: drift findings, missing runbook steps, doc change plan
   - Validation: verify every step against shipped behavior
   - Approval: not required for review
10. Testing and QA planning
   - Use: `ruflo-testgen`, `tester`, `analyze`
   - Input: changed scope, current test coverage, known gaps
   - Expected output: concrete missing-test list and generated-test candidates
   - Validation: keep only tests that map to real ARES risks and pass local standards
   - Approval: not required for planning
11. CI/CD and deployment validation
   - Use: `agent-ops-cicd-github`, `deployment`, `doctor`, `process`, `ruflo-observability`, `observability-engineer`
   - Input: deployment artifacts, workflow files, health endpoints, SLO/alert plan
   - Expected output: deploy review notes, health checks, observability checklist
   - Validation: stage deploy, rollback drill, alert test, and runtime probe remain mandatory
   - Approval: required before any deployment-affecting action
12. Final production-readiness review
   - Use: `verify`, `reviewer`, `tester`, `security-auditor`, `docs-writer`, optional `goal-planner`
   - Input: release candidate state and evidence bundle
   - Expected output: final readiness findings and release decision support
   - Validation: final decision must come from ARES release criteria in this document
   - Approval: required for release

### Phase-by-Phase Ruflo Usage

| Phase | Ruflo tools/workflows to use | Why they are used | What they should produce | How output affects implementation | Validation required | What not to use Ruflo for in this phase |
|---|---|---|---|---|---|---|
| Phase 0 - Repository Re-Understanding and Planning Lock | `README.md`, `AGENTS.md`, `.agents/config.toml`, `verification-inventory.json`, `analyze`, `route`, `ruflo-sparc`, `ruflo-goals`, `researcher`, `graph-navigator`, `memory` | Build a verified capability map before implementation begins | Dependency map, task decomposition, phase risk list, validated Ruflo usage plan | Narrows the first implementation slice and prevents planning drift | Confirm every recommendation against actual ARES code, tests, docs, and workflows | Do not let Ruflo invent features, architecture, or maturity claims absent from the repo |
| Phase 1 - Critical Production Gaps | `sparc-methodology`, `swarm-orchestration`, `analyze`, `ruflo-migrations`, `ruflo-security-audit`, `security`, `claims`, `aidefence_*`, `migration-engineer`, `security-auditor`, `reviewer`, `ruflo-testgen` | Pressure-test high-risk backend, auth, rollback, ingestion, and alerting work | Migration plan, security findings, test-gap list, code review findings | Shapes implementation order and hardens risky slices before merge | Reproduce all findings with ARES migrations, tests, and runtime checks | Do not use Ruflo output as final proof of drift monitoring, rollback safety, or API-key correctness |
| Phase 2 - Product Completeness | `ruflo-ddd`, `ruflo-docs`, `ruflo-browser`, `browser-agent`, `ruflo-testgen`, `tester`, `docs-writer`, `reviewer`, optional `ruflo-workflows` | Support evaluator/plugin design, UX review, API-client docs, model-card and troubleshooting docs | Domain-boundary notes, UI bug list, test proposals, doc drift findings | Helps sequence UX/docs/test work after contracts stabilize | Validate against running dashboard flows, API contracts, and seeded test data | Do not use Ruflo to redesign the dashboard before APIs and data contracts settle |
| Phase 3 - Enterprise Production Readiness | `agent-ops-cicd-github`, `deployment`, `doctor`, `process`, `ruflo-observability`, `observability-engineer`, `ruflo-security-audit`, `security-auditor`, `ruflo-docs`, `docs-writer`, `ruflo-adr` | Review deployment, observability, backup/restore, SLO/SLA instrumentation, and operational documentation | Deployment review notes, observability checklist, security findings, ADRs, doc drift findings | Informs deployment hardening order and release readiness evidence | Validate with staging deploys, health probes, rollback drills, alert tests, and runbook walkthroughs | Do not treat Ruflo deployment or doctor output as a substitute for staged release evidence |
| Phase 4 - Top 0.01% Excellence | `ruflo-goals`, `ruflo-sparc`, `ruflo-ddd`, `ruflo-workflows`, `ruflo-testgen`, `tester`, `reviewer`, `ruflo-docs`, `ruflo-knowledge-graph`, optional `ruflo-browser` | Keep advanced work intentional, measurable, and aligned with the architecture | Advanced task decomposition, graph/context notes, test proposals, workflow sketches, release-candidate findings | Helps decide which excellence items are justified and which should stay deferred | Validate every advanced proposal against cost, complexity, and measurable benefit | Do not let Ruflo expand Phase 4 into speculative platform work unrelated to ARES outcomes |

Coverage notes for required review categories:

- repository understanding: directly supported by `analyze`, `researcher`, `graph-navigator`, `memory`, and the local skills;
- architecture analysis: directly supported by `architect`, `domain-modeler`, `ruflo-sparc`, `ruflo-ddd`, and `route`;
- planning: directly supported by `ruflo-goals`, SPARC, swarm/task/workflow routing, and ADR support;
- code review: directly supported by `reviewer`, `analyze`, `ruflo-jujutsu`, and the code-quality agent skill;
- security review: directly supported by `security`, `ruflo-security-audit`, `claims`, `aidefence_*`, and `security-auditor`;
- frontend/dashboard review: partially supported by `ruflo-browser` and `browser-agent`; final UI acceptance still depends on the live ARES dashboard;
- documentation/runbook work: directly supported by `ruflo-docs`, `docs-writer`, `workflow-specialist`;
- testing and QA planning: directly supported by `ruflo-testgen`, `tester`, and review/analysis surfaces;
- CI/CD validation: partially supported by `agent-ops-cicd-github`, `deployment`, `doctor`, and `process`;
- deployment planning: partially supported by `deployment`, `ruflo-observability`, ADR, and CI/CD review surfaces;
- performance/scalability review: partially supported by `benchmark` and `performance`, but ARES load testing and profiling remain authoritative;
- production-readiness verification: partially supported by `verify`, `doctor`, security, observability, docs, and review surfaces;
- final release validation: not directly supported by Ruflo alone; use Ruflo to challenge evidence, then rely on ARES release criteria, tests, lint, type checks, migration validation, and deployment evidence.

### Ruflo Usage Rules

- Do not use Ruflo blindly.
- Do not use Ruflo when repository evidence is stronger than generated analysis.
- Do not let Ruflo override actual tests, linting, type checks, migration runs, runtime probes, or security scans.
- Do not implement a Ruflo recommendation unless it maps to a task in this production plan.
- Do not introduce speculative abstractions, new orchestration layers, or duplicated systems based only on Ruflo output.
- Do not create duplicate systems if ARES already has an equivalent implementation or a simpler extension path.
- Do not modify files based only on Ruflo output without validating dependencies and blast radius first.
- Every Ruflo-generated recommendation must map to one of: a task, a test, a documented decision, a risk, a rollback step, or an acceptance criterion.
- Every major production change must have validation evidence.
- `autopilot`, persistent hooks, and broad swarm coordination are opt-in for ARES. They require a phase-specific reason and explicit operator judgment.
- Domain-specific Ruflo plugins (`ruflo-market-data`, `ruflo-neural-trader`, `ruflo-iot-cognitum`) are out of scope for ARES unless the project itself changes.

### Approval Gate

- First produce the analysis.
- Then update only `Production_grade_final_plan.md`.
- Do not touch any other file.
- Do not implement source code until explicit approval is given.
- After approval, implementation must happen in small, production-ready steps.
- Each step must use the correct Ruflo tools/workflows only where they materially help.
- Each step must still include tests, linting, type checks, and rollback notes.
- Ruflo output is planning and review input; ARES evidence is the merge and release gate.

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

Skills/tools to use: GStack repo understanding docs (`gstack-main/README.md`, `gstack-main/ARCHITECTURE.md`), `/office-hours`, `/plan-eng-review`, `/autoplan`, `/health`; optional external `graphify` refresh for ARES code topology.

Tests required: collection-only baseline and full `scripts/verify_repo.py` if local services are ready.

Documentation required: updated architecture map, risk register, dependency map.

Acceptance criteria:

- Every claimed completed feature is backed by a file path or test.
- Every missing feature has a priority, dependency, and definition of done.
- Current verification results are recorded with exact commands and dates.

Risks:

- Existing docs are partly stale.
- Existing coverage artifacts may not match current code.
- Graphify repo-wide graph includes noisy `skills/` and `gstack-main/` content; prefer scoped core ARES graph for implementation.

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
- Complete API key lifecycle operator surfaces, policy controls, and documentation on top of the existing expiration/rotation/usage-tracking primitives.
- Add basic alerting rules and alert delivery.
- Complete production-ready error taxonomy with remediation messages.

Implementation order:

1. Data model migrations for scheduler runs, production data sources, rollback records, any remaining API key policy fields, audit retention metadata, and alert events.
2. Drift ingestion interface and scheduler.
3. Error taxonomy and remediation payloads.
4. API key lifecycle surface completion.
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

Skills/tools to use: `/plan-eng-review`, `/review`, `/codex`, `/cso`, `/investigate`, `/guard`, `/careful`, `/document-release`.

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
- API key lifecycle guide covering TTL, rotation, revocation, audit visibility, and env-key compatibility.
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
- [ ] API key lifecycle operator surfaces completed and documented.
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

Skills/tools to use: `/plan-eng-review`, `/plan-design-review`, `/plan-devex-review`, `/browse`, `/qa`, `/qa-only`, `/design-review`, `/benchmark`, `/document-release`, `/review`.

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

Skills/tools to use: `/plan-eng-review`, `/cso`, `/devex-review`, `/setup-deploy`, `/land-and-deploy`, `/canary`, `/document-release`, `/review`.

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

Skills/tools to use: `/plan-ceo-review`, `/plan-eng-review`, `/review`, `/codex`, `/cso`, `/qa-only`, `/benchmark`, `/devex-review`, `/document-release`; optional external `graphify` for architecture explorer work.

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

- Problem: DB-backed API keys already support expiration, usage tracking, and rotation in the model/auth/CRUD layer, but the operator-facing lifecycle workflow is incomplete.
- Goal: Complete and operationalize the lifecycle controls rather than re-invent them.
- User/operator value: Safer long-running production deployments.
- Technical approach: preserve the existing schema/auth primitives, add any missing policy/config fields, and complete CLI/API/dashboard/admin/audit/documentation surfaces.
- Architecture impact: Auth becomes stateful and auditable.
- Files/modules likely affected: `ares/models/api_key.py`, `ares/db/crud_api_keys.py`, `ares/api/auth.py`, `scripts/manage_api_keys.py`, tests, docs.
- Data model changes: only additive policy or audit-support fields if the current schema is insufficient.
- API changes: optional admin endpoints for create, rotate, revoke, list.
- Dashboard/UI changes: key lifecycle admin page if dashboard admin scope is in product scope.
- Configuration changes: default TTL, max TTL, warning window.
- Security considerations: never return raw key after creation; hash using configured secret; update last-used without timing leaks.
- Observability requirements: auth failures, expired key attempts, rotation count, last-used updates.
- Tests required: expired key rejection, rotation overlap, revoke, env-key compatibility, DB precedence.
- Documentation required: key rotation guide.
- Step-by-step implementation sequence:
  1. Verify the existing `ApiKey` schema and CRUD/auth paths remain the source of truth.
  2. Add missing policy/config fields only if required.
  3. Update CLI.
  4. Add optional admin API endpoints.
  5. Add dashboard/admin surface if in scope.
  6. Add audit/metrics/docs.
  7. Add tests proving old behavior still works.
- Definition of done: Keys can be created, rotated, expired, revoked, audited, surfaced to operators, and tested without breaking env-key compatibility.

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
