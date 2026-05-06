from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from ares.api.main import app


def test_response_includes_nosniff_header() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_response_includes_deny_frame_options_header() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.headers["X-Frame-Options"] == "DENY"


def test_server_header_does_not_expose_version_info() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    server_header = response.headers.get("Server", "")
    assert not server_header or "/" not in server_header


def test_unlisted_cross_origin_request_is_rejected() -> None:
    local_app = FastAPI()
    local_app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://allowed.example"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @local_app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(local_app)
    response = client.options(
        "/health/live",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in {
        key.lower(): value for key, value in response.headers.items()
    }
