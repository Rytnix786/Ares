"""Error response schemas for API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    category: str = Field(default="domain", description="Error category")
    remediation: str = Field(default="Review the request and retry after correcting the reported issue.")
    retryable: bool = False
    request_id: str | None = None
    details: dict[str, str | int | float | bool | list[str] | None] = Field(
        default_factory=dict,
        description="Additional error details",
    )


class ValidationErrorResponse(BaseModel):
    """Validation error response schema."""

    error_code: str = Field(default="VALIDATION_ERROR", description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Field validation errors",
    )
