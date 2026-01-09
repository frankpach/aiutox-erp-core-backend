"""Integration tests for Tasks API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_task(client_with_db, test_user, db_session):
    """Test creating a task."""
    # Assign tasks.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(test_user)

    # Create token with updated permissions
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {access_token}"}

    task_data = {
        "title": "Test Task",
        "description": "Test description",
        "status": "todo",
        "priority": "high",
    }

    response = client_with_db.post(
        "/api/v1/tasks",
        json=task_data,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Test Task"
    assert data["description"] == "Test description"
    assert data["status"] == "todo"
    assert data["priority"] == "high"
    assert "id" in data


def test_list_tasks(client_with_db, test_user, db_session):
    """Test listing tasks."""
    # Assign tasks.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(test_user)

    # Create token with updated permissions
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client_with_db.get("/api/v1/tasks", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "meta" in response.json()
    assert "total" in response.json()["meta"]
    assert "page" in response.json()["meta"]


def test_get_task(client_with_db, test_user, db_session):
    """Test getting a task."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(test_user)

    # Create token with updated permissions
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a task
    task_data = {"title": "Test Task", "description": "Test description"}
    create_response = client_with_db.post(
        "/api/v1/tasks",
        json=task_data,
        headers=headers,
    )
    task_id = create_response.json()["data"]["id"]

    # Get it
    response = client_with_db.get(f"/api/v1/tasks/{task_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == task_id
    assert data["title"] == "Test Task"


def test_update_task(client_with_db, test_user, db_session):
    """Test updating a task."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(test_user)

    # Create token with updated permissions
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a task
    task_data = {"title": "Original Title"}
    create_response = client_with_db.post(
        "/api/v1/tasks",
        json=task_data,
        headers=headers,
    )
    task_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"title": "Updated Title", "status": "in_progress"}
    response = client_with_db.put(
        f"/api/v1/tasks/{task_id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Updated Title"
    assert data["status"] == "in_progress"


def test_delete_task(client_with_db, test_user, auth_headers, db_session):
    """Test deleting a task."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a task
    task_data = {"title": "Test Task"}
    create_response = client_with_db.post(
        "/api/v1/tasks",
        json=task_data,
        headers=auth_headers,
    )
    task_id = create_response.json()["data"]["id"]

    # Delete it
    response = client_with_db.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client_with_db.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_add_checklist_item(client_with_db, test_user, db_session):
    """Test adding a checklist item to a task."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(test_user)

    # Create token with updated permissions
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a task
    task_data = {"title": "Test Task"}
    create_response = client_with_db.post(
        "/api/v1/tasks",
        json=task_data,
        headers=headers,
    )
    task_id = create_response.json()["data"]["id"]

    # Add checklist item
    item_data = {"title": "Checklist Item 1", "order": 0}
    response = client_with_db.post(
        f"/api/v1/tasks/{task_id}/checklist",
        json=item_data,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Checklist Item 1"
    assert data["completed"] is False


def test_list_checklist_items(client_with_db, test_user, db_session):
    """Test listing checklist items for a task."""
    # Assign permissions (manager to create, viewer to view)
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tasks",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()
    db_session.refresh(test_user)

    # Create token with updated permissions
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {access_token}"}

    # Create a task and add items
    task_data = {"title": "Test Task"}
    create_response = client_with_db.post(
        "/api/v1/tasks",
        json=task_data,
        headers=headers,
    )
    task_id = create_response.json()["data"]["id"]

    # Add items
    client_with_db.post(
        f"/api/v1/tasks/{task_id}/checklist",
        json={"title": "Item 1", "order": 0},
        headers=headers,
    )
    client_with_db.post(
        f"/api/v1/tasks/{task_id}/checklist",
        json={"title": "Item 2", "order": 1},
        headers=headers,
    )

    # List items
    response = client_with_db.get(f"/api/v1/tasks/{task_id}/checklist", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) >= 2





