# Performance Baseline and Load Testing

ARES Phase 3 defines a repeatable staging smoke-load gate. The shipped scenario is `load/k6/ares-api-smoke.js`.

## SLO budgets

| Surface | Budget |
|---|---:|
| API read p95 latency under smoke load | `< 750 ms` |
| HTTP failure rate | `< 1%` |
| Ready endpoint availability during smoke | no 5xx |
| Core read endpoints during smoke | no 5xx |

## Run locally against staging

```bash
export ARES_BASE_URL=https://ares-staging.example.com
export ARES_API_KEY=staging-load-test-key
export ARES_LOAD_VUS=5
export ARES_LOAD_DURATION=1m
k6 run --summary-export reports/k6-summary.json load/k6/ares-api-smoke.js
python scripts/validate_k6_summary.py reports/k6-summary.json
```

Run this only against an isolated staging environment with test credentials and seeded non-sensitive data.

## CI gate

`.github/workflows/performance.yml` provides a manual `workflow_dispatch` gate for staging and validates the exported k6 summary with `scripts/validate_k6_summary.py`.

## Baseline evidence template

| Field | Value |
|---|---|
| Environment | staging namespace / cluster |
| Image tag | `<tag>` |
| DB size | `<rows / fixture>` |
| VUs / duration | `5 / 1m` |
| p95 latency | from `k6-summary.json` |
| failure rate | from `k6-summary.json` |
| Result | pass/fail against budgets |

## Tuning guidance

- If p95 exceeds budget, first inspect DB pool saturation, API CPU throttling, and dashboard/API pagination.
- If failures spike, inspect `/health/ready`, Redis/Postgres connectivity, and rate-limit configuration.
- Do not raise budgets without recording the dataset, traffic profile, and operator impact.
