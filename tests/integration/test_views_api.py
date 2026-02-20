"""Integration tests for Views API endpoints."""

from app.models.module_role import ModuleRole


def test_create_saved_filter(client_with_db, test_user, auth_headers, db_session):
    """Test creating a saved filter."""
    # Assign views.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="views",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    filter_data = {
        "name": "Test Filter",
        "module": "products",
        "filters": {"status": "active"},
    }

    response = client_with_db.post(
        "/api/v1/views/filters",
        json=filter_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Filter"
    assert data["module"] == "products"
    assert "id" in data


def test_create_custom_view(client_with_db, test_user, auth_headers, db_session):
    """Test creating a custom view."""
    # Assign views.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="views",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    view_data = {
        "name": "Test View",
        "module": "products",
        "columns": {"name": True, "price": True},
    }

    response = client_with_db.post(
        "/api/v1/views/views",
        json=view_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test View"
    assert data["module"] == "products"
    assert "id" in data
