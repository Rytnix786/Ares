from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import scripts.run_drift_check as run_drift_check


@pytest.mark.asyncio
async def test_post_report_only() -> None:
    report_dict = {
        "model_name": "test-model",
        "feature": "confidence",
        "kl_divergence": 0.05,
        "psi": 0.08,
        "is_alerting": False,
        "severity": "none",
        "payload": {},
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "report-123"}
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        await run_drift_check.post_report_and_rollback(
            model_name="test-model",
            report_data=report_dict,
            predictions_dir="data",
            auto_rollback=True,
            post=True,
        )
        
        assert mock_post.call_count == 1
        url = mock_post.call_args_list[0][0][0]
        json_payload = mock_post.call_args_list[0][1]["json"]
        assert "drift/reports" in url
        assert json_payload["model_name"] == "test-model"
        assert json_payload["is_alerting"] is False


@pytest.mark.asyncio
async def test_post_report_and_trigger_rollback() -> None:
    report_dict = {
        "model_name": "test-model",
        "feature": "confidence",
        "kl_divergence": 0.35,
        "psi": 0.45,
        "is_alerting": True,
        "severity": "critical",
        "payload": {},
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        await run_drift_check.post_report_and_rollback(
            model_name="test-model",
            report_data=report_dict,
            predictions_dir="data",
            auto_rollback=True,
            post=True,
        )
        
        assert mock_post.call_count == 2
        
        url_report = mock_post.call_args_list[0][0][0]
        assert "drift/reports" in url_report
        
        url_rollback = mock_post.call_args_list[1][0][0]
        json_rollback = mock_post.call_args_list[1][1]["json"]
        assert "rollback" in url_rollback
        assert json_rollback["rolled_back_by"] == "drift_monitor"
        assert "Automated rollback triggered by drift alert" in json_rollback["reason"]
