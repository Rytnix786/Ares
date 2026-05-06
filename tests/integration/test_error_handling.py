"""Integration tests for error handling in API endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ares.api.main import ERROR_REMEDIATION, ERROR_STATUS, app
from ares.exceptions import (
    APIKeyNotConfiguredError,
    AresException,
    ChampionNotFoundError,
    ComparisonError,
    ConcurrentPromotionError,
    ConfigurationInvalidError,
    ConfigurationMissingError,
    DatasetChecksumError,
    DatasetNotFoundError,
    DatasetSchemaError,
    DatasetValidationError,
    EvaluationTimeoutError,
    FeatureFlagError,
    GateConfigError,
    GateDecisionError,
    InsufficientScopeError,
    InvalidAPIKeyError,
    MetricComputationError,
    ModelLoadError,
    PredictionError,
    PromotionError,
    RateLimitExceededError,
)

ERROR_RESPONSE_SHAPE = {
    "category": "str",
    "details": "object",
    "error_code": "str",
    "message": "str",
    "remediation": "str",
    "request_id": "str|null",
    "retryable": "bool",
}


def _category(exc: AresException) -> str:
    return exc.__class__.__mro__[1].__name__.replace("Error", "").lower()


def _snapshot_entry(exc: AresException, message_shape: str) -> dict[str, object]:
    return {
        "error_code": exc.error_code,
        "category": _category(exc),
        "http_status": ERROR_STATUS.get(exc.error_code, 400),
        "message": exc.user_message,
        "message_shape": message_shape,
        "details_keys": sorted(exc.details),
        "remediation": ERROR_REMEDIATION.get(
            exc.error_code,
            "Review the error details, correct the request, and retry.",
        ),
        "retryable": exc.error_code.endswith("TIMEOUT"),
    }


def _expected_error_catalog() -> dict[str, object]:
    entries = [
        _snapshot_entry(
            APIKeyNotConfiguredError("production"),
            "API keys are not configured for environment: {environment}",
        ),
        _snapshot_entry(
            ChampionNotFoundError("fraud-model"),
            "No active champion found for model: {model_name}",
        ),
        _snapshot_entry(
            ComparisonError("metric mismatch"),
            "Failed to compare candidate to champion: {reason}",
        ),
        _snapshot_entry(
            ConcurrentPromotionError("fraud-model"),
            "Concurrent promotion attempt for model: {model_name}",
        ),
        _snapshot_entry(
            ConfigurationInvalidError("ARES_API_URL", "malformed URL"),
            "Invalid configuration for {config_key}: {reason}",
        ),
        _snapshot_entry(
            ConfigurationMissingError("DATABASE_URL"),
            "Required configuration missing: {config_key}",
        ),
        _snapshot_entry(
            DatasetChecksumError("abc123", "def456"),
            "Dataset checksum mismatch: expected {expected}, got {actual}",
        ),
        _snapshot_entry(
            DatasetNotFoundError("/data/missing.csv"),
            "Dataset not found: {dataset_path}",
        ),
        _snapshot_entry(DatasetSchemaError(missing_columns=[], extra_columns=[]), "Dataset schema is invalid"),
        _snapshot_entry(
            DatasetValidationError("row_count", "too few rows"),
            "Dataset validation failed ({validation_type}): {reason}",
        ),
        _snapshot_entry(
            EvaluationTimeoutError(30.0),
            "Evaluation exceeded time limit of {timeout_seconds}s",
        ),
        _snapshot_entry(
            FeatureFlagError("new_gate", "invalid value"),
            "Feature flag error ({flag_name}): {reason}",
        ),
        _snapshot_entry(
            GateConfigError("max_regression_f1", "must be positive"),
            "Invalid gate configuration for {config_key}: {reason}",
        ),
        _snapshot_entry(
            GateDecisionError("missing champion metrics"),
            "Failed to make gate decision: {reason}",
        ),
        _snapshot_entry(
            InsufficientScopeError("admin", ["read"]),
            "API key lacks required scope: {required_scope}",
        ),
        _snapshot_entry(InvalidAPIKeyError(), "Invalid API key"),
        _snapshot_entry(
            MetricComputationError("f1_score", "division by zero"),
            "Failed to compute metric {metric_name}: {reason}",
        ),
        _snapshot_entry(
            ModelLoadError("/models/model.pkl", "file not found"),
            "Failed to load model from {model_path}: {reason}",
        ),
        _snapshot_entry(PredictionError("invalid input shape"), "Model prediction failed: {reason}"),
        _snapshot_entry(
            PromotionError("fraud-model", "target run did not pass"),
            "Failed to promote champion for {model_name}: {reason}",
        ),
        {
            "error_code": "HTTP_404",
            "category": "http",
            "http_status": 404,
            "message": "Not found",
            "message_shape": "{detail}",
            "details_keys": [],
            "remediation": "Review the endpoint documentation, required scopes, and request parameters before retrying.",
            "retryable": False,
        },
        {
            "error_code": "RATE_LIMIT_EXCEEDED",
            "category": "rate_limit",
            "http_status": 429,
            "message": "Rate limit exceeded",
            "message_shape": "Rate limit exceeded",
            "details_keys": [],
            "remediation": "Wait for the current rate-limit window to reset or use a key with an appropriate policy.",
            "retryable": True,
        },
        {
            "error_code": "VALIDATION_ERROR",
            "category": "validation",
            "http_status": 422,
            "message": "Request validation failed",
            "message_shape": "Request validation failed",
            "details_keys": ["errors"],
            "remediation": "Fix the fields identified in details and retry.",
            "retryable": False,
        },
    ]
    return {"response_shape": ERROR_RESPONSE_SHAPE, "errors": sorted(entries, key=lambda item: str(item["error_code"]))}


def _leaf_exception_codes() -> set[str]:
    exceptions = [
        APIKeyNotConfiguredError("production"),
        ChampionNotFoundError("fraud-model"),
        ComparisonError("metric mismatch"),
        ConcurrentPromotionError("fraud-model"),
        ConfigurationInvalidError("ARES_API_URL", "malformed URL"),
        ConfigurationMissingError("DATABASE_URL"),
        DatasetChecksumError("abc123", "def456"),
        DatasetNotFoundError("/data/missing.csv"),
        DatasetSchemaError(missing_columns=[], extra_columns=[]),
        DatasetValidationError("row_count", "too few rows"),
        EvaluationTimeoutError(30.0),
        FeatureFlagError("new_gate", "invalid value"),
        GateConfigError("max_regression_f1", "must be positive"),
        GateDecisionError("missing champion metrics"),
        InsufficientScopeError("admin", ["read"]),
        InvalidAPIKeyError(),
        MetricComputationError("f1_score", "division by zero"),
        ModelLoadError("/models/model.pkl", "file not found"),
        PredictionError("invalid input shape"),
        PromotionError("fraud-model", "target run did not pass"),
        RateLimitExceededError("10/minute"),
    ]
    return {exc.error_code for exc in exceptions}


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test that custom exceptions are handled correctly in API responses."""

    def test_ares_exception_returns_structured_error(self) -> None:
        """Test that AresException returns structured error response."""
        # This test verifies the exception handler is registered
        # We'll need to add an endpoint that raises an AresException
        # For now, we'll test the handler directly via a simulated scenario
        pass

    def test_error_response_schema(self) -> None:
        """Test that error responses match the ErrorResponse schema."""
        from ares.api.schemas.error import ErrorResponse
        
        # Test schema validation
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test message",
            details={"key": "value"},
        )
        assert error.error_code == "TEST_ERROR"
        assert error.message == "Test message"
        assert error.details == {"key": "value"}

    def test_dataset_schema_error_structure(self) -> None:
        """Test that DatasetSchemaError has correct structure."""
        exc = DatasetSchemaError(missing_columns=["id", "label"])
        error_dict = exc.to_dict()
        
        assert error_dict["error_code"] == "DATASET_SCHEMA_INVALID"
        assert "schema" in error_dict["message"].lower()
        assert error_dict["details"]["missing_columns"] == ["id", "label"]

    def test_model_load_error_structure(self) -> None:
        """Test that ModelLoadError has correct structure."""
        exc = ModelLoadError(
            model_path="/path/to/model.pkl",
            reason="File not found",
        )
        error_dict = exc.to_dict()
        
        assert error_dict["error_code"] == "MODEL_LOAD_FAILED"
        assert "model.pkl" in error_dict["message"]
        assert error_dict["details"]["model_path"] == "/path/to/model.pkl"
        assert error_dict["details"]["reason"] == "File not found"

    def test_prediction_error_structure(self) -> None:
        """Test that PredictionError has correct structure."""
        exc = PredictionError(
            reason="Invalid input shape",
            details={"input_shape": (10,), "expected_shape": (5,)},
        )
        error_dict = exc.to_dict()
        
        assert error_dict["error_code"] == "PREDICTION_FAILED"
        assert "Invalid input shape" in error_dict["message"]
        assert error_dict["details"]["reason"] == "Invalid input shape"
        assert error_dict["details"]["input_shape"] == (10,)

    def test_exception_handler_registered(self) -> None:
        """Test that the AresException handler is registered in the app."""
        # Check that the exception handler is registered
        from ares.exceptions import AresException
        
        handlers = app.exception_handlers
        assert AresException in handlers, "AresException handler not registered"

    def test_error_taxonomy_matches_golden_snapshot(self) -> None:
        """Lock the production error taxonomy response shape and status mapping."""
        golden_path = Path("tests/golden/error_catalog.json")
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        assert _expected_error_catalog() == golden

    def test_error_taxonomy_snapshot_covers_all_exception_codes(self) -> None:
        """Ensure new domain error codes cannot be added without updating the catalog."""
        golden_path = Path("tests/golden/error_catalog.json")
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
        catalog_codes = {entry["error_code"] for entry in golden["errors"]}
        assert _leaf_exception_codes().issubset(catalog_codes)
