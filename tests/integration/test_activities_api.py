"""Integration tests for Activities API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_activity(client, test_user, auth_headers, db_session):
    """Test creating an activity."""
    # Assign activities.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="activities",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    entity_id = uuid4()
    activity_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "activity_type": "comment",
        "title": "Test Comment",
        "description": "This is a test comment",
    }

    response = client.post(
        "/api/v1/activities",
        json=activity_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Test Comment"
    assert data["activity_type"] == "comment"
    assert data["entity_type"] == "product"
    assert "id" in data


def test_list_activities(client, test_user, auth_headers, db_session):
    """Test listing activities."""
    # Assign activities.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="activities",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/activities", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "total" in response.json()


def test_list_activities_by_entity(client, test_user, auth_headers, db_session):
    """Test listing activities for a specific entity."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="activities",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    entity_id = uuid4()

    # Create activities for the entity
    activity_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "activity_type": "comment",
        "title": "Comment 1",
    }
    client.post(
        "/api/v1/activities",
        json=activity_data,
        headers=auth_headers,
    )

    # List activities for entity
    response = client.get(
        f"/api/v1/activities?entity_type=product&entity_id={entity_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_activity(client, test_user, auth_headers, db_session):
    """Test getting an activity."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="activities",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create an activity
    entity_id = uuid4()
    activity_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "activity_type": "comment",
        "title": "Test Comment",
    }
    create_response = client.post(
        "/api/v1/activities",
        json=activity_data,
        headers=auth_headers,
    )
    activity_id = create_response.json()["data"]["id"]

    # Get it
    response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == activity_id
    assert data["title"] == "Test Comment"


def test_update_activity(client, test_user, auth_headers, db_session):
    """Test updating an activity."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="activities",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create an activity
    entity_id = uuid4()
    activity_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "activity_type": "comment",
        "title": "Original Title",
    }
    create_response = client.post(
        "/api/v1/activities",
        json=activity_data,
        headers=auth_headers,
    )
    activity_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"title": "Updated Title", "description": "Updated description"}
    response = client.put(
        f"/api/v1/activities/{activity_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated description"


def test_delete_activity(client, test_user, auth_headers, db_session):
    """Test deleting an activity."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="activities",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create an activity
    entity_id = uuid4()
    activity_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "activity_type": "comment",
        "title": "Test Comment",
    }
    create_response = client.post(
        "/api/v1/activities",
        json=activity_data,
        headers=auth_headers,
    )
    activity_id = create_response.json()["data"]["id"]

    # Delete it
    response = client.delete(f"/api/v1/activities/{activity_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/activities/{activity_id}", headers=auth_headers)
    assert get_response.status_code == 404

