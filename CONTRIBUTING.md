# Contributing

## Local setup on Windows

Run these commands from `H:\Projects\Ares`:

1. `copy .env.example .env`
2. `python -m venv .venv`
3. `.venv\Scripts\python -m pip install -e ".[dev,eval,dashboard]"`
4. `pre-commit install`
5. `docker compose up -d && python -m alembic upgrade head && python scripts/seed_champion.py`

The repository includes `make.cmd`, so `make <target>` works on Windows without GNU Make.

## Common commands

- `make build`
- `make build-pkg`
- `make lint`
- `make test-unit`
- `make test-integration`
- `make test-all`
- `make eval`
- `make verify`

`make verify` is the canonical local quality gate and matches the repository automation workflow.

## Add a new evaluator in under 50 lines

1. Create a class under `ares/evaluators/` that subclasses `BaseEvaluator`.
2. Implement `load_model()`, `predict()`, and `compute_metrics()`.
3. Add unit coverage for dataset validation, metric output, and slice behavior.

`BaseEvaluator` already handles shared dataset validation, latency measurement, and slice analysis.

## Add a new gate rule

1. Add the threshold to `ares.config.yaml` under `gate:`.
2. Update `ares/gate/rules_engine.py` where current tolerance checks are evaluated.
3. Document the rule in `README.md`.
4. Add unit tests for both pass and fail paths in `tests/unit/test_gate.py`.

## Docker and local overrides

You may create an untracked `docker-compose.override.yml` for local-only customization. Do not edit tracked compose files for personal machine setup.

## Pre-commit

Install hooks once with:

```bash
pre-commit install
```

Quarterly, review updates with `pre-commit autoupdate` before committing hook changes.

## PR checklist

- [ ] Tests added or updated
- [ ] Gate or evaluator behavior documented
- [ ] Migration included for schema changes
- [ ] Docker / CI impact reviewed
- [ ] README / docs updated when behavior changes
- [ ] Verification evidence included in the PR description

## Verification evidence requirement

Every substantive PR should include the exact commands run and outcomes. At minimum, capture:

- `make lint`
- `make test-unit`
- `make test-integration`
- `make test-all`
- `make verify`
