from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from ares.evaluators.base import BaseEvaluator
from ares.evaluators.classification import ClassificationEvaluator
from ares.evaluators.detection import DetectionEvaluator
from ares.evaluators.regression import RegressionEvaluator


class EvaluatorFactory(Protocol):
    def __call__(self, model_path: str, config: dict[str, Any] | None = None) -> BaseEvaluator: ...


class PluginManifest(BaseModel):
    name: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_.-]+$")
    version: str = Field(min_length=1)
    description: str = ""
    trusted: bool = False
    entry_point: str | None = None

    @field_validator("description")
    @classmethod
    def description_is_small(cls, value: str) -> str:
        if len(value) > 512:
            raise ValueError("description must be <= 512 characters")
        return value


@dataclass(frozen=True)
class EvaluatorPlugin:
    manifest: PluginManifest
    factory: EvaluatorFactory

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def description(self) -> str:
        return self.manifest.description


def validate_plugin_manifest(raw: dict[str, Any]) -> PluginManifest:
    return PluginManifest.model_validate(raw)


_BUILTINS: dict[str, EvaluatorPlugin] = {
    "classification": EvaluatorPlugin(PluginManifest(name="classification", version="1.0.0", description="Built-in classification evaluator", trusted=True), ClassificationEvaluator),
    "regression": EvaluatorPlugin(PluginManifest(name="regression", version="1.0.0", description="Built-in regression evaluator", trusted=True), RegressionEvaluator),
    "detection": EvaluatorPlugin(PluginManifest(name="detection", version="1.0.0", description="Built-in detection evaluator", trusted=True), DetectionEvaluator),
}


def _manifest_from_factory(name: str, factory: EvaluatorFactory, entry_point: str) -> PluginManifest:
    raw = getattr(factory, "ARES_PLUGIN_MANIFEST", None)
    if isinstance(raw, dict):
        manifest = validate_plugin_manifest({"name": name, "entry_point": entry_point, **raw})
    else:
        manifest = validate_plugin_manifest({"name": name, "version": "external", "entry_point": entry_point, "trusted": False})
    if manifest.name != name:
        raise ValueError("plugin manifest name must match entry point name")
    return manifest


def _load_entry_points() -> dict[str, EvaluatorPlugin]:
    loaded: dict[str, EvaluatorPlugin] = {}
    try:
        entry_points = metadata.entry_points(group="ares.evaluators")
    except Exception:
        return loaded
    for entry_point in entry_points:
        try:
            factory = entry_point.load()
            manifest = _manifest_from_factory(entry_point.name, factory, entry_point.value)
            loaded[entry_point.name] = EvaluatorPlugin(manifest=manifest, factory=factory)
        except (ValidationError, TypeError, ValueError, AttributeError):
            continue
        except Exception:
            continue
    return loaded


def list_evaluator_plugins() -> list[EvaluatorPlugin]:
    plugins = {**_BUILTINS, **_load_entry_points()}
    return sorted(plugins.values(), key=lambda plugin: plugin.name)


def get_evaluator_plugin(name: str) -> EvaluatorPlugin:
    plugins = {plugin.name: plugin for plugin in list_evaluator_plugins()}
    if name not in plugins:
        raise ValueError(f"unknown evaluator plugin: {name}")
    return plugins[name]


def create_evaluator(name: str, model_path: str, config: dict[str, Any] | None = None) -> BaseEvaluator:
    plugin = get_evaluator_plugin(name)
    evaluator = plugin.factory(model_path, config)
    if not isinstance(evaluator, BaseEvaluator):
        raise TypeError(f"evaluator plugin {name} did not return BaseEvaluator")
    return evaluator
