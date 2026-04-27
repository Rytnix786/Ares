from __future__ import annotations

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

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
from ares.logging import configure_logging
from ares.observability.telemetry import setup_telemetry

configure_logging()

app = FastAPI(title="Ares", version="1.0.0")
if SlowAPIMiddleware is not None:
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    del request, exc
    return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)


for router in [health.router, evaluations.router, champions.router, gate.router, drift.router]:
    app.include_router(router)

if Instrumentator is not None:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")
setup_telemetry(app)