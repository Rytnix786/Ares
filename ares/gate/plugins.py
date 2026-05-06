from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any, Protocol

from ares.gate import rules_engine
from ares.gate.decision import GateDecision


class GatePlugin(Protocol):
    name: str
    version: str

    def evaluate(
        self,
        new_metrics: Mapping[str, float],
        champion_metrics: Mapping[str, float],
        slice_metrics: Mapping[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        n_samples: int = 1,
    ) -> GateDecision: ...


@dataclass(frozen=True)
class GatePluginMetadata:
    name: str
    version: str
    description: str = ""


class GatePluginError(RuntimeError):
    pass


class DefaultGatePlugin:
    name = "default"
    version = "1.0.0"
    description = "ARES built-in regression gate rules engine"

    def evaluate(
        self,
        new_metrics: Mapping[str, float],
        champion_metrics: Mapping[str, float],
        slice_metrics: Mapping[str, Any] | None = None,
        config: dict[str, Any] | None = None,
        n_samples: int = 1,
    ) -> GateDecision:
        return rules_engine.evaluate(new_metrics, champion_metrics, slice_metrics, config, n_samples)


class GatePluginRegistry:
    def __init__(self, plugins: Mapping[str, GatePlugin] | None = None) -> None:
        self._plugins: dict[str, GatePlugin] = {"default": DefaultGatePlugin()}
        if plugins:
            for name, plugin in plugins.items():
                self.register(name, plugin)

    def register(self, name: str, plugin: GatePlugin) -> None:
        if not name or not name.replace("-", "_").isidentifier():
            raise GatePluginError(f"Invalid gate plugin name: {name!r}")
        if not callable(getattr(plugin, "evaluate", None)):
            raise GatePluginError(f"Gate plugin {name!r} does not expose evaluate()")
        self._plugins[name] = plugin

    def get(self, name: str = "default") -> GatePlugin:
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise GatePluginError(f"Unknown gate plugin: {name}") from exc

    def list(self) -> list[GatePluginMetadata]:
        return [
            GatePluginMetadata(
                name=name,
                version=str(getattr(plugin, "version", "0.0.0")),
                description=str(getattr(plugin, "description", "")),
            )
            for name, plugin in sorted(self._plugins.items())
        ]

    @classmethod
    def discover(cls, group: str = "ares.gate_plugins") -> GatePluginRegistry:
        registry = cls()
        for ep in entry_points(group=group):
            try:
                plugin = ep.load()
                plugin_obj = plugin() if isinstance(plugin, type) else plugin
                registry.register(ep.name, plugin_obj)
            except Exception as exc:
                raise GatePluginError(f"Failed to load gate plugin {ep.name}: {exc}") from exc
        return registry


def evaluate_with_plugin(
    plugin_name: str,
    new_metrics: Mapping[str, float],
    champion_metrics: Mapping[str, float],
    slice_metrics: Mapping[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    n_samples: int = 1,
    registry: GatePluginRegistry | None = None,
) -> GateDecision:
    active_registry = registry or GatePluginRegistry.discover()
    return active_registry.get(plugin_name).evaluate(new_metrics, champion_metrics, slice_metrics, config, n_samples)
