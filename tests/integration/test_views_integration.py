"""Integration tests for Views module interactions."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_saved_filter_sharing(client, test_user, auth_headers, db_session):
    """Test sharing saved filters with other users."""
    # Assign permissions
    view_role = ModuleRole(
        user_id=test_user.id,
        module="views",
        role_name="manager",
        granted_by=test_user.id,
    )
    share_role = ModuleRole(
        user_id=test_user.id,
        module="views",
        role_name="sharer",
        granted_by=test_user.id,
    )
    db_session.add(view_role)
    db_session.add(share_role)
    db_session.commit()

    # Create filter
    filter_data = {
        "name": "Shared Filter",
        "module": "products",
        "filters": {"status": "active"},
        "is_shared": True,
    }
    filter_response = client.post(
        "/api/v1/views/filters",
        json=filter_data,
        headers=auth_headers,
    )
    filter_id = filter_response.json()["data"]["id"]

    # Create another user
    from app.models.user import User
    shared_user = User(
        id=uuid4(),
        email="shared@test.com",
        tenant_id=test_user.tenant_id,
        password_hash="hashed",
    )
    db_session.add(shared_user)
    db_session.commit()

    # Share filter
    share_data = {
        "filter_id": filter_id,
        "shared_with_user_id": str(shared_user.id),
    }
    share_response = client.post(
        f"/api/v1/views/filters/{filter_id}/share",
        json=share_data,
        headers=auth_headers,
    )

    assert share_response.status_code == 201
    assert share_response.json()["data"]["filter_id"] == filter_id


def test_custom_view_with_filters(client, test_user, auth_headers, db_session):
    """Test custom view with associated filters."""
    # Assign permissions
    view_role = ModuleRole(
        user_id=test_user.id,
        module="views",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(view_role)
    db_session.commit()

    # Create filter
    filter_data = {
        "name": "Active Products",
        "module": "products",
        "filters": {"status": "active"},
    }
    filter_response = client.post(
        "/api/v1/views/filters",
        json=filter_data,
        headers=auth_headers,
    )
    filter_id = filter_response.json()["data"]["id"]

    # Create view with filter
    view_data = {
        "name": "Active Products View",
        "module": "products",
        "columns": {"name": True, "price": True, "status": True},
        "filters": {"saved_filter_id": filter_id},
    }
    view_response = client.post(
        "/api/v1/views/views",
        json=view_data,
        headers=auth_headers,
    )

    assert view_response.status_code == 201
    view = view_response.json()["data"]
    assert view["name"] == "Active Products View"
    assert view["filters"] is not None








