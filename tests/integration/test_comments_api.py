"""Integration tests for Comments API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_comment(client, test_user, auth_headers, db_session):
    """Test creating a comment."""
    # Assign comments.create permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="creator",  # Maps to internal.creator -> comments.view, comments.create
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    entity_id = uuid4()
    comment_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "content": "This is a test comment",
    }

    response = client.post(
        "/api/v1/comments",
        json=comment_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["content"] == "This is a test comment"
    assert data["entity_type"] == "product"
    assert "id" in data


def test_list_comments(client, test_user, auth_headers, db_session):
    """Test listing comments for an entity."""
    # Assign comments.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="viewer",  # Maps to internal.viewer -> comments.view
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    entity_id = uuid4()

    response = client.get(
        f"/api/v1/comments?entity_type=product&entity_id={entity_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_update_comment(client, test_user, auth_headers, db_session):
    """Test updating a comment."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="comments",
        role_name="creator",  # Maps to internal.creator -> comments.view, comments.create
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First create a comment
    entity_id = uuid4()
    comment_data = {
        "entity_type": "product",
        "entity_id": str(entity_id),
        "content": "Original comment",
    }
    comment_response = client.post(
        "/api/v1/comments",
        json=comment_data,
        headers=auth_headers,
    )
    comment_id = comment_response.json()["data"]["id"]

    # Update comment
    update_data = {"content": "Updated comment"}

    response = client.put(
        f"/api/v1/comments/{comment_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["content"] == "Updated comment"
    assert data["is_edited"] == True

