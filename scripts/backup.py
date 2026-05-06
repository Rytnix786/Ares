#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, unquote, urlsplit, urlunsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DEFAULT_BACKUP_ROOT = Path("backups")
DEFAULT_BUCKET = "ares-artifacts"
MANIFEST_NAME = "manifest.json"
DUMP_NAME = "postgres.sql.gz"
ARTIFACTS_DIR_NAME = "artifacts"
ROW_COUNT_TABLES = {
    "evaluation_runs": "evaluation_runs",
    "champions": "model_champions",
    "drift_reports": "drift_reports",
    "audit_logs": "audit_logs",
}


class BackupError(RuntimeError):
    """Raised when backup or restore prerequisites fail."""


@dataclass(frozen=True)
class PostgresCliConfig:
    database_url: str
    database_name: str
    admin_database_name: str
    env: dict[str, str]


@dataclass(frozen=True)
class MinioConfig:
    endpoint: str
    secure: bool
    access_key: str
    secret_key: str
    region: str | None
    bucket: str


def _strip_driver(scheme: str) -> str:
    return scheme.split("+", 1)[0].lower()


def _normalize_postgres_url(database_url: str) -> SplitResult:
    parsed = urlsplit(database_url)
    scheme = _strip_driver(parsed.scheme)
    if scheme not in {"postgresql", "postgres"}:
        raise BackupError("DATABASE_URL must use a PostgreSQL driver for backup and restore")
    if not parsed.hostname or not parsed.path or parsed.path == "/":
        raise BackupError("DATABASE_URL must include a PostgreSQL host and database name")
    return parsed


def get_postgres_cli_config(database_url: str | None = None) -> PostgresCliConfig:
    raw_url = database_url or os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise BackupError("DATABASE_URL is required")

    parsed = _normalize_postgres_url(raw_url)
    database_name = parsed.path.lstrip("/")
    admin_database = "template1" if database_name == "postgres" else "postgres"
    env = {
        "PGHOST": parsed.hostname or "",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": unquote(parsed.username or ""),
    }
    if parsed.password is not None:
        env["PGPASSWORD"] = unquote(parsed.password)
    return PostgresCliConfig(
        database_url=raw_url,
        database_name=database_name,
        admin_database_name=admin_database,
        env=env,
    )


def sync_database_url(database_url: str) -> str:
    parsed = _normalize_postgres_url(database_url)
    scheme = _strip_driver(parsed.scheme)
    return urlunsplit((scheme, parsed.netloc, parsed.path, parsed.query, parsed.fragment))


def ensure_command_available(command: str) -> str:
    resolved = shutil.which(command)
    if resolved is None:
        raise BackupError(f"Required command '{command}' was not found on PATH")
    return resolved


