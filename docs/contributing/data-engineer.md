# Data Engineer Guide

Data engineers connect production prediction sources for drift monitoring.

1. Follow the production prediction schema in `ares/drift/contracts.py`.
2. Use push ingestion or configured source adapters.
3. Validate timestamps, model names, predictions/confidence, and payload size.
4. Keep raw predictions out of logs.
5. Use slice metrics and `docs/slice-monitoring-guide.md` to expose subgroup regressions.
6. Verify drift jobs and alerts through the dashboard and API.
