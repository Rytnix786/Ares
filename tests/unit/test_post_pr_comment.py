from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import scripts.post_pr_comment as post_pr_comment


def test_build_markdown_comment_passes() -> None:
    payload = {
        "passed": True,
        "run_id": "run-xyz-123",
        "details_url": "http://localhost:8501/drill-down?run_id=run-xyz-123",
        "failure_reason": None,
        "decision_narrative": "Candidate F1 overall is 0.91, which improved from champion F1 0.89.",
        "metric_table": {
            "overall_f1": {
                "champion": 0.89,
                "candidate": 0.91,
                "delta": 0.02,
                "status": "improved",
            }
        },
        "slice_comparison": [
            {
                "slice": "critical",
                "is_critical": True,
                "champion_f1": 0.88,
                "candidate_f1": 0.90,
                "delta": 0.02,
                "status": "improved",
            }
        ],
    }

    markdown = post_pr_comment.build_markdown_comment(payload)
    
    assert "⚔️ ARES Model Regression Gate: 🟢 **PASS**" in markdown
    assert "[View Dashboard]" in markdown
    assert "overall_f1" in markdown
    assert "0.8900" in markdown
    assert "0.9100" in markdown
    assert "+0.0200" in markdown
    assert "✅ *Improved*" in markdown
    assert "critical" in markdown
    assert "⚠️ **Yes**" in markdown


def test_build_markdown_comment_fails() -> None:
    payload = {
        "passed": False,
        "run_id": "run-abc-456",
        "details_url": "http://localhost:8501/drill-down?run_id=run-abc-456",
        "failure_reason": "overall_f1 dropped below tolerance",
        "decision_narrative": "Candidate F1 overall is 0.82, which dropped below champion F1 0.89.",
        "metric_table": {
            "overall_f1": {
                "champion": 0.89,
                "candidate": 0.82,
                "delta": -0.07,
                "status": "regressed",
            }
        },
        "slice_comparison": [],
    }

    markdown = post_pr_comment.build_markdown_comment(payload)
    
    assert "⚔️ ARES Model Regression Gate: 🔴 **FAIL**" in markdown
    assert "overall_f1 dropped below tolerance" in markdown
    assert "❌ **Regressed**" in markdown


def test_post_to_github_success() -> None:
    mock_response = MagicMock()
    mock_response.status_code = 201
    
    with patch("httpx.post") as mock_post:
        mock_post.return_value = mock_response
        
        success = post_pr_comment.post_to_github(
            comment_body="test comment",
            repository="owner/repo",
            pr_number=42,
            token="test-token",
        )
        
        assert success is True
        mock_post.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/issues/42/comments",
            json={"body": "test comment"},
            headers={
                "Authorization": "token test-token",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )


def test_post_to_github_failure() -> None:
    with patch("httpx.post", side_effect=Exception("network error")) as mock_post:
        success = post_pr_comment.post_to_github(
            comment_body="test comment",
            repository="owner/repo",
            pr_number=42,
            token="test-token",
        )
        assert success is False