def run_command(
    command: list[str],
    *,
    extra_env: dict[str, str] | None = None,
    cwd: Path | None = None,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        return subprocess.run(
            command,
            check=True,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            capture_output=capture_output,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        message = stderr or stdout or str(exc)
        raise BackupError(f"Command failed: {' '.join(command)}\n{message}") from exc


async def collect_row_counts(database_url: str) -> dict[str, int]:
    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.connect() as connection:
            counts: dict[str, int] = {}
            for manifest_key, table_name in ROW_COUNT_TABLES.items():
                result = await connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                counts[manifest_key] = int(result.scalar_one())
            return counts
    finally:
        await engine.dispose()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_bucket_name() -> str:
    return os.environ.get("ARES_BACKUP_BUCKET", DEFAULT_BUCKET)


def get_minio_config() -> MinioConfig:
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL", "").strip()
    access_key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
    region = os.environ.get("AWS_REGION", "").strip() or None
    if not endpoint_url:
        raise BackupError("AWS_ENDPOINT_URL is required for MinIO artifact backup")
    if not access_key or not secret_key:
        raise BackupError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required for MinIO artifact backup")

    parsed = urlsplit(endpoint_url if "://" in endpoint_url else f"http://{endpoint_url}")
    if not parsed.hostname:
        raise BackupError("AWS_ENDPOINT_URL must include a valid MinIO host")
    endpoint = parsed.netloc or parsed.path
    secure = parsed.scheme == "https"
    return MinioConfig(
        endpoint=endpoint,
        secure=secure,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        bucket=get_bucket_name(),
    )


def get_minio_client():
    try:
        from minio import Minio
    except ImportError as exc:
        raise BackupError("The Python 'minio' client is required for artifact backup and restore") from exc

    config = get_minio_config()
    client = Minio(
        config.endpoint,
        access_key=config.access_key,
        secret_key=config.secret_key,
        secure=config.secure,
        region=config.region,
    )
    return client, config


def ensure_bucket_exists(client: Any, bucket: str, *, create: bool) -> None:
    try:
        exists = client.bucket_exists(bucket)
    except Exception as exc:
        raise BackupError(f"Failed to query MinIO bucket '{bucket}': {exc}") from exc
    if exists:
        return
    if not create:
        raise BackupError(f"MinIO bucket '{bucket}' does not exist")
    try:
        client.make_bucket(bucket)
    except Exception as exc:
        raise BackupError(f"Failed to create MinIO bucket '{bucket}': {exc}") from exc


def download_bucket(client: Any, bucket: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    try:
        for obj in client.list_objects(bucket, recursive=True):
            target = destination / obj.object_name
            target.parent.mkdir(parents=True, exist_ok=True)
            client.fget_object(bucket, obj.object_name, str(target))
    except Exception as exc:
        raise BackupError(f"Failed to download artifacts from bucket '{bucket}': {exc}") from exc


def upload_directory(client: Any, bucket: str, source_dir: Path) -> None:
    ensure_bucket_exists(client, bucket, create=True)
    if not source_dir.exists():
        raise BackupError(f"Artifact backup directory does not exist: {source_dir}")
    try:
        for file_path in sorted(path for path in source_dir.rglob("*") if path.is_file()):
            object_name = file_path.relative_to(source_dir).as_posix()
            client.fput_object(bucket, object_name, str(file_path))
    except Exception as exc:
        raise BackupError(f"Failed to upload artifacts to bucket '{bucket}': {exc}") from exc


def build_backup_dir(output_dir: str | Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = Path(output_dir) / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    return backup_dir


def dump_database(config: PostgresCliConfig, dump_path: Path) -> None:
    ensure_command_available("pg_dump")
    plain_dump_path = dump_path.with_suffix("")
    command = [
        "pg_dump",
        "--format=plain",
        "--encoding=UTF8",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(plain_dump_path),
        "--dbname",
        config.database_name,
    ]
    try:
        run_command(command, extra_env=config.env)
        with plain_dump_path.open("rb") as source_handle:
            with dump_path.open("wb") as raw_output:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0) as gzip_output:
                    shutil.copyfileobj(source_handle, gzip_output)
    finally:
        if plain_dump_path.exists():
            plain_dump_path.unlink()

    if not dump_path.exists() or dump_path.stat().st_size == 0:
        raise BackupError(f"Postgres dump was not created or is empty: {dump_path}")


def write_manifest(backup_dir: Path, payload: dict[str, Any]) -> Path:
    manifest_path = backup_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest_path


def load_manifest(backup_dir: str | Path) -> dict[str, Any]:
    manifest_path = Path(backup_dir) / MANIFEST_NAME
    if not manifest_path.exists():
        raise BackupError(f"Backup manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def create_backup(output_dir: str = str(DEFAULT_BACKUP_ROOT)) -> Path:
    config = get_postgres_cli_config()
    backup_dir = build_backup_dir(output_dir)
    dump_path = backup_dir / DUMP_NAME
    artifacts_path = backup_dir / ARTIFACTS_DIR_NAME

    dump_database(config, dump_path)
    row_counts = asyncio.run(collect_row_counts(config.database_url))

    minio_client, minio_config = get_minio_client()
    ensure_bucket_exists(minio_client, minio_config.bucket, create=False)
    download_bucket(minio_client, minio_config.bucket, artifacts_path)

    checksum = sha256_file(dump_path)
    manifest = {
        "timestamp": backup_dir.name,
        "pg_dump_path": DUMP_NAME,
        "minio_sync_path": ARTIFACTS_DIR_NAME,
        "db_row_counts": row_counts,
        "sha256": checksum,
    }
    write_manifest(backup_dir, manifest)
    return backup_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a real ARES Postgres and MinIO backup")
    parser.add_argument("--output-dir", default=str(DEFAULT_BACKUP_ROOT), help="Root directory that will receive a timestamped backup folder")
    args = parser.parse_args()
    backup_dir = create_backup(args.output_dir)
    manifest = load_manifest(backup_dir)
    print(f"Backup directory: {backup_dir}")
    print(f"Postgres dump: {backup_dir / manifest['pg_dump_path']}")
    print(f"Artifacts path: {backup_dir / manifest['minio_sync_path']}")
    print(f"SHA256: {manifest['sha256']}")


if __name__ == "__main__":
    main()
