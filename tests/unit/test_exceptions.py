"""Unit tests for custom exception hierarchy."""

from __future__ import annotations

from ares.exceptions import (
    APIKeyNotConfiguredError,
    AresException,
    AuthError,
    ChampionError,
    ChampionNotFoundError,
    ComparisonError,
    ConcurrentPromotionError,
    ConfigurationError,
    ConfigurationInvalidError,
    ConfigurationMissingError,
    DatasetChecksumError,
    DatasetError,
    DatasetNotFoundError,
    DatasetSchemaError,
    DatasetValidationError,
    EvaluationError,
    EvaluationTimeoutError,
    FeatureFlagError,
    GateConfigError,
    GateDecisionError,
    GateError,
    InsufficientScopeError,
    InvalidAPIKeyError,
    MetricComputationError,
    ModelLoadError,
    PredictionError,
    PromotionError,
    RateLimitExceededError,
)


class TestAresException:
    """Test base AresException functionality."""

    def test_base_exception_initialization(self) -> None:
        """Test that base exception initializes correctly."""
        exc = AresException(
            error_code="TEST_ERROR",
            user_message="Test message",
            details={"key": "value"},
        )
        assert exc.error_code == "TEST_ERROR"
        assert exc.user_message == "Test message"
        assert exc.details == {"key": "value"}
        assert str(exc) == "Test message"

    def test_to_dict(self) -> None:
        """Test that exception converts to dict correctly."""
        exc = AresException(
            error_code="TEST_ERROR",
            user_message="Test message",
            details={"key": "value"},
        )
        result = exc.to_dict()
        assert result == {
            "error_code": "TEST_ERROR",
            "message": "Test message",
            "details": {"key": "value"},
        }

    def test_to_dict_without_details(self) -> None:
        """Test that exception converts to dict without details."""
        exc = AresException(
            error_code="TEST_ERROR",
            user_message="Test message",
        )
        result = exc.to_dict()
        assert result == {
            "error_code": "TEST_ERROR",
            "message": "Test message",
            "details": {},
        }


class TestEvaluationErrors:
    """Test evaluation-related exceptions."""

    def test_model_load_error(self) -> None:
        """Test ModelLoadError initialization."""
        exc = ModelLoadError(
            model_path="/path/to/model.pkl",
            reason="File not found",
        )
        assert exc.error_code == "MODEL_LOAD_FAILED"
        assert "model.pkl" in exc.user_message
        assert exc.details["model_path"] == "/path/to/model.pkl"
        assert exc.details["reason"] == "File not found"

    def test_prediction_error(self) -> None:
        """Test PredictionError initialization."""
        exc = PredictionError(reason="Invalid input shape")
        assert exc.error_code == "PREDICTION_FAILED"
        assert "Invalid input shape" in exc.user_message
        assert exc.details["reason"] == "Invalid input shape"

    def test_metric_computation_error(self) -> None:
        """Test MetricComputationError initialization."""
        exc = MetricComputationError(
            metric_name="f1_score",
            reason="Division by zero",
        )
        assert exc.error_code == "METRIC_COMPUTATION_FAILED"
        assert "f1_score" in exc.user_message
        assert exc.details["metric_name"] == "f1_score"

    def test_evaluation_timeout_error(self) -> None:
        """Test EvaluationTimeoutError initialization."""
        exc = EvaluationTimeoutError(timeout_seconds=30.0)
        assert exc.error_code == "EVALUATION_TIMEOUT"
        assert "30" in exc.user_message
        assert exc.details["timeout_seconds"] == 30.0


class TestGateErrors:
    """Test gate-related exceptions."""

    def test_gate_config_error(self) -> None:
        """Test GateConfigError initialization."""
        exc = GateConfigError(
            config_key="max_regression",
            reason="Must be positive",
        )
        assert exc.error_code == "GATE_CONFIG_INVALID"
        assert "max_regression" in exc.user_message
        assert exc.details["config_key"] == "max_regression"

    def test_gate_decision_error(self) -> None:
        """Test GateDecisionError initialization."""
        exc = GateDecisionError(reason="Missing champion metrics")
        assert exc.error_code == "GATE_DECISION_FAILED"
        assert "Missing champion metrics" in exc.user_message

    def test_comparison_error(self) -> None:
        """Test ComparisonError initialization."""
        exc = ComparisonError(reason="Metric mismatch")
        assert exc.error_code == "COMPARISON_FAILED"
        assert "Metric mismatch" in exc.user_message


class TestDatasetErrors:
    """Test dataset-related exceptions."""

    def test_dataset_validation_error(self) -> None:
        """Test DatasetValidationError initialization."""
        exc = DatasetValidationError(
            validation_type="row_count",
            reason="Too few rows",
        )
        assert exc.error_code == "DATASET_VALIDATION_FAILED"
        assert "row_count" in exc.user_message
        assert exc.details["validation_type"] == "row_count"

    def test_dataset_schema_error(self) -> None:
        """Test DatasetSchemaError initialization."""
        exc = DatasetSchemaError(
            missing_columns=["id", "label"],
            extra_columns=["extra_col"],
        )
        assert exc.error_code == "DATASET_SCHEMA_INVALID"
        assert exc.details["missing_columns"] == ["id", "label"]
        assert exc.details["extra_columns"] == ["extra_col"]

    def test_dataset_checksum_error(self) -> None:
        """Test DatasetChecksumError initialization."""
        exc = DatasetChecksumError(
            expected="abc123",
            actual="def456",
        )
        assert exc.error_code == "DATASET_CHECKSUM_MISMATCH"
        assert exc.details["expected_checksum"] == "abc123"
        assert exc.details["actual_checksum"] == "def456"

    def test_dataset_not_found_error(self) -> None:
        """Test DatasetNotFoundError initialization."""
        exc = DatasetNotFoundError(dataset_path="/path/to/data.csv")
        assert exc.error_code == "DATASET_NOT_FOUND"
        assert "/path/to/data.csv" in exc.user_message
        assert exc.details["dataset_path"] == "/path/to/data.csv"


