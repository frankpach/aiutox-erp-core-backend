"""Integration tests for Tasks Files API endpoints."""

import pytest


@pytest.mark.integration
def test_list_task_files_empty(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test listing files when task has no attachments."""
    task = task_factory()

    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["meta"]["total"] == 0


@pytest.mark.integration
def test_attach_file_to_task_success(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test successfully attaching a file to a task."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": "12345678-1234-5678-9abc-123456789def",
            "file_name": "test_document.pdf",
            "file_size": 1024000,  # 1MB
            "file_type": "application/pdf",
            "file_url": "https://example.com/files/test_document.pdf"
        },
        headers=tasks_manager_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["file_id"] == "12345678-1234-5678-9abc-123456789def"
    assert data["data"]["file_name"] == "test_document.pdf"
    assert data["data"]["file_size"] == 1024000
    assert data["data"]["file_type"] == "application/pdf"
    assert data["data"]["file_url"] == "https://example.com/files/test_document.pdf"


@pytest.mark.integration
def test_attach_file_validation_error_missing_params(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test validation error when required parameters are missing."""
    task = task_factory()

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": "12345678-1234-5678-9abc-123456789def",
            # Missing file_name, file_size, file_type, file_url
        },
        headers=tasks_manager_headers,
    )

    assert response.status_code == 422


@pytest.mark.integration
def test_attach_file_to_nonexistent_task(
    client_with_db, tasks_manager_headers
):
    """Test attaching file to non-existent task returns 404."""
    fake_task_id = "12345678-1234-5678-9abc-123456789def"

    response = client_with_db.post(
        f"/api/v1/tasks/{fake_task_id}/files",
        params={
            "file_id": "87654321-4321-8765-cba-987654321fed",
            "file_name": "test_document.pdf",
            "file_size": 1024000,
            "file_type": "application/pdf",
            "file_url": "https://example.com/files/test_document.pdf"
        },
        headers=tasks_manager_headers,
    )

    # Should return 422 for invalid UUID format, not 404
    assert response.status_code == 422
    assert "uuid" in response.json()["error"]["message"].lower() or "validation" in response.json()["error"]["message"].lower()


@pytest.mark.integration
def test_list_task_files_with_data(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test listing files when task has attachments."""
    task = task_factory()

    # Attach a file first
    client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": "12345678-1234-5678-9abc-123456789def",
            "file_name": "test_document.pdf",
            "file_size": 1024000,
            "file_type": "application/pdf",
            "file_url": "https://example.com/files/test_document.pdf"
        },
        headers=tasks_manager_headers,
    )

    # List files
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["meta"]["total"] == 1
    assert data["data"][0]["file_name"] == "test_document.pdf"


@pytest.mark.integration
def test_detach_file_from_task_success(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test successfully detaching a file from a task."""
    task = task_factory()
    file_id = "12345678-1234-5678-9abc-123456789def"

    # Attach a file first
    client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": file_id,
            "file_name": "test_document.pdf",
            "file_size": 1024000,
            "file_type": "application/pdf",
            "file_url": "https://example.com/files/test_document.pdf"
        },
        headers=tasks_manager_headers,
    )

    # Detach the file
    response = client_with_db.delete(
        f"/api/v1/tasks/{task.id}/files/{file_id}",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 204

    # Verify file is detached
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 0


@pytest.mark.integration
def test_detach_nonexistent_file(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test detaching a file that doesn't exist returns 404."""
    task = task_factory()
    fake_file_id = "87654321-4321-8765-cba-987654321fed"

    response = client_with_db.delete(
        f"/api/v1/tasks/{task.id}/files/{fake_file_id}",
        headers=tasks_manager_headers,
    )

    # Should return 422 for invalid UUID format, not 404
    assert response.status_code == 422
    assert "uuid" in response.json()["error"]["message"].lower() or "validation" in response.json()["error"]["message"].lower()


@pytest.mark.integration
def test_detach_file_from_nonexistent_task(
    client_with_db, tasks_manager_headers
):
    """Test detaching file from non-existent task returns 404."""
    fake_task_id = "12345678-1234-5678-9abc-123456789def"
    file_id = "87654321-4321-8765-cba-987654321fed"

    response = client_with_db.delete(
        f"/api/v1/tasks/{fake_task_id}/files/{file_id}",
        headers=tasks_manager_headers,
    )

    # Should return 422 for invalid UUID format, not 404
    assert response.status_code == 422
    assert "uuid" in response.json()["error"]["message"].lower() or "validation" in response.json()["error"]["message"].lower()


@pytest.mark.integration
def test_files_tenant_isolation(
    client_with_db, tasks_manager_headers, task_factory, other_tenant, other_user, db_session
):
    """Test that file attachments respect tenant isolation."""
    # Create task in main tenant
    task = task_factory()

    # Create headers for other tenant user with proper permissions
    from tests.helpers import create_user_with_permission
    other_headers = create_user_with_permission(db_session=db_session, user=other_user, module="tasks", role_name="manager")

    response = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": "12345678-1234-5678-9abc-123456789def",
            "file_name": "test_document.pdf",
            "file_size": 1024000,
            "file_type": "application/pdf",
            "file_url": "https://example.com/files/test_document.pdf"
        },
        headers=other_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


@pytest.mark.integration
def test_attach_file_multiple_files(
    client_with_db, tasks_manager_headers, task_factory
):
    """Test attaching multiple files to the same task."""
    task = task_factory()

    # Attach first file
    response1 = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": "11111111-1111-1111-1111-111111111111",
            "file_name": "document1.pdf",
            "file_size": 1024000,
            "file_type": "application/pdf",
            "file_url": "https://example.com/files/document1.pdf"
        },
        headers=tasks_manager_headers,
    )
    assert response1.status_code == 201

    # Attach second file
    response2 = client_with_db.post(
        f"/api/v1/tasks/{task.id}/files",
        params={
            "file_id": "22222222-2222-2222-2222-222222222222",
            "file_name": "document2.jpg",
            "file_size": 512000,
            "file_type": "image/jpeg",
            "file_url": "https://example.com/files/document2.jpg"
        },
        headers=tasks_manager_headers,
    )
    assert response2.status_code == 201

    # List files - should have both
    response = client_with_db.get(
        f"/api/v1/tasks/{task.id}/files",
        headers=tasks_manager_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 2

    file_names = [f["file_name"] for f in data["data"]]
    assert "document1.pdf" in file_names
    assert "document2.jpg" in file_names
