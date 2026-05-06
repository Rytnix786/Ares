from __future__ import annotations

import argparse
import asyncio
import secrets
from datetime import datetime, timedelta

from ares.api.auth import hash_api_key
from ares.config import settings
from ares.db.crud_api_keys import create_api_key, list_api_keys, revoke_api_key, rotate_api_key
from ares.db.session import get_sessionmaker


async def _create(args: argparse.Namespace) -> None:
    raw_key = args.key or f"ares_{secrets.token_urlsafe(32)}"
    ttl_days = args.ttl_days if args.ttl_days is not None else settings.API_KEY_DEFAULT_TTL_DAYS
    if ttl_days <= 0 or ttl_days > settings.API_KEY_MAX_TTL_DAYS:
        raise SystemExit(f"ttl-days must be between 1 and {settings.API_KEY_MAX_TTL_DAYS}")
    expires_at = datetime.utcnow() + timedelta(days=ttl_days)
    async with get_sessionmaker()() as db:
        key = await create_api_key(
            db,
            key_hash=hash_api_key(raw_key),
            name=args.name,
            scopes=args.scopes.split(","),
            rate_limit=args.rate_limit or settings.API_KEY_DEFAULT_RATE_LIMIT,
            expires_at=expires_at,
        )
        await db.commit()
    print(f"id={key.id}")
    print(f"key={raw_key}")


async def _list(_args: argparse.Namespace) -> None:
    async with get_sessionmaker()() as db:
        keys = await list_api_keys(db)
    for key in keys:
        print(
            f"{key.id}\t{key.name}\t{','.join(key.scopes)}\tactive={key.is_active}"
            f"\texpires_at={key.expires_at}\tlast_used_at={key.last_used_at}\tuse_count={key.use_count}"
        )


async def _revoke(args: argparse.Namespace) -> None:
    async with get_sessionmaker()() as db:
        revoked = await revoke_api_key(db, args.key_id, revoked_by=args.revoked_by, reason=args.reason)
        await db.commit()
    print("revoked" if revoked else "not_found")


async def _rotate(args: argparse.Namespace) -> None:
    raw_key = args.key or f"ares_{secrets.token_urlsafe(32)}"
    ttl_days = args.ttl_days if args.ttl_days is not None else settings.API_KEY_DEFAULT_TTL_DAYS
    if ttl_days <= 0 or ttl_days > settings.API_KEY_MAX_TTL_DAYS:
        raise SystemExit(f"ttl-days must be between 1 and {settings.API_KEY_MAX_TTL_DAYS}")
    expires_at = datetime.utcnow() + timedelta(days=ttl_days)
    scopes = args.scopes.split(",") if args.scopes else None
    async with get_sessionmaker()() as db:
        key = await rotate_api_key(
            db,
            args.key_id,
            new_key_hash=hash_api_key(raw_key),
            name=args.name,
            scopes=scopes,
            rate_limit=args.rate_limit,
            expires_at=expires_at,
            grace_days=args.grace_days,
        )
        await db.commit()
    if key is None:
        print("not_found")
        return
    print(f"id={key.id}")
    print(f"key={raw_key}")
    print(f"rotated_from={args.key_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Ares DB-backed API keys")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--key")
    create.add_argument("--scopes", default="read,write")
    create.add_argument("--rate-limit")
    create.add_argument("--ttl-days", type=int)
    sub.add_parser("list")
    revoke = sub.add_parser("revoke")
    revoke.add_argument("key_id")
    revoke.add_argument("--revoked-by")
    revoke.add_argument("--reason")
    rotate = sub.add_parser("rotate")
    rotate.add_argument("key_id")
    rotate.add_argument("--name")
    rotate.add_argument("--key")
    rotate.add_argument("--scopes")
    rotate.add_argument("--rate-limit")
    rotate.add_argument("--ttl-days", type=int)
    rotate.add_argument("--grace-days", type=int, default=0)
    args = parser.parse_args()
    if args.command == "create":
        asyncio.run(_create(args))
    elif args.command == "list":
        asyncio.run(_list(args))
    elif args.command == "revoke":
        asyncio.run(_revoke(args))
    elif args.command == "rotate":
        asyncio.run(_rotate(args))


if __name__ == "__main__":
    main()
