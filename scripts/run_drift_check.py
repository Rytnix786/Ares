#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ares.config import load_ares_config
from ares.drift_sources import LocalFileDataSource
from ares.metrics.drift import compute_drift_report


def main() -> None:
    config = load_ares_config()
    predictions_dir = config.get("drift", {}).get("local_predictions_dir", "data/sample_predictions")
    source = LocalFileDataSource(predictions_dir)
    live = source.fetch_recent_predictions("default-model", hours=24)
    reference = pd.read_csv("data/golden_set/val.csv")
    report = compute_drift_report(
        "confidence",
        reference["difficulty"].to_numpy(dtype=float),
        live["confidence"].to_numpy(dtype=float),
        kl_threshold=float(config.get("drift", {}).get("kl_divergence_alert_threshold", 0.1)),
        psi_threshold=float(config.get("drift", {}).get("psi_alert_threshold", 0.2)),
    )
    Path("reports").mkdir(exist_ok=True)
    Path("reports/drift_report.json").write_text(json.dumps({**report.__dict__, "model_name": "default-model", "payload": {"source": predictions_dir}}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()