from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ares.config import settings

log = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"id", "input", "expected_label", "slice"}


def detect_outliers(dataset: pd.DataFrame, column: str = "difficulty", z_threshold: float = 3.0) -> list[int]:
    if column not in dataset.columns or dataset.empty:
        return []
    series = pd.to_numeric(dataset[column], errors="coerce").dropna()
    if series.empty or float(series.std(ddof=0)) == 0.0:
        return []
    mean = float(series.mean())
    std = float(series.std(ddof=0))
    return [int(index) for index, value in series.items() if abs((float(value) - mean) / std) > z_threshold]


def freshness_status(dataset_path: str | Path, max_age_days: int = 30) -> dict[str, Any]:
    path = Path(dataset_path)
    if not path.exists():
        return {"status": "missing", "age_days": None}
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    age_days = (datetime.now(UTC) - modified).days
    return {"status": "fresh" if age_days <= max_age_days else "stale", "age_days": age_days}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_golden_set(
    dataset: pd.DataFrame,
    dataset_path: str | Path,
    split: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    missing = REQUIRED_COLUMNS - set(dataset.columns)
    if missing:
        raise ValueError(f"golden set missing required columns: {sorted(missing)}")

    data_cfg = config.get("data", {})
    bounds = data_cfg.get("row_count_bounds", {}).get(split, {})
    min_rows = int(bounds.get("min", 1))
    max_rows = int(bounds.get("max", 1_000_000))
    if not (min_rows <= len(dataset) <= max_rows):
        raise ValueError(
            f"golden set row count {len(dataset)} is outside expected bounds for split '{split}'"
        )

    if dataset["expected_label"].nunique(dropna=True) < 2:
        raise ValueError("golden set must contain at least two labels")

    label_distribution = dataset["expected_label"].value_counts(normalize=True).to_dict()
    for label, label_bounds in data_cfg.get("class_balance_bounds", {}).items():
        observed = float(label_distribution.get(label, 0.0))
        lower = float(label_bounds.get("min", 0.0))
        upper = float(label_bounds.get("max", 1.0))
        if observed < lower or observed > upper:
            raise ValueError(
                f"golden set class balance for '{label}' is {observed:.3f}, outside [{lower:.3f}, {upper:.3f}]"
            )

    slice_distribution = dataset["slice"].value_counts(normalize=True).to_dict()
    for slice_name, slice_bounds in data_cfg.get("slice_distribution_bounds", {}).items():
        observed = float(slice_distribution.get(slice_name, 0.0))
        lower = float(slice_bounds.get("min", 0.0))
        upper = float(slice_bounds.get("max", 1.0))
        if observed < lower or observed > upper:
            raise ValueError(
                f"golden set slice distribution for '{slice_name}' is {observed:.3f}, outside [{lower:.3f}, {upper:.3f}]"
            )

    dataset_file = Path(dataset_path)
    checksum = sha256_file(dataset_file)
    expected_checksum = data_cfg.get("checksums", {}).get(split)
    checksum_status = "skipped"
    if settings.GOLDEN_SET_SKIP_CHECKSUM:
        checksum_status = "skipped-by-setting"
    elif expected_checksum:
        if checksum != expected_checksum:
            raise ValueError(f"golden set checksum mismatch for split '{split}'")
        checksum_status = "verified"
    elif settings.GOLDEN_SET_REQUIRE_CHECKSUM:
        raise ValueError(
            f"golden set checksum missing for split '{split}' while strict mode is enabled"
        )
    else:
        log.warning(
            "golden_set_checksum_missing",
            extra={"split": split, "dataset_path": str(dataset_file)},
        )
        checksum_status = "missing"

    return {
        "split": split,
        "dataset_path": str(dataset_file),
        "row_count": len(dataset),
        "label_distribution": {str(k): float(v) for k, v in label_distribution.items()},
        "slice_distribution": {str(k): float(v) for k, v in slice_distribution.items()},
        "checksum": checksum,
        "checksum_status": checksum_status,
        "outlier_rows": detect_outliers(dataset),
        "freshness": freshness_status(dataset_file, int(data_cfg.get("max_age_days", 30))),
    }