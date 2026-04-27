# Contributing

## Local setup

1. `python -m venv .venv`
2. `. .venv/Scripts/activate`
3. `pip install -e ".[dev,eval]"`
4. `pre-commit install`

Quarterly, run `pre-commit autoupdate` and review pinned hook revisions before committing the updated config.

## Common commands

- `make lint`
- `make test`
- `make migrate`
- `make eval`
- `make verify`

## Evaluator extension workflow

New evaluators should subclass `BaseEvaluator` and implement only `load_model()`, `predict()`, and `compute_metrics()`. Any evaluator change must include unit coverage for required columns, metric output, and slice behavior.

## Gate rule extension workflow

New gate rules must be added to `ares.config.yaml`, documented in `README.md`, and covered with unit tests that demonstrate both pass and fail paths.

## Docker and local overrides

You may create an untracked `docker-compose.override.yml` for local port, volume, or environment customization. Do not edit tracked compose files for personal setup.

## PR checklist

- [ ] Tests added or updated
- [ ] Gate rule changes documented
- [ ] Migration included for schema changes
- [ ] Docker and CI impact reviewed
- [ ] README / docs updated when behavior changes