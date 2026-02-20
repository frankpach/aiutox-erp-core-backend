"""Integration tests for Tasks Dependencies API endpoints."""

import pytest


@pytest.mark.integration
def test_list_task_dependencies_empty(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test listing dependencies when task has none."""
    task = task_factory()

    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/dependencies",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["dependencies"] == []
    assert data["data"]["dependents"] == []


@pytest.mark.integration
def test_add_task_dependency_success(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test successfully adding a dependency between tasks."""
    task1 = task_factory()
    task2 = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task1.id}/dependencies",
        json={"depends_on_id": str(task2.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["task_id"] == str(task1.id)
    assert data["data"]["depends_on_id"] == str(task2.id)
    assert data["data"]["dependency_type"] == "finish_to_start"


@pytest.mark.integration
def test_add_dependency_prevents_cycle(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test that adding dependencies prevents cycles."""
    task1 = task_factory()
    task2 = task_factory()

    # Create first dependency: task1 -> task2
    client_with_db.post(
        f"/api/v1/tasks/{task1.id}/dependencies",
        json={"depends_on_id": str(task2.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )

    # Try to create cycle: task2 -> task1
    response = client_with_db.post(
        f"/api/v1/tasks/{task2.id}/dependencies",
        json={"depends_on_id": str(task1.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )

    assert response.status_code == 400
    assert (
        "cycle" in response.json()["error"]["message"].lower()
        or "ciclo" in response.json()["error"]["message"].lower()
    )


@pytest.mark.integration
def test_remove_task_dependency_success(
    client_with_db, tasks_manager_headers, task_factory, db_session
):
    """Test successfully removing a dependency."""
    task1 = task_factory()
    task2 = task_factory()

    # Create dependency
    response = client_with_db.post(
        f"/api/v1/tasks/{task1.id}/dependencies",
        json={"depends_on_id": str(task2.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )
    dependency_id = response.json()["data"]["id"]

    # Remove dependency
    response = client_with_db.delete(
        f"/api/v1/tasks/{task1.id}/dependencies/{dependency_id}",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 204

    # Verify dependency is gone
    response = client_with_db.get(
        f"/api/v1/tasks/{task1.id}/dependencies",
        headers=tasks_manager_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["dependencies"] == []


@pytest.mark.integration
def test_list_task_dependencies_with_data(
    client_with_db, tasks_manager_headers, task_factory, db_session
):
    """Test listing dependencies when task has them."""
    task1 = task_factory()
    task2 = task_factory()
    task3 = task_factory()

    # Create dependencies: task1 -> task2, task3 -> task1
    client_with_db.post(
        f"/api/v1/tasks/{task1.id}/dependencies",
        json={"depends_on_id": str(task2.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )

    client_with_db.post(
        f"/api/v1/tasks/{task3.id}/dependencies",
        json={"depends_on_id": str(task1.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )

    response = client_with_db.get(
        f"/api/v1/tasks/{task1.id}/dependencies",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["dependencies"]) == 1  # task1 depends on task2
    assert len(data["data"]["dependents"]) == 1  # task3 depends on task1
    assert data["data"]["dependencies"][0]["depends_on_id"] == str(task2.id)
    assert data["data"]["dependents"][0]["task_id"] == str(task3.id)


@pytest.mark.integration
def test_dependency_tenant_isolation(
    client_with_db,
    tasks_manager_headers,
    task_factory,
    other_tenant,
    other_user,
    db_session,
):
    """Test that dependencies respect tenant isolation."""
    # Create task in main tenant
    task1 = task_factory()
    task2 = task_factory()

    # Create dependency in main tenant
    response = client_with_db.post(
        f"/api/v1/tasks/{task1.id}/dependencies",
        json={"depends_on_id": str(task2.id), "dependency_type": "finish_to_start"},
        headers=tasks_manager_headers,
    )
    assert response.status_code == 201

    # Create headers for other tenant user with proper permissions
    from tests.conftest import create_user_with_permission

    other_headers = create_user_with_permission(
        db_session=db_session, user=other_user, module="tasks", role_name="manager"
    )

    # Try to access dependency from other tenant - task should not exist for other tenant
    response = client_with_db.get(
        f"/api/v1/tasks/{task1.id}/dependencies",
        headers=other_headers,
    )

    assert response.status_code == 404  # Task not found for other tenant

    # Try to create dependency across tenants (other_tenant task -> main_tenant task)
    response = client_with_db.post(
        f"/api/v1/tasks/{task1.id}/dependencies",
        json={"depends_on_id": str(task2.id), "dependency_type": "finish_to_start"},
        headers=other_headers,
    )

    assert response.status_code == 404
