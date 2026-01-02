"""Integration tests for Files upload with permissions."""

import pytest
from uuid import uuid4

from app.models.file import FilePermission
from tests.helpers import create_user_with_permission


def test_upload_file_with_permissions(client, test_user, db_session):
    """Test uploading a file with specific permissions."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create another user
    from app.models.user import User
    other_user = User(
        email="other@test.com",
        full_name="Other User",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    other_user.set_password("test_password_123")
    db_session.add(other_user)
    db_session.commit()

    # Upload file with permissions for other_user
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    permissions_data = {
        "permissions": [
            {
                "target_type": "user",
                "target_id": str(other_user.id),
                "can_view": True,
                "can_download": True,
                "can_edit": False,
                "can_delete": False,
            }
        ]
    }

    response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
        data=permissions_data,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert "id" in data
    file_id = data["id"]

    # Verify permissions were created
    from app.repositories.file_repository import FileRepository
    repo = FileRepository(db_session)
    permissions = repo.get_permissions(uuid4() if isinstance(file_id, str) else file_id, test_user.tenant_id)
    # Note: file_id needs to be converted to UUID
    from uuid import UUID
    permissions = repo.get_permissions(UUID(file_id), test_user.tenant_id)
    assert len(permissions) >= 1
    user_permission = next((p for p in permissions if p.target_type == "user" and p.target_id == other_user.id), None)
    assert user_permission is not None
    assert user_permission.can_view is True
    assert user_permission.can_download is True
    assert user_permission.can_edit is False
    assert user_permission.can_delete is False


def test_upload_file_with_multiple_permissions(client, test_user, db_session):
    """Test uploading a file with multiple permissions (user, role, organization)."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create another user
    from app.models.user import User
    other_user = User(
        email="other@test.com",
        full_name="Other User",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    other_user.set_password("test_password_123")
    db_session.add(other_user)
    db_session.commit()

    # Upload file with multiple permissions
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    permissions_data = {
        "permissions": [
            {
                "target_type": "user",
                "target_id": str(other_user.id),
                "can_view": True,
                "can_download": True,
                "can_edit": False,
                "can_delete": False,
            },
            {
                "target_type": "organization",
                "target_id": str(test_user.organization_id) if test_user.organization_id else str(uuid4()),
                "can_view": True,
                "can_download": False,
                "can_edit": False,
                "can_delete": False,
            },
        ]
    }

    response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
        data=permissions_data,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert "id" in data
    file_id = data["id"]

    # Verify permissions were created
    from app.repositories.file_repository import FileRepository
    from uuid import UUID
    repo = FileRepository(db_session)
    permissions = repo.get_permissions(UUID(file_id), test_user.tenant_id)
    assert len(permissions) >= 2


def test_upload_file_without_permissions(client, test_user, db_session):
    """Test uploading a file without specifying permissions (should work, owner has access)."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload file without permissions
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert "id" in data
    # File should be accessible by owner (test_user) even without explicit permissions

