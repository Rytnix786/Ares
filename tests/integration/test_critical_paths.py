from __future__ import annotations

import pytest

from ares.gate.rules_engine import evaluate


@pytest.mark.integration
def test_gate_critical_path_passes() -> None:
    decision = evaluate({"overall_f1": 0.9}, {"overall_f1": 0.89}, {"critical": {"f1": 0.9}})
    assert decision.passed is True
