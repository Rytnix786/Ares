# Evaluator Plugin Authoring Guide

ARES loads evaluator plugins from Python entry points in the `ares.evaluators` group. A plugin factory must return an `ares.evaluators.base.BaseEvaluator` instance.

```toml
[project.entry-points."ares.evaluators"]
my-evaluator = "my_package.evaluator:create_evaluator"
```

Factories receive `(model_path: str, config: dict | None)` and should avoid network side effects during import. Plugins are trusted code, so install them only from reviewed packages and use an allowlist in production deployment policy.

List available evaluators with:

```bash
curl -H "X-API-Key: $ARES_API_KEY" "$ARES_API_ORIGIN/api/v1/evaluators"
```
