from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ares.api.auth import APIKeyPrincipal, require_api_key
from ares.api.main import app
from ares.db import crud
from ares.db.session import get_db
from ares.models import Base, ChampionRollback, EvaluationRun
from scripts import rollback as rollback_cli


async def _create_seeded_champions(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        first = EvaluationRun(
            id="rollback-cli-run-1",
            commit_sha="rollback-cli-sha-1",
            model_name="rollback-cli-model",
            model_version="stable",
            branch="test",
            pr_number=1,
            overall_f1=0.91,
            overall_accuracy=0.92,
            overall_precision=0.93,
            overall_recall=0.94,
            latency_p50_ms=5.0,
            latency_p99_ms=10.0,
            model_size_mb=1.0,
            slice_metrics={"critical": {"f1": 0.91, "is_critical": True}},
            gate_config_snapshot={"critical_slice_min_f1": 0.6},
            metadata_json={},
            passed=True,
            failure_reason=None,
            golden_set_version="v1.0.0",
            n_samples_evaluated=10,
            duration_seconds=0.1,
            mlflow_status="skipped",
        )
        second = EvaluationRun(
            id="rollback-cli-run-2",
            commit_sha="rollback-cli-sha-2",
            model_name="rollback-cli-model",
            model_version="bad-rollout",
            branch="test",
            pr_number=2,
            overall_f1=0.95,
            overall_accuracy=0.96,
            overall_precision=0.97,
            overall_recall=0.98,
            latency_p50_ms=4.0,
            latency_p99_ms=9.0,
            model_size_mb=1.0,
            slice_metrics={"critical": {"f1": 0.95, "is_critical": True}},
            gate_config_snapshot={"critical_slice_min_f1": 0.6},
            metadata_json={},
            passed=True,
            failure_reason=None,
            golden_set_version="v1.0.0",
            n_samples_evaluated=10,
            duration_seconds=0.1,
            mlflow_status="skipped",
        )
        session.add_all([first, second])
        await session.flush()
        await crud.promote_champion(session, "rollback-cli-model", first.id, "tester", "initial")
        await crud.promote_champion(session, "rollback-cli-model", second.id, "tester", "bad rollout")
        await session.commit()
    return sessionmaker


def test_rollback_cli_rolls_back_seeded_champion_and_records_audit(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'rollback_cli.db').as_posix()}"
    sessionmaker = asyncio.run(_create_seeded_champions(database_url))

    async def override_get_db():
        async with sessionmaker() as session:
            async with session.begin():
                yield session

    async def override_require_api_key():
        return APIKeyPrincipal(
            key="test-key",
            key_id="test-key",
            scopes=frozenset({"read", "write", "admin"}),
        )

    class InProcessAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            super().__init__(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
                timeout=kwargs.get("timeout", 30.0),
            )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_api_key] = override_require_api_key
    monkeypatch.setattr(rollback_cli.httpx, "AsyncClient", InProcessAsyncClient)
    monkeypatch.setattr(rollback_cli.settings, "ARES_API_URL", "http://testserver/api/v1")
    monkeypatch.setattr(rollback_cli.settings, "ARES_API_KEYS", ["test-key"])
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "rollback.py",
            "--model-name",
            "rollback-cli-model",
            "--reason",
            "incident INC-CLI rollback",
        ],
    )

    try:
        rollback_cli.main()
    finally:
        app.dependency_overrides.clear()

    payload = json.loads(capsys.readouterr().out)
    assert payload["model_name"] == "rollback-cli-model"
    assert payload["dry_run"] is False
    assert payload["from_run_id"] == "rollback-cli-run-2"
    assert payload["to_run_id"] == "rollback-cli-run-1"
    assert payload["champion"]["champion_run_id"] == "rollback-cli-run-1"

    async def verify_database_state() -> None:
        async with sessionmaker() as session:
            active = await crud.get_active_champion(session, "rollback-cli-model")
            assert active is not None
            assert active.champion_run_id == "rollback-cli-run-1"
            records = await crud.list_champion_rollbacks(session, "rollback-cli-model")
            assert len(records) == 1
            record: ChampionRollback = records[0]
            assert record.from_run_id == "rollback-cli-run-2"
            assert record.to_run_id == "rollback-cli-run-1"
            assert record.actor == "rollback_cli"
            assert record.reason == "incident INC-CLI rollback"
            assert record.status == "completed"

    asyncio.run(verify_database_state())
    asyncio.run(sessionmaker.kw["bind"].dispose())
