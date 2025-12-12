"""Integration tests for Notifications API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_notification_template(client, test_user, auth_headers, db_session):
    """Test creating a notification template."""
    # Assign notifications.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="notifications",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    template_data = {
        "name": "Product Created Email",
        "event_type": "product.created",
        "channel": "email",
        "subject": "New Product: {{product_name}}",
        "body": "A new product {{product_name}} with SKU {{sku}} has been created.",
        "is_active": True,
    }

    response = client.post(
        "/api/v1/notifications/templates",
        json=template_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Product Created Email"
    assert data["event_type"] == "product.created"
    assert data["channel"] == "email"
    assert "id" in data


def test_list_notification_templates(client, test_user, auth_headers, db_session):
    """Test listing notification templates."""
    # Assign notifications.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="notifications",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    response = client.get("/api/v1/notifications/templates", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) > 0
    assert data[0]["name"] == "Test Template"


def test_get_notification_template(client, test_user, auth_headers, db_session):
    """Test getting a specific notification template."""
    # Assign notifications.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="notifications",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    template = repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    response = client.get(
        f"/api/v1/notifications/templates/{template.id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(template.id)
    assert data["name"] == "Test Template"


def test_update_notification_template(client, test_user, auth_headers, db_session):
    """Test updating a notification template."""
    # Assign notifications.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="notifications",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    template = repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    update_data = {"name": "Updated Template", "body": "Updated body"}

    response = client.put(
        f"/api/v1/notifications/templates/{template.id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Template"
    assert data["body"] == "Updated body"


def test_delete_notification_template(client, test_user, auth_headers, db_session):
    """Test deleting a notification template."""
    # Assign notifications.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="notifications",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a template
    from app.repositories.notification_repository import NotificationRepository

    repo = NotificationRepository(db_session)
    template = repo.create_template(
        {
            "tenant_id": test_user.tenant_id,
            "name": "Test Template",
            "event_type": "product.created",
            "channel": "email",
            "subject": "Test",
            "body": "Test body",
            "is_active": True,
        }
    )

    response = client.delete(
        f"/api/v1/notifications/templates/{template.id}", headers=auth_headers
    )

    assert response.status_code == 204

    # Verify it's deleted
    response = client.get(
        f"/api/v1/notifications/templates/{template.id}", headers=auth_headers
    )
    assert response.status_code == 404


def test_list_notification_queue(client, test_user, auth_headers, db_session):
    """Test listing notification queue entries."""
    # Assign notifications.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="notifications",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/notifications/queue", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_send_notification_requires_permission(client, test_user, auth_headers):
    """Test that sending notification requires notifications.manage permission."""
    send_data = {
        "event_type": "product.created",
        "recipient_id": str(test_user.id),
        "channels": ["email"],
        "data": {"product_name": "Test Product"},
    }

    response = client.post(
        "/api/v1/notifications/send", json=send_data, headers=auth_headers
    )

    assert response.status_code == 403

