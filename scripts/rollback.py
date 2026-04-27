#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

import httpx

from ares.config import settings


async def rollback(model_name: str, reason: str) -> None:
    headers = {"X-API-Key": settings.ARES_API_KEYS[0]} if settings.ARES_API_KEYS else {}
    async with httpx.AsyncClient() as client:
        previous_response = await client.get(f"{settings.ARES_API_URL}/champions/{model_name}/previous", headers=headers)
        previous_response.raise_for_status()
        previous = previous_response.json()
        response = await client.post(f"{settings.ARES_API_URL}/champions/{model_name}/promote", json={"run_id": previous["champion_run_id"], "promoted_by": "automated_rollback", "reason": reason}, headers=headers)
        response.raise_for_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--reason", default="Automated rollback")
    args = parser.parse_args()
    asyncio.run(rollback(args.model_name, args.reason))