"""Integration tests for Tasks Comments API endpoints."""

from uuid import uuid4

import pytest

from app.core.auth import hash_password
from app.models.module_role import ModuleRole
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


def _create_same_tenant_user(db_session, test_tenant) -> User:
    user = User(
        email=f"commenter-{uuid4().hex[:8]}@example.com",
        password_hash=hash_password("test_password_123"),
        full_name="Task Commenter",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.refresh(user)
    return user


def test_list_task_comments_empty(client_with_db, test_user, auth_headers, db_session):
    """Test listing comments for a task when empty."""
    # Assign tasks.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="viewer",  # Maps to internal.viewer -> tasks.view
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    task_id = uuid4()

    response = client_with_db.get(
        f"/api/v1/tasks/{task_id}/comments",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["page"] == 1
    expected_page_size = 20 if len(data["data"]) == 0 else len(data["data"])
    assert data["meta"]["page_size"] == expected_page_size
    assert data["meta"]["total_pages"] == 1
    assert data["error"] is None


def test_list_task_comments_with_data(
    client_with_db, test_user, auth_headers, db_session, task_factory
):
    """Test listing comments for a task with existing comments."""
    # Assign tasks.view permission for listing
    headers_view = create_user_with_permission(db_session, test_user, "tasks", "viewer")
    headers_create = headers_view

    task = task_factory()

    # First create a comment using the tasks endpoint
    comment_data = {"content": "Test comment for task", "mentions": []}

    create_response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/comments",
        json=comment_data,
        headers=headers_create,
    )

    assert create_response.status_code == 201
    created_comment = create_response.json()["data"]
    assert created_comment["content"] == "Test comment for task"
    assert created_comment["user_id"] == str(test_user.id)

    # Now list the comments
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/comments",
        headers=headers_view,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["meta"]["total"] == 1
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == max(1, len(data["data"]))
    assert data["meta"]["total_pages"] == 1
    assert data["error"] is None

    # Verify the comment data
    comment = data["data"][0]
    assert comment["content"] == "Test comment for task"
    assert comment["user_id"] == str(test_user.id)
    assert "created_at" in comment
    assert "updated_at" in comment
    assert comment["mentions"] == []


def test_list_task_comments_requires_permission(
    client_with_db, test_user, auth_headers, db_session
):
    """Test that listing task comments requires tasks.view permission."""
    task_id = uuid4()

    response = client_with_db.get(
        f"/api/v1/tasks/{task_id}/comments",
        headers=auth_headers,  # No tasks permission assigned
    )

    assert response.status_code == 403
    assert "permission" in response.json()["error"]["code"].lower()


def test_list_task_comments_wrong_task_id(
    client_with_db, test_user, auth_headers, db_session
):
    """Test listing comments for a non-existent task."""
    # Assign tasks.view permission
    headers = create_user_with_permission(db_session, test_user, "tasks", "viewer")

    # Use a valid UUID format but non-existent task
    fake_task_id = uuid4()

    response = client_with_db.get(
        f"/api/v1/tasks/{fake_task_id}/comments",
        headers=headers,
    )

    # Should return 200 with empty list (comments are filtered by task existence)
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["meta"]["total"] == 0


def test_list_task_comments_isolation_by_tenant(
    client_with_db, test_user, auth_headers, db_session, task_factory
):
    """Test that comments are isolated by tenant."""
    # Create another user with different tenant
    from app.models.tenant import Tenant
    from app.models.user import User

    other_tenant = Tenant(name="Other Tenant", slug="other")
    db_session.add(other_tenant)
    db_session.commit()

    other_user = User(
        email="other@example.com",
        password_hash="hash",
        tenant_id=other_tenant.id,
    )
    db_session.add(other_user)
    db_session.commit()

    # Assign permissions to both users
    headers1 = create_user_with_permission(db_session, test_user, "tasks", "viewer")
    headers2 = create_user_with_permission(db_session, other_user, "tasks", "viewer")

    task = task_factory()

    # Create comment with first user
    comment_data = {"content": "Comment from user 1", "mentions": []}

    create_response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/comments",
        json=comment_data,
        headers=headers1,
    )
    assert create_response.status_code == 201

    # Try to list with second user (different tenant)
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/comments",
        headers=headers2,
    )

    # Should return empty list (tenant isolation)
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["meta"]["total"] == 0


@pytest.mark.integration
@pytest.mark.security
def test_add_task_comment_requires_auth(client_with_db):
    """Ensure unauthenticated users cannot add comments."""
    response = client_with_db.post(
        f"/api/v1/tasks/{uuid4()}/comments",
        json={"content": "No auth", "mentions": []},
    )
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.security
def test_add_task_comment_requires_permission(client_with_db, auth_headers):
    """Ensure tasks.view permission is required to add comments."""
    response = client_with_db.post(
        f"/api/v1/tasks/{uuid4()}/comments",
        json={"content": "No permission", "mentions": []},
        headers=auth_headers,
    )
    assert response.status_code == 403
    _assert_api_error_code(response, "AUTH_INSUFFICIENT_PERMISSIONS")


@pytest.mark.integration
@pytest.mark.security
def test_add_task_comment_rejects_empty_content(client_with_db, tasks_viewer_headers):
    """Ensure empty content is rejected."""
    response = client_with_db.post(
        f"/api/v1/tasks/{uuid4()}/comments",
        json={"content": "   ", "mentions": []},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.security
def test_add_task_comment_sanitizes_xss(
    client_with_db, tasks_viewer_headers, task_factory
):
    """Ensure comment content is sanitized against XSS."""
    task = task_factory()
    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "<script>alert(1)</script>", "mentions": []},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 201
    content = response.json()["data"]["content"].lower()
    assert "<script>" not in content
    assert "&lt;script&gt;" in content


@pytest.mark.integration
@pytest.mark.security
def test_add_task_comment_mentions_parsed(
    client_with_db, db_session, tasks_viewer_headers, task_factory, test_tenant
):
    """Ensure mentions are returned in response."""
    task = task_factory()
    mentioned_user = _create_same_tenant_user(db_session, test_tenant)

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "Hola @user", "mentions": [str(mentioned_user.id)]},
        headers=tasks_viewer_headers,
    )
    assert response.status_code == 201
    assert str(mentioned_user.id) in response.json()["data"]["mentions"]


@pytest.mark.integration
@pytest.mark.security
def test_add_task_comment_tenant_isolation(
    client_with_db, task_factory, module_role_headers, other_user
):
    """Ensure users from other tenants cannot comment on tasks."""
    task = task_factory()
    headers = module_role_headers("tasks", "viewer", user=other_user)

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"content": "Other tenant", "mentions": []},
        headers=headers,
    )
    assert response.status_code == 404
    _assert_api_error_code(response, "TASK_NOT_FOUND")
