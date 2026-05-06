#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare multiple ARES evaluation candidates")
    parser.add_argument("run_ids", nargs="+", help="Evaluation run IDs to compare")
    parser.add_argument("--api-url", default=os.getenv("ARES_API_URL", "http://localhost:8000/api/v1"))
    parser.add_argument("--api-key", default=os.getenv("ARES_API_KEY") or os.getenv("ARES_API_KEYS", "").split(",")[0])
    args = parser.parse_args()
    if len(args.run_ids) < 2:
        raise SystemExit("at least two run IDs are required")
    base_url = args.api_url.rstrip("/")
    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{base_url}/evaluations/compare", headers=headers, json={"run_ids": args.run_ids})
    if response.is_error:
        print(response.text, file=sys.stderr)
        raise SystemExit(response.status_code)
    print(json.dumps(response.json(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
