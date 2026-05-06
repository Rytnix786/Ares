# Evaluator Author Guide

Use evaluator plugins when a model type cannot be represented by built-in classification, regression, or detection evaluators.

1. Implement `BaseEvaluator` or an `EvaluatorPlugin` factory.
2. Publish an entry point under `ares.evaluator_plugins`.
3. Keep model loading deterministic and avoid network calls in constructors.
4. Add contract tests like `tests/unit/test_plugins.py`.
5. Document trust boundaries and required optional dependencies.

See `docs/evaluator-plugin-authoring.md` and `docs/plugin-authoring-guide.md`.
