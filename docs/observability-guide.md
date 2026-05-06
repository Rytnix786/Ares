# Observability Guide

ARES exposes Prometheus metrics at `/metrics`, emits request-correlated JSON logs, and ships starter
observability assets under `deploy/observability/`.

Primary sources:

- `ares/observability/metrics.py`
- `ares/logging.py`
- `ares/api/main.py`
- `deploy/observability/prometheus-rules.yaml`
- `deploy/observability/grafana-dashboard.json`
- `deploy/helm/ares/templates/observability-network.yaml`
- `deploy/helm/ares/values.yaml`

## Current Observability Surface

The current repo provides:

- custom Prometheus counters, gauges, and histograms in `ares/observability/metrics.py`
- HTTP metrics exposure at `/metrics` through `prometheus_fastapi_instrumentator`
- request ID propagation through `X-Request-ID`
- JSON log rendering with `structlog`
- a starter Prometheus alert rules file
- a starter Grafana dashboard JSON
- optional Helm `ServiceMonitor` rendering

The chart enables Prometheus scraping when:

- `serviceMonitor.enabled=true`

The `ServiceMonitor` template then scrapes:

- port `http`
- path `/metrics`
- interval from `serviceMonitor.interval`

## SLO Definitions

The repo does not enforce SLOs automatically today.
The targets below are operator guidance for a Phase 3 deployment using the metrics and alerts already present.

### Availability target

- target: 99.9% API availability over a rolling 30-day window
- primary signals: `/health/live`, `/health/ready`, `up`, and `http_requests_total`

### p99 latency budget

- target: p99 API latency under 1 second for normal read/write control-plane traffic
- primary signals: `http_request_duration_seconds_bucket` and `ares_evaluation_latency_seconds`

### Evaluation success rate

- target: at least 99% of persisted evaluation runs complete without internal execution failure
- primary signal: `ares_evaluation_runs_total{status=...}`

### Drift job success rate

- target: at least 99% of scheduled or manually triggered drift job runs complete successfully
- current repo limitation: there is no dedicated drift-job success metric in `ares/observability/metrics.py`, so operators must
  combine drift endpoints, alert events, and persisted drift job state until the metric surface is expanded

## Prometheus Metrics From `ares/observability/metrics.py`

The custom metric surface currently defined in code is:

### `ares_gate_decisions_total`

- type: Counter
- labels: `decision`
- purpose: count pass/fail gate decisions
- operator use: watch gate failure spikes and compare pass/fail ratios during candidate promotion windows

### `ares_evaluation_runs_total`

- type: Counter
- labels: `status`
- purpose: count evaluation runs by status
- operator use: track throughput and detect failure-rate changes in the evaluation pipeline

### `ares_evaluation_latency_seconds`

- type: Histogram
- labels: `model_name`
- purpose: observe evaluation runtime latency in seconds
- operator use: compare long-running evaluation patterns by model name

Important implementation note:

- the middleware currently also records API request timing into this histogram with label value `api_request`

### `ares_cache_operations_total`

- type: Counter
- labels: `operation`, `result`
- purpose: count cache gets/sets and their outcomes
- operator use: identify cache hit/miss or failure patterns if cache-backed paths are active

### `ares_active_requests`

- type: Gauge
- labels: none
- purpose: track in-flight API requests
- operator use: identify saturation or traffic bursts in real time

### `ares_drift_alerts_total`

- type: Counter
- labels: `severity`
- purpose: count emitted drift alerts by severity
- operator use: alert routing, breach trending, and incident review

### `ares_audit_write_failures_total`

- type: Counter
- labels: none
- purpose: count failed audit-log writes
- operator use: detect governance and traceability failures during mutations

### `ares_auth_failures_total`

- type: Counter
- labels: `reason`
- purpose: count authentication or authorization failures by reason
- operator use: detect invalid-key spikes, scope problems, or key-configuration outages

## HTTP Metrics Used by Alert Rules

The alert rules also rely on HTTP metrics that are not defined in `metrics.py` itself.
Those come from `prometheus_fastapi_instrumentator` and include:

- `http_requests_total`
- `http_request_duration_seconds_bucket`

Those metrics matter because:

- `AresApiHighErrorRate` uses `http_requests_total`
- the Grafana latency panel uses `http_request_duration_seconds_bucket`

## Alert Rules

The alert rule file is `deploy/observability/prometheus-rules.yaml`.
Each current rule is documented below with its actual expression, severity, and runbook annotation state.

### `AresApiHighErrorRate`

- condition:
  `sum(rate(http_requests_total{status=~"5.."}[5m])) / clamp_min(sum(rate(http_requests_total[5m])), 1) > 0.05`
- `for`: `10m`
- severity: `page`
- runbook link:
  `docs/runbooks/operator-incident-response.md#api-outage-or-high-error-rate`

### `AresApiNoTraffic`

- condition:
  `absent(up{job=~".*ares.*"} == 1)`
- `for`: `5m`
- severity: `page`
- runbook link:
  none in the current rule file

### `AresDriftAlertsFiring`

- condition:
  `increase(ares_drift_alerts_total[15m]) > 0`
- `for`: `0m`
- severity: `ticket`
- runbook link:
  `docs/runbooks/operator-incident-response.md#drift-alert`

### `AresGateFailuresSpike`

- condition:
  `increase(ares_gate_decisions_total{decision="fail"}[30m]) > 5`
