#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_backup(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("version") != 1:
        raise ValueError("unsupported backup version")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate and restore an Ares metadata backup")
    parser.add_argument("backup")
    args = parser.parse_args()
    validate_backup(args.backup)
    print("restore validation ok")


if __name__ == "__main__":
    main()
