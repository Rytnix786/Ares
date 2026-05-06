# Observability Guide

ARES exposes Prometheus metrics at `/metrics` and ships starter production assets:

- `deploy/observability/prometheus-rules.yaml`
- `deploy/observability/grafana-dashboard.json`
- Helm `serviceMonitor.enabled=true` support

## Alert map

| Alert | Signal | Primary runbook |
|---|---|---|
| `AresApiHighErrorRate` | API 5xx ratio over 5% for 10 minutes | API outage/high error rate |
| `AresApiNoTraffic` | Metrics target missing | API outage/high error rate |
| `AresDriftAlertsFiring` | Drift alerts emitted | Drift alert |
| `AresGateFailuresSpike` | Gate failures spike | Failed gate / bad candidate |
| `AresAuditWriteFailures` | Audit writes fail | Security/audit incident |
| `AresAuthFailuresSpike` | Auth failures spike | Key compromise |

## Metric labels

Keep labels low-cardinality. Use status, decision, severity, and reason. Do not use API keys, raw model paths, user emails, payload hashes, or unbounded slice names as Prometheus labels.

## Staging check

1. Install with `serviceMonitor.enabled=true`.
2. Confirm Prometheus scrapes `/metrics`.
3. Import `grafana-dashboard.json`.
4. Trigger a known gate pass/fail and verify `ares_gate_decisions_total` moves.
5. Trigger a staging drift breach and verify alert routing reaches the configured receiver.
