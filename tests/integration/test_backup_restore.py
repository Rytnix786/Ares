from __future__ import annotations

import asyncio
import io
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import SplitResult, urlsplit, urlunsplit

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ares.models import DriftReportRecord, EvaluationRun, ModelChampion
from scripts.backup import BackupError, create_backup, load_manifest, sha256_file
from scripts.restore import RestoreError, restore_backup


def _strip_driver(scheme: str) -> str:
    return scheme.split("+", 1)[0].lower()


def _parse_postgres_url(database_url: str) -> SplitResult:
    parsed = urlsplit(database_url)
    if _strip_driver(parsed.scheme) not in {"postgresql", "postgres"}:
        raise pytest.skip.Exception("backup/restore integration test requires a PostgreSQL DATABASE_URL")
    if not parsed.hostname or not parsed.path or parsed.path == "/":
        raise pytest.skip.Exception("backup/restore integration test requires a PostgreSQL DATABASE_URL with a database name")
    return parsed


def _require_tool(tool_name: str) -> None:
    if shutil.which(tool_name) is None:
        raise pytest.skip.Exception(f"backup/restore integration test requires '{tool_name}' on PATH")


def _build_pg_env(parsed: SplitResult) -> dict[str, str]:
    env = {
        "PGHOST": parsed.hostname or "",
        "PGPORT": str(parsed.port or 5432),
        "PGUSER": parsed.username or "",
    }
    if parsed.password is not None:
        env["PGPASSWORD"] = parsed.password
    return env


def _admin_database_name(database_name: str) -> str:
    return "template1" if database_name == "postgres" else "postgres"


def _run_command(command: list[str], *, env: dict[str, str], cwd: Path | None = None) -> None:
    process_env = os.environ.copy()
    process_env.update(env)
    subprocess.run(
        command,
        check=True,
        env=process_env,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )


def _build_database_url(parsed: SplitResult, database_name: str) -> str:
    return urlunsplit((parsed.scheme, parsed.netloc, f"/{database_name}", parsed.query, parsed.fragment))


def _recreate_database(parsed: SplitResult, database_name: str) -> None:
    pg_env = _build_pg_env(parsed)
    admin_database = _admin_database_name(database_name)
    quoted_database_name = database_name.replace('"', '""')
    sql_database_name = database_name.replace("'", "''")
    terminate_sql = (
        "SELECT pg_terminate_backend(pid) "
        f"FROM pg_stat_activity WHERE datname = '{sql_database_name}' AND pid <> pg_backend_pid();"
    )
    _run_command(["psql", "--dbname", admin_database, "-v", "ON_ERROR_STOP=1", "-c", terminate_sql], env=pg_env)
    _run_command(
        ["psql", "--dbname", admin_database, "-v", "ON_ERROR_STOP=1", "-c", f'DROP DATABASE IF EXISTS "{quoted_database_name}";'],
        env=pg_env,
    )
    _run_command(
        ["psql", "--dbname", admin_database, "-v", "ON_ERROR_STOP=1", "-c", f'CREATE DATABASE "{quoted_database_name}";'],
        env=pg_env,
    )


