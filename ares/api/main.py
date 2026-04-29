from __future__ import annotations

import uuid
from typing import cast

from fastapi import FastAPI
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
from ares.api.routers import champions, drift, evaluations, gate, health
from ares.api.schemas.error import ErrorResponse
from ares.exceptions import AresException
from ares.logging import configure_logging
from ares.observability.metrics import MetricsMiddleware
from ares.observability.telemetry import setup_telemetry

configure_logging()

app = FastAPI(title="Ares", version="1.0.0")
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


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    del request, exc
    return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)


@app.exception_handler(AresException)
async def ares_exception_handler(request: Request, exc: AresException) -> JSONResponse:
    """Handle Ares domain exceptions with structured error responses."""
    error_response = ErrorResponse(
        error_code=exc.error_code,
        message=exc.user_message,
        details=exc.details,
    )
    return JSONResponse(
        content=error_response.model_dump(),
        status_code=400,
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


for router in [health.router, evaluations.router, champions.router, gate.router, drift.router]:
    app.include_router(router)

if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
setup_telemetry(app)