class TestChampionErrors:
    """Test champion-related exceptions."""

    def test_champion_not_found_error(self) -> None:
        """Test ChampionNotFoundError initialization."""
        exc = ChampionNotFoundError(model_name="sentiment-model")
        assert exc.error_code == "CHAMPION_NOT_FOUND"
        assert "sentiment-model" in exc.user_message
        assert exc.details["model_name"] == "sentiment-model"

    def test_promotion_error(self) -> None:
        """Test PromotionError initialization."""
        exc = PromotionError(
            model_name="sentiment-model",
            reason="Database constraint violation",
        )
        assert exc.error_code == "PROMOTION_FAILED"
        assert "sentiment-model" in exc.user_message
        assert exc.details["model_name"] == "sentiment-model"

    def test_concurrent_promotion_error(self) -> None:
        """Test ConcurrentPromotionError initialization."""
        exc = ConcurrentPromotionError(model_name="sentiment-model")
        assert exc.error_code == "CONCURRENT_PROMOTION"
        assert "sentiment-model" in exc.user_message


class TestAuthErrors:
    """Test authentication-related exceptions."""

    def test_invalid_api_key_error(self) -> None:
        """Test InvalidAPIKeyError initialization."""
        exc = InvalidAPIKeyError()
        assert exc.error_code == "INVALID_API_KEY"
        assert exc.user_message == "Invalid API key"

    def test_api_key_not_configured_error(self) -> None:
        """Test APIKeyNotConfiguredError initialization."""
        exc = APIKeyNotConfiguredError(environment="production")
        assert exc.error_code == "API_KEYS_NOT_CONFIGURED"
        assert "production" in exc.user_message
        assert exc.details["environment"] == "production"

    def test_insufficient_scope_error(self) -> None:
        """Test InsufficientScopeError initialization."""
        exc = InsufficientScopeError(
            required_scope="admin",
            provided_scopes=["read"],
        )
        assert exc.error_code == "INSUFFICIENT_SCOPE"
        assert "admin" in exc.user_message
        assert exc.details["required_scope"] == "admin"
        assert exc.details["provided_scopes"] == ["read"]

    def test_rate_limit_exceeded_error(self) -> None:
        """Test RateLimitExceededError initialization."""
        exc = RateLimitExceededError(limit="10/minute")
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert "10/minute" in exc.user_message
        assert exc.details["limit"] == "10/minute"


class TestConfigurationErrors:
    """Test configuration-related exceptions."""

    def test_configuration_missing_error(self) -> None:
        """Test ConfigurationMissingError initialization."""
        exc = ConfigurationMissingError(config_key="DATABASE_URL")
        assert exc.error_code == "CONFIGURATION_MISSING"
        assert "DATABASE_URL" in exc.user_message
        assert exc.details["config_key"] == "DATABASE_URL"

    def test_configuration_invalid_error(self) -> None:
        """Test ConfigurationInvalidError initialization."""
        exc = ConfigurationInvalidError(
            config_key="DB_POOL_SIZE",
            reason="Must be positive integer",
        )
        assert exc.error_code == "CONFIGURATION_INVALID"
        assert "DB_POOL_SIZE" in exc.user_message
        assert exc.details["config_key"] == "DB_POOL_SIZE"

    def test_feature_flag_error(self) -> None:
        """Test FeatureFlagError initialization."""
        exc = FeatureFlagError(
            flag_name="new_evaluation_pipeline",
            reason="Flag not found in database",
        )
        assert exc.error_code == "FEATURE_FLAG_ERROR"
        assert "new_evaluation_pipeline" in exc.user_message
        assert exc.details["flag_name"] == "new_evaluation_pipeline"


class TestExceptionHierarchy:
    """Test that all exceptions inherit correctly."""

    def test_evaluation_error_inherits_from_ares(self) -> None:
        """Test that EvaluationError inherits from AresException."""
        exc = EvaluationError("TEST", "message")
        assert isinstance(exc, AresException)

    def test_gate_error_inherits_from_ares(self) -> None:
        """Test that GateError inherits from AresException."""
        exc = GateError("TEST", "message")
        assert isinstance(exc, AresException)

    def test_dataset_error_inherits_from_ares(self) -> None:
        """Test that DatasetError inherits from AresException."""
        exc = DatasetError("TEST", "message")
        assert isinstance(exc, AresException)

    def test_champion_error_inherits_from_ares(self) -> None:
        """Test that ChampionError inherits from AresException."""
        exc = ChampionError("TEST", "message")
        assert isinstance(exc, AresException)

    def test_auth_error_inherits_from_ares(self) -> None:
        """Test that AuthError inherits from AresException."""
        exc = AuthError("TEST", "message")
        assert isinstance(exc, AresException)

    def test_configuration_error_inherits_from_ares(self) -> None:
        """Test that ConfigurationError inherits from AresException."""
        exc = ConfigurationError("TEST", "message")
        assert isinstance(exc, AresException)

    def test_specific_errors_inherit_from_base(self) -> None:
        """Test that specific errors inherit from their base classes."""
        assert issubclass(ModelLoadError, EvaluationError)
        assert issubclass(GateConfigError, GateError)
        assert issubclass(DatasetValidationError, DatasetError)
        assert issubclass(ChampionNotFoundError, ChampionError)
        assert issubclass(InvalidAPIKeyError, AuthError)
        assert issubclass(ConfigurationMissingError, ConfigurationError)
