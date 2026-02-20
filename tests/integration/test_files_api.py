"""Integration tests for Files API endpoints."""

from uuid import uuid4

from app.models.module_role import ModuleRole
from tests.helpers import create_user_with_permission


def test_upload_file(client_with_db, test_user, auth_headers, db_session):
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

    response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "test.pdf"
    assert data["size"] == len(file_content)
    assert "id" in data


def test_list_files(client_with_db, test_user, db_session):
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
    db_session.refresh(test_user)

    # Create token with updated permissions
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    access_token = auth_service.create_access_token_for_user(test_user)
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client_with_db.get("/api/v1/files", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_get_file_info(client_with_db, test_user, db_session):
    """Test getting file information."""
    # Assign files.manage permission for upload, files.view for get
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # First upload a file
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    file_id = upload_response.json()["data"]["id"]

    # Get file info
    response = client_with_db.get(f"/api/v1/files/{file_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == file_id
    assert data["name"] == "test.pdf"


def test_delete_file(client_with_db, test_user, db_session):
    """Test deleting a file."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # First upload a file
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    file_id = upload_response.json()["data"]["id"]

    # Delete file
    response = client_with_db.delete(f"/api/v1/files/{file_id}", headers=headers)

    assert response.status_code == 204

    # Verify it's deleted (soft delete with deleted_at)
    from uuid import UUID

    from app.repositories.file_repository import FileRepository

    repo = FileRepository(db_session)
    deleted_file = repo.get_by_id(
        UUID(file_id), test_user.tenant_id, current_only=False
    )
    if deleted_file:
        assert deleted_file.is_current is False
        assert deleted_file.deleted_at is not None

    # Verify it's not accessible via API (excluded from queries)
    get_response = client_with_db.get(f"/api/v1/files/{file_id}", headers=headers)
    assert get_response.status_code == 404


def test_get_file_preview_image(client_with_db, test_user, db_session):
    """Test getting file preview/thumbnail for an image."""
    # Assign files.manage permission for upload, files.view for preview
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create a simple test image (1x1 PNG)
    import io

    from PIL import Image

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    file_content = img_bytes.getvalue()

    # Upload image
    files = {"file": ("test.png", file_content, "image/png")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Get preview
    response = client_with_db.get(
        f"/api/v1/files/{file_id}/preview?width=50&height=50&quality=80",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert "Cache-Control" in response.headers
    assert len(response.content) > 0

    # Verify it's a valid image
    preview_img = Image.open(io.BytesIO(response.content))
    assert preview_img.format == "JPEG"
    # Thumbnail should be resized (max 50x50)
    assert preview_img.width <= 50
    assert preview_img.height <= 50


def test_get_file_preview_non_image(client_with_db, test_user, db_session):
    """Test that preview endpoint returns 400 for non-image files."""
    # Assign files.manage permission for upload, files.view for preview
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload a PDF file
    file_content = b"%PDF-1.4 test pdf content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Try to get preview
    response = client_with_db.get(
        f"/api/v1/files/{file_id}/preview?width=50&height=50",
        headers=headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FILE_NOT_IMAGE"


def test_get_file_content_text_file(client_with_db, test_user, db_session):
    """Test getting file content for a text file."""
    # Assign files.manage permission for upload, files.view for content
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload a text file
    file_content = b"This is a test text file content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Get file content
    response = client_with_db.get(f"/api/v1/files/{file_id}/content", headers=headers)

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert response.text == file_content.decode("utf-8")


def test_get_file_content_json_file(client_with_db, test_user, db_session):
    """Test getting file content for a JSON file."""
    # Assign files.manage permission for upload, files.view for content
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload a JSON file
    json_content = b'{"test": "data", "number": 123}'
    files = {"file": ("test.json", json_content, "application/json")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Get file content
    response = client_with_db.get(f"/api/v1/files/{file_id}/content", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.text == json_content.decode("utf-8")


def test_get_file_content_file_not_found(client_with_db, test_user, db_session):
    """Test getting file content for non-existent file."""
    # Assign files.view permission
    headers = create_user_with_permission(db_session, test_user, "files", "viewer")

    # Try to get content of non-existent file
    fake_file_id = str(uuid4())
    response = client_with_db.get(
        f"/api/v1/files/{fake_file_id}/content", headers=headers
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FILE_NOT_FOUND"


def test_get_file_content_no_permission(client_with_db, test_user, db_session):
    """Test getting file content without permission."""
    # Create another user without files.view permission
    from app.core.auth import hash_password
    from app.models.user import User

    other_user = User(
        email="other@test.com",
        full_name="Other User",
        tenant_id=test_user.tenant_id,
        is_active=True,
        password_hash=hash_password("test_password_123"),
    )
    db_session.add(other_user)
    db_session.commit()

    # Upload file with first user
    headers = create_user_with_permission(db_session, test_user, "files", "manager")
    file_content = b"test content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    file_id = upload_response.json()["data"]["id"]

    # Try to get content with other user (no permission)
    from app.services.auth_service import AuthService

    auth_service = AuthService(db_session)
    other_token = auth_service.create_access_token_for_user(other_user)
    other_headers = {"Authorization": f"Bearer {other_token}"}

    response = client_with_db.get(
        f"/api/v1/files/{file_id}/content", headers=other_headers
    )

    # Should return 403 or 404 depending on implementation
    assert response.status_code in [403, 404]