- `for`: `5m`
- severity: `ticket`
- runbook link:
  none in the current rule file

### `AresAuditWriteFailures`

- condition:
  `increase(ares_audit_write_failures_total[10m]) > 0`
- `for`: `0m`
- severity: `page`
- runbook link:
  none in the current rule file

### `AresAuthFailuresSpike`

- condition:
  `increase(ares_auth_failures_total[10m]) > 20`
- `for`: `5m`
- severity: `ticket`
- runbook link:
  none in the current rule file

Operational note:

- only two of the current six rules carry explicit `runbook_url` annotations
- the remaining rules should be treated as observability debt until explicit runbook links are added

## Grafana Dashboard Navigation

The starter dashboard file is `deploy/observability/grafana-dashboard.json`.
It currently contains six panels.

### Panel 1: `Active Requests`

- type: stat
- query: `ares_active_requests`
- what it shows: current in-flight API requests

### Panel 2: `API Request Latency`

- type: timeseries
- query: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))`
- what it shows: rolling 95th percentile API latency from HTTP instrumentation

### Panel 3: `Gate Decisions`

- type: timeseries
- query: `sum(rate(ares_gate_decisions_total[5m])) by (decision)`
- what it shows: pass/fail decision rate over time

### Panel 4: `Evaluation Runs`

- type: timeseries
- query: `sum(rate(ares_evaluation_runs_total[5m])) by (status)`
- what it shows: evaluation throughput and status distribution

### Panel 5: `Drift Alerts`

- type: timeseries
- query: `increase(ares_drift_alerts_total[1h])`
- what it shows: drift-alert volume over the last hour

### Panel 6: `Auth Failures`

- type: timeseries
- query: `sum(rate(ares_auth_failures_total[5m]))`
- what it shows: aggregate authentication and authorization failure rate

Current dashboard limitation:

- the dashboard is a starter operational overview, not a full service, worker, DB, Redis, or drift-job deep-dive dashboard

## Log Structure

Structured logging is configured in `ares/logging.py`.

The renderer is:

- `structlog.processors.JSONRenderer()`

The configured processors add:

- merged contextvars
- log level
- ISO timestamp
- JSON output

### Fields currently visible in structured logs

For request-scoped log lines emitted through `structlog`, the reliable fields are:

- `event`
- `level`
- `timestamp`
- `request_id`

### How request IDs are propagated

`ares/api/main.py` assigns:

- request header `X-Request-ID` if present
- otherwise a generated UUID

That request ID is:

- stored in `request.state.request_id`
- returned in the response header `X-Request-ID`
- bound into log context by `MetricsMiddleware`

### Audit-related log behavior

The audit middleware does not emit the full audit row into stdout logs.
Instead:

- it writes audit records to the database
- it increments `ares_audit_write_failures_total` on failure
- it emits the warning event `audit_log_write_failed` if the write itself fails

### How to query logs operationally

Because the current logger renders JSON to stdout:

- use your container runtime or log shipper to collect stdout from the API, worker, scheduler, and dashboard
- pivot first on `request_id` for per-request tracing
- pivot on `event="audit_log_write_failed"` when audit persistence is failing

Current limitation:

- the repo does not ship a dedicated log aggregation query pack or vendor-specific log-search examples

## Staging Verification

The current repo already supports this minimal observability staging check:

1. install with `serviceMonitor.enabled=true`
2. confirm Prometheus scrapes `/metrics`
3. import `deploy/observability/grafana-dashboard.json`
4. trigger a known gate pass/fail and verify `ares_gate_decisions_total` changes
5. trigger a staging drift breach and verify alert routing receives the event

If you are checking the metric endpoint manually, use the already verified health-and-port-forward flow:

```bash
kubectl -n ares port-forward svc/ares-ares-api 8000:80
curl http://127.0.0.1:8000/metrics
```

## How to Add a New Metric

Follow the existing pattern in `ares/observability/metrics.py`.

### Step 1: Choose the metric type

The current file uses:

- `Counter`
- `Gauge`
- `Histogram`

### Step 2: Register through `_metric(...)`

New metrics should follow the existing helper pattern so duplicate registration failures during tests
fall back to `_NoopMetric` instead of crashing module import.

### Step 3: Keep labels low-cardinality

The existing docs guidance still applies:

- use labels like `status`, `decision`, `severity`, and `reason`
- do not use API keys, emails, raw payloads, or unbounded identifiers as labels

### Step 4: Emit from middleware or business logic

Examples already in the repo:

- auth failures increment `ares_auth_failures_total`
- audit write failures increment `ares_audit_write_failures_total`
- request timing is observed in middleware

### Step 5: Update alerting and dashboard assets

After adding a metric, update:

- `deploy/observability/prometheus-rules.yaml` if the metric should page or ticket
- `deploy/observability/grafana-dashboard.json` if operators need a panel for it
- this guide so the metric inventory stays complete

## Current Limitations

The observability surface is real but incomplete.
The main verified gaps are:

- no dedicated drift-job success metric in `metrics.py`
- only some alert rules include explicit runbook links
- the Grafana dashboard is intentionally small
- no log aggregation or trace query examples are shipped in the repo
- custom metrics cover key auth, audit, evaluation, gate, and drift signals, but not every infrastructure or business signal a full production rollout would eventually need

Use these gaps to drive future observability work, but do not hide them in the current operational docs.
