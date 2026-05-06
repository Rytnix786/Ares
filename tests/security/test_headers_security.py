from __future__ import annotations

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
    client = TestClient(app)
    response = client.options(
        "/health/live",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code in {400, 405}
    assert "access-control-allow-origin" not in {
        key.lower(): value for key, value in response.headers.items()
    }
