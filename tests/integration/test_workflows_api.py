"""Integration tests for Workflows API endpoints."""


from tests.helpers import create_user_with_permission


def test_create_workflow(client_with_db, test_user, db_session):
    """Test creating a workflow."""
    # Assign workflows.manage permission
    headers = create_user_with_permission(db_session, test_user, "workflows", "manager")

    workflow_data = {
        "name": "Test Workflow",
        "description": "Test description",
        "enabled": True,
        "definition": {"steps": []},
    }

    response = client_with_db.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Workflow"
    assert data["enabled"] is True
    assert "id" in data


def test_list_workflows(client_with_db, test_user, db_session):
    """Test listing workflows."""
    # Assign workflows.view permission
    headers = create_user_with_permission(db_session, test_user, "workflows", "viewer")

    response = client_with_db.get("/api/v1/workflows", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "meta" in response.json()
    assert "total" in response.json()["meta"]


def test_get_workflow(client_with_db, test_user, db_session):
    """Test getting a workflow."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "workflows", "manager")

    # Create a workflow
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client_with_db.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Get it
    response = client_with_db.get(f"/api/v1/workflows/{workflow_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == workflow_id
    assert data["name"] == "Test Workflow"


def test_update_workflow(client_with_db, test_user, db_session):
    """Test updating a workflow."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "workflows", "manager")

    # Create a workflow
    workflow_data = {"name": "Original Name", "definition": {"steps": []}}
    create_response = client_with_db.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"name": "Updated Name", "enabled": False}
    response = client_with_db.put(
        f"/api/v1/workflows/{workflow_id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["enabled"] is False


def test_delete_workflow(client_with_db, test_user, db_session):
    """Test deleting a workflow."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "workflows", "manager")

    # Create a workflow
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client_with_db.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Delete it
    response = client_with_db.delete(f"/api/v1/workflows/{workflow_id}", headers=headers)

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client_with_db.get(f"/api/v1/workflows/{workflow_id}", headers=headers)
    assert get_response.status_code == 404


def test_create_workflow_step(client_with_db, test_user, db_session):
    """Test creating a workflow step."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "workflows", "manager")

    # Create a workflow
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client_with_db.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=headers,
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
    response = client_with_db.post(
        f"/api/v1/workflows/{workflow_id}/steps",
        json=step_data,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Step 1"
    assert data["step_type"] == "task"
    assert data["order"] == 0


def test_list_workflow_steps(client_with_db, test_user, db_session):
    """Test listing workflow steps."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "workflows", "viewer")

    # Create a workflow (need manager for creation)
    manager_headers = create_user_with_permission(db_session, test_user, "workflows", "manager")
    workflow_data = {"name": "Test Workflow", "definition": {"steps": []}}
    create_response = client_with_db.post(
        "/api/v1/workflows",
        json=workflow_data,
        headers=manager_headers,
    )
    workflow_id = create_response.json()["data"]["id"]

    # Create steps
    step_data = {"workflow_id": workflow_id, "name": "Step 1", "step_type": "task", "order": 0}
    client_with_db.post(
        f"/api/v1/workflows/{workflow_id}/steps",
        json=step_data,
        headers=manager_headers,
    )

    # List steps
    response = client_with_db.get(f"/api/v1/workflows/{workflow_id}/steps", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1





