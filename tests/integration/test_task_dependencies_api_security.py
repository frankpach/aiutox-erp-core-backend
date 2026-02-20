"""Security-focused integration tests for Task Dependencies API endpoints."""

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
def test_dependencies_require_auth(client_with_db):
    """Ensure unauthenticated users cannot access dependencies."""
    response = client_with_db.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000/dependencies"
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_dependencies_list_requires_permission(
    client_with_db, auth_headers, task_factory
):
    """Ensure tasks.view permission is required to list dependencies."""
    task = task_factory()
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/dependencies",
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_dependencies_add_and_remove_requires_edit_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure tasks.edit permission is required to add/remove dependencies."""
    task = task_factory()
    depends_on = task_factory()

    create_response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/dependencies",
        json={
            "depends_on_id": str(depends_on.id),
            "dependency_type": "finish_to_start",
        },
        headers=tasks_viewer_headers,
    )
    assert create_response.status_code == 403
    _assert_api_error_code(create_response, "AUTH_INSUFFICIENT_PERMISSIONS")

    delete_response = client_with_db.delete(
        f"/api/v1/tasks/{task.id}/dependencies/00000000-0000-0000-0000-000000000000",
        headers=tasks_viewer_headers,
    )
    assert delete_response.status_code == 403
    _assert_api_error_code(delete_response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_dependencies_create_cycle_returns_bad_request(
    client_with_db, tasks_manager_headers, task_factory
):
    """Ensure circular dependencies are rejected."""
    task_a = task_factory()
    task_b = task_factory()

    create_response = client_with_db.post(
        f"/api/v1/tasks/{task_a.id}/dependencies",
        json={"depends_on_id": str(task_b.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )
    assert create_response.status_code == 201

    cycle_response = client_with_db.post(
        f"/api/v1/tasks/{task_b.id}/dependencies",
        json={"depends_on_id": str(task_a.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )
    assert cycle_response.status_code == 400
    assert "ciclo" in cycle_response.json()["error"]["message"].lower()


@pytest.mark.integration
@pytest.mark.security
def test_dependencies_list_with_view_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure viewer can list dependencies for a task."""
    task = task_factory()
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/dependencies",
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert "dependencies" in payload["data"]
    assert "dependents" in payload["data"]
