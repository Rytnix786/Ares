#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_step(label: str, command: list[str]) -> None:
    print(f"\n==> {label}")
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    run_step("Ruff", [PYTHON, "-m", "ruff", "check", "."])
    run_step("Mypy", [PYTHON, "-m", "mypy", "ares"])
    run_step(
        "Pytest with reports",
        [
            PYTHON,
            "-m",
            "pytest",
            "--cov=ares",
            "--cov-fail-under=92",
            "--cov-report=term-missing",
            "--cov-report=xml:reports/coverage.xml",
            "--junitxml=reports/test-results.xml",
        ],
    )
    run_step("Docker Compose config", ["docker", "compose", "config", "-q"])
    run_step("DVC dry run", [PYTHON, "-m", "dvc", "repro", "--dry"])
    run_step(
        "Targeted compile check",
        [
            PYTHON,
            "-m",
            "compileall",
            "ares",
            "dashboard",
            "scripts",
            "tests",
        ],
    )
    print("\nVerification complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())