"""Integration tests for Workflows API endpoints."""

import pytest

from app.models.module_role import ModuleRole


def test_create_workflow(client, test_user, auth_headers, db_session):
    """Test creating a workflow."""
    # Assign workflows.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="workflows",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    workflow_data = {
        "name": "Test Workflow",
        "description": "Test description",
        "enabled": True,
        "definition": {"steps": []},
    }

    response = client.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Workflow"
    assert data["enabled"] is True
    assert "id" in data


def test_list_workflows(client, test_user, auth_headers, db_session):
    """Test listing workflows."""
    # Assign workflows.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="workflows",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/workflows", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "total" in response.json()


def test_get_workflow(client, test_user, auth_headers, db_session):
    """Test getting a workflow."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="workflows",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a workflow
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=auth_headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Get it
    response = client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == workflow_id
    assert data["name"] == "Test Workflow"


def test_update_workflow(client, test_user, auth_headers, db_session):
    """Test updating a workflow."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="workflows",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a workflow
    workflow_data = {"name": "Original Name", "definition": {"steps": []}}
    create_response = client.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=auth_headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"name": "Updated Name", "enabled": False}
    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["enabled"] is False


def test_delete_workflow(client, test_user, auth_headers, db_session):
    """Test deleting a workflow."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="workflows",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a workflow
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=auth_headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Delete it
    response = client.delete(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/workflows/{workflow_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_create_workflow_step(client, test_user, auth_headers, db_session):
    """Test creating a workflow step."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="workflows",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a workflow
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=auth_headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Create a step
    step_data = {
        "workflow_id": workflow_id,
        "name": "Step 1",
        "step_type": "task",
        "order": 0,
        "config": {"action": "create_task"},
    }
    response = client.post(
        f"/api/v1/workflows/{workflow_id}/steps",
        json=step_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Step 1"
    assert data["step_type"] == "task"
    assert data["order"] == 0


def test_list_workflow_steps(client, test_user, auth_headers, db_session):
    """Test listing workflow steps."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="workflows",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a workflow
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=auth_headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Create steps
    step_data = {"workflow_id": workflow_id, "name": "Step 1", "step_type": "task", "order": 0}
    client.post(
        f"/api/v1/workflows/{workflow_id}/steps",
        json=step_data,
        headers=auth_headers,
    )

    # List steps
    response = client.get(f"/api/v1/workflows/{workflow_id}/steps", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1

