# Configuration Tuning Guide

ARES gate and drift thresholds should be tuned with historical evidence, not one-off anecdotes. This guide covers the configuration surfaces that affect Phase 2 workflows: evaluation gates, slice trends, model cards, dashboard refresh, API authentication, and plugin selection.

## Configuration sources

ARES settings are loaded from environment variables and `.env` through `ares.config.AresSettings`. Some operational tuning also comes from `ares.config.yaml` when present.

Common local stack defaults:

| Setting | Default | Why it matters |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://ares:ares@localhost:55432/ares` | Evaluation, champion, drift, audit, and alert persistence. |
| `ARES_API_URL` | `http://localhost:8000/api/v1` | CLI and dashboard API target. |
| `ARES_DASHBOARD_URL` | `http://localhost:8501` | Links from API/operator output to dashboard. |
| `ARES_API_KEYS` | empty in development | Comma-separated or JSON list of accepted env-backed API keys. |
| `ARES_API_KEY_SCOPES` | `{}` | Optional per-key scopes, for example `{"ops-key":["read","admin"]}`. |
| `RATE_LIMIT_EVALUATE` | `10/minute` | Protects evaluation submit endpoints. |
| `RATE_LIMIT_CHAMPION_MUTATION` | `20/minute` | Protects promotion/rollback endpoints. |
| `RATE_LIMIT_READ` | `120/minute` | Protects read-heavy API endpoints. |
| `SLICE_TREND_RETENTION_DAYS` | `365` | Retention horizon for normalized slice trend queries. |
| `GOLDEN_SET_VERSION` | `v1.0.0` | Default evidence version stamped into evaluations/model cards. |
| `GOLDEN_SET_REQUIRE_CHECKSUM` | `false` | Enforces production data contract checks when enabled. |
| `SLACK_WEBHOOK_URL` | empty | Enables Slack alert channel when configured. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | empty | Enables tracing export when configured. |

## Gate threshold tuning process

1. Review recent evaluation history in the dashboard leaderboard.
2. Compare candidate and champion runs through `/api/v1/evaluations/compare` or `AresClient.compare_evaluations`.
3. Inspect critical slice trends through `/api/v1/slices/trends` and the drift monitor.
4. Change one threshold family at a time.
5. Re-run representative evaluations.
6. Generate a model card for each changed threshold decision and archive it with release evidence.

Do not lower a critical-slice threshold just to pass a single candidate. If the same critical slice repeatedly fails, prefer model or data fixes over weaker governance.

## Slice trend retention

`SLICE_TREND_RETENTION_DAYS` controls how long normalized `slice_metric_points` remain queryable. Tune it by use case:

| Use case | Suggested value |
|---|---:|
| Local demos and CI fixtures | 30 |
| Active model operations | 180 to 365 |
| Regulated audit trail | 365 or longer, with database storage planning |

Longer retention improves trend context but increases query and storage cost. Keep high-cardinality slice names under control.

## API key and scope tuning

Development allows a permissive fallback key when no API keys are configured. Staging and production must configure keys.

Recommended pattern:

```bash
ARES_API_KEYS='ops-read,release-admin'
ARES_API_KEY_SCOPES='{"ops-read":["read"],"release-admin":["read","write","admin"]}'
```

Use managed API keys for rotation and expiration when possible. The dashboard and API client should use keys with the minimum scope needed for the workflow.

## Plugin tuning

Evaluator plugins are trusted code. Tune plugin behavior with these controls:

- Install only reviewed plugin packages.
- Prefer explicit plugin allowlists in deployment/package-management policy. ARES currently discovers installed `ares.evaluators` entry points and does not implement an in-app allowlist setting.
- Check `/api/v1/evaluators` after startup to verify the loaded evaluator name and version.
- Treat plugin load failures as release blockers when the plugin is required for a model family.

## Dashboard tuning

Dashboard behavior is controlled by API connectivity and Streamlit state:

- `ARES_API_URL` should point at the API origin or `/api/v1`; the dashboard strips `/api/v1` as needed.
- `ARES_API_KEY` or the first `ARES_API_KEYS` value supplies `X-API-Key`.
- Use the sidebar connection settings for local operator overrides during QA.
- Browser QA evidence is recorded in `docs/dashboard-qa-results.md` and screenshots in `docs/screenshots/`.

## Alert tuning

Use alert rules for operator signal, not noise:

- Start with conservative drift thresholds until enough production data is available.
- Route P0/P1 alerts to Slack or another on-call channel.
- Keep low-severity drift reports visible in the dashboard without paging humans.
- Test alert delivery from the dashboard Alerts page after changing channel configuration.

## Safe rollout checklist

Before committing a tuning change:

- [ ] Record the old and new value.
- [ ] Link the evaluation runs or drift reports that motivated the change.
- [ ] Re-run representative evaluations.
- [ ] Confirm model cards include the new evidence.
- [ ] Check dashboard pages load without console errors on in-app navigation.
- [ ] Run `python scripts/verify_repo.py` before release.
