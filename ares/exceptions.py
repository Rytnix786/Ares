"""Custom exception hierarchy for Ares domain errors.

All domain-specific errors should inherit from AresException.
Each exception has an error_code for programmatic handling and a user_message for display.
"""

from __future__ import annotations

from typing import Any


class AresException(Exception):
    """Base exception for all Ares domain errors."""

    def __init__(
        self,
        error_code: str,
        user_message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.error_code = error_code
        self.user_message = user_message
        self.details = details or {}
        super().__init__(self.user_message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_code": self.error_code,
            "message": self.user_message,
            "details": self.details,
        }


class EvaluationError(AresException):
    """Base exception for evaluation-related errors."""

    pass


class GateError(AresException):
    """Base exception for gate decision errors."""

    pass


class DatasetError(AresException):
    """Base exception for dataset-related errors."""

    pass


class ChampionError(AresException):
    """Base exception for champion management errors."""

    pass


class AuthError(AresException):
    """Base exception for authentication/authorization errors."""

    pass


class ConfigurationError(AresException):
    """Base exception for configuration errors."""

    pass


# Specific evaluation errors


class ModelLoadError(EvaluationError):
    """Raised when a model cannot be loaded."""

    def __init__(
        self,
        model_path: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="MODEL_LOAD_FAILED",
            user_message=f"Failed to load model from {model_path}: {reason}",
            details={"model_path": model_path, "reason": reason, **(details or {})},
        )


class PredictionError(EvaluationError):
    """Raised when model prediction fails."""

    def __init__(
        self,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="PREDICTION_FAILED",
            user_message=f"Model prediction failed: {reason}",
            details={"reason": reason, **(details or {})},
        )


class MetricComputationError(EvaluationError):
    """Raised when metric computation fails."""

    def __init__(
        self,
        metric_name: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="METRIC_COMPUTATION_FAILED",
            user_message=f"Failed to compute metric {metric_name}: {reason}",
            details={"metric_name": metric_name, "reason": reason, **(details or {})},
        )


class EvaluationTimeoutError(EvaluationError):
    """Raised when evaluation exceeds time limit."""

    def __init__(
        self,
        timeout_seconds: float,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="EVALUATION_TIMEOUT",
            user_message=f"Evaluation exceeded time limit of {timeout_seconds}s",
            details={"timeout_seconds": timeout_seconds, **(details or {})},
        )


# Specific gate errors


class GateConfigError(GateError):
    """Raised when gate configuration is invalid."""

    def __init__(
        self,
        config_key: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="GATE_CONFIG_INVALID",
            user_message=f"Invalid gate configuration for {config_key}: {reason}",
            details={"config_key": config_key, "reason": reason, **(details or {})},
        )


class GateDecisionError(GateError):
    """Raised when gate decision cannot be made."""

    def __init__(
        self,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="GATE_DECISION_FAILED",
            user_message=f"Failed to make gate decision: {reason}",
            details={"reason": reason, **(details or {})},
        )


class ComparisonError(GateError):
    """Raised when comparing candidate to champion fails."""

    def __init__(
        self,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="COMPARISON_FAILED",
            user_message=f"Failed to compare candidate to champion: {reason}",
            details={"reason": reason, **(details or {})},
        )


# Specific dataset errors


class DatasetValidationError(DatasetError):
    """Raised when dataset validation fails."""

    def __init__(
        self,
        validation_type: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="DATASET_VALIDATION_FAILED",
            user_message=f"Dataset validation failed ({validation_type}): {reason}",
            details={"validation_type": validation_type, "reason": reason, **(details or {})},
        )


class DatasetSchemaError(DatasetError):
    """Raised when dataset schema is invalid."""

    def __init__(
        self,
        missing_columns: list[str] | None = None,
        extra_columns: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="DATASET_SCHEMA_INVALID",
            user_message="Dataset schema is invalid",
            details={
                "missing_columns": missing_columns or [],
                "extra_columns": extra_columns or [],
                **(details or {}),
            },
        )


class DatasetChecksumError(DatasetError):
    """Raised when dataset checksum mismatch."""

    def __init__(
        self,
        expected: str,
        actual: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="DATASET_CHECKSUM_MISMATCH",
            user_message=f"Dataset checksum mismatch: expected {expected}, got {actual}",
            details={"expected_checksum": expected, "actual_checksum": actual, **(details or {})},
        )


class DatasetNotFoundError(DatasetError):
    """Raised when dataset file is not found."""

    def __init__(
        self,
        dataset_path: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="DATASET_NOT_FOUND",
            user_message=f"Dataset not found: {dataset_path}",
            details={"dataset_path": dataset_path, **(details or {})},
        )


# Specific champion errors


class ChampionNotFoundError(ChampionError):
    """Raised when champion is not found."""

    def __init__(
        self,
        model_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="CHAMPION_NOT_FOUND",
            user_message=f"No active champion found for model: {model_name}",
            details={"model_name": model_name, **(details or {})},
        )


class PromotionError(ChampionError):
    """Raised when champion promotion fails."""

    def __init__(
        self,
        model_name: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="PROMOTION_FAILED",
            user_message=f"Failed to promote champion for {model_name}: {reason}",
            details={"model_name": model_name, "reason": reason, **(details or {})},
        )


class ConcurrentPromotionError(ChampionError):
    """Raised when concurrent promotion attempts conflict."""

    def __init__(
        self,
        model_name: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="CONCURRENT_PROMOTION",
            user_message=f"Concurrent promotion attempt for model: {model_name}",
            details={"model_name": model_name, **(details or {})},
        )


# Specific auth errors


class InvalidAPIKeyError(AuthError):
    """Raised when API key is invalid."""

    def __init__(
        self,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="INVALID_API_KEY",
            user_message="Invalid API key",
            details=details or {},
        )


class APIKeyNotConfiguredError(AuthError):
    """Raised when API keys are not configured."""

    def __init__(
        self,
        environment: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="API_KEYS_NOT_CONFIGURED",
            user_message=f"API keys are not configured for environment: {environment}",
            details={"environment": environment, **(details or {})},
        )


class InsufficientScopeError(AuthError):
    """Raised when API key lacks required scope."""

    def __init__(
        self,
        required_scope: str,
        provided_scopes: list[str],
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="INSUFFICIENT_SCOPE",
            user_message=f"API key lacks required scope: {required_scope}",
            details={
                "required_scope": required_scope,
                "provided_scopes": provided_scopes,
                **(details or {}),
            },
        )


class RateLimitExceededError(AuthError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="RATE_LIMIT_EXCEEDED",
            user_message=f"Rate limit exceeded: {limit}",
            details={"limit": limit, **(details or {})},
        )


# Specific configuration errors


class ConfigurationMissingError(ConfigurationError):
    """Raised when required configuration is missing."""

    def __init__(
        self,
        config_key: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="CONFIGURATION_MISSING",
            user_message=f"Required configuration missing: {config_key}",
            details={"config_key": config_key, **(details or {})},
        )


class ConfigurationInvalidError(ConfigurationError):
    """Raised when configuration value is invalid."""

    def __init__(
        self,
        config_key: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="CONFIGURATION_INVALID",
            user_message=f"Invalid configuration for {config_key}: {reason}",
            details={"config_key": config_key, "reason": reason, **(details or {})},
        )


class FeatureFlagError(ConfigurationError):
    """Raised when feature flag operation fails."""

    def __init__(
        self,
        flag_name: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            error_code="FEATURE_FLAG_ERROR",
            user_message=f"Feature flag error ({flag_name}): {reason}",
            details={"flag_name": flag_name, "reason": reason, **(details or {})},
        )
