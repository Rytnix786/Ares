from __future__ import annotations

from typing import Any

import httpx


class AresClientError(RuntimeError):
    pass


class AresClient:
    """Typed-enough synchronous Python client for main ARES API workflows."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/api/v1"):
            self.base_url = self.base_url[: -len("/api/v1")]
        self._client = httpx.Client(base_url=self.base_url, headers={"X-API-Key": api_key}, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> AresClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        normalized = path if path.startswith(("/api/v1", "/health")) else f"/api/v1{path if path.startswith('/') else '/' + path}"
        response = self._client.request(method, normalized, **kwargs)
        if response.is_error:
            raise AresClientError(f"ARES API error {response.status_code}: {response.text}")
        return response.json()

    @classmethod
    def contract_paths(cls) -> dict[str, tuple[str, str]]:
        return {
            "authenticate": ("GET", "/health/ready"),
            "submit_evaluation": ("POST", "/api/v1/evaluate/compare"),
            "compare_evaluations": ("POST", "/api/v1/evaluations/compare"),
            "get_model_card": ("GET", "/api/v1/evaluations/{run_id}/model-card"),
            "poll_job_status": ("GET", "/api/v1/drift/jobs/{job_id}/runs"),
            "get_champion": ("GET", "/api/v1/champions/{model_name}"),
            "trigger_rollback": ("POST", "/api/v1/champions/{model_name}/rollback"),
            "query_drift_reports": ("GET", "/api/v1/drift/reports"),
            "list_api_keys": ("GET", "/api/v1/admin/api-keys"),
        }

    def authenticate(self) -> dict[str, Any]:
        return dict(self._request("GET", "/health/ready"))

    def submit_evaluation(self, model_name: str, commit_sha: str, metrics: dict[str, float], *, slice_metrics: dict[str, Any] | None = None, n_samples: int = 1) -> dict[str, Any]:
        return dict(self._request("POST", "/evaluate/compare", json={"model_name": model_name, "commit_sha": commit_sha, "new_metrics": metrics, "slice_metrics": slice_metrics or {}, "n_samples": n_samples}))

    def poll_job_status(self, job_id: str) -> list[dict[str, Any]]:
        return list(self._request("GET", f"/drift/jobs/{job_id}/runs"))

    def list_evaluations(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/evaluations/"))

    def get_evaluation(self, run_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/evaluations/{run_id}"))

    def compare_evaluations(self, run_ids: list[str]) -> dict[str, Any]:
        return dict(self._request("POST", "/evaluations/compare", json={"run_ids": run_ids}))

    def get_model_card(self, run_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/evaluations/{run_id}/model-card"))

    def list_evaluators(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/evaluators"))

    def slice_trends(self, **params: Any) -> list[dict[str, Any]]:
        return list(self._request("GET", "/slices/trends", params=params))

    def promote_champion(self, model_name: str, run_id: str, *, promoted_by: str = "client", reason: str | None = None) -> dict[str, Any]:
        return dict(self._request("POST", f"/champions/{model_name}/promote", json={"run_id": run_id, "promoted_by": promoted_by, "reason": reason}))

    def get_champion(self, model_name: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/champions/{model_name}"))

    def rollback_champion(self, model_name: str, *, reason: str, target_run_id: str | None = None, dry_run: bool = False, actor: str = "client") -> dict[str, Any]:
        return dict(self._request("POST", f"/champions/{model_name}/rollback", json={"rolled_back_by": actor, "reason": reason, "target_run_id": target_run_id, "dry_run": dry_run}))

    def list_drift_jobs(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/drift/jobs"))

    def query_drift_reports(self, model_name: str | None = None) -> list[dict[str, Any]]:
        params = {"model_name": model_name} if model_name else None
        return list(self._request("GET", "/drift/reports", params=params))

    def list_api_keys(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/admin/api-keys"))

    def list_alerts(self, status: str | None = None) -> list[dict[str, Any]]:
        params = {"status": status} if status else None
        return list(self._request("GET", "/alerts/events", params=params))
