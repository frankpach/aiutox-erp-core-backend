"""Security-focused integration tests for Tasks API endpoints."""

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
def test_list_tasks_requires_auth(client_with_db):
    """Ensure unauthenticated users cannot list tasks."""
    response = client_with_db.get("/api/v1/tasks")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_list_tasks_requires_permission(client_with_db, auth_headers):
    """Ensure users without tasks.view permission are forbidden."""
    response = client_with_db.get("/api/v1/tasks", headers=auth_headers)
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_create_task_requires_manage_permission(client_with_db, tasks_viewer_headers):
    """Ensure tasks.manage is required to create tasks."""
    response = client_with_db.post(
        "/api/v1/tasks",
        json={"title": "Test Task"},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_update_task_requires_manage_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure tasks.manage is required to update tasks."""
    task = task_factory()
    response = client_with_db.put(
        f"/api/v1/tasks/{task.id}",
        json={"title": "Updated"},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_delete_task_requires_manage_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure tasks.manage is required to delete tasks."""
    task = task_factory()
    response = client_with_db.delete(
        f"/api/v1/tasks/{task.id}",
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_list_my_tasks_requires_view_permission(client_with_db, auth_headers):
    """Ensure tasks.view is required for /my-tasks."""
    response = client_with_db.get("/api/v1/tasks/my-tasks", headers=auth_headers)
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_get_task_tenant_isolation(
    client_with_db,
    other_user,
    module_role_headers,
    task_factory,
):
    """Ensure tasks are isolated by tenant."""
    task = task_factory()
    other_headers = module_role_headers("tasks", "viewer", user=other_user)

    response = client_with_db.get(f"/api/v1/tasks/{task.id}", headers=other_headers)
    assert response.status_code == 404
    _assert_api_error_code(response, "TASK_NOT_FOUND")
