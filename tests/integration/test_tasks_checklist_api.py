"""Security-focused integration tests for Task Checklist API endpoints."""

import json
from uuid import uuid4

import pytest

from app.core.auth import hash_password
from app.models.user import User


def _assert_api_error_code(response, expected_code: str) -> None:
    payload = response.json()
    if "error" in payload:
        assert payload["error"]["code"] == expected_code
        return
    if "detail" in payload and isinstance(payload["detail"], dict):
        assert payload["detail"]["error"]["code"] == expected_code
        return
    raise AssertionError("API error code not found in response payload")


def _create_same_tenant_user(db_session, test_tenant) -> User:
    user = User(
        email=f"viewer-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test_password_123"),
        full_name="Checklist Viewer",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


@pytest.mark.integration
@pytest.mark.security
def test_checklist_list_requires_auth(client_with_db, task_factory):
    """Ensure unauthenticated users cannot list checklist items."""
    task = task_factory()
    response = client_with_db.get(f"/api/v1/tasks/{task.id}/checklist")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_checklist_list_requires_view_permission(
    client_with_db, auth_headers, task_factory
):
    """Ensure tasks.view permission is required to list checklist items."""
    task = task_factory()
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/checklist",
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_checklist_list_with_view_permission(
    client_with_db, tasks_manager_headers, tasks_viewer_headers, task_factory
):
    """Ensure viewer can list checklist items and response is safe."""
    task = task_factory()
    create_response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"title": "Primer item"},
        headers=tasks_manager_headers,
    )
    assert create_response.status_code == 201

    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/checklist",
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["data"], list)
    assert payload["meta"]["total"] >= 1
    assert payload["error"] is None
    assert "password" not in json.dumps(payload).lower()


@pytest.mark.integration
@pytest.mark.security
def test_checklist_add_requires_manage_permission(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure tasks.manage permission is required to add checklist items."""
    task = task_factory()
    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"title": "No autorizado"},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_checklist_add_rejects_long_title(
    client_with_db, tasks_manager_headers, task_factory
):
    """Ensure title length validation is enforced."""
    task = task_factory()
    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"title": "A" * 300},
        headers=tasks_manager_headers,
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.security
def test_checklist_update_requires_manage_permission(
    client_with_db,
    db_session,
    tasks_manager_headers,
    module_role_headers,
    task_factory,
    test_tenant,
):
    """Ensure tasks.manage permission is required to update checklist items."""
    task = task_factory()
    create_response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"title": "Actualizar item"},
        headers=tasks_manager_headers,
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["data"]["id"]

    viewer_user = _create_same_tenant_user(db_session, test_tenant)
    viewer_headers = module_role_headers("tasks", "viewer", user=viewer_user)

    response = client_with_db.put(
        f"/api/v1/tasks/checklist/{item_id}",
        json={"completed": True},
        headers=viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_checklist_delete_requires_manage_permission(
    client_with_db,
    db_session,
    tasks_manager_headers,
    module_role_headers,
    task_factory,
    test_tenant,
):
    """Ensure tasks.manage permission is required to delete checklist items."""
    task = task_factory()
    create_response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/checklist",
        json={"title": "Eliminar item"},
        headers=tasks_manager_headers,
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["data"]["id"]

    viewer_user = _create_same_tenant_user(db_session, test_tenant)
    viewer_headers = module_role_headers("tasks", "viewer", user=viewer_user)

    response = client_with_db.delete(
        f"/api/v1/tasks/checklist/{item_id}",
        headers=viewer_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")
