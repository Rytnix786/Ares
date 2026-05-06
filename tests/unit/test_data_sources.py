from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import pandas as pd
import pytest

from ares.drift.contracts import (
    HttpPushDataSource,
    S3DataSource,
    load_prediction_batch_async,
    source_from_config,
)
from ares.exceptions import DatasetSchemaError


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


@dataclass
class _Body:
    payload: bytes

    def read(self) -> bytes:
        return self.payload


class _S3Client:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.list_calls: list[tuple[str, str]] = []
        self.get_calls: list[str] = []

    def list_objects_v2(self, *, Bucket: str, Prefix: str) -> dict[str, list[dict[str, str]]]:
        self.list_calls.append((Bucket, Prefix))
        return {"Contents": [{"Key": key} for key in sorted(self.objects)]}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, _Body]:
        del Bucket
        self.get_calls.append(Key)
        return {"Body": _Body(self.objects[Key])}


@pytest.mark.asyncio
async def test_http_push_data_source_reads_latest_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        [{"id": 1, "timestamp": "2026-05-06T00:00:00Z", "model_name": "demo", "confidence": 0.9, "prediction": 1}]
    )

    @dataclass
    class _Batch:
        records: list[dict[str, object]]

    async def fake_latest_prediction_batch(_db: object, model_name: str, source: str | None = None) -> _Batch | None:
        assert model_name == "demo"
        assert source == "api_push"
        return _Batch(records=frame.to_dict(orient="records"))

    from ares.db import crud

    monkeypatch.setattr(crud, "latest_prediction_batch", fake_latest_prediction_batch)

    source = HttpPushDataSource(db=object())
    result = await source.fetch_recent_predictions("demo")

    assert result.equals(frame)


def test_s3_data_source_loads_csv_and_parquet(monkeypatch: pytest.MonkeyPatch) -> None:
    csv_frame = pd.DataFrame(
        [{"id": "1", "timestamp": "2026-05-06T00:00:00Z", "model_name": "demo", "confidence": 0.8, "prediction": 1}]
    )
    parquet_frame = pd.DataFrame(
        [{"id": "2", "timestamp": "2026-05-06T01:00:00Z", "model_name": "demo", "confidence": 0.7, "prediction": 0}]
    )
    client = _S3Client(
        {
            "live/demo/batch-a.csv": csv_frame.to_csv(index=False).encode("utf-8"),
            "live/demo/batch-b.parquet": _parquet_bytes(parquet_frame),
        }
    )

    class _Boto3:
        def client(self, *_args: object, **_kwargs: object) -> _S3Client:
            return client

    from ares.drift import contracts

    monkeypatch.setattr(contracts, "boto3", _Boto3())

    source = S3DataSource(bucket="demo-bucket", prefix="live/demo", endpoint_url="https://example.test")
    result = source.fetch_recent_predictions("demo")

    assert len(result) == 2
    assert client.list_calls == [("demo-bucket", "live/demo")]
    assert client.get_calls == ["live/demo/batch-a.csv", "live/demo/batch-b.parquet"]


def test_s3_data_source_rejects_missing_bucket() -> None:
    source = S3DataSource(bucket="", prefix="live/demo")

    with pytest.raises(DatasetSchemaError):
        source.fetch_recent_predictions("demo")


def test_s3_data_source_rejects_empty_prefix() -> None:
    source = S3DataSource(bucket="demo-bucket", prefix="")

    with pytest.raises(DatasetSchemaError):
        source.fetch_recent_predictions("demo")


def test_s3_data_source_rejects_unknown_object_format(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _S3Client({"live/demo/batch-a.txt": b"not-a-table"})

    class _Boto3:
        def client(self, *_args: object, **_kwargs: object) -> _S3Client:
            return client

    from ares.drift import contracts

    monkeypatch.setattr(contracts, "boto3", _Boto3())

    source = S3DataSource(bucket="demo-bucket", prefix="live/demo")

    with pytest.raises(DatasetSchemaError):
        source.fetch_recent_predictions("demo")


def test_source_from_config_supports_s3_and_http_push() -> None:
    s3_source = source_from_config("s3", {"bucket": "demo", "prefix": "live/demo"})
    assert isinstance(s3_source, S3DataSource)

    fake_db = object()
    http_push_source = source_from_config("http_push", {"source": "api_push"}, db_session=fake_db)  # type: ignore[arg-type]
    assert isinstance(http_push_source, HttpPushDataSource)
    assert http_push_source.db is fake_db


def test_source_from_config_supports_local_file(tmp_path) -> None:
    frame = pd.DataFrame(
        [{"id": 1, "timestamp": "2026-05-06T00:00:00Z", "model_name": "demo", "confidence": 0.9, "prediction": 1}]
    )
    source_dir = tmp_path / "local"
    source_dir.mkdir()
    frame.to_csv(source_dir / "demo_predictions.csv", index=False)

    source = source_from_config("local_file", {"path": str(source_dir)})
    result = source.fetch_recent_predictions("demo", hours=24)

    assert result.equals(frame)


@pytest.mark.asyncio
async def test_load_prediction_batch_async_http_push(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = pd.DataFrame(
        [{"id": "1", "timestamp": "2026-05-06T00:00:00Z", "model_name": "demo", "confidence": 0.9, "prediction": 1}]
    )

    @dataclass
    class _Batch:
        records: list[dict[str, object]]

    async def fake_latest_prediction_batch(_db: object, model_name: str, source: str | None = None) -> _Batch | None:
        assert model_name == "demo"
        assert source == "http_push"
        return _Batch(records=frame.to_dict(orient="records"))

    from ares.db import crud

    monkeypatch.setattr(crud, "latest_prediction_batch", fake_latest_prediction_batch)

    batch = await load_prediction_batch_async(object(), "demo", "http_push", {"source": "http_push"})  # type: ignore[arg-type]

    assert batch.rows == 1
    assert batch.source_type == "http_push"