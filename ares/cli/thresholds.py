from __future__ import annotations

import argparse
import json
from pathlib import Path

from ares.gate.threshold_optimizer import HistoricalRun, optimize_thresholds


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend ARES gate thresholds from historical runs.")
    parser.add_argument("history", type=Path, help="JSON list of historical run objects")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    raw = json.loads(args.history.read_text(encoding="utf-8"))
    runs = [
        HistoricalRun(
            candidate_metrics=item["candidate_metrics"],
            champion_metrics=item["champion_metrics"],
            should_pass=item.get("should_pass"),
            slice_metrics=item.get("slice_metrics"),
        )
        for item in raw
    ]
    recommendation = optimize_thresholds(runs)
    payload = {
        "recommended_config": recommendation.config,
        "pass_rate": recommendation.pass_rate,
        "expected_accuracy": recommendation.expected_accuracy,
        "false_pass_rate": recommendation.false_pass_rate,
        "false_fail_rate": recommendation.false_fail_rate,
        "evaluated_configs": recommendation.evaluated_configs,
    }
    text = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0
