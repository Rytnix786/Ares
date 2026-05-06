from __future__ import annotations

import os
import subprocess

import pytest


@pytest.mark.e2e
def test_sandbox_compose_smoke_is_available() -> None:
    if os.environ.get("ARES_RUN_DOCKER_SMOKE") != "1":
        pytest.skip("Set ARES_RUN_DOCKER_SMOKE=1 to run Docker Compose sandbox smoke")
    subprocess.run(["docker", "compose", "config"], check=True)
    subprocess.run(["python", "scripts/run_evaluation.py", "--model-path", "models/candidate.json", "--commit-sha", "sandbox", "--model-name", "default-model", "--split", "val"], check=True)
