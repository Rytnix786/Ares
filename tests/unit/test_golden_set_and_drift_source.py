from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ares.drift_sources import LocalFileDataSource
from ares.golden_set import sha256_file, validate_golden_set


def build_dataset() -> pd.DataFrame:
    rows = []
    quotas = [("easy", 2), ("typical", 6), ("edge_case", 2), ("critical", 2)]
    idx = 0
    for slice_name, count in quotas:
        for i in range(count):
            label = "positive" if i % 2 == 0 else "negative"
            rows.append(
                {
                    "id": f"row-{idx}",
                    "input": json.dumps({"text": f"{label} example", "slice_hint": slice_name}),
                    "expected_label": label,
                    "slice": slice_name,
                    "difficulty": 1,
                }
            )
            idx += 1
    return pd.DataFrame(rows)


def build_config(checksum: str | None) -> dict:
    return {
        "data": {
            "checksums": {"val": checksum},
            "row_count_bounds": {"val": {"min": 10, "max": 100}},
            "class_balance_bounds": {
                "positive": {"min": 0.3, "max": 0.7},
                "negative": {"min": 0.3, "max": 0.7},
            },
            "slice_distribution_bounds": {
                "easy": {"min": 0.05, "max": 0.2},
                "typical": {"min": 0.45, "max": 0.7},
                "edge_case": {"min": 0.1, "max": 0.25},
                "critical": {"min": 0.1, "max": 0.2},
            },
        }
    }


def test_validate_golden_set_returns_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.golden_set.settings.GOLDEN_SET_SKIP_CHECKSUM", True)
    dataset = build_dataset()
    path = tmp_path / "val.csv"
    dataset.to_csv(path, index=False)
    summary = validate_golden_set(dataset, path, "val", build_config(None))
    assert summary["checksum_status"] == "skipped-by-setting"
    assert summary["row_count"] == len(dataset)


def test_validate_golden_set_checksum_mismatch_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.golden_set.settings.GOLDEN_SET_SKIP_CHECKSUM", False)
    monkeypatch.setattr("ares.golden_set.settings.GOLDEN_SET_REQUIRE_CHECKSUM", False)
    dataset = build_dataset()
    path = tmp_path / "val.csv"
    dataset.to_csv(path, index=False)
    with pytest.raises(ValueError):
        validate_golden_set(dataset, path, "val", build_config("bad-checksum"))


def test_validate_golden_set_requires_checksum_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("ares.golden_set.settings.GOLDEN_SET_SKIP_CHECKSUM", False)
    monkeypatch.setattr("ares.golden_set.settings.GOLDEN_SET_REQUIRE_CHECKSUM", True)
    dataset = build_dataset()
    path = tmp_path / "val.csv"
    dataset.to_csv(path, index=False)
    with pytest.raises(ValueError):
        validate_golden_set(dataset, path, "val", build_config(None))


def test_sha256_file_returns_hex_digest(tmp_path: Path) -> None:
    path = tmp_path / "file.txt"
    path.write_text("hello", encoding="utf-8")
    digest = sha256_file(path)
    assert len(digest) == 64


def test_local_file_data_source_reads_csv(tmp_path: Path) -> None:
    path = tmp_path / "demo_predictions.csv"
    pd.DataFrame(
        [
            {"id": "1", "model_name": "demo", "prediction": "positive", "confidence": 0.8, "timestamp": "2026-01-01T00:00:00Z"}
        ]
    ).to_csv(path, index=False)
    source = LocalFileDataSource(tmp_path)
    df = source.fetch_recent_predictions("demo", 24)
    assert list(df.columns) == ["id", "model_name", "prediction", "confidence", "timestamp"]


def test_local_file_data_source_validates_columns(tmp_path: Path) -> None:
    path = tmp_path / "demo_predictions.csv"
    pd.DataFrame([{"id": "1"}]).to_csv(path, index=False)
    source = LocalFileDataSource(tmp_path)
    with pytest.raises(ValueError):
        source.fetch_recent_predictions("demo", 24)


def test_local_file_data_source_missing_file_raises(tmp_path: Path) -> None:
    source = LocalFileDataSource(tmp_path)
    with pytest.raises(FileNotFoundError):
        source.fetch_recent_predictions("missing", 24)