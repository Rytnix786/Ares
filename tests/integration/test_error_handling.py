"""Integration tests for error handling in API endpoints."""

from __future__ import annotations

import pytest

from ares.api.main import app
from ares.exceptions import (
    DatasetSchemaError,
    ModelLoadError,
    PredictionError,
)


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
