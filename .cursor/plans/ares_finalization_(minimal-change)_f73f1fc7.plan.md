---
name: Ares finalization (minimal-change)
overview: "Finalize Ares against your 10-step contract using a minimal-change, production-safe approach: generate a project structure graph (Graphify), close the remaining contract gaps (especially CI compose + env/service-name policy), and then execute the full verification / seed / gate / dashboard / test-artifact / security checklist with evidence outputs."
todos:
  - id: graphify-structure
    content: Generate `graphify-out/` artifacts and summarize Graph Report sections for architecture guidance.
    status: completed
  - id: compose-ci-parity
    content: Make `docker-compose.ci.yml` compliant with service naming + dependencies and ensure no localhost env leaks into containers.
    status: completed
  - id: env-contract
    content: Complete env contract keys and enforce container-safe overrides while preserving host-run localhost defaults.
    status: completed
  - id: verify-gates
    content: Ensure `make verify` and `make test-all` are strict and always emit required `reports/` artifacts.
    status: completed
  - id: seed-and-gate
    content: Run seed champion, evaluation gate, checksum pinning only if needed, and validate output schemas/artifacts.
    status: completed
  - id: dashboard-ux
    content: Apply ui-ux-pro-max-driven improvements to Streamlit dashboard without broad redesign.
    status: completed
  - id: security-and-report
    content: Run security grep audit and generate `COMPLETION_REPORT.md` with evidence for all checklist items.
    status: completed
isProject: false
---

# Ares Finalization Plan (minimal-change, production-safe)

## What I verified in the current repo (so we don’t redo work)
- **Compose (local)**: `docker-compose.yml` already includes the required topology and service-name wiring: `db`, `worker`, `mlflow`, `minio`, `minio-init`, `api`, `dashboard`, `redis`.
- **Seed champion**: `scripts/seed_champion.py` already exists and already trains `StandardScaler + LogisticRegression(random_state=42)` and promotes a champion.
- **Test artifacts**: `make test-all` already generates both `reports/coverage.xml` and `reports/test-results.xml` and does **not** suppress failures.
- **Golden checksums**: `ares.config.yaml` already contains 64-char SHA256 checksums for `train/val/test`.

## Real gaps I see that still matter for your contract
- **CI Compose mismatch**: `docker-compose.ci.yml` still uses a `postgres` service (not `db`) and the `api` service uses `env_file: .env.example`, which currently contains **localhost URLs** that are unsafe inside containers.
- **Env/service-name policy**: Defaults in `.env.example` and `ares/config.py` are localhost-based (good for host-run dev), but CI/containers must override to service names (`db`, `redis`, `mlflow`, `minio`, `api`, `dashboard`) consistently.
- **Graphify structure output**: there is currently **no** `graphify-out/` folder checked in or generated yet, so we need to generate it during execution.

## Workstreams & sub-agent split (for fast, low-risk changes)
- **Agent A — Graph & architecture map (non-blocking)**: attempt Graphify to produce `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.json`, then extract “God Nodes / Surprising Connections / Suggested Questions” to guide later steps. **If Graphify is unavailable or fails, log a warning and continue immediately** (Graphify is informational only and must not block Step 1).
- **Agent B — Compose contract (CI + local parity)**: make `docker-compose.ci.yml` match the naming + dependency contract from `docker-compose.yml` (minimal diff; no broad refactors). Include a **fast-fail healthcheck strategy** in CI compose.
- **Agent C — Env contract & service-name policy (enforced via compose overrides)**: keep localhost defaults for host-run dev, but ensure CI/compose services always inject container-safe service DNS names using explicit `environment:` blocks (not `env_file` alone).
- **Agent D — Verification gates & artifacts**: ensure `make verify` and `make test-all` meet strictness and always produce required artifacts in `reports/`.
- **Agent E — Dashboard UX (strict scope boundary)**: apply `ui-ux-pro-max` to the Streamlit dashboard (`dashboard/`) as *surgical improvements* (a11y, error states, polish) within a defined allowed-change set (below).

## Ordered execution (matches your 10 steps, with evidence checkpoints)

### Pre-flight (before Step 1)
- **Rollback safety (compose/env)**: before changing any compose/env files, create backups so we can instantly revert if local/dev stack regresses.\n+  - Backup files to create: `docker-compose.ci.yml.bak` (and if edited, `.env.example.bak`).\n+  - If a change breaks behavior, restore from `.bak` before deeper debugging.\n+\n+- **Graphify attempt (non-blocking)**: attempt to generate Graphify outputs (since `graphify-out/` is absent).\n+  - Outputs (if successful): `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/graph.json`.\n+  - Evidence (if successful): paste only the three requested sections from `GRAPH_REPORT.md` (God Nodes, Surprising Connections, Suggested Questions).\n+  - **Fallback**: if Graphify fails/unavailable, log a warning in the final report and proceed immediately to CI compose/env parity.\n+\n+- **Compose parity fix (CI) with explicit env overrides + healthchecks**: update `docker-compose.ci.yml` so container-to-container traffic never relies on `.env.example` localhost defaults.\n+  - **Enforcement mechanism (required)**: CI compose services must use explicit `environment:` blocks that override any `.env.example` values. Do **not** rely on `env_file: .env.example` alone.\n+    - Example shape (values adjusted to your service names):\n+      - `DATABASE_URL=postgresql+asyncpg://ares:ares@<db_service>:5432/<db_name>`\n+      - `REDIS_URL=redis://redis:6379/0`\n+      - `MLFLOW_TRACKING_URI=http://mlflow:5000` (only if MLflow runs in CI)\n+      - `AWS_ENDPOINT_URL=http://minio:9000` (only if MinIO runs in CI)\n+  - **Fast-fail healthchecks (required)**: add/standardize CI healthchecks with tighter settings (target: `interval: 5s`, `timeout: 5s`, `retries: 3` where reasonable) to avoid long hangs.\n+  - Evidence: `docker compose -f docker-compose.ci.yml config` shows correct service names and explicit env overrides (service-name URLs).\n+\n+- **Env contract completion**: ensure `.env.example` contains the required keys you listed (even if their values remain “host-run localhost defaults”), while CI correctness is enforced via compose `environment:` overrides.\n+  - Evidence: show final required key list plus the two-mode policy: **host-run defaults** vs **compose/CI overrides**.

