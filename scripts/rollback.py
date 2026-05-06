#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json

import httpx

from ares.config import settings


async def rollback(model_name: str, reason: str, *, target_run_id: str | None = None, dry_run: bool = False) -> dict[str, object]:
    headers = {"X-API-Key": settings.ARES_API_KEYS[0]} if settings.ARES_API_KEYS else {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.ARES_API_URL}/champions/{model_name}/rollback",
            json={
                "rolled_back_by": "rollback_cli",
                "reason": reason,
                "target_run_id": target_run_id,
                "dry_run": dry_run,
            },
            headers=headers,
        )
        response.raise_for_status()
        return dict(response.json())


def main() -> None:
    parser = argparse.ArgumentParser(description="Governed champion rollback")
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--target-run-id")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    payload = asyncio.run(rollback(args.model_name, args.reason, target_run_id=args.target_run_id, dry_run=args.dry_run))
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
