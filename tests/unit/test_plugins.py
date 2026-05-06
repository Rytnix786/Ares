from __future__ import annotations

import pandas as pd
import pytest
from pydantic import ValidationError

from ares.evaluators.base import BaseEvaluator
from ares.plugins import create_evaluator, list_evaluator_plugins, validate_plugin_manifest


class FakeEvaluator(BaseEvaluator):
    def load_model(self) -> None:
        self._model = object()

    def predict(self, inputs: list[object]) -> list[str]:
        return ["positive" for _ in inputs]

    def compute_metrics(self, predictions: list[object], ground_truth: list[object]) -> dict[str, float]:
        return {"overall_f1": 1.0, "overall_accuracy": 1.0}


def fake_factory(model_path: str, config: dict | None = None) -> BaseEvaluator:
    return FakeEvaluator(model_path, config)


fake_factory.ARES_PLUGIN_MANIFEST = {"version": "0.1.0", "description": "fake external evaluator", "trusted": True}


class _EntryPoint:
    name = "fake_external"
    value = "fake_package:fake_factory"

    def load(self):
        return fake_factory


class _BadEntryPoint:
    name = "bad_external"
    value = "bad_package:factory"

    def load(self):
        def bad_factory(_model_path: str, _config: dict | None = None):
            return object()
        bad_factory.ARES_PLUGIN_MANIFEST = {"name": "wrong", "version": "0.1.0"}
        return bad_factory


def test_plugin_manifest_validation_rejects_bad_names():
    with pytest.raises(ValidationError):
        validate_plugin_manifest({"name": "bad name", "version": "1"})


def test_entry_point_plugin_loads_without_core_edits(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("ares.plugins.evaluators.metadata.entry_points", lambda group: [_EntryPoint()] if group == "ares.evaluators" else [])
    names = {plugin.name for plugin in list_evaluator_plugins()}
    assert "fake_external" in names
    evaluator = create_evaluator("fake_external", "memory://fake")
    result = evaluator.evaluate(pd.DataFrame({"id": ["1"], "input": ["x"], "expected_label": ["positive"], "slice": ["critical"]}))
    assert result.passed is True


def test_bad_plugin_is_isolated_and_not_listed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("ares.plugins.evaluators.metadata.entry_points", lambda group: [_BadEntryPoint()] if group == "ares.evaluators" else [])
    names = {plugin.name for plugin in list_evaluator_plugins()}
    assert "bad_external" not in names
