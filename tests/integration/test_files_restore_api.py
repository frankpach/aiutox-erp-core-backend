"""Integration tests for Files restore API endpoint."""

import pytest
from datetime import UTC, datetime
from uuid import uuid4

from app.models.file import File
from app.models.module_role import ModuleRole
from tests.helpers import create_user_with_permission


def test_restore_file_success(client, test_user, db_session):
    """Test restoring a deleted file."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create a deleted file
    from app.repositories.file_repository import FileRepository
    repo = FileRepository(db_session)
    deleted_file = repo.create({
        "tenant_id": test_user.tenant_id,
        "name": "deleted.pdf",
        "original_name": "deleted.pdf",
        "mime_type": "application/pdf",
        "size": 1024,
        "storage_backend": "local",
        "storage_path": "/test/deleted",
        "is_current": False,
        "deleted_at": datetime.now(UTC),
    })

    # Restore the file
    response = client.post(
        f"/api/v1/files/{deleted_file.id}/restore",
        headers=headers,
    )

    # Assert
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(deleted_file.id)
    assert data["is_current"] is True
    assert data["deleted_at"] is None

    # Verify in database
    db_session.refresh(deleted_file)
    assert deleted_file.is_current is True
    assert deleted_file.deleted_at is None


def test_restore_file_not_found(client, test_user, db_session):
    """Test restoring a non-existent file."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    fake_id = uuid4()
    response = client.post(
        f"/api/v1/files/{fake_id}/restore",
        headers=headers,
    )

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FILE_NOT_FOUND"


def test_restore_file_already_restored(client, test_user, db_session):
    """Test restoring a file that was never deleted."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create a current (not deleted) file
    from app.repositories.file_repository import FileRepository
    repo = FileRepository(db_session)
    current_file = repo.create({
        "tenant_id": test_user.tenant_id,
        "name": "current.pdf",
        "original_name": "current.pdf",
        "mime_type": "application/pdf",
        "size": 1024,
        "storage_backend": "local",
        "storage_path": "/test/current",
        "is_current": True,
        "deleted_at": None,
    })

    # Try to restore
    response = client.post(
        f"/api/v1/files/{current_file.id}/restore",
        headers=headers,
    )

    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FILE_NOT_FOUND"


def test_restore_file_requires_permission(client, test_user, db_session):
    """Test that restore requires files.manage permission."""
    # Create a deleted file
    from app.repositories.file_repository import FileRepository
    repo = FileRepository(db_session)
    deleted_file = repo.create({
        "tenant_id": test_user.tenant_id,
        "name": "deleted.pdf",
        "original_name": "deleted.pdf",
        "mime_type": "application/pdf",
        "size": 1024,
        "storage_backend": "local",
        "storage_path": "/test/deleted",
        "is_current": False,
        "deleted_at": datetime.now(UTC),
    })

    # Try to restore without permission
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        f"/api/v1/files/{deleted_file.id}/restore",
        headers=headers,
    )

    # Assert
    assert response.status_code == 403
    data = response.json()
    assert "error" in data

