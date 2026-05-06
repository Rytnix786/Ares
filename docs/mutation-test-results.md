# Mutation Test Results

Phase 4 configures `mutmut` in the development dependency set for advanced release hardening.

## Target scope

- `ares/gate/rules_engine.py`
- `ares/evaluators/`

## Command

```bash
python -m mutmut run --paths-to-mutate ares/gate/rules_engine.py,ares/evaluators
python -m mutmut results
```

## Baseline

Target mutation score: `> 70%`.

The baseline is release-gate controlled because mutation runs are slow and environment-sensitive. The normal verifier remains `python scripts/verify_repo.py`; mutation testing is an advanced Phase 4 gate for release candidates.
