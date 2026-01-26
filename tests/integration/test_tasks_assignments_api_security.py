"""Security-focused integration tests for Tasks Assignments API endpoints."""

import pytest

from app.core.auth import hash_password
from app.models.user import User
from tests.helpers import create_user_with_system_permission


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
def test_assignments_require_auth(client_with_db):
    """Ensure unauthenticated users cannot list assignments."""
    response = client_with_db.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000/assignments")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_assignments_list_requires_permission(
    client_with_db, auth_headers, task_factory
):
    """Ensure tasks.view permission is required to list assignments."""
    task = task_factory()
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/assignments",
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_assignments_create_requires_permission(
    client_with_db, tasks_viewer_headers, task_factory, test_user
):
    """Ensure tasks.assign permission is required to create assignments."""
    task = task_factory()
    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/assignments",
        json={
            "task_id": str(task.id),
            "assigned_to_id": str(test_user.id),
            "created_by_id": str(test_user.id),
        },
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_assignments_create_and_delete_with_owner_role(
    client_with_db, db_session, test_user, test_tenant, task_factory
):
    """Ensure owner role (global wildcard) can create and delete assignments."""
    owner_headers = create_user_with_system_permission(db_session, test_user, "owner")

    assignee = User(
        email="assignee@example.com",
        password_hash=hash_password("test_password_123"),
        full_name="Assignee User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(assignee)
    db_session.commit()
    db_session.refresh(assignee)

    task = task_factory()

    create_response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/assignments",
        json={
            "task_id": str(task.id),
            "assigned_to_id": str(assignee.id),
            "created_by_id": str(test_user.id),
        },
        headers=owner_headers,
    )
    assert create_response.status_code == 201
    assignment_id = create_response.json()["data"]["id"]

    list_response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/assignments",
        headers=owner_headers,
    )
    assert list_response.status_code == 200
    assignments = list_response.json()["data"]
    assert any(a["id"] == assignment_id for a in assignments)

    delete_response = client_with_db.delete(
        f"/api/v1/tasks/{task.id}/assignments/{assignment_id}",
        headers=owner_headers,
    )
    assert delete_response.status_code == 204