### Step 1 — Full verification suite (`make verify`)
- Keep `make verify` strict (already strict today) and ensure it remains a single “exit non-zero on failure” gate.
- Evidence: final `make verify` exit code 0 and last lines showing ruff/mypy/pytest/docker compose config/dvc dry run.

### Step 2 — Seed baseline champion
- Use existing `scripts/seed_champion.py`; adjust only if it doesn’t meet your deterministic + DB registration expectations.
- Evidence: printed `run_id` plus a deterministic export file (plan: `reports/champion-export.json`) produced via the API.

### Step 3 — Pin golden checksums
- Confirm `scripts/pin_golden_checksums.py` aligns with `ares.config.yaml` format and enforces 64-char SHA256.
- Evidence: checksum verification output and `git log --oneline -3` after committing the checksum update (only if changes are needed).

### Step 4 — Simulate CI regression gate
- Run `scripts/run_evaluation.py` (or the `dvc.yaml` stage) against the seeded champion/candidate.
- Ensure output schema includes required fields (`passed`, `run_id`, `details_url`, `metric_table`) and fix only the schema emitter if missing.
- Evidence: `reports/ares_result.json` content.

### Step 5 — Full stack health verification
- Validate the API + dashboard + dependencies via their health endpoints.
- Evidence: HTTP 200s + response JSON checks for required shapes.

### Step 6 — Dashboard verification (Streamlit)
- **Scope boundary (do / don’t)**\n+  - Allowed changes:\n+    - Empty states + error states copy/layout\n+    - Connection status + retry UX (`dashboard/components/connection_status.py`)\n+    - Visual hierarchy (titles/headers), spacing, chart titles/labels/legends, and pass/fail color cues\n+    - Small usability affordances (loading spinners, expanders for error details)\n+  - Forbidden changes:\n+    - Page routing / page structure changes that alter navigation semantics\n+    - API client behavior/logic (`dashboard/api_client.py`) beyond presentation of errors\n+    - Authentication model, API key requirements, backend routes, or data fetching logic\n+\n+- Apply **UI/UX Pro Max** checks to `dashboard/` within the scope above:\n+  - accessibility: clearer headings/captions, readable typography, non-color-only indicators\n+  - interaction: better retry UX, clearer connection settings affordance\n+  - performance: avoid brittle reload loops if possible\n+\n+- Evidence (stronger than “it starts”):\n+  - Record exactly what changed and where (file list + bullets) in `dashboard/CHANGES.md` (or in the Step 6 section of `COMPLETION_REPORT.md`).\n+  - Run dashboard smoke checks after the change and capture outputs/screenshots/logs as feasible.

### Step 7 — Full test suite + artifacts
- Confirm `make test-all` is strict and produces both XML artifacts (already does).
- Add missing report directory creation if needed (only if test runner fails on fresh env).
- Evidence: presence of `reports/test-results.xml` and `reports/coverage.xml` + pytest summary.

### Step 8 — Critical business invariants
- Run `tests/unit/test_gate.py` (and add/repair only truly missing explicit assertions).
- Evidence: pytest `-v` output showing the 4 invariant behaviors passing.

### Step 9 — Security audit
- Run a grep-based audit (secrets, keys, tokens) and classify findings; ensure `.env` stays untracked and no key material is committed.
- Evidence: `reports/security-grep-raw.txt` line count + classification + git status checks.

### Step 10 — Completion report
- Produce `COMPLETION_REPORT.md` with all checklist items backed by concrete outputs (commands + files).\n+  - **Add section: “Changes by workstream”** that attributes each edited file to Agent A/B/C/D/E, with 1–2 bullets per file describing the intent.\n+- Evidence: the report itself, referencing the actual artifacts in `reports/` and the health outputs.

## Minimal-change principles (to keep your production project stable)
- Only touch contract-critical files first: `[docker-compose.ci.yml](docker-compose.ci.yml)`, `[.env.example](.env.example)`, and any CI workflows if needed.
- Avoid refactors across `ares/` unless a contract gate fails and the fix is localized.

## Key files that will be referenced/edited during execution
- Compose: `[docker-compose.yml](docker-compose.yml)`, `[docker-compose.ci.yml](docker-compose.ci.yml)`
- Env/config: `[.env.example](.env.example)`, `[ares/config.py](ares/config.py)`
- Verification: `[Makefile](Makefile)`, `[pyproject.toml](pyproject.toml)`
- CI: `[.github/workflows/regression_gate.yml](.github/workflows/regression_gate.yml)`
- Data/gates: `[ares.config.yaml](ares.config.yaml)`, `[dvc.yaml](dvc.yaml)`
- Dashboard: `[dashboard/app.py](dashboard/app.py)`, `[dashboard/api_client.py](dashboard/api_client.py)`
- Seeding: `[scripts/seed_champion.py](scripts/seed_champion.py)`
