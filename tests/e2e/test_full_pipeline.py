import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine

from ares.models import Base


def subprocess_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = prepare_sqlite_db(tmp_path)
    env.pop("MLFLOW_TRACKING_URI", None)
    for key in ("COV_CORE_SOURCE", "COV_CORE_CONFIG", "COV_CORE_DATAFILE"):
        env.pop(key, None)
    return env


def prepare_sqlite_db(tmp_path: Path) -> str:
    db_path = tmp_path / "ares_cli.db"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    # Use a synchronous engine just to initialize schema quickly.
    # The CLI uses the async driver (aiosqlite) against the same file.
    sync_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    return database_url


@pytest.mark.e2e
def test_cli_failure_json(tmp_path: Path):
    out = tmp_path / "result.json"
    env = subprocess_env(tmp_path)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_evaluation.py",
            "--model-path",
            "missing",
            "--commit-sha",
            "abc",
            "--dataset-path",
            str(tmp_path / "missing.csv"),
            "--output-json",
            str(out),
        ],
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 1
    payload = json.loads(out.read_text())
    assert payload["passed"] is False
    assert payload["error_type"]


@pytest.mark.e2e
def test_cli_success(tmp_path: Path):
    data = tmp_path / "val.csv"
    pd.DataFrame(
        {
            "id": [f"row-{i}" for i in range(12)],
            "input": [
                '{"text": "clearly positive stable example"}',
                '{"text": "failed broken escalation example"}',
                '{"text": "mostly positive production traffic"}',
                '{"text": "ambiguous but still negative"}',
                '{"text": "clearly positive stable example"}',
                '{"text": "failed broken escalation example"}',
                '{"text": "mostly positive production traffic"}',
                '{"text": "ambiguous but still negative"}',
                '{"text": "mostly positive production traffic"}',
                '{"text": "mostly negative production traffic failed"}',
                '{"text": "mostly positive production traffic"}',
                '{"text": "mostly negative production traffic failed"}',
            ],
            "expected_label": [
                "positive",
                "negative",
                "positive",
                "negative",
                "positive",
                "negative",
                "positive",
                "negative",
                "positive",
                "negative",
                "positive",
                "negative",
            ],
            "slice": [
                "easy",
                "critical",
                "typical",
                "edge_case",
                "easy",
                "critical",
                "typical",
                "edge_case",
                "typical",
                "typical",
                "typical",
                "typical",
            ],
            "difficulty": [1, 5, 2, 4, 1, 5, 2, 4, 2, 2, 2, 2],
        }
    ).to_csv(data, index=False)
    out = tmp_path / "result.json"
    env = subprocess_env(tmp_path)
    env["GOLDEN_SET_SKIP_CHECKSUM"] = "true"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_evaluation.py",
            "--model-path",
            "models/candidate.json",
            "--commit-sha",
            "abc",
            "--dataset-path",
            str(data),
            "--output-json",
            str(out),
        ],
        text=True,
        env=env,
        timeout=60,
    )
    assert proc.returncode == 0
    assert json.loads(out.read_text())["run_id"]
