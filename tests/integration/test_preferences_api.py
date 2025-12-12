"""Integration tests for Preferences API endpoints."""

import pytest
from app.models.module_role import ModuleRole


def test_get_preferences(client, test_user, auth_headers, db_session):
    """Test getting user preferences."""
    # Assign preferences.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="preferences",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/preferences", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, dict)


def test_update_preferences(client, test_user, auth_headers, db_session):
    """Test updating user preferences."""
    # Assign preferences.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="preferences",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    preference_data = {
        "preferences": {
            "language": "en",
            "timezone": "UTC",
            "theme": "dark",
        }
    }

    response = client.put(
        "/api/v1/preferences?preference_type=basic",
        json=preference_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["language"] == "en"
    assert data["timezone"] == "UTC"


def test_get_notification_preferences(client, test_user, auth_headers, db_session):
    """Test getting notification preferences."""
    # Assign preferences.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="preferences",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/preferences/notifications", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, dict)


def test_update_notification_preferences(client, test_user, auth_headers, db_session):
    """Test updating notification preferences."""
    # Assign preferences.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="preferences",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    notification_data = {
        "preferences": {
            "product.created": {
                "enabled": True,
                "channels": ["email", "in-app"],
                "frequency": "immediate",
            }
        }
    }

    response = client.put(
        "/api/v1/preferences/notifications",
        json=notification_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert "product.created" in data


def test_save_view(client, test_user, auth_headers, db_session):
    """Test saving a view."""
    # Assign preferences.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="preferences",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    view_data = {
        "name": "My Products View",
        "config": {"columns": ["name", "sku", "price"], "filters": {}},
        "is_default": False,
    }

    response = client.post(
        "/api/v1/preferences/views/products",
        json=view_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "My Products View"
    assert data["module"] == "products"


def test_get_saved_views(client, test_user, auth_headers, db_session):
    """Test getting saved views."""
    # Assign preferences.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="preferences",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    from app.core.preferences.views import ViewsService

    views_service = ViewsService(db_session)
    views_service.save_view(
        user_id=test_user.id,
        tenant_id=test_user.tenant_id,
        module="products",
        name="Test View",
        config={"columns": ["name"]},
    )

    response = client.get("/api/v1/preferences/views/products", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0


def test_create_dashboard(client, test_user, auth_headers, db_session):
    """Test creating a dashboard."""
    # Assign preferences.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="preferences",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    dashboard_data = {
        "name": "My Dashboard",
        "widgets": [
            {"type": "kpi", "title": "Total Products", "value": 100},
            {"type": "chart", "title": "Sales", "data": []},
        ],
        "is_default": False,
    }

    response = client.post(
        "/api/v1/preferences/dashboards",
        json=dashboard_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "My Dashboard"
    assert len(data["widgets"]) == 2

