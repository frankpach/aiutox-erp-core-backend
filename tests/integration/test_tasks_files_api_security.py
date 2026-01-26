"""Security-focused integration tests for Tasks Files API endpoints."""

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
def test_files_list_requires_auth(client_with_db, task_factory):
    """Ensure unauthenticated users cannot list task files."""
    task = task_factory()
    response = client_with_db.get(f"/api/v1/tasks/{task.id}/files")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_files_list_requires_view_permission(
    client_with_db, auth_headers, task_factory
):
    """Ensure tasks.view permission is required to list files."""
    task = task_factory()
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/files",
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_files_list_with_view_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure viewer can list task files."""
    task = task_factory()
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["data"], list)
    assert payload["error"] is None


@pytest.mark.integration
@pytest.mark.security
def test_files_attach_requires_manage_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure tasks.manage permission is required to attach files."""
    task = task_factory()
    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": "00000000-0000-0000-0000-000000000001",
            "file_name": "test.txt",
            "file_size": 123,
            "file_type": "text/plain",
            "file_url": "https://example.com/test.txt",
        },
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_files_detach_requires_manage_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure tasks.manage permission is required to detach files."""
    task = task_factory()
    response = client_with_db.delete(
        f"/api/v1/tasks/{task.id}/files/00000000-0000-0000-0000-000000000001",
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")
