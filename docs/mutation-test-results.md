# Mutation Test Results

Mutation testing is now configured as a quality gate for the highest-value logic:

- `ares/gate/rules_engine.py`
- `ares/evaluators/`

## Repo Configuration

`pyproject.toml` now includes a `[tool.mutmut]` section with:

- `paths_to_mutate = ["ares/gate/rules_engine.py", "ares/evaluators"]`
- `tests_dir` is intentionally narrowed to the gate/evaluator unit and property suites that exercise the configured mutation targets
- `also_copy = ["ares", "dashboard", "ares.config.yaml"]`
- `pytest_add_cli_args = ["--no-cov"]`
- `mutate_only_covered_lines = true`

The `--no-cov` override is required because the repo-level pytest addopts enforce a global coverage gate that would make mutation runs fail for the wrong reason.

## Commands

Local or CI mutation runs use:

```bash
mutmut run
mutmut results --all
```

The GitHub Actions quality workflow captures `reports/mutmut-results.txt`, counts survived mutants, and fails when the mutation score drops below `80%`.

## Current Baseline

- Scope enforced by config: `ares/gate/rules_engine.py` and `ares/evaluators/`
- Required mutation score: `>= 80%`
- Local Windows limitation verified on 2026-05-07: native `mutmut` exits immediately and requires WSL or Linux
- Linux container verification on 2026-05-07: `mutmut run` successfully generated mutants for the configured scope, but the run failed later during `mutmut` stats collection before a final scored result was emitted

Observed native Windows result on this host:

```text
To run mutmut on Windows, please use the WSL. Native windows support is tracked in issue https://github.com/boxed/mutmut/issues/397
```

Observed Linux-container mutation attempt:

```text
done in 31860ms (9 files mutated, 0 ignored, 0 unmodified)
mutmut.__main__.BadTestExecutionCommandsException: Failed to run pytest ... during stats collection
```

## Operational Notes

- `python scripts/verify_repo.py` remains the canonical functional verification gate.
- Mutation testing is additive and intentionally Linux-oriented.
- The initial scored mutation baseline still needs a follow-up fix for the `mutmut` stats-collection phase in Linux before the 80% threshold can be enforced with a real score.
