# Mutation Test Results

Mutation testing is configured as a quality gate for the highest-value logic:

- `ares/gate/rules_engine.py`
- `ares/evaluators/`

## Tooling

`mutmut` was replaced with `cosmic-ray` because `mutmut` does not work on Windows natively and fails during stats collection in Linux containers.

## Repo Configuration

`cosmic-ray.toml` at repo root defines the mutation scope:

- `module-path = "ares"` (top-level package)
- `excluded-modules` filters out non-target modules (`ares.api`, `ares.cache`, `ares.cli`, etc.)
- `test-command` runs only the gate/evaluator unit and property suites
- `timeout = 60.0` seconds per mutation job
- `distributor.name = "local"` for single-node execution

The `--no-cov` flag in the test command is required because the repo-level pytest addopts enforce a global coverage gate that would make mutation runs fail for the wrong reason.

## Commands

Local or CI mutation runs use:

```bash
cosmic-ray init cosmic-ray.toml session.sqlite
cosmic-ray baseline --report cosmic-ray.toml session.sqlite
cosmic-ray exec cosmic-ray.toml session.sqlite
cr-report session.sqlite --show-pending
```

The GitHub Actions quality workflow runs the full sequence, pipes `cr-report` to `reports/mutmut-results.txt`, parses the kill rate, and fails when it drops below `80%`.

## Current Baseline

- Scope enforced by config: `ares/gate/rules_engine.py` and `ares/evaluators/`
- Required mutation score (kill rate): `>= 80%`
- Cross-platform: `cosmic-ray` works on Windows, macOS, and Linux without WSL

## Operational Notes

- `python scripts/verify_repo.py` remains the canonical functional verification gate.
- Mutation testing is additive; the `cosmic-ray` step runs after the standard test suite in CI.
