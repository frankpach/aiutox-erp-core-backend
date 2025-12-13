"""Integration tests for Integrations API endpoints."""

import pytest
from uuid import uuid4

from app.models.module_role import ModuleRole


def test_create_integration(client, test_user, auth_headers, db_session):
    """Test creating an integration."""
    # Assign integrations.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    integration_data = {
        "name": "Test Integration",
        "description": "Test description",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
        "credentials": {"api_key": "secret-key"},
    }

    response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Integration"
    assert data["integration_type"] == "webhook"
    assert "id" in data


def test_list_integrations(client, test_user, auth_headers, db_session):
    """Test listing integrations."""
    # Assign integrations.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/integrations", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "total" in response.json()


def test_get_integration(client, test_user, auth_headers, db_session):
    """Test getting an integration."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create an integration
    integration_data = {
        "name": "Test Integration",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=auth_headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Get it
    response = client.get(f"/api/v1/integrations/{integration_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == integration_id
    assert data["name"] == "Test Integration"


def test_update_integration(client, test_user, auth_headers, db_session):
    """Test updating an integration."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create an integration
    integration_data = {
        "name": "Original Name",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=auth_headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"name": "Updated Name", "status": "inactive"}
    response = client.put(
        f"/api/v1/integrations/{integration_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["status"] == "inactive"


def test_delete_integration(client, test_user, auth_headers, db_session):
    """Test deleting an integration."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create an integration
    integration_data = {
        "name": "Test Integration",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=auth_headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Delete it
    response = client.delete(f"/api/v1/integrations/{integration_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/integrations/{integration_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_get_integration_logs(client, test_user, auth_headers, db_session):
    """Test getting integration logs."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create an integration
    integration_data = {
        "name": "Test Integration",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=auth_headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Get logs
    response = client.get(
        f"/api/v1/integrations/{integration_id}/logs",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    # Should have at least the creation log
    assert len(data) >= 1


def test_create_webhook(client, test_user, auth_headers, db_session):
    """Test creating a webhook."""
    # Assign integrations.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    webhook_data = {
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "event_type": "product.created",
        "enabled": True,
        "method": "POST",
    }

    response = client.post(
        "/api/v1/integrations/webhooks",
        json=webhook_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Webhook"
    assert data["event_type"] == "product.created"
    assert data["enabled"] is True
    assert "id" in data


def test_list_webhooks(client, test_user, auth_headers, db_session):
    """Test listing webhooks."""
    # Assign integrations.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="viewer",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client.get("/api/v1/integrations/webhooks", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "total" in response.json()


def test_get_webhook(client, test_user, auth_headers, db_session):
    """Test getting a webhook."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a webhook
    webhook_data = {
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "event_type": "product.created",
    }
    create_response = client.post(
        "/api/v1/integrations/webhooks",
        json=webhook_data,
        headers=auth_headers,
    )
    webhook_id = create_response.json()["data"]["id"]

    # Get it
    response = client.get(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == webhook_id
    assert data["name"] == "Test Webhook"


def test_update_webhook(client, test_user, auth_headers, db_session):
    """Test updating a webhook."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a webhook
    webhook_data = {
        "name": "Original Name",
        "url": "https://example.com/webhook",
        "event_type": "product.created",
    }
    create_response = client.post(
        "/api/v1/integrations/webhooks",
        json=webhook_data,
        headers=auth_headers,
    )
    webhook_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"name": "Updated Name", "enabled": False}
    response = client.put(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        json=update_data,
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["enabled"] is False


def test_delete_webhook(client, test_user, auth_headers, db_session):
    """Test deleting a webhook."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="integrations",
        role_name="manager",
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # Create a webhook
    webhook_data = {
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "event_type": "product.created",
    }
    create_response = client.post(
        "/api/v1/integrations/webhooks",
        json=webhook_data,
        headers=auth_headers,
    )
    webhook_id = create_response.json()["data"]["id"]

    # Delete it
    response = client.delete(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 404

