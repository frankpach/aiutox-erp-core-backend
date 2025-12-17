"""Integration tests for Files API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole
from tests.helpers import create_user_with_permission


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


def test_list_files(client, test_user, db_session):
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

    response = client.get("/api/v1/files", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_get_file_info(client, test_user, db_session):
    """Test getting file information."""
    # Assign files.manage permission for upload, files.view for get
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # First upload a file
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    upload_response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    file_id = upload_response.json()["data"]["id"]

    # Get file info
    response = client.get(f"/api/v1/files/{file_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == file_id
    assert data["name"] == "test.pdf"


def test_delete_file(client, test_user, db_session):
    """Test deleting a file."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # First upload a file
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}

    upload_response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    file_id = upload_response.json()["data"]["id"]

    # Delete file
    response = client.delete(f"/api/v1/files/{file_id}", headers=headers)

    assert response.status_code == 204

    # Verify it's deleted (soft delete)
    get_response = client.get(f"/api/v1/files/{file_id}", headers=headers)
    assert get_response.status_code == 404


def test_get_file_preview_image(client, test_user, db_session):
    """Test getting file preview/thumbnail for an image."""
    # Assign files.manage permission for upload, files.view for preview
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create a simple test image (1x1 PNG)
    from PIL import Image
    import io

    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    file_content = img_bytes.getvalue()

    # Upload image
    files = {"file": ("test.png", file_content, "image/png")}
    upload_response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Get preview
    response = client.get(
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


def test_get_file_preview_non_image(client, test_user, db_session):
    """Test that preview endpoint returns 400 for non-image files."""
    # Assign files.manage permission for upload, files.view for preview
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Upload a PDF file
    file_content = b"%PDF-1.4 test pdf content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client.post(
        "/api/v1/files/upload",
        files=files,
        headers=headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Try to get preview
    response = client.get(
        f"/api/v1/files/{file_id}/preview?width=50&height=50",
        headers=headers,
    )

    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "FILE_NOT_IMAGE"

