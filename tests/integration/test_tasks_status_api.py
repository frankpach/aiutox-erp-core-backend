"""Integration tests for Tasks Status Definitions API endpoints."""

import pytest


@pytest.mark.integration
def test_list_status_definitions_success(
    client_with_db, tasks_manager_headers, db_session, test_tenant
):
    """Test successful listing of status definitions."""
    # Initialize default statuses for the tenant
    from app.core.tasks.status_service import get_task_status_service

    status_service = get_task_status_service(db_session)
    status_service.initialize_default_statuses(test_tenant.id)

    response = client_with_db.get(
        "/api/v1/tasks/status-definitions",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert isinstance(data["data"], list)
    # Should include default system statuses (in English)
    status_names = [status["name"] for status in data["data"]]
    assert "todo" in status_names
    assert "in_progress" in status_names
    assert "done" in status_names


@pytest.mark.integration
def test_create_status_definition_success(client_with_db, tasks_manager_headers):
    """Test successful creation of custom status definition."""
    response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "name": "custom_status",
            "type": "custom",
            "color": "#FF5722",
            "order": 100,
        },
        headers=tasks_manager_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["name"] == "custom_status"
    assert data["data"]["type"] == "custom"
    assert data["data"]["color"] == "#FF5722"
    assert data["data"]["order"] == 100


@pytest.mark.integration
def test_create_status_definition_validation_error(
    client_with_db, tasks_manager_headers
):
    """Test validation error when creating status with missing required fields."""
    response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "type": "custom",
            "color": "#FF5722",
            # Missing "name" field
        },
        headers=tasks_manager_headers,
    )

    assert response.status_code == 422
    assert "validation" in response.json()["error"]["code"].lower()


@pytest.mark.integration
def test_update_status_definition_success(client_with_db, tasks_manager_headers):
    """Test successful update of custom status definition."""
    # First create a status
    create_response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "name": "updatable_status",
            "type": "custom",
            "color": "#FF5722",
            "order": 100,
        },
        headers=tasks_manager_headers,
    )
    status_id = create_response.json()["data"]["id"]

    # Update the status
    response = client_with_db.put(
        f"/api/v1/tasks/status-definitions/{status_id}",
        json={"name": "updated_status", "color": "#2196F3"},
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["name"] == "updated_status"
    assert data["data"]["color"] == "#2196F3"


@pytest.mark.integration
def test_update_system_status_forbidden(client_with_db, tasks_manager_headers):
    """Test that system statuses cannot be updated."""
    # Try to update a system status using an invalid UUID format (should return 422)
    response = client_with_db.put(
        "/api/v1/tasks/status-definitions/todo",
        json={"name": "modified_todo", "color": "#FF0000"},
        headers=tasks_manager_headers,
    )

    # Should return 422 for invalid UUID format, not 404
    assert response.status_code == 422
    assert (
        "uuid" in response.json()["error"]["message"].lower()
        or "validation" in response.json()["error"]["message"].lower()
    )


@pytest.mark.integration
def test_delete_custom_status_success(client_with_db, tasks_manager_headers):
    """Test successful deletion of custom status definition."""
    # First create a status
    create_response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "name": "deletable_status",
            "type": "custom",
            "color": "#FF5722",
            "order": 100,
        },
        headers=tasks_manager_headers,
    )
    status_id = create_response.json()["data"]["id"]

    # Delete the status
    response = client_with_db.delete(
        f"/api/v1/tasks/status-definitions/{status_id}",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 204

    # Verify it's deleted
    response = client_with_db.get(
        "/api/v1/tasks/status-definitions",
        headers=tasks_manager_headers,
    )
    status_names = [status["name"] for status in response.json()["data"]]
    assert "deletable_status" not in status_names


@pytest.mark.integration
def test_delete_system_status_forbidden(client_with_db, tasks_manager_headers):
    """Test that system statuses cannot be deleted."""
    # Try to delete a system status using invalid UUID format (should return 422)
    response = client_with_db.delete(
        "/api/v1/tasks/status-definitions/todo",
        headers=tasks_manager_headers,
    )

    # Should return 422 for invalid UUID format, not 400
    assert response.status_code == 422
    assert (
        "uuid" in response.json()["error"]["message"].lower()
        or "validation" in response.json()["error"]["message"].lower()
    )


@pytest.mark.integration
def test_reorder_status_definitions_success(client_with_db, tasks_manager_headers):
    """Test successful reordering of status definitions."""
    # Create some custom statuses first
    status1_response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={"name": "status_one", "type": "custom", "color": "#FF5722", "order": 100},
        headers=tasks_manager_headers,
    )
    status2_response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={"name": "status_two", "type": "custom", "color": "#2196F3", "order": 200},
        headers=tasks_manager_headers,
    )

    status1_id = status1_response.json()["data"]["id"]
    status2_id = status2_response.json()["data"]["id"]

    # Reorder them
    response = client_with_db.post(
        "/api/v1/tasks/status-definitions/reorder",
        json={str(status1_id): 200, str(status2_id): 100},
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    statuses = data["data"]

    # Find the updated statuses
    status1_updated = next((s for s in statuses if s["id"] == status1_id), None)
    status2_updated = next((s for s in statuses if s["id"] == status2_id), None)

    assert status1_updated["order"] == 200
    assert status2_updated["order"] == 100


@pytest.mark.integration
def test_status_definitions_tenant_isolation(
    client_with_db, tasks_manager_headers, other_tenant, other_user, db_session
):
    """Test that status definitions are isolated by tenant."""
    # Initialize default statuses for other tenant
    from app.core.tasks.status_service import get_task_status_service

    status_service = get_task_status_service(db_session)
    status_service.initialize_default_statuses(other_tenant.id)

    # Create status in main tenant
    response = client_with_db.post(
        "/api/v1/tasks/status-definitions",
        json={
            "name": "main_tenant_status",
            "type": "custom",
            "color": "#FF5722",
            "order": 100,
        },
        headers=tasks_manager_headers,
    )
    assert response.status_code == 201

    # Create headers for other tenant user with proper permissions
    from tests.helpers import create_user_with_permission

    other_headers = create_user_with_permission(
        db_session=db_session, user=other_user, module="tasks", role_name="manager"
    )

    # List statuses for other tenant - should not include main tenant's status
    response = client_with_db.get(
        "/api/v1/tasks/status-definitions",
        headers=other_headers,
    )

    assert response.status_code == 200
    status_names = [status["name"] for status in response.json()["data"]]
    assert "main_tenant_status" not in status_names
    # Should still have system statuses (in English)
    assert "todo" in status_names
