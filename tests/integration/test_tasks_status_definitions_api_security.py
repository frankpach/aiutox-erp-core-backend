"""Security-focused integration tests for Task Status Definitions API endpoints."""

from uuid import uuid4

import pytest

from app.core.auth import hash_password
from app.models.user import User
from tests.helpers import create_user_with_permission


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
def test_status_definitions_list_requires_auth(client_with_db):
    """Ensure unauthenticated users cannot list status definitions."""
    response = client_with_db.get("/api/v1/tasks/status-definitions")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_status_definitions_list_requires_view_permission(
    client_with_db, auth_headers
):
    """Ensure tasks.view permission is required to list status definitions."""
    response = client_with_db.get(
        "/api/v1/tasks/status-definitions",
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_status_definitions_list_with_view_permission(
    client_with_db, tasks_viewer_headers
):
    """Ensure viewer can list status definitions."""
    response = client_with_db.get(
        "/api/v1/tasks/status-definitions",
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["data"], list)
    assert payload["error"] is None


@pytest.mark.integration
@pytest.mark.security
def test_status_definitions_create_requires_manage_permission(
    client_with_db, tasks_viewer_headers
):
    """Ensure tasks.manage permission is required to create status definitions."""
    response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "name": "Security Test",
            "type": "open",
            "color": "#123456",
            "order": 10,
        },
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_status_definitions_update_requires_manage_permission(
    client_with_db, db_session, tasks_manager_headers, test_tenant
):
    """Ensure tasks.manage permission is required to update status definitions."""
    create_response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "name": "To Update",
            "type": "open",
            "color": "#654321",
            "order": 20,
        },
        headers=tasks_manager_headers,
    )
    assert create_response.status_code == 201
    status_id = create_response.json()["data"]["id"]

    viewer_user = User(
        email=f"viewer-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test_password_123"),
        full_name="Viewer User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(viewer_user)
    db_session.commit()
    db_session.refresh(viewer_user)

    viewer_headers = create_user_with_permission(
        db_session, viewer_user, "tasks", "viewer"
    )

    update_response = client_with_db.put(
        f"/api/v1/tasks/status-definitions/{status_id}",
        json={"name": "Updated Name"},
        headers=viewer_headers,
    )
    assert update_response.status_code == 403
    _assert_api_error_code(update_response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_status_definitions_delete_requires_manage_permission(
    client_with_db, db_session, tasks_manager_headers, test_tenant
):
    """Ensure tasks.manage permission is required to delete status definitions."""
    create_response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "name": "To Delete",
            "type": "open",
            "color": "#abcdef",
            "order": 30,
        },
        headers=tasks_manager_headers,
    )
    assert create_response.status_code == 201
    status_id = create_response.json()["data"]["id"]

    viewer_user = User(
        email=f"viewer-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test_password_123"),
        full_name="Viewer User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(viewer_user)
    db_session.commit()
    db_session.refresh(viewer_user)

    viewer_headers = create_user_with_permission(
        db_session, viewer_user, "tasks", "viewer"
    )

    delete_response = client_with_db.delete(
        f"/api/v1/tasks/status-definitions/{status_id}",
        headers=viewer_headers,
    )
    assert delete_response.status_code == 403
    _assert_api_error_code(delete_response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_status_definitions_reorder_requires_manage_permission(
    client_with_db, tasks_viewer_headers
):
    """Ensure tasks.manage permission is required to reorder status definitions."""
    response = client_with_db.post(
        "/api/v1/tasks/status-definitions/reorder",
        json={},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")
