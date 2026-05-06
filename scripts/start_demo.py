#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.error import URLError
from urllib.request import Request, urlopen

from ares.api.auth import hash_api_key
from ares.config import settings
from ares.db import crud
from ares.db.crud_api_keys import create_api_key, list_api_keys
from ares.db.session import get_sessionmaker


class DemoStartupError(RuntimeError):
    pass


@dataclass(frozen=True)
class DemoRunSpec:
    run_id: str
    commit_sha: str
    passed: bool
    overall_f1: float
    overall_accuracy: float


def _ensure_docker_compose() -> None:
    try:
        subprocess.run(["docker", "compose", "version"], check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise DemoStartupError("Docker is not available") from exc
    except subprocess.CalledProcessError as exc:
        raise DemoStartupError(f"Docker Compose is not available: {exc.stderr or exc.stdout or exc}") from exc


def _run_compose(args: list[str]) -> None:
    subprocess.run(["docker", "compose", *args], check=True)


def _wait_for_ready(url: str, timeout_seconds: int = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            request = Request(url, headers={"Accept": "application/json"})
            with urlopen(request, timeout=5) as response:
                if response.status == 200:
                    json.loads(response.read().decode("utf-8"))
                    return
        except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            last_error = exc
            time.sleep(2)
    raise DemoStartupError(f"health check did not become ready within {timeout_seconds}s: {last_error}")


async def _seed_database() -> tuple[list[str], str, list[str], str]:
    run_specs = [
        DemoRunSpec("demo-run-001", "demo-commit-001", True, 0.93, 0.95),
        DemoRunSpec("demo-run-002", "demo-commit-002", True, 0.91, 0.93),
        DemoRunSpec("demo-run-003", "demo-commit-003", False, 0.82, 0.84),
    ]
    raw_api_key = "demo-api-key"

    async with get_sessionmaker()() as session:
        async with session.begin():
            seeded_runs: list[str] = []
            for spec in run_specs:
                existing = await crud.get_cached_evaluation(session, spec.commit_sha, settings.GOLDEN_SET_VERSION, "demo-model")
                if existing is None:
                    await crud.create_evaluation_run(
                        session,
                        id=spec.run_id,
                        commit_sha=spec.commit_sha,
                        model_name="demo-model",
                        passed=spec.passed,
                        overall_f1=spec.overall_f1,
                        overall_accuracy=spec.overall_accuracy,
                        overall_precision=spec.overall_f1,
                        overall_recall=spec.overall_accuracy,
                        golden_set_version=settings.GOLDEN_SET_VERSION,
                        n_samples_evaluated=128,
                        failure_reason=None if spec.passed else "demo failure",
                    )
                    seeded_runs.append(spec.run_id)

            champion = await crud.get_active_champion(session, "demo-model")
            if champion is None or champion.champion_run_id != "demo-run-001":
                await crud.promote_champion(session, "demo-model", "demo-run-001", "start_demo", "demo baseline")

            reports = await crud.list_drift_reports(session, model_name="demo-model")
            report_features = {report.feature for report in reports}
            for feature, psi, kl, severity in [("confidence", 0.12, 0.08, "warning"), ("response_length", 0.18, 0.14, "critical")]:
                if feature not in report_features:
                    await crud.create_drift_report(
                        session,
                        model_name="demo-model",
                        feature=feature,
                        kl_divergence=kl,
                        psi=psi,
                        is_alerting=True,
                        severity=severity,
                        payload={"source": "start_demo"},
                    )

            keys = await list_api_keys(session)
            if not any(key.name == raw_api_key for key in keys):
                await create_api_key(
                    session,
                    key_hash=hash_api_key(raw_api_key),
                    name=raw_api_key,
                    scopes=["read", "write"],
                    rate_limit=settings.API_KEY_DEFAULT_RATE_LIMIT,
                    expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=30),
                )

            await session.commit()

    return [spec.run_id for spec in run_specs], "demo-run-001", ["confidence", "response_length"], raw_api_key


def main() -> int:
    _ensure_docker_compose()
    _run_compose(["up", "-d"])
    _wait_for_ready("http://localhost:8000/health/ready")
    _run_compose(["exec", "-T", "api", "python", "-m", "alembic", "upgrade", "head"])

    seeded_runs, champion_run_id, drift_features, api_key = asyncio.run(_seed_database())

    print("Demo stack ready")
    print("API docs: http://localhost:8000/docs")
    print(f"Dashboard: {settings.ARES_DASHBOARD_URL}")
    print(f"API key: {api_key}")
    print(f"Seeded runs: {', '.join(seeded_runs)}")
    print(f"Champion run: {champion_run_id}")
    print(f"Drift reports: {', '.join(drift_features)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())