def _run_alembic_upgrade(database_url: str, repo_root: Path) -> None:
    env = {"DATABASE_URL": database_url}
    _run_command([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, cwd=repo_root)


async def _seed_database(database_url: str) -> None:
    engine = create_async_engine(database_url, future=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sessionmaker() as session:
            runs = [
                EvaluationRun(
                    id=f"backup-restore-run-{index}",
                    commit_sha=f"backup-restore-sha-{index}",
                    model_name="backup-restore-model",
                    model_version=f"candidate-{index}",
                    branch="test",
                    pr_number=index,
                    overall_f1=0.90 + (index * 0.01),
                    overall_accuracy=0.91 + (index * 0.01),
                    overall_precision=0.92 + (index * 0.01),
                    overall_recall=0.93 + (index * 0.01),
                    latency_p50_ms=5.0 + index,
                    latency_p99_ms=10.0 + index,
                    model_size_mb=1.0 + index,
                    slice_metrics={"critical": {"f1": 0.9 + (index * 0.01), "is_critical": True}},
                    gate_config_snapshot={"critical_slice_min_f1": 0.6},
                    metadata_json={"seed": True, "index": index},
                    passed=True,
                    failure_reason=None,
                    golden_set_version=f"seed-v{index}",
                    n_samples_evaluated=10 + index,
                    duration_seconds=0.2 + index,
                    mlflow_status="skipped",
                    artifact_uri=f"s3://ares-artifacts/models/run-{index}",
                )
                for index in range(1, 4)
            ]
            session.add_all(runs)
            session.add(
                ModelChampion(
                    id="backup-restore-champion-1",
                    model_name="backup-restore-model",
                    champion_run_id=runs[0].id,
                    promoted_by="integration-test",
                    promotion_reason="seed champion",
                    is_active=True,
                )
            )
            session.add_all(
                [
                    DriftReportRecord(
                        id=f"backup-restore-drift-{index}",
                        model_name="backup-restore-model",
                        feature=f"feature-{index}",
                        kl_divergence=0.10 * index,
                        psi=0.08 * index,
                        is_alerting=index == 2,
                        severity="high" if index == 2 else "medium",
                        payload={"seed": True, "index": index},
                    )
                    for index in range(1, 3)
                ]
            )
            await session.commit()
    finally:
        await engine.dispose()


async def _table_count(database_url: str, table_name: str) -> int:
    engine = create_async_engine(database_url, future=True)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return int(result.scalar_one())
    finally:
        await engine.dispose()


def _minio_client_from_env():
    try:
        from minio import Minio
    except ImportError as exc:
        raise pytest.skip.Exception("backup/restore integration test requires the Python 'minio' client") from exc

    endpoint = os.environ.get("BACKUP_RESTORE_TEST_AWS_ENDPOINT_URL") or os.environ.get("AWS_ENDPOINT_URL")
    access_key = os.environ.get("BACKUP_RESTORE_TEST_AWS_ACCESS_KEY_ID") or os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("BACKUP_RESTORE_TEST_AWS_SECRET_ACCESS_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not endpoint or not access_key or not secret_key:
        raise pytest.skip.Exception("backup/restore integration test requires MinIO endpoint and credentials in env")

    parsed = urlsplit(endpoint if "://" in endpoint else f"http://{endpoint}")
    if not parsed.hostname:
        raise pytest.skip.Exception("backup/restore integration test requires a valid MinIO endpoint")

    return Minio(
        parsed.netloc or parsed.path,
        access_key=access_key,
        secret_key=secret_key,
        secure=parsed.scheme == "https",
        region=os.environ.get("AWS_REGION") or "us-east-1",
    )


def _prepare_artifact_bucket(bucket_name: str) -> None:
    client = _minio_client_from_env()
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
        for obj in client.list_objects(bucket_name, recursive=True):
            client.remove_object(bucket_name, obj.object_name)
        client.put_object(
            bucket_name,
            "integration/seed-artifact.txt",
            data=io.BytesIO(b"seed-artifact"),
            length=len(b"seed-artifact"),
            content_type="text/plain",
        )
    except Exception as exc:
        raise pytest.skip.Exception(f"backup/restore integration test could not prepare MinIO bucket: {exc}") from exc


def _clear_artifact_bucket(bucket_name: str) -> None:
    client = _minio_client_from_env()
    for obj in client.list_objects(bucket_name, recursive=True):
        client.remove_object(bucket_name, obj.object_name)


def _artifact_exists(bucket_name: str, object_name: str) -> bool:
    client = _minio_client_from_env()
    try:
        client.stat_object(bucket_name, object_name)
        return True
    except Exception:
        return False


@pytest.fixture
def backup_restore_env(monkeypatch, tmp_path: Path):
    _require_tool("pg_dump")
    _require_tool("psql")

    raw_database_url = os.environ.get("BACKUP_RESTORE_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not raw_database_url:
        raise pytest.skip.Exception("backup/restore integration test requires BACKUP_RESTORE_TEST_DATABASE_URL or DATABASE_URL")

    parsed = _parse_postgres_url(raw_database_url)
    base_database_name = parsed.path.lstrip("/")
    explicit_test_database = os.environ.get("BACKUP_RESTORE_TEST_DATABASE_URL")
    if explicit_test_database is None and "test" not in base_database_name.lower():
        raise pytest.skip.Exception(
            "backup/restore integration test requires BACKUP_RESTORE_TEST_DATABASE_URL or a DATABASE_URL whose database name includes 'test'"
        )

    test_database_name = f"{base_database_name}_backup_restore_{uuid.uuid4().hex[:8]}"
    test_database_url = _build_database_url(parsed, test_database_name)
    repo_root = Path(__file__).resolve().parents[2]
    bucket_name = "ares-artifacts"

    _prepare_artifact_bucket(bucket_name)
    _recreate_database(parsed, test_database_name)
    _run_alembic_upgrade(test_database_url, repo_root)

    monkeypatch.setenv("DATABASE_URL", test_database_url)
    monkeypatch.setenv("ARES_BACKUP_BUCKET", bucket_name)
    if os.environ.get("BACKUP_RESTORE_TEST_AWS_ENDPOINT_URL"):
        monkeypatch.setenv("AWS_ENDPOINT_URL", os.environ["BACKUP_RESTORE_TEST_AWS_ENDPOINT_URL"])
    if os.environ.get("BACKUP_RESTORE_TEST_AWS_ACCESS_KEY_ID"):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", os.environ["BACKUP_RESTORE_TEST_AWS_ACCESS_KEY_ID"])
    if os.environ.get("BACKUP_RESTORE_TEST_AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", os.environ["BACKUP_RESTORE_TEST_AWS_SECRET_ACCESS_KEY"])

    yield {
        "database_url": test_database_url,
        "parsed": parsed,
        "database_name": test_database_name,
        "repo_root": repo_root,
        "bucket_name": bucket_name,
        "backup_root": tmp_path / "backups",
    }

    _clear_artifact_bucket(bucket_name)
    _recreate_database(parsed, test_database_name)
    admin_database = _admin_database_name(test_database_name)
    _run_command(
        ["psql", "--dbname", admin_database, "-v", "ON_ERROR_STOP=1", "-c", f'DROP DATABASE IF EXISTS "{test_database_name.replace(chr(34), chr(34) * 2)}";'],
        env=_build_pg_env(parsed),
    )


@pytest.mark.integration
@pytest.mark.serial
def test_backup_restore_round_trip(backup_restore_env) -> None:
    database_url = backup_restore_env["database_url"]
    bucket_name = backup_restore_env["bucket_name"]
    backup_root = backup_restore_env["backup_root"]

    asyncio.run(_seed_database(database_url))

    backup_dir = create_backup(str(backup_root))
    manifest = load_manifest(backup_dir)
    dump_path = backup_dir / str(manifest["pg_dump_path"])

    assert dump_path.exists()
    assert dump_path.stat().st_size > 0
    assert manifest["db_row_counts"] == {
        "evaluation_runs": 3,
        "champions": 1,
        "drift_reports": 2,
        "audit_logs": 0,
    }
    assert manifest["sha256"] == sha256_file(dump_path)

    _recreate_database(backup_restore_env["parsed"], backup_restore_env["database_name"])
    _run_alembic_upgrade(database_url, backup_restore_env["repo_root"])
    _clear_artifact_bucket(bucket_name)

    restore_backup(str(backup_dir))

    assert asyncio.run(_table_count(database_url, "evaluation_runs")) == 3
    assert asyncio.run(_table_count(database_url, "model_champions")) == 1
    assert asyncio.run(_table_count(database_url, "drift_reports")) == 2
    assert asyncio.run(_table_count(database_url, "audit_logs")) == 0
    assert _artifact_exists(bucket_name, "integration/seed-artifact.txt") is True


def test_restore_rejects_checksum_mismatch(tmp_path: Path, monkeypatch) -> None:
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir(parents=True)
    dump_path = backup_dir / "postgres.sql.gz"
    dump_path.write_bytes(b"not-a-real-dump")
    (backup_dir / "artifacts").mkdir()
    (backup_dir / "manifest.json").write_text(
        '{"timestamp":"20260507T000000Z","pg_dump_path":"postgres.sql.gz","minio_sync_path":"artifacts","db_row_counts":{"evaluation_runs":0,"champions":0,"drift_reports":0,"audit_logs":0},"sha256":"deadbeef"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://ares:ares@localhost:55432/ares_test")

    with pytest.raises(RestoreError, match="Checksum verification failed"):
        restore_backup(str(backup_dir))


def test_backup_rejects_non_postgres_database_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'local.db').as_posix()}")

    with pytest.raises(BackupError, match="PostgreSQL"):
        create_backup(str(tmp_path / "backups"))
