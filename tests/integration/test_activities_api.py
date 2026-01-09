"""Integration tests for Activities API endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.models.activity import ActivityType
from tests.helpers import create_user_with_permission


def test_create_activity(client_with_db: TestClient, test_user, db_session):
    """Test creating an activity."""
    # Assign activities.manage permission
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")

    entity_id = str(uuid4())
    response = client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": entity_id,
            "activity_type": ActivityType.COMMENT,
            "title": "Test Comment",
            "description": "This is a test comment",
            "metadata": {"priority": "high"},
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["data"]["entity_type"] == "product"
    assert data["data"]["entity_id"] == entity_id
    assert data["data"]["activity_type"] == ActivityType.COMMENT
    assert data["data"]["title"] == "Test Comment"
    assert data["data"]["description"] == "This is a test comment"
    # Schema uses metadata with alias activity_metadata, check both
    assert data["data"].get("metadata") == {"priority": "high"} or data["data"].get("activity_metadata") == {"priority": "high"}
    assert data["data"]["user_id"] == str(test_user.id)
    assert "id" in data["data"]
    assert "created_at" in data["data"]


def test_create_activity_requires_permission(client_with_db: TestClient, test_user, db_session, auth_headers):
    """Test that creating an activity requires activities.manage permission."""
    # Use auth_headers but without activities.manage permission
    headers = auth_headers
    entity_id = str(uuid4())
    response = client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": entity_id,
            "activity_type": ActivityType.COMMENT,
            "title": "Test Comment",
        },
        headers=headers,
    )

    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"


def test_list_activities(client_with_db: TestClient, test_user, db_session):
    """Test listing activities."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")

    entity_id = uuid4()

    # Create multiple activities
    for i in range(3):
        client_with_db.post(
            "/api/v1/activities",
            json={
                "entity_type": "product",
                "entity_id": str(entity_id),
                "activity_type": ActivityType.COMMENT,
                "title": f"Comment {i+1}",
            },
            headers=headers,
        )

    # List all activities
    response = client_with_db.get("/api/v1/activities?page=1&page_size=20", headers=view_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 3
    assert data["meta"]["total"] >= 3
    assert data["meta"]["page"] == 1
    assert data["meta"]["page_size"] == 20


def test_list_activities_with_filters(client_with_db: TestClient, test_user, db_session):
    """Test listing activities with filters."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")

    entity_id = uuid4()

    # Create activities with different types
    client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.COMMENT,
            "title": "Comment",
        },
        headers=headers,
    )

    client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.STATUS_CHANGE,
            "title": "Status Changed",
        },
        headers=headers,
    )

    # Filter by entity
    response = client_with_db.get(
        f"/api/v1/activities?entity_type=product&entity_id={entity_id}&page=1&page_size=20",
        headers=view_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2

    # Filter by activity type - verify activities were created
    # First, get all activities for this entity to verify they exist
    response_all = client_with_db.get(
        f"/api/v1/activities?entity_type=product&entity_id={entity_id}&page=1&page_size=20",
        headers=view_headers,
    )
    assert response_all.status_code == 200
    data_all = response_all.json()
    # We should have 2 activities (comment and status_change)
    assert len(data_all["data"]) == 2, f"Expected 2 activities, got {len(data_all['data'])}"

    # Now filter by activity type
    response = client_with_db.get(
        f"/api/v1/activities?entity_type=product&entity_id={entity_id}&activity_type={ActivityType.COMMENT.value}&page=1&page_size=20",
        headers=view_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Should return only comments for this specific entity
    assert len(data["data"]) >= 1, f"Expected at least 1 comment, got {len(data['data'])}. Response: {data}"
    # Verify all returned activities match the filters
    for activity in data["data"]:
        assert activity["entity_type"] == "product"
        assert activity["entity_id"] == str(entity_id)
        assert activity["activity_type"] == ActivityType.COMMENT.value


def test_list_activities_with_search(client_with_db: TestClient, test_user, db_session):
    """Test listing activities with search."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")

    entity_id = uuid4()

    # Create activities with searchable content
    client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.COMMENT,
            "title": "Product Review",
            "description": "This product is great",
        },
        headers=headers,
    )

    client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.COMMENT,
            "title": "Price Update",
            "description": "Updated the price",
        },
        headers=headers,
    )

    # Search
    response = client_with_db.get("/api/v1/activities?search=Review&page=1&page_size=20", headers=view_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) >= 1
    assert "Review" in data["data"][0]["title"] or "Review" in data["data"][0].get("description", "")


