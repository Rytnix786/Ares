import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("ARES_API_KEYS", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./tests/ares_test.db")
os.environ.setdefault("GOLDEN_SET_SKIP_CHECKSUM", "true")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ares.api.main import app
from ares.db.session import get_db
from ares.models import Base, DriftReportRecord, EvaluationRun, ModelChampion


class _FallbackBenchmark:
    """Minimal pytest-benchmark-compatible fixture for environments without the plugin."""

    def __call__(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    def pedantic(self, func: Callable[[], Any], *, rounds: int = 1, **_: Any) -> Any:
        result: Any = None
        for _round in range(rounds):
            result = func()
        return result


@pytest.fixture
def benchmark() -> _FallbackBenchmark:
    return _FallbackBenchmark()

TEST_DB_PATH = Path("tests") / f"ares_test_{uuid.uuid4().hex}.db"
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"


@pytest_asyncio.fixture(scope="session")
async def engine():
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.unlink(TEST_DB_PATH)


@pytest_asyncio.fixture
async def async_session(engine):
    async with engine.connect() as conn:
        await conn.begin()
        async_session = async_sessionmaker(bind=conn, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            await session.begin_nested()
            yield session
            await session.rollback()
        await conn.rollback()


@pytest_asyncio.fixture
async def db_session(async_session):
    yield async_session


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_dataset():
    return [
        {"id": "1", "input": '{"text": "clearly positive stable example"}', "expected_label": "positive", "slice": "easy", "difficulty": 1},
        {"id": "2", "input": '{"text": "failed broken escalation example"}', "expected_label": "negative", "slice": "critical", "difficulty": 5},
        {"id": "3", "input": '{"text": "mostly positive production traffic"}', "expected_label": "positive", "slice": "typical", "difficulty": 2},
        {"id": "4", "input": '{"text": "ambiguous but still negative"}', "expected_label": "negative", "slice": "edge_case", "difficulty": 4},
    ]


@pytest_asyncio.fixture
async def sample_run(async_session):
    run = EvaluationRun(
        id="run-1",
        commit_sha="abc123",
        model_name="default-model",
        model_version="candidate",
        branch="test",
        pr_number=1,
        overall_f1=0.9,
        overall_accuracy=0.9,
        overall_precision=0.9,
        overall_recall=0.9,
        latency_p50_ms=5.0,
        latency_p99_ms=10.0,
        model_size_mb=1.0,
        slice_metrics={"critical": {"f1": 0.9, "passed_critical_threshold": True, "is_critical": True}},
        gate_config_snapshot={"critical_slice_min_f1": 0.6},
        metadata_json={},
        passed=True,
        failure_reason=None,
        golden_set_version="v1.0.0",
        n_samples_evaluated=4,
        duration_seconds=0.2,
        mlflow_run_id=None,
        artifact_uri=None,
        mlflow_status="skipped",
        mlflow_error=None,
    )
    async_session.add(run)
    await async_session.flush()
    return run


@pytest_asyncio.fixture
async def sample_run_2(async_session):
    run = EvaluationRun(
        id="run-2",
        commit_sha="def456",
        model_name="default-model",
        model_version="candidate",
        branch="test",
        pr_number=2,
        overall_f1=0.9,
        overall_accuracy=0.9,
        overall_precision=0.9,
        overall_recall=0.9,
        latency_p50_ms=5.0,
        latency_p99_ms=10.0,
        model_size_mb=1.0,
        slice_metrics={"critical": {"f1": 0.9, "passed_critical_threshold": True, "is_critical": True}},
        gate_config_snapshot={"critical_slice_min_f1": 0.6},
        metadata_json={},
        passed=True,
        failure_reason=None,
        golden_set_version="v1.0.0",
        n_samples_evaluated=4,
        duration_seconds=0.2,
        mlflow_run_id=None,
        artifact_uri=None,
        mlflow_status="skipped",
        mlflow_error=None,
    )
    async_session.add(run)
    await async_session.flush()
    return run


@pytest_asyncio.fixture
async def sample_champion(db_session: AsyncSession, sample_run: EvaluationRun):
    champion = ModelChampion(
        id="champ-1",
        model_name="default-model",
        champion_run_id=sample_run.id,
        promoted_by="test",
        promotion_reason="fixture",
        is_active=True,
    )
    db_session.add(champion)
    await db_session.flush()
    return champion


@pytest_asyncio.fixture
async def sample_drift_report(async_session):
    report = DriftReportRecord(
        id="drift-1",
        model_name="default-model",
        feature="feature1",
        kl_divergence=0.15,
        psi=0.12,
        is_alerting=True,
        severity="high",
        payload={"details": "test"},
    )
    async_session.add(report)
    await async_session.flush()
    return report
