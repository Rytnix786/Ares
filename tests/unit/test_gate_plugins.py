from __future__ import annotations

import pytest

from ares.gate.decision import GateDecision
from ares.gate.plugins import GatePluginError, GatePluginRegistry, evaluate_with_plugin
from ares.gate.rules_engine import evaluate


class AlwaysPassGate:
    name = "always_pass"
    version = "0.1.0"
    description = "test plugin"

    def evaluate(self, *_args: object, **_kwargs: object) -> GateDecision:
        return GateDecision("PASS", True, "custom pass", {}, [], True)


class BrokenGate:
    name = "broken"
    version = "0.1.0"


def test_default_gate_plugin_matches_core_rules() -> None:
    new_metrics = {"overall_f1": 0.90, "overall_accuracy": 0.91}
    champion_metrics = {"overall_f1": 0.89, "overall_accuracy": 0.90}

    registry = GatePluginRegistry()

    assert registry.get("default").evaluate(new_metrics, champion_metrics).verdict == evaluate(new_metrics, champion_metrics).verdict


def test_custom_gate_plugin_runs_without_core_edits() -> None:
    registry = GatePluginRegistry({"always_pass": AlwaysPassGate()})

    decision = evaluate_with_plugin("always_pass", {"overall_f1": 0.1}, {"overall_f1": 0.9}, registry=registry)

    assert decision.verdict == "PASS"
    assert decision.reason == "custom pass"


def test_gate_plugin_registry_isolates_failures() -> None:
    registry = GatePluginRegistry()

    with pytest.raises(GatePluginError):
        registry.register("bad", BrokenGate())  # type: ignore[arg-type]
    with pytest.raises(GatePluginError):
        registry.get("missing")
