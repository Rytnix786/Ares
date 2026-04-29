#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def create_backup(output: str) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "created_at": datetime.now(UTC).isoformat(), "status": "ok"}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an Ares metadata backup")
    parser.add_argument("--output", default="reports/ares-backup.json")
    args = parser.parse_args()
    print(create_backup(args.output))


if __name__ == "__main__":
    main()
