"""Integration tests for Files API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_upload_file(client, test_user, auth_headers, db_session):
    """Test uploading a file."""
    # Assign files.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="files",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a test file content
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "test.pdf"
    assert data["size"] == len(file_content)
    assert "id" in data


def test_list_files(client, test_user, auth_headers, db_session):
    """Test listing files."""
    # Assign files.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="files",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/files", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_get_file_info(client, test_user, auth_headers, db_session):
    """Test getting file information."""
    # Assign files.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="files",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First upload a file
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    upload_response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=auth_headers,
    )
    file_id = upload_response.json()["data"]["id"]

    # Get file info
    response = client.get(f"/api/v1/files/{file_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == file_id
    assert data["name"] == "test.pdf"


def test_delete_file(client, test_user, auth_headers, db_session):
    """Test deleting a file."""
    # Assign files.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="files",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First upload a file
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    upload_response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=auth_headers,
    )
    file_id = upload_response.json()["data"]["id"]

    # Delete file
    response = client.delete(f"/api/v1/files/{file_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify it's deleted (soft delete)
    get_response = client.get(f"/api/v1/files/{file_id}", headers=auth_headers)
    assert get_response.status_code == 404