def test_get_activity(client_with_db: TestClient, test_user, db_session):
    """Test getting a specific activity."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")

    entity_id = uuid4()

    # Create activity
    create_response = client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.COMMENT,
            "title": "Test Comment",
        },
        headers=headers,
    )

    activity_id = create_response.json()["data"]["id"]

    # Get activity
    response = client_with_db.get(f"/api/v1/activities/{activity_id}", headers=view_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["id"] == activity_id
    assert data["data"]["title"] == "Test Comment"


def test_get_activity_not_found(client_with_db: TestClient, test_user, db_session):
    """Test getting a non-existent activity."""
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")
    fake_id = uuid4()
    response = client_with_db.get(f"/api/v1/activities/{fake_id}", headers=view_headers)

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_update_activity(client_with_db: TestClient, test_user, db_session):
    """Test updating an activity."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")

    entity_id = uuid4()

    # Create activity
    create_response = client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.COMMENT,
            "title": "Original Title",
            "description": "Original description",
        },
        headers=headers,
    )

    activity_id = create_response.json()["data"]["id"]

    # Update activity
    response = client_with_db.put(
        f"/api/v1/activities/{activity_id}",
        json={
            "title": "Updated Title",
            "description": "Updated description",
            "metadata": {"updated": True},
        },
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["title"] == "Updated Title"
    assert data["data"]["description"] == "Updated description"
    # Schema uses metadata with alias activity_metadata, check both
    assert data["data"].get("metadata") == {"updated": True} or data["data"].get("activity_metadata") == {"updated": True}


def test_update_activity_not_found(client_with_db: TestClient, test_user, db_session):
    """Test updating a non-existent activity."""
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    fake_id = uuid4()
    response = client_with_db.put(
        f"/api/v1/activities/{fake_id}",
        json={"title": "Updated Title"},
        headers=headers,
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_delete_activity(client_with_db: TestClient, test_user, db_session):
    """Test deleting an activity."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")

    entity_id = uuid4()

    # Create activity
    create_response = client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.COMMENT,
            "title": "To Delete",
        },
        headers=headers,
    )

    activity_id = create_response.json()["data"]["id"]

    # Delete activity
    response = client_with_db.delete(f"/api/v1/activities/{activity_id}", headers=headers)

    assert response.status_code == 204

    # Verify it's gone
    get_response = client_with_db.get(f"/api/v1/activities/{activity_id}", headers=view_headers)
    assert get_response.status_code == 404


def test_delete_activity_not_found(client_with_db: TestClient, test_user, db_session):
    """Test deleting a non-existent activity."""
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    fake_id = uuid4()
    response = client_with_db.delete(f"/api/v1/activities/{fake_id}", headers=headers)

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "ACTIVITY_NOT_FOUND"


def test_get_entity_timeline(client_with_db: TestClient, test_user, db_session):
    """Test getting timeline for an entity."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")

    entity_id = uuid4()

    # Create multiple activities
    for i in range(3):
        client_with_db.post(
            "/api/v1/activities",
            json={
                "entity_type": "product",
                "entity_id": str(entity_id),
                "activity_type": ActivityType.COMMENT,
                "title": f"Comment {i+1}",
            },
            headers=headers,
        )

    # Get timeline
    response = client_with_db.get(
        f"/api/v1/activities/entity/product/{entity_id}?page=1&page_size=20",
        headers=view_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 3
    assert data["meta"]["total"] == 3
    # Verify chronological order (most recent first)
    assert data["data"][0]["title"] == "Comment 3"
    assert data["data"][2]["title"] == "Comment 1"


def test_get_entity_timeline_with_filter(client_with_db: TestClient, test_user, db_session):
    """Test getting timeline with activity type filter."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "activities", "manager")
    view_headers = create_user_with_permission(db_session, test_user, "activities", "viewer")

    entity_id = uuid4()

    # Create activities with different types
    client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.COMMENT.value,  # Use .value to get string
            "title": "Comment",
        },
        headers=headers,
    )

    client_with_db.post(
        "/api/v1/activities",
        json={
            "entity_type": "product",
            "entity_id": str(entity_id),
            "activity_type": ActivityType.STATUS_CHANGE.value,  # Use .value to get string
            "title": "Status Changed",
        },
        headers=headers,
    )

    # Get timeline filtered by type - verify activities were created first
    response_all = client_with_db.get(
        f"/api/v1/activities/entity/product/{entity_id}?page=1&page_size=20",
        headers=view_headers,
    )
    assert response_all.status_code == 200
    data_all = response_all.json()
    # We should have 2 activities (comment and status_change)
    assert len(data_all["data"]) == 2, f"Expected 2 activities, got {len(data_all['data'])}"

    # Get timeline filtered by type
    response = client_with_db.get(
        f"/api/v1/activities/entity/product/{entity_id}?activity_type={ActivityType.COMMENT.value}&page=1&page_size=20",
        headers=view_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Should return only comments for this entity
    # We created 1 comment and 1 status_change, so filtered should return 1
    assert len(data["data"]) >= 1, f"Expected at least 1 comment, got {len(data['data'])}. Response: {data}"
    # Verify all returned activities are comments and match the entity
    for activity in data["data"]:
        assert activity["entity_type"] == "product"
        assert activity["entity_id"] == str(entity_id)
        assert activity["activity_type"] == ActivityType.COMMENT.value


def test_list_activities_requires_permission(client_with_db: TestClient, test_user, db_session, auth_headers):
    """Test that listing activities requires activities.view permission."""
    # Use auth_headers but without activities.view permission
    headers = auth_headers
    response = client_with_db.get("/api/v1/activities", headers=headers)

    assert response.status_code == 403
    data = response.json()
    assert data["error"]["code"] == "AUTH_INSUFFICIENT_PERMISSIONS"
