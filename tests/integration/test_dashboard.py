from __future__ import annotations

import importlib
import importlib.util


def test_dashboard_pages_importable() -> None:
    for module in [
        "dashboard.pages.01_leaderboard",
        "dashboard.pages.02_drill_down",
        "dashboard.pages.03_drift_monitor",
        "dashboard.pages.04_model_comparison",
        "dashboard.pages.05_promotion_workflow",
        "dashboard.pages.06_alerts",
    ]:
        assert importlib.util.find_spec(module) is not None
