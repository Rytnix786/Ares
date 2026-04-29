from __future__ import annotations

import argparse
import asyncio
import secrets

from ares.api.auth import hash_api_key
from ares.config import settings
from ares.db.crud_api_keys import create_api_key, list_api_keys, revoke_api_key
from ares.db.session import get_sessionmaker


async def _create(args: argparse.Namespace) -> None:
    raw_key = args.key or f"ares_{secrets.token_urlsafe(32)}"
    async with get_sessionmaker()() as db:
        key = await create_api_key(
            db,
            key_hash=hash_api_key(raw_key),
            name=args.name,
            scopes=args.scopes.split(","),
            rate_limit=args.rate_limit or settings.API_KEY_DEFAULT_RATE_LIMIT,
        )
        await db.commit()
    print(f"id={key.id}")
    print(f"key={raw_key}")


async def _list(_args: argparse.Namespace) -> None:
    async with get_sessionmaker()() as db:
        keys = await list_api_keys(db)
    for key in keys:
        print(f"{key.id}\t{key.name}\t{','.join(key.scopes)}\tactive={key.is_active}")


async def _revoke(args: argparse.Namespace) -> None:
    async with get_sessionmaker()() as db:
        revoked = await revoke_api_key(db, args.key_id)
        await db.commit()
    print("revoked" if revoked else "not_found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Ares DB-backed API keys")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--key")
    create.add_argument("--scopes", default="read,write")
    create.add_argument("--rate-limit")
    sub.add_parser("list")
    revoke = sub.add_parser("revoke")
    revoke.add_argument("key_id")
    args = parser.parse_args()
    if args.command == "create":
        asyncio.run(_create(args))
    elif args.command == "list":
        asyncio.run(_list(args))
    elif args.command == "revoke":
        asyncio.run(_revoke(args))


if __name__ == "__main__":
    main()
