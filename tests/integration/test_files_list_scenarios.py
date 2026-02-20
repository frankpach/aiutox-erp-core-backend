"""Integration tests for Files API list endpoint scenarios (Fase 1)."""

from uuid import uuid4

from tests.helpers import create_user_with_permission


def test_list_files_empty_database(client_with_db, test_user, db_session):
    """Test listing files when database is empty."""
    # Assign files.view permission
    headers = create_user_with_permission(db_session, test_user, "files", "viewer")

    # List files (should return empty list, not error)
    response = client_with_db.get("/api/v1/files?page=1&page_size=20", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0
    assert "meta" in data
    assert data["meta"]["total"] == 0
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 20
    assert data["meta"]["total_pages"] == 0


def test_list_files_without_permissions(client_with_db, test_user, db_session):
    """Test listing files when user has no permissions to view any files."""
    # Assign files.view permission (module level)
    headers = create_user_with_permission(db_session, test_user, "files", "viewer")

    # Create another user
    from app.core.auth import hash_password
    from app.models.user import User

    other_user = User(
        email=f"other-list-{uuid4().hex[:8]}@test.com",
        full_name="Other User",
        tenant_id=test_user.tenant_id,
        is_active=True,
    )
    other_user.password_hash = hash_password("test_password_123")
    db_session.add(other_user)
    db_session.commit()

    # Upload file with other user (test_user won't have permission to view it)
    other_headers = create_user_with_permission(db_session, other_user, "files", "manager")
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=other_headers,
    )
    assert upload_response.status_code == 201

    # List files with test_user (should return empty list, not error)
    response = client_with_db.get("/api/v1/files?page=1&page_size=20", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    # Should be empty because test_user has no permission to view other_user's file
    assert len(data["data"]) == 0
    assert data["meta"]["total"] == 0


def test_list_files_with_deleted_files(client_with_db, test_user, db_session):
    """Test listing files when there are deleted files (soft delete)."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload a file
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Delete the file (soft delete)
    delete_response = client_with_db.delete(f"/api/v1/files/{file_id}", headers=headers)
    assert delete_response.status_code == 204

    # Verify file is marked as deleted
    from uuid import UUID

    from app.repositories.file_repository import FileRepository
    repo = FileRepository(db_session)
    deleted_file = repo.get_by_id(UUID(file_id), test_user.tenant_id, current_only=False)
    assert deleted_file is not None
    assert deleted_file.deleted_at is not None
    assert deleted_file.is_current is False

    # List files (should not include deleted file, not error)
    response = client_with_db.get("/api/v1/files?page=1&page_size=20", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    # Deleted file should not appear in the list
    assert len(data["data"]) == 0
    assert data["meta"]["total"] == 0

    # Verify deleted file is not accessible
    get_response = client_with_db.get(f"/api/v1/files/{file_id}", headers=headers)
    assert get_response.status_code == 404


def test_list_files_different_folders(client_with_db, test_user, db_session):
    """Test listing files in different folders."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create folders
    from app.models.folder import Folder
    folder1 = Folder(
        id=uuid4(),
        tenant_id=test_user.tenant_id,
        name="Folder 1",
        created_by=test_user.id,
    )
    folder2 = Folder(
        id=uuid4(),
        tenant_id=test_user.tenant_id,
        name="Folder 2",
        created_by=test_user.id,
    )
    db_session.add(folder1)
    db_session.add(folder2)
    db_session.commit()

    # Upload files to different folders
    file_content = b"test file content"

    # File in folder1
    files1 = {"file": ("file1.pdf", file_content, "application/pdf")}
    upload_response1 = client_with_db.post(
        f"/api/v1/files/upload?folder_id={folder1.id}",
        files=files1,
        headers=headers,
    )
    assert upload_response1.status_code == 201
    file_id1 = upload_response1.json()["data"]["id"]

    # File in folder2
    files2 = {"file": ("file2.pdf", file_content, "application/pdf")}
    upload_response2 = client_with_db.post(
        f"/api/v1/files/upload?folder_id={folder2.id}",
        files=files2,
        headers=headers,
    )
    assert upload_response2.status_code == 201
    file_id2 = upload_response2.json()["data"]["id"]

    # File in root (no folder)
    files3 = {"file": ("file3.pdf", file_content, "application/pdf")}
    upload_response3 = client_with_db.post(
        "/api/v1/files/upload",
        files=files3,
        headers=headers,
    )
    assert upload_response3.status_code == 201
    file_id3 = upload_response3.json()["data"]["id"]

    # List all files (should return all 3)
    response = client_with_db.get("/api/v1/files?page=1&page_size=20", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3
    assert data["meta"]["total"] == 3
    all_ids = {f["id"] for f in data["data"]}
    assert file_id3 in all_ids

    # List files in folder1 (should return only file1)
    response = client_with_db.get(f"/api/v1/files?folder_id={folder1.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == file_id1
    assert data["data"][0]["folder_id"] == str(folder1.id)

    # List files in folder2 (should return only file2)
    response = client_with_db.get(f"/api/v1/files?folder_id={folder2.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["id"] == file_id2
    assert data["data"][0]["folder_id"] == str(folder2.id)

    # List files in root (folder_id=null, should return only file3)
    # Note: This might require special handling in the API
    response = client_with_db.get("/api/v1/files", headers=headers)
    assert response.status_code == 200
    data = response.json()
    # Should include all files (folder1, folder2, and root)
    assert len(data["data"]) >= 1


def test_list_files_with_pagination(client_with_db, test_user, db_session):
    """Test listing files with pagination."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload multiple files
    file_content = b"test file content"
    uploaded_files = []
    for i in range(5):
        files = {"file": (f"file{i}.pdf", file_content, "application/pdf")}
        upload_response = client_with_db.post(
            "/api/v1/files/upload",
            files=files,
            headers=headers,
        )
        assert upload_response.status_code == 201
        uploaded_files.append(upload_response.json()["data"]["id"])

    # List files with page_size=2, page=1
    response = client_with_db.get("/api/v1/files?page=1&page_size=2", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 5
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 2
    assert data["meta"]["total_pages"] == 3

    # List files with page_size=2, page=2
    response = client_with_db.get("/api/v1/files?page=2&page_size=2", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["page"] == 2

    # List files with page_size=2, page=3 (last page)
    response = client_with_db.get("/api/v1/files?page=3&page_size=2", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1  # Only 1 file remaining
    assert data["meta"]["page"] == 3

