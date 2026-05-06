# Dashboard Browser QA Results

Date: 2026-05-06
Phase: 2 browser-backed dashboard QA
Runtime: Docker Compose local stack
Dashboard URL: http://localhost:8501
Browser tool: gstack browse (`gstack-main/browse/dist/browse.exe`)

## Stack health

- `docker compose ps`: API, dashboard, db, redis, minio, mlflow all healthy; worker running.
- API health: `http://localhost:8000/health/live` reachable through Docker health check.
- Dashboard health: `http://localhost:8501/_stcore/health` healthy through Docker health check.
- GStack browser daemon: `Status: healthy`, mode `launched`.

## Numbered QA findings before fixes

1. Direct-loading Streamlit multipage URLs, for example `http://localhost:8501/leaderboard`, emits two console 404s for `/<page>/_stcore/health` and `/<page>/_stcore/host-config` before successfully falling back to root `/_stcore/health` and `/_stcore/host-config`.
   - Evidence: network capture showed `GET http://localhost:8501/leaderboard/_stcore/health -> 404`, `GET http://localhost:8501/leaderboard/_stcore/host-config -> 404`, followed by `GET http://localhost:8501/_stcore/health -> 200` and `GET http://localhost:8501/_stcore/host-config -> 200`.
   - Disposition: not fixed in Ares application code. This is documented Streamlit multipage expected behavior on direct subpage session start, not an Ares route or dashboard component bug. The supported in-app sidebar navigation path was re-tested and produced no console errors.
   - Upstream reference checked: Streamlit forum thread "Setting up 'health' and 'host-config' for a multipage app", where Streamlit maintainers describe this as expected behavior when a session starts from a subpage.

## Pages tested

| Page | URL / Navigation | Result | Screenshot |
|---|---|---|---|
| Home | `http://localhost:8501` | Loads, data summary visible, no console errors | `docs/screenshots/dashboard-home.png` |
| Leaderboard | Sidebar link from home | Loads seeded run and filters, no console errors | `docs/screenshots/dashboard-leaderboard.png` |
| Drill down | Sidebar link | Loads useful empty state, no console errors | `docs/screenshots/dashboard-drill-down.png` |
| Drift monitor | Sidebar link | Loads useful empty state, no console errors | `docs/screenshots/dashboard-drift-monitor.png` |
| Model comparison | Sidebar link | Loads comparison widgets and charts, no console errors | `docs/screenshots/dashboard-model-comparison.png` |
| Promotion workflow | Sidebar link | Loads tabs and empty states, no console errors | `docs/screenshots/dashboard-promotion-workflow.png` |
| Alerts | Sidebar link | Loads alert rules/channels/history/test sections, no console errors | `docs/screenshots/dashboard-alerts.png` |

## Final QA-only pass

Final in-app navigation pass cleared console/network buffers, entered from `http://localhost:8501`, and used sidebar navigation. Result: no console errors on the supported operator navigation path for tested pages.

## Render cost / benchmark baseline

Initial cold home page measurement from `browse perf`:

| Metric | Value |
|---|---:|
| DNS | 3 ms |
| TCP | 14 ms |
| SSL | 0 ms |
| TTFB | 17 ms |
| Download | 34 ms |
| DOM parse | 356 ms |
| DOM ready | 1091 ms |
| Load | 1132 ms |
| Total | 1132 ms |

Warm final pass page totals from `browse perf`:

| Page | Total |
|---|---:|
| Home | 71 ms |
| Leaderboard | 36 ms |
| Drill down | 28 ms |
| Drift monitor | 25 ms |
| Model comparison | 25 ms |
| Promotion workflow | 26 ms |
| Alerts | 24 ms |

## Open app bugs after QA

Zero Ares dashboard application bugs remain open from this QA pass. The only browser console finding is Streamlit upstream expected behavior for direct subpage loads and is documented above.
