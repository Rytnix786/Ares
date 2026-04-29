from __future__ import annotations

from pathlib import Path
from typing import Any

from ares.config import settings


def categorize_mlflow_error(exc: BaseException) -> str:
    message = str(exc).lower()
    if "connect" in message or "connection" in message or "timeout" in message:
        return "connection_error"
    if "permission" in message or "auth" in message or "forbidden" in message:
        return "auth_error"
    if "not found" in message or "404" in message:
        return "not_found"
    return "unknown_error"


class AresMlflowLogger:
    def __init__(self, experiment_name: str | None = None) -> None:
        self.experiment_name = experiment_name or settings.MLFLOW_EXPERIMENT
        self._mlflow: Any | None = None
        self.run_id: str | None = None
        self.artifact_uri: str | None = None

    def start_run(self, run_name: str) -> None:
        import mlflow

        self._mlflow = mlflow
        if settings.MLFLOW_TRACKING_URI:
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(self.experiment_name)
        active_run = mlflow.start_run(run_name=run_name)
        self.run_id = active_run.info.run_id
        self.artifact_uri = active_run.info.artifact_uri

    def log_params(self, params: dict[str, Any]) -> None:
        if self._mlflow is not None:
            self._mlflow.log_params({k: v for k, v in params.items() if isinstance(v, (str, int, float, bool))})

    def log_metrics(self, metrics: dict[str, float]) -> None:
        if self._mlflow is not None:
            self._mlflow.log_metrics({k: float(v) for k, v in metrics.items()})

    def log_artifact(self, path: str | Path, artifact_path: str | None = None) -> None:
        if self._mlflow is not None:
            self._mlflow.log_artifact(str(path), artifact_path=artifact_path)

    def end_run(self, status: str = "FINISHED") -> None:
        if self._mlflow is not None:
            self._mlflow.end_run(status=status)
