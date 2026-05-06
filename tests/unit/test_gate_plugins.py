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


def test_register_rejects_invalid_name() -> None:
    registry = GatePluginRegistry()
    with pytest.raises(GatePluginError, match="Invalid gate plugin name"):
        registry.register("123-invalid", AlwaysPassGate())
    with pytest.raises(GatePluginError, match="Invalid gate plugin name"):
        registry.register("", AlwaysPassGate())


def test_list_returns_sorted_metadata() -> None:
    registry = GatePluginRegistry({"always_pass": AlwaysPassGate()})
    metadata = registry.list()
    names = [m.name for m in metadata]
    assert names == ["always_pass", "default"]
    assert all(isinstance(m.version, str) for m in metadata)
    assert all(isinstance(m.description, str) for m in metadata)


def test_empty_registry_keeps_default_plugin() -> None:
    registry = GatePluginRegistry({})

    assert [entry.name for entry in registry.list()] == ["default"]


def test_duplicate_registration_overwrites_existing_plugin() -> None:
    registry = GatePluginRegistry()
    first = AlwaysPassGate()
    second = AlwaysPassGate()

    registry.register("always_pass", first)
    registry.register("always_pass", second)

    assert registry.get("always_pass") is second


def test_discover_loads_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeEntryPoint:
        name = "fake_plugin"

        def load(self) -> AlwaysPassGate:
            return AlwaysPassGate()

    def fake_entry_points(*, group: str) -> list[FakeEntryPoint]:
        return [FakeEntryPoint()]

    monkeypatch.setattr("ares.gate.plugins.entry_points", fake_entry_points)
    registry = GatePluginRegistry.discover()
    assert "fake_plugin" in {m.name for m in registry.list()}


def test_discover_raises_on_load_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenEntryPoint:
        name = "broken"

        def load(self) -> None:
            raise RuntimeError("boom")

    def fake_entry_points(*, group: str) -> list[BrokenEntryPoint]:
        return [BrokenEntryPoint()]

    monkeypatch.setattr("ares.gate.plugins.entry_points", fake_entry_points)
    with pytest.raises(GatePluginError, match="Failed to load gate plugin broken"):
        GatePluginRegistry.discover()
