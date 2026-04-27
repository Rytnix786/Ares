#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

import yaml


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    config_path = Path("ares.config.yaml")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    data_cfg = config.setdefault("data", {})
    checksums = data_cfg.setdefault("checksums", {})
    golden_dir = Path("data/golden_set")
    for split in ("train", "val", "test"):
        split_path = golden_dir / f"{split}.csv"
        if not split_path.exists():
            raise FileNotFoundError(f"golden set split does not exist: {split_path}")
        checksums[split] = sha256_file(split_path)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()