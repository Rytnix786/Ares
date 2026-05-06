from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ares.db import crud
from ares.drift_sources import LocalFileDataSource
from ares.exceptions import DatasetSchemaError

REQUIRED_PREDICTION_COLUMNS = {"timestamp", "model_name"}


class ProductionPredictionSource(Protocol):
    def fetch_recent_predictions(self, model_name: str, hours: int = 24) -> pd.DataFrame: ...


@dataclass(frozen=True)
class DriftPredictionBatch:
    model_name: str
    rows: int
    columns: list[str]
    data: pd.DataFrame
    source_type: str
    source_config: dict[str, Any]


class ObjectPrefixDataSource:
    """Read production prediction CSVs from a local or fsspec-compatible object prefix."""

    def __init__(self, prefix: str) -> None:
        self.prefix = prefix

    def fetch_recent_predictions(self, model_name: str, hours: int = 24) -> pd.DataFrame:
        del hours
        prefix_path = Path(self.prefix)
        if prefix_path.exists():
            frames = [pd.read_csv(path) for path in sorted(prefix_path.glob(f"{model_name}*.csv"))]
            if not frames:
                raise FileNotFoundError(f"no prediction CSV files for {model_name} under {self.prefix}")
            return pd.concat(frames, ignore_index=True)
        return pd.read_csv(self.prefix)


def validate_prediction_frame(frame: pd.DataFrame, *, model_name: str) -> pd.DataFrame:
    missing = REQUIRED_PREDICTION_COLUMNS - set(frame.columns)
    if missing:
        raise DatasetSchemaError(
            missing_columns=sorted(missing),
            details={"dataset_path": "production_predictions"},
        )
    invalid_model_rows = frame[frame["model_name"].astype(str) != model_name]
    if not invalid_model_rows.empty:
        raise DatasetSchemaError(
            missing_columns=[],
            details={"dataset_path": "production_predictions", "reason": "payload contains rows for a different model", "model_name": model_name},
        )
    if "confidence" not in frame.columns and "prediction" not in frame.columns:
        raise DatasetSchemaError(
            missing_columns=["confidence or prediction"],
            details={"dataset_path": "production_predictions"},
        )
    return frame.copy()


def source_from_config(source_type: str, source_config: dict[str, Any]) -> ProductionPredictionSource:
    if source_type == "local_file":
        return LocalFileDataSource(str(source_config.get("path") or source_config.get("directory") or "data/sample_predictions"))  # type: ignore[return-value]
    if source_type in {"object_prefix", "object_store"}:
        return ObjectPrefixDataSource(str(source_config.get("prefix") or source_config.get("path") or ""))
    raise ValueError(f"unsupported production prediction source type: {source_type}")


def load_prediction_batch(model_name: str, source_type: str, source_config: dict[str, Any], *, hours: int = 24) -> DriftPredictionBatch:
    source = source_from_config(source_type, source_config)
    frame = validate_prediction_frame(source.fetch_recent_predictions(model_name, hours=hours), model_name=model_name)
    return DriftPredictionBatch(
        model_name=model_name,
        rows=len(frame),
        columns=[str(column) for column in frame.columns],
        data=frame,
        source_type=source_type,
        source_config=source_config,
    )


async def load_prediction_batch_async(
    db: AsyncSession,
    model_name: str,
    source_type: str,
    source_config: dict[str, Any],
    *,
    hours: int = 24,
) -> DriftPredictionBatch:
    if source_type == "api_push":
        persisted = await crud.latest_prediction_batch(db, model_name, source=str(source_config.get("source", "api_push")))
        if persisted is None:
            raise FileNotFoundError(f"no pushed prediction batch found for {model_name}")
        frame = validate_prediction_frame(pd.DataFrame(persisted.records), model_name=model_name)
        return DriftPredictionBatch(
            model_name=model_name,
            rows=len(frame),
            columns=[str(column) for column in frame.columns],
            data=frame,
            source_type="api_push",
            source_config={"batch_id": persisted.id, **source_config},
        )
    return load_prediction_batch(model_name, source_type, source_config, hours=hours)


async def ingest_prediction_payload(
    db: AsyncSession,
    *,
    model_name: str,
    records: list[dict[str, Any]],
    source: str = "api_push",
) -> DriftPredictionBatch:
    frame = validate_prediction_frame(pd.DataFrame(records), model_name=model_name)
    await crud.create_prediction_batch(
        db,
        model_name=model_name,
        source=source,
        rows=len(frame),
        columns=[str(column) for column in frame.columns],
        records=frame.to_dict(orient="records"),
    )
    return DriftPredictionBatch(
        model_name=model_name,
        rows=len(frame),
        columns=[str(column) for column in frame.columns],
        data=frame,
        source_type=source,
        source_config={"source": source},
    )
