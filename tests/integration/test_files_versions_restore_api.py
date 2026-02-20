"""Integration tests for Files version restore API endpoint."""

from uuid import uuid4

from tests.helpers import create_user_with_permission


def test_restore_file_version_success(client_with_db, test_user, db_session):
    """Test restoring a file version."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload a file
    file_content = b"version 1 content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Create a new version
    file_content_v2 = b"version 2 content"
    files_v2 = {"file": ("test_v2.pdf", file_content_v2, "application/pdf")}
    version_response = client_with_db.post(
        f"/api/v1/files/{file_id}/versions",
        files=files_v2,
        headers=headers,
        data={"change_description": "Updated content"},
    )
    assert version_response.status_code == 201
    version_id = version_response.json()["data"]["id"]
    assert version_id is not None

    # Get the first version (should be version 1)
    versions_response = client_with_db.get(
        f"/api/v1/files/{file_id}/versions", headers=headers
    )
    if versions_response.status_code != 200:
        print(f"Error response: {versions_response.status_code}")
        print(f"Response body: {versions_response.text}")
    assert versions_response.status_code == 200
    versions = versions_response.json()["data"]
    # Find version 1 (not the current one)
    version_1 = next((v for v in versions if v["version_number"] == 1), None)
    assert version_1 is not None
    version_1_id = version_1["id"]

    # Restore version 1
    response = client_with_db.post(
        f"/api/v1/files/{file_id}/versions/{version_1_id}/restore",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "id" in data
    # Should create a new version (version 3) with content from version 1
    assert data["version_number"] == 3


def test_restore_file_version_not_found(client_with_db, test_user, db_session):
    """Test restoring a non-existent file version."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload a file
    file_content = b"test content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Try to restore non-existent version
    fake_version_id = uuid4()
    response = client_with_db.post(
        f"/api/v1/files/{file_id}/versions/{fake_version_id}/restore",
        headers=headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FILE_VERSION_NOT_FOUND"


def test_restore_file_version_requires_permission(
    client_with_db, test_user, db_session
):
    """Test that restore version requires files.manage permission."""
    from app.core.auth import hash_password
    from app.models.module_role import ModuleRole
    from app.models.user import User

    # Create a separate user for uploading (with manager permission)
    manager_user = User(
        email="manager@test.com",
        full_name="Manager User",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    manager_user.password_hash = hash_password("test_password_123")
    db_session.add(manager_user)
    db_session.commit()

    # Upload a file with manager permission
    manager_headers = create_user_with_permission(
        db_session, manager_user, "files", "manager"
    )
    file_content = b"test content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=manager_headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Get versions
    versions_response = client_with_db.get(
        f"/api/v1/files/{file_id}/versions", headers=manager_headers
    )
    assert versions_response.status_code == 200
    versions = versions_response.json()["data"]
    version_id = versions[0]["id"]

    # Try to restore without manage permission (test_user only has viewer)
    # First, remove any existing manager role from test_user
    db_session.query(ModuleRole).filter(
        ModuleRole.user_id == test_user.id,
        ModuleRole.module == "files",
        ModuleRole.role_name == "manager",
    ).delete()
    db_session.commit()

    viewer_headers = create_user_with_permission(
        db_session, test_user, "files", "viewer"
    )
    response = client_with_db.post(
        f"/api/v1/files/{file_id}/versions/{version_id}/restore",
        headers=viewer_headers,
    )

    assert response.status_code == 403
    data = response.json()
    assert "error" in data
