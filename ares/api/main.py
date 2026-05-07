from __future__ import annotations

import asyncio
import uuid
from typing import Any, cast

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

try:
    from prometheus_fastapi_instrumentator import Instrumentator
except ModuleNotFoundError:  # pragma: no cover - minimal smoke-test fallback
    Instrumentator = None

try:
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
except ModuleNotFoundError:  # pragma: no cover - minimal smoke-test fallback
    RateLimitExceeded = Exception
    SlowAPIMiddleware = None

from ares.api.limiting import limiter
from ares.api.routers import alerts, api_keys, audit, champions, drift, evaluations, gate, health
from ares.api.schemas.error import ErrorResponse
from ares.config import settings
from ares.exceptions import AresException
from ares.logging import configure_logging
from ares.observability.metrics import MetricsMiddleware
from ares.observability.telemetry import setup_telemetry
from ares.scheduler.maintenance_scheduler import MaintenanceScheduler

ERROR_REMEDIATION = {
    "MODEL_LOAD_FAILED": "Verify the model path/artifact URI, file permissions, and configured evaluator mode.",
    "PREDICTION_FAILED": "Validate input schema and model compatibility before retrying the evaluation.",
    "DATASET_SCHEMA_INVALID": "Fix the dataset columns or production prediction payload to match the documented schema.",
    "PROMOTION_FAILED": "Check champion history, target run gate status, and rollback/promotion permissions.",
    "INSUFFICIENT_SCOPE": "Use an API key with the required scope or ask an administrator to rotate/provision one.",
}

ERROR_STATUS = {
    "DATASET_SCHEMA_INVALID": 422,
    "GATE_CONFIG_INVALID": 422,
    "INSUFFICIENT_SCOPE": 403,
    "PROMOTION_FAILED": 409,
    "CONFIGURATION_INVALID": 500,
}

configure_logging()

app = FastAPI(title="Ares", version="1.0.0")
if settings.ARES_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ARES_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
if SlowAPIMiddleware is not None:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def request_id_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def security_headers_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    response = await call_next(request)
    if settings.ARES_SECURITY_HEADERS_ENABLED:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    del exc
    return JSONResponse(
        ErrorResponse(
            error_code="RATE_LIMIT_EXCEEDED",
            message="Rate limit exceeded",
            category="rate_limit",
            remediation="Wait for the current rate-limit window to reset or use a key with an appropriate policy.",
            retryable=True,
            request_id=getattr(request.state, "request_id", None),
        ).model_dump(),
        status_code=429,
    )


@app.exception_handler(AresException)
async def ares_exception_handler(request: Request, exc: AresException) -> JSONResponse:
    """Handle Ares domain exceptions with structured error responses."""
    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.user_message,
        category=exc.__class__.__mro__[1].__name__.replace("Error", "").lower(),
        remediation=ERROR_REMEDIATION.get(exc.error_code, "Review the error details, correct the request, and retry."),
        retryable=exc.error_code.endswith("TIMEOUT"),
        request_id=getattr(request.state, "request_id", None),
        details=exc.details,
    )
    return JSONResponse(
        content=error_response.model_dump(),
        status_code=ERROR_STATUS.get(exc.error_code, 400),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
    raw_details: Any = detail.get("details", {})
    safe_details = raw_details if isinstance(raw_details, dict) else {}
    body = ErrorResponse(
        error_code=str(detail.get("error_code", f"HTTP_{exc.status_code}")),
        message=str(detail.get("message", detail.get("detail", exc.detail))),
        category="http",
        remediation="Review the endpoint documentation, required scopes, and request parameters before retrying.",
        retryable=exc.status_code in {408, 409, 429, 500, 502, 503, 504},
        request_id=getattr(request.state, "request_id", None),
        details={k: v for k, v in safe_details.items() if isinstance(v, (str, int, float, bool, list)) or v is None},
    ).model_dump()
    if isinstance(exc.detail, dict):
        body["detail"] = exc.detail
    return JSONResponse(
        body,
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        ErrorResponse(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            category="validation",
            remediation="Fix the fields identified in details and retry.",
            retryable=False,
            request_id=getattr(request.state, "request_id", None),
            details={"errors": [str(error) for error in exc.errors()]},
        ).model_dump(),
        status_code=422,
    )


# Add audit middleware (optional - only if DB is configured)
try:
    from ares.api.middleware.audit import AuditMiddleware
    from ares.db.session import get_sessionmaker
    
    @app.middleware("http")
    async def audit_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Audit logging middleware for mutations."""
        middleware = AuditMiddleware(get_sessionmaker())
        return await middleware(request, call_next)
except Exception:
    # Skip audit middleware if not configured
    pass


@app.middleware("http")
async def metrics_context_middleware(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    """Bind request_id to log context for correlation."""
    middleware = MetricsMiddleware()
    return cast(Response, await middleware(request, call_next))


for router in [health.router, evaluations.router, champions.router, gate.router, drift.router, alerts.router, api_keys.router, audit.router]:
    app.include_router(router)

if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
setup_telemetry(app)


@app.on_event("startup")
async def start_maintenance_scheduler() -> None:  # pragma: no cover
    try:
        from ares.db.session import get_sessionmaker

        app.state.maintenance_scheduler = MaintenanceScheduler(get_sessionmaker())
        app.state.maintenance_scheduler_task = asyncio.create_task(app.state.maintenance_scheduler.run_forever())
    except Exception:
        pass


@app.on_event("shutdown")
async def stop_maintenance_scheduler() -> None:  # pragma: no cover
    task = getattr(app.state, "maintenance_scheduler_task", None)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
