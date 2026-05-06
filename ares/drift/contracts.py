from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ares.db import crud
from ares.drift_sources import LocalFileDataSource
from ares.exceptions import DatasetSchemaError

try:
    import boto3 as _boto3
except Exception:  # pragma: no cover - optional dependency in tests
    _boto3 = None

boto3 = _boto3

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


class S3DataSource:
    """Read prediction batches from an S3-compatible bucket prefix."""

    def __init__(self, *, bucket: str, prefix: str, endpoint_url: str | None = None, region_name: str | None = None) -> None:
        self.bucket = bucket.strip()
        self.prefix = prefix.strip().lstrip("/")
        self.endpoint_url = endpoint_url.strip() if endpoint_url else None
        self.region_name = region_name.strip() if region_name else None

    def _client(self) -> Any:
        if boto3 is None:
            raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": "boto3 is not installed"})
        client_kwargs: dict[str, Any] = {}
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        if self.region_name:
            client_kwargs["region_name"] = self.region_name
        return boto3.client("s3", **client_kwargs)

    @staticmethod
    def _frame_from_bytes(data: bytes, key: str) -> pd.DataFrame:
        suffix = Path(key).suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(io.BytesIO(data))
        if suffix == ".parquet":
            return pd.read_parquet(io.BytesIO(data))
        raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": f"unsupported object format: {key}"})

    def fetch_recent_predictions(self, model_name: str, hours: int = 24) -> pd.DataFrame:
        del hours
        if not self.bucket:
            raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": "missing S3 bucket"})
        if not self.prefix:
            raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": "missing S3 prefix"})

        client = self._client()
        response = client.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix)
        contents = response.get("Contents", []) or []
        keys = [str(item.get("Key", "")) for item in contents if item.get("Key")]
        if not keys:
            raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": "no matching prediction objects found"})

        preferred_keys = [key for key in keys if Path(key).name.startswith(model_name)]
        selected_keys = preferred_keys or [key for key in keys if Path(key).suffix.lower() in {".csv", ".parquet"}]
        if not selected_keys:
            raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": "no CSV or parquet prediction objects found"})

        frames: list[pd.DataFrame] = []
        for key in sorted(selected_keys):
            body = client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
            try:
                frames.append(self._frame_from_bytes(body, key))
            except DatasetSchemaError:
                raise
            except Exception as exc:
                raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": f"failed to load {key}: {exc}"}) from exc

        if not frames:
            raise DatasetSchemaError(details={"dataset_path": "production_predictions", "reason": "no readable prediction objects found"})
        return pd.concat(frames, ignore_index=True)


@dataclass(frozen=True)
class HttpPushDataSource:
    """Read a previously pushed prediction batch from the database."""

    db: AsyncSession
    source: str = "api_push"

    async def fetch_recent_predictions(self, model_name: str, hours: int = 24) -> pd.DataFrame:
        del hours
        persisted = await crud.latest_prediction_batch(self.db, model_name, source=self.source)
        if persisted is None:
            raise FileNotFoundError(f"no pushed prediction batch found for {model_name}")
        return validate_prediction_frame(pd.DataFrame(persisted.records), model_name=model_name)


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


def source_from_config(source_type: str, source_config: dict[str, Any], *, db_session: AsyncSession | None = None) -> Any:
    if source_type == "local_file":
        return LocalFileDataSource(str(source_config.get("path") or source_config.get("directory") or "data/sample_predictions"))
    if source_type in {"object_prefix", "object_store"}:
        return ObjectPrefixDataSource(str(source_config.get("prefix") or source_config.get("path") or ""))
    if source_type == "s3":
        return S3DataSource(
            bucket=str(source_config.get("bucket") or ""),
            prefix=str(source_config.get("prefix") or source_config.get("path") or ""),
            endpoint_url=source_config.get("endpoint_url") or source_config.get("endpoint"),
            region_name=source_config.get("region_name") or source_config.get("region"),
        )
    if source_type == "http_push":
        if db_session is None:
            raise ValueError("http_push sources require a db_session")
        return HttpPushDataSource(db_session, source=str(source_config.get("source") or source_type))
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
    if source_type in {"api_push", "http_push"}:
        source = source_from_config("http_push", source_config, db_session=db)
        frame = await source.fetch_recent_predictions(model_name, hours=hours)
        return DriftPredictionBatch(
            model_name=model_name,
            rows=len(frame),
            columns=[str(column) for column in frame.columns],
            data=frame,
            source_type=source_type,
            source_config={"source": getattr(source, "source", source_type), **source_config},
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
