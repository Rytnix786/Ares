#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd


def validate_composition(df: pd.DataFrame) -> None:
    counts = df["slice"].value_counts(normalize=True).to_dict()
    edge = counts.get("edge_case", 0) + counts.get("critical", 0)
    label_counts = df["expected_label"].value_counts(normalize=True).to_dict()
    if counts.get("easy", 0) < 0.05 or counts.get("typical", 0) < 0.45 or edge < 0.20:
        raise ValueError("golden set composition does not meet minimum slice distribution")
    if min(label_counts.values(), default=0.0) < 0.30:
        raise ValueError("golden set class balance does not meet minimum requirements")


def build_row(i: int, label: str, slice_name: str, difficulty: int, template: str) -> dict[str, object]:
    text = template.format(index=i, sentiment=label, slice=slice_name)
    return {
        "id": f"sample-{i}",
        "input": json.dumps({"text": text, "slice_hint": slice_name}),
        "expected_label": label,
        "slice": slice_name,
        "difficulty": difficulty,
    }


def write_slice_views(df: pd.DataFrame, out_dir: Path) -> None:
    slices_dir = out_dir / "slices"
    slices_dir.mkdir(parents=True, exist_ok=True)
    for slice_name, slice_df in df.groupby("slice"):
        slice_df.to_csv(slices_dir / f"{slice_name}.csv", index=False)


def main() -> None:
    rng = random.Random(42)
    out = Path("data/golden_set")
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    templates = {
        "easy": "Example {index}: a clearly {sentiment} support conversation in an {slice} slice.",
        "typical": "Example {index}: a mostly {sentiment} customer message representing {slice} production traffic.",
        "edge_case": "Example {index}: an ambiguous but still {sentiment} message for the {slice} slice.",
        "critical": "Example {index}: a high-risk {sentiment} escalation where the {slice} slice must remain stable.",
    }
    split_plan = {
        "train": {"easy": 12, "typical": 42, "edge_case": 12, "critical": 10},
        "val": {"easy": 4, "typical": 14, "edge_case": 4, "critical": 4},
        "test": {"easy": 4, "typical": 14, "edge_case": 4, "critical": 4},
    }

    current_index = 0
    for split, quotas in split_plan.items():
        split_rows: list[dict[str, object]] = []
        for slice_name, count in quotas.items():
            positives = count // 2
            negatives = count - positives
            labels = ["positive"] * positives + ["negative"] * negatives
            rng.shuffle(labels)
            difficulty = 1 if slice_name == "easy" else 2 if slice_name == "typical" else 4 if slice_name == "edge_case" else 5
            for label in labels:
                split_rows.append(build_row(current_index, label, slice_name, difficulty, templates[slice_name]))
                current_index += 1
        split_df = pd.DataFrame(split_rows)
        validate_composition(split_df)
        split_df.to_csv(out / f"{split}.csv", index=False)
        if split == "train":
            write_slice_views(split_df, out)
        rows.extend(split_rows)

    validate_composition(pd.DataFrame(rows))


if __name__ == "__main__":
    main()