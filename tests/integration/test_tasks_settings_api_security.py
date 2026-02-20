"""Security-focused integration tests for Tasks Settings API endpoints."""

import pytest


def _assert_api_error_code(response, expected_code: str) -> None:
    payload = response.json()
    if "error" in payload:
        assert payload["error"]["code"] == expected_code
        return
    if "detail" in payload and isinstance(payload["detail"], dict):
        assert payload["detail"]["error"]["code"] == expected_code
        return
    raise AssertionError("API error code not found in response payload")


@pytest.mark.integration
@pytest.mark.security
def test_get_settings_requires_auth(client_with_db):
    """Ensure unauthenticated users cannot read settings."""
    response = client_with_db.get("/api/v1/tasks/settings")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_get_settings_requires_view_permission(client_with_db, auth_headers):
    """Ensure tasks.view permission is required to read settings."""
    response = client_with_db.get("/api/v1/tasks/settings", headers=auth_headers)
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_get_settings_with_view_permission(client_with_db, tasks_viewer_headers):
    """Ensure viewer can read settings."""
    response = client_with_db.get(
        "/api/v1/tasks/settings", headers=tasks_viewer_headers
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] is not None
    assert payload["error"] is None
    assert "calendar_enabled" in payload["data"]


@pytest.mark.integration
@pytest.mark.security
def test_update_settings_requires_manage_permission(
    client_with_db, tasks_viewer_headers
):
    """Ensure tasks.manage permission is required to update settings."""
    response = client_with_db.put(
        "/api/v1/tasks/settings",
        json={"calendar_enabled": False},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_update_settings_with_manage_permission(client_with_db, tasks_manager_headers):
    """Ensure manager can update settings."""
    response = client_with_db.put(
        "/api/v1/tasks/settings",
        json={"calendar_enabled": False},
        headers=tasks_manager_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["calendar_enabled"] is False
    assert payload["error"] is None
