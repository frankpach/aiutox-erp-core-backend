"""Security-focused integration tests for SSE notifications endpoint."""

import pytest


@pytest.mark.integration
@pytest.mark.security
def test_sse_requires_auth(client_with_db):
    """Ensure unauthenticated users cannot open SSE stream."""
    response = client_with_db.get("/api/v1/sse/notifications")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_sse_connects_with_auth(client_with_db, auth_headers):
    """Ensure authenticated users can connect to SSE stream."""
    with client_with_db.stream(
        "GET",
        "/api/v1/sse/notifications",
        headers=auth_headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
