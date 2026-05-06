#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

DEFAULT_BUCKET = "ares-artifacts"
MANIFEST_NAME = "manifest.json"


class RestoreError(RuntimeError):
    """Raised when restore prerequisites or execution fail."""


def _strip_driver(scheme: str) -> str:
    return scheme.split("+", 1)[0].lower()


def _normalize_postgres_url(database_url: str):
    parsed = urlsplit(database_url)
    if _strip_driver(parsed.scheme) not in {"postgresql", "postgres"}:
        raise RestoreError("DATABASE_URL must use a PostgreSQL driver for restore")
    if not parsed.hostname or not parsed.path or parsed.path == "/":
        raise RestoreError("DATABASE_URL must include a PostgreSQL host and database name")
    return parsed


def get_postgres_env(database_url: str | None = None) -> tuple[dict[str, str], str, str]:
    raw_url = database_url or os.environ.get("DATABASE_URL", "")
    if not raw_url:
        raise RestoreError("DATABASE_URL is required")
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
    return env, database_name, admin_database


def ensure_command_available(command: str) -> None:
    if shutil.which(command) is None:
        raise RestoreError(f"Required command '{command}' was not found on PATH")


def run_command(command: list[str], *, extra_env: dict[str, str] | None = None, cwd: Path | None = None) -> None:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    try:
        subprocess.run(
            command,
            check=True,
            env=env,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        stdout = exc.stdout.strip() if exc.stdout else ""
        message = stderr or stdout or str(exc)
        raise RestoreError(f"Command failed: {' '.join(command)}\n{message}") from exc


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(backup_dir: Path) -> dict[str, object]:
    manifest_path = backup_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise RestoreError(f"Backup manifest not found: {manifest_path}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def get_bucket_name() -> str:
    return os.environ.get("ARES_BACKUP_BUCKET", DEFAULT_BUCKET)


def get_minio_client():
    try:
        from minio import Minio
    except ImportError as exc:
        raise RestoreError("The Python 'minio' client is required for artifact restore") from exc

    endpoint_url = os.environ.get("AWS_ENDPOINT_URL", "").strip()
    access_key = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
    region = os.environ.get("AWS_REGION", "").strip() or None
    if not endpoint_url:
        raise RestoreError("AWS_ENDPOINT_URL is required for MinIO artifact restore")
    if not access_key or not secret_key:
        raise RestoreError("AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required for MinIO artifact restore")
    parsed = urlsplit(endpoint_url if "://" in endpoint_url else f"http://{endpoint_url}")
    if not parsed.hostname:
        raise RestoreError("AWS_ENDPOINT_URL must include a valid MinIO host")
    endpoint = parsed.netloc or parsed.path
    secure = parsed.scheme == "https"
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        region=region,
    )


def ensure_bucket_exists(client, bucket: str) -> None:
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except Exception as exc:
        raise RestoreError(f"Failed to ensure MinIO bucket '{bucket}': {exc}") from exc


def upload_directory(client, bucket: str, source_dir: Path) -> None:
    if not source_dir.exists():
        raise RestoreError(f"Artifact backup directory does not exist: {source_dir}")
    ensure_bucket_exists(client, bucket)
    try:
        for obj in client.list_objects(bucket, recursive=True):
            client.remove_object(bucket, obj.object_name)
        for file_path in sorted(path for path in source_dir.rglob("*") if path.is_file()):
            object_name = file_path.relative_to(source_dir).as_posix()
            client.fput_object(bucket, object_name, str(file_path))
    except Exception as exc:
        raise RestoreError(f"Failed to upload artifacts to bucket '{bucket}': {exc}") from exc


def verify_checksum(dump_path: Path, expected_sha256: str) -> None:
    actual_sha256 = sha256_file(dump_path)
    if actual_sha256 != expected_sha256:
        raise RestoreError(
            f"Checksum verification failed for {dump_path}: expected {expected_sha256}, got {actual_sha256}"
        )


def recreate_database(pg_env: dict[str, str], database_name: str, admin_database: str) -> None:
    quoted_database_name = database_name.replace('"', '""')
    sql_database_name = database_name.replace("'", "''")
    terminate_sql = (
        "SELECT pg_terminate_backend(pid) "
        f"FROM pg_stat_activity WHERE datname = '{sql_database_name}' AND pid <> pg_backend_pid();"
    )
    run_command(["psql", "--dbname", admin_database, "-v", "ON_ERROR_STOP=1", "-c", terminate_sql], extra_env=pg_env)
    run_command(
        ["psql", "--dbname", admin_database, "-v", "ON_ERROR_STOP=1", "-c", f'DROP DATABASE IF EXISTS "{quoted_database_name}";'],
        extra_env=pg_env,
    )
    run_command(
        ["psql", "--dbname", admin_database, "-v", "ON_ERROR_STOP=1", "-c", f'CREATE DATABASE "{quoted_database_name}";'],
        extra_env=pg_env,
    )


def restore_dump(pg_env: dict[str, str], database_name: str, dump_path: Path) -> None:
    try:
        with gzip.open(dump_path, "rb") as dump_stream:
            process = subprocess.Popen(
                ["psql", "--dbname", database_name, "-v", "ON_ERROR_STOP=1"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env={**os.environ, **pg_env},
            )
            assert process.stdin is not None
            assert process.stderr is not None
            shutil.copyfileobj(dump_stream, process.stdin)
            process.stdin.close()
            stderr = process.stderr.read().decode("utf-8", errors="replace").strip()
            return_code = process.wait()
            if return_code != 0:
                raise RestoreError(f"psql restore failed with exit code {return_code}: {stderr}")
    except OSError as exc:
        raise RestoreError(f"Failed to restore dump with psql: {exc}") from exc


def run_alembic_upgrade() -> None:
    run_command([sys.executable, "-m", "alembic", "upgrade", "head"])


def restore_backup(backup_dir: str) -> Path:
    backup_path = Path(backup_dir)
    manifest = load_manifest(backup_path)
    dump_path = backup_path / str(manifest["pg_dump_path"])
    artifacts_path = backup_path / str(manifest["minio_sync_path"])

    if not dump_path.exists():
        raise RestoreError(f"Backup dump not found: {dump_path}")
    if not artifacts_path.exists():
        raise RestoreError(f"Artifact backup directory not found: {artifacts_path}")
    verify_checksum(dump_path, str(manifest["sha256"]))

    ensure_command_available("psql")
    pg_env, database_name, admin_database = get_postgres_env()
    recreate_database(pg_env, database_name, admin_database)
    restore_dump(pg_env, database_name, dump_path)

    minio_client = get_minio_client()
    upload_directory(minio_client, get_bucket_name(), artifacts_path)
    run_alembic_upgrade()
    return backup_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore a real ARES Postgres and MinIO backup")
    parser.add_argument("--backup-dir", required=True, help="Timestamped backup directory created by scripts/backup.py")
    args = parser.parse_args()

    backup_dir = restore_backup(args.backup_dir)
    manifest = load_manifest(backup_dir)
    print(f"Checksum verified: {backup_dir / str(manifest['pg_dump_path'])}")
    print("Database recreated and restored")
    print(f"Artifacts restored: {backup_dir / str(manifest['minio_sync_path'])}")
    print("Alembic upgrade head completed")


if __name__ == "__main__":
    main()
