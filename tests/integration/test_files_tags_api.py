"""Integration tests for Files Tags API endpoints."""

from uuid import uuid4

from tests.helpers import create_user_with_permission


def test_add_tags_to_file(client_with_db, test_user, db_session):
    """Test adding tags to a file."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create tags
    from app.core.tags.service import TagService
    tag_service = TagService(db_session)
    tag1 = tag_service.create_tag(
        name="Tag 1",
        tenant_id=test_user.tenant_id,
        color="#FF5733",
    )
    tag2 = tag_service.create_tag(
        name="Tag 2",
        tenant_id=test_user.tenant_id,
        color="#33FF57",
    )

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

    # Add tags to file
    response = client_with_db.post(
        f"/api/v1/files/{file_id}/tags?tag_ids={tag1.id}&tag_ids={tag2.id}",
        headers=headers,
    )

    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    tag_ids = [tag["id"] for tag in data["data"]]
    assert str(tag1.id) in tag_ids
    assert str(tag2.id) in tag_ids


def test_remove_tag_from_file(client_with_db, test_user, db_session):
    """Test removing a tag from a file."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create tag
    from app.core.tags.service import TagService
    tag_service = TagService(db_session)
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_user.tenant_id,
        color="#FF5733",
    )

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

    # Add tag to file
    add_response = client_with_db.post(
        f"/api/v1/files/{file_id}/tags?tag_ids={tag.id}",
        headers=headers,
    )
    assert add_response.status_code == 200

    # Remove tag from file
    response = client_with_db.delete(
        f"/api/v1/files/{file_id}/tags/{tag.id}",
        headers=headers,
    )

    assert response.status_code == 204

    # Verify tag is removed
    get_response = client_with_db.get(f"/api/v1/files/{file_id}/tags", headers=headers)
    if get_response.status_code != 200:
        print(f"Response status: {get_response.status_code}")
        print(f"Response body: {get_response.text}")
    assert get_response.status_code == 200
    data = get_response.json()
    assert len(data["data"]) == 0


