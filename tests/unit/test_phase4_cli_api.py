from __future__ import annotations

import json

import pytest
from starlette.requests import Request

from ares.api.routers.gate import (
    ThresholdHistoricalRunPayload,
    ThresholdOptimizeRequest,
    optimize_gate_thresholds,
)
from ares.cli.thresholds import main as thresholds_main


def test_threshold_cli_writes_recommendation(tmp_path, monkeypatch) -> None:
    history = tmp_path / "history.json"
    output = tmp_path / "recommendation.json"
    history.write_text(
        json.dumps(
            [
                {
                    "candidate_metrics": {"overall_f1": 0.91, "overall_accuracy": 0.91},
                    "champion_metrics": {"overall_f1": 0.90, "overall_accuracy": 0.90},
                    "should_pass": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.argv", ["ares-optimize-thresholds", str(history), "--output", str(output)])

    assert thresholds_main() == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["recommended_config"]["max_regression_f1"] > 0


@pytest.mark.asyncio
async def test_threshold_optimize_api_endpoint_function() -> None:
    payload = ThresholdOptimizeRequest(
        historical_runs=[
            ThresholdHistoricalRunPayload(
                candidate_metrics={"overall_f1": 0.91, "overall_accuracy": 0.91},
                champion_metrics={"overall_f1": 0.90, "overall_accuracy": 0.90},
                should_pass=True,
            )
        ]
    )

    request = Request({"type": "http", "method": "POST", "path": "/api/v1/gate/optimize", "headers": []})
    result = await optimize_gate_thresholds(request, payload, object())

    assert result["evaluated_configs"] == 48
    assert result["recommended_config"]["max_regression_f1"] > 0
