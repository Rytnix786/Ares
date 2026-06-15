#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from ares.config import load_ares_config, settings
from ares.drift_sources import LocalFileDataSource
from ares.metrics.drift import compute_drift_report


async def post_report_and_rollback(
    model_name: str,
    report_data: dict[str, Any],
    predictions_dir: str,
    auto_rollback: bool,
    post: bool,
) -> None:
    headers = {"X-API-Key": settings.ARES_API_KEYS[0]} if settings.ARES_API_KEYS else {}
    
    # Post the report if requested
    if post:
        print(f"Posting drift report for model '{model_name}' to API...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{settings.ARES_API_URL}/drift/reports",
                    json=report_data,
                    headers=headers,
                )
                res.raise_for_status()
                print("Drift report successfully posted.")
        except Exception as e:
            print(f"Error posting drift report: {e}")
            
    # Automated rollback if alerting and requested
    if auto_rollback and report_data.get("is_alerting"):
        kl = report_data["kl_divergence"]
        psi = report_data["psi"]
        reason = f"Automated rollback triggered by drift alert: kl_divergence={kl:.4f}, psi={psi:.4f}"
        print(f"ALERT: Drift detected on model '{model_name}'. {reason}")
        print("Executing automated rollback...")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{settings.ARES_API_URL}/champions/{model_name}/rollback",
                    json={
                        "rolled_back_by": "drift_monitor",
                        "reason": reason,
                        "dry_run": False,
                    },
                    headers=headers,
                )
                res.raise_for_status()
                rollback_res = res.json()
                print("Automated rollback executed successfully:")
                print(json.dumps(rollback_res, indent=2))
        except Exception as e:
            print(f"Error executing automated rollback: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run drift check and automated rollback")
    parser.add_argument("--model-name", default="default-model", help="Model name to evaluate")
    parser.add_argument("--predictions-dir", help="Directory where predictions are stored")
    parser.add_argument("--post", action="store_true", help="Post the drift report to the API")
    parser.add_argument("--auto-rollback", action="store_true", help="Automatically trigger rollback on drift alert")
    args = parser.parse_args()

    config = load_ares_config()
    predictions_dir = args.predictions_dir or config.get("drift", {}).get("local_predictions_dir", "data/sample_predictions")
    source = LocalFileDataSource(predictions_dir)
    live = source.fetch_recent_predictions(args.model_name, hours=24)
    reference = pd.read_csv("data/golden_set/val.csv")
    report = compute_drift_report(
        "confidence",
        reference["difficulty"].to_numpy(dtype=float),
        live["confidence"].to_numpy(dtype=float),
        kl_threshold=float(config.get("drift", {}).get("kl_divergence_alert_threshold", 0.1)),
        psi_threshold=float(config.get("drift", {}).get("psi_alert_threshold", 0.2)),
    )
    
    report_dict = {
        "model_name": args.model_name,
        "feature": report.feature,
        "kl_divergence": report.kl_divergence,
        "psi": report.psi,
        "is_alerting": report.is_alerting,
        "severity": report.severity,
        "payload": {"source": predictions_dir},
    }

    Path("reports").mkdir(exist_ok=True)
    Path("reports/drift_report.json").write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
    print("Drift report written to reports/drift_report.json")

    # Run async API calls
    if args.post or args.auto_rollback:
        asyncio.run(post_report_and_rollback(args.model_name, report_dict, predictions_dir, args.auto_rollback, args.post))


if __name__ == "__main__":
    main()