def test_get_file_tags(client_with_db, test_user, db_session):
    """Test getting tags for a file."""
    # Assign files.manage and files.view permissions
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create tags
    from app.core.tags.service import TagService
    tag_service = TagService(db_session)
    tag1 = tag_service.create_tag(
        name="Tag 1",
        tenant_id=test_user.tenant_id,
        color="#FF5733",
    )
    tag2 = tag_service.create_tag(
        name="Tag 2",
        tenant_id=test_user.tenant_id,
        color="#33FF57",
    )

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

    # Add tags to file
    client_with_db.post(
        f"/api/v1/files/{file_id}/tags?tag_ids={tag1.id}&tag_ids={tag2.id}",
        headers=headers,
    )

    # Get tags
    response = client_with_db.get(f"/api/v1/files/{file_id}/tags", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2
    tag_names = [tag["name"] for tag in data["data"]]
    assert "Tag 1" in tag_names
    assert "Tag 2" in tag_names


def test_list_files_filtered_by_tags(client_with_db, test_user, db_session):
    """Test listing files filtered by tags."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create tags
    from app.core.tags.service import TagService
    tag_service = TagService(db_session)
    tag1 = tag_service.create_tag(
        name="Important",
        tenant_id=test_user.tenant_id,
        color="#FF5733",
    )
    tag2 = tag_service.create_tag(
        name="Archive",
        tenant_id=test_user.tenant_id,
        color="#33FF57",
    )

    # Upload files
    file_content = b"test file content"

    # File 1 with tag1
    files1 = {"file": ("file1.pdf", file_content, "application/pdf")}
    upload_response1 = client_with_db.post(
        "/api/v1/files/upload",
        files=files1,
        headers=headers,
    )
    assert upload_response1.status_code == 201
    file_id1 = upload_response1.json()["data"]["id"]
    client_with_db.post(
        f"/api/v1/files/{file_id1}/tags?tag_ids={tag1.id}",
        headers=headers,
    )

    # File 2 with tag2
    files2 = {"file": ("file2.pdf", file_content, "application/pdf")}
    upload_response2 = client_with_db.post(
        "/api/v1/files/upload",
        files=files2,
        headers=headers,
    )
    assert upload_response2.status_code == 201
    file_id2 = upload_response2.json()["data"]["id"]
    client_with_db.post(
        f"/api/v1/files/{file_id2}/tags?tag_ids={tag2.id}",
        headers=headers,
    )

    # File 3 with both tags
    files3 = {"file": ("file3.pdf", file_content, "application/pdf")}
    upload_response3 = client_with_db.post(
        "/api/v1/files/upload",
        files=files3,
        headers=headers,
    )
    assert upload_response3.status_code == 201
    file_id3 = upload_response3.json()["data"]["id"]
    client_with_db.post(
        f"/api/v1/files/{file_id3}/tags?tag_ids={tag1.id}&tag_ids={tag2.id}",
        headers=headers,
    )

    # List files with tag1
    response = client_with_db.get(
        f"/api/v1/files?tags={tag1.id}",
        headers=headers,
    )
    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
    assert response.status_code == 200
    data = response.json()
    file_ids = [f["id"] for f in data["data"]]
    assert file_id1 in file_ids
    assert file_id3 in file_ids
    assert file_id2 not in file_ids

    # List files with both tags (must have ALL tags)
    response = client_with_db.get(
        f"/api/v1/files?tags={tag1.id},{tag2.id}",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    file_ids = [f["id"] for f in data["data"]]
    assert file_id3 in file_ids
    assert file_id1 not in file_ids
    assert file_id2 not in file_ids


def test_add_tags_to_file_no_permission(client_with_db, test_user, db_session):
    """Test adding tags to a file without permission."""
    # Assign files.view permission (not manage)
    headers = create_user_with_permission(db_session, test_user, "files", "viewer")

    # Create another user to upload the file (so test_user is not the owner)
    from app.core.auth import hash_password
    from app.models.user import User
    other_user = User(
        email=f"other-tags-{uuid4().hex[:8]}@test.com",
        full_name="Other User",
        tenant_id=test_user.tenant_id,
        is_active=True,
        password_hash=hash_password("test_password_123"),
    )
    db_session.add(other_user)
    db_session.commit()

    # Create tag
    from app.core.tags.service import TagService
    tag_service = TagService(db_session)
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_user.tenant_id,
    )

    # Upload a file with other_user (need manager permission)
    other_manager_headers = create_user_with_permission(db_session, other_user, "files", "manager")
    file_content = b"test file content"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    upload_response = client_with_db.post(
        "/api/v1/files/upload",
        files=files,
        headers=other_manager_headers,
    )
    assert upload_response.status_code == 201
    file_id = upload_response.json()["data"]["id"]

    # Try to add tag without manage permission (test_user is not the owner)
    response = client_with_db.post(
        f"/api/v1/files/{file_id}/tags?tag_ids={tag.id}",
        headers=headers,
    )

    assert response.status_code == 403


def test_file_response_includes_tags(client_with_db, test_user, db_session):
    """Test that file response includes tags."""
    # Assign files.manage permission
    headers = create_user_with_permission(db_session, test_user, "files", "manager")

    # Create tag
    from app.core.tags.service import TagService
    tag_service = TagService(db_session)
    tag = tag_service.create_tag(
        name="Test Tag",
        tenant_id=test_user.tenant_id,
        color="#FF5733",
    )

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

    # Add tag to file
    client_with_db.post(
        f"/api/v1/files/{file_id}/tags?tag_ids={tag.id}",
        headers=headers,
    )

    # Get file info
    response = client_with_db.get(f"/api/v1/files/{file_id}", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert "tags" in data
    assert isinstance(data["tags"], list)
    assert len(data["tags"]) == 1
    assert data["tags"][0]["id"] == str(tag.id)
    assert data["tags"][0]["name"] == "Test Tag"

