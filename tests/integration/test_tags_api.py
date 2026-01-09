"""Integration tests for Tags API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_tag(client_with_db, test_user, db_session):
    """Test creating a tag."""
    # Assign tags.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
        role_name="manager",
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

    tag_data = {
        "name": "Important",
        "color": "#FF5733",
        "description": "Important items",
    }

    response = client_with_db.post(
        "/api/v1/tags",
        json=tag_data,
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Important"
    assert data["color"] == "#FF5733"
    assert "id" in data


def test_list_tags(client_with_db, test_user, db_session):
    """Test listing tags."""
    # Assign tags.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
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

    response = client_with_db.get("/api/v1/tags", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "total" in data["meta"]


def test_get_tag(client_with_db, test_user, auth_headers, db_session):
    """Test getting a tag."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a tag
    tag_data = {"name": "Test Tag", "color": "#000000"}
    create_response = client_with_db.post(
        "/api/v1/tags",
        json=tag_data,
        headers=auth_headers,
    )
    tag_id = create_response.json()["data"]["id"]

    # Get it
    response = client_with_db.get(f"/api/v1/tags/{tag_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == tag_id
    assert data["name"] == "Test Tag"


def test_update_tag(client_with_db, test_user, db_session):
    """Test updating a tag."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
        role_name="manager",
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

    # Create a tag
    tag_data = {"name": "Original Name", "color": "#000000"}
    create_response = client_with_db.post(
        "/api/v1/tags",
        json=tag_data,
        headers=headers,
    )
    tag_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"name": "Updated Name", "color": "#FFFFFF"}
    response = client_with_db.put(
        f"/api/v1/tags/{tag_id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["color"] == "#FFFFFF"


def test_delete_tag(client_with_db, test_user, db_session):
    """Test deleting a tag."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
        role_name="manager",
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

    # Create a tag
    tag_data = {"name": "Test Tag"}
    create_response = client_with_db.post(
        "/api/v1/tags",
        json=tag_data,
        headers=headers,
    )
    tag_id = create_response.json()["data"]["id"]

    # Delete it
    response = client_with_db.delete(f"/api/v1/tags/{tag_id}", headers=headers)

    assert response.status_code == 204

    # Verify it's deleted (soft delete)
    get_response = client_with_db.get(f"/api/v1/tags/{tag_id}", headers=headers)
    assert get_response.status_code == 404


def test_attach_tag_to_entity(client_with_db, test_user, db_session):
    """Test attaching a tag to an entity."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
        role_name="manager",
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

    # Create a tag
    tag_data = {"name": "Test Tag"}
    create_response = client_with_db.post(
        "/api/v1/tags",
        json=tag_data,
        headers=headers,
    )
    tag_id = create_response.json()["data"]["id"]

    # Attach to entity
    entity_id = uuid4()
    response = client_with_db.post(
        f"/api/v1/tags/{tag_id}/entities/product/{entity_id}",
        headers=headers,
    )

    assert response.status_code == 204


def test_detach_tag_from_entity(client_with_db, test_user, auth_headers, db_session):
    """Test detaching a tag from an entity."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a tag
    tag_data = {"name": "Test Tag"}
    create_response = client_with_db.post(
        "/api/v1/tags",
        json=tag_data,
        headers=auth_headers,
    )
    tag_id = create_response.json()["data"]["id"]

    # Attach to entity
    entity_id = uuid4()
    client_with_db.post(
        f"/api/v1/tags/{tag_id}/entities/product/{entity_id}",
        headers=auth_headers,
    )

    # Detach it
    response = client_with_db.delete(
        f"/api/v1/tags/{tag_id}/entities/product/{entity_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204


def test_get_entity_tags(client_with_db, test_user, db_session):
    """Test getting tags for an entity."""
    # Assign permissions (manager to create tags, viewer to view)
    module_role = ModuleRole(
        user_id=test_user.id,
        module="tags",
        role_name="manager",
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

    # Create tags
    tag1_data = {"name": "Tag 1"}
    tag1_response = client_with_db.post(
        "/api/v1/tags",
        json=tag1_data,
        headers=headers,
    )
    tag1_id = tag1_response.json()["data"]["id"]

    tag2_data = {"name": "Tag 2"}
    tag2_response = client_with_db.post(
        "/api/v1/tags",
        json=tag2_data,
        headers=headers,
    )
    tag2_id = tag2_response.json()["data"]["id"]

    # Attach tags to entity
    entity_id = uuid4()
    client_with_db.post(
        f"/api/v1/tags/{tag1_id}/entities/product/{entity_id}",
        headers=headers,
    )
    client_with_db.post(
        f"/api/v1/tags/{tag2_id}/entities/product/{entity_id}",
        headers=headers,
    )

    # Get entity tags
    response = client_with_db.get(
        f"/api/v1/tags/entities/product/{entity_id}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 2
    tag_ids = [t["id"] for t in data]
    assert tag1_id in tag_ids
    assert tag2_id in tag_ids

