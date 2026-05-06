# Slice Monitoring Guide

ARES normalizes per-run `slice_metrics` into `slice_metric_points` so operators can query critical slice trends without parsing evaluation JSON.

## Query trends

```bash
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/slices/trends?model_name=default-model&metric_name=f1"
```

Use `slice_name`, `metric_name`, and `limit` to bound queries. The default retention policy is controlled by `SLICE_TREND_RETENTION_DAYS`.

## Threshold hook

Passing `alert_threshold` on the trend query opens a deduplicated `slice_trend_threshold_breach` alert for critical slice points below the threshold.

```bash
curl -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/slices/trends?model_name=default-model&metric_name=f1&alert_threshold=0.8"
```

## Retention

Admins can purge old points:

```bash
curl -X DELETE -H "X-API-Key: $ARES_API_KEY" \
  "$ARES_API_ORIGIN/api/v1/slices/trends/retention?retention_days=365"
```
