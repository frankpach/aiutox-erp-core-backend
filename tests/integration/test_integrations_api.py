"""Integration tests for Integrations API endpoints."""

import pytest
from uuid import uuid4

from tests.helpers import create_user_with_permission


def test_create_integration(client, test_user, db_session):
    """Test creating an integration."""
    # Assign integrations.manage permission
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

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
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Integration"
    assert data["integration_type"] == "webhook"
    assert "id" in data


def test_list_integrations(client, test_user, db_session):
    """Test listing integrations."""
    # Assign integrations.view permission
    headers = create_user_with_permission(db_session, test_user, "integrations", "viewer")

    response = client.get("/api/v1/integrations", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "meta" in response.json()
    assert "total" in response.json()["meta"]


def test_get_integration(client, test_user, db_session):
    """Test getting an integration."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

    # Create an integration
    integration_data = {
        "name": "Test Integration",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Get it
    response = client.get(f"/api/v1/integrations/{integration_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == integration_id
    assert data["name"] == "Test Integration"


def test_update_integration(client, test_user, db_session):
    """Test updating an integration."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

    # Create an integration
    integration_data = {
        "name": "Original Name",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"name": "Updated Name", "status": "inactive"}
    response = client.put(
        f"/api/v1/integrations/{integration_id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["status"] == "inactive"


def test_delete_integration(client, test_user, db_session):
    """Test deleting an integration."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

    # Create an integration
    integration_data = {
        "name": "Test Integration",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Delete it
    response = client.delete(f"/api/v1/integrations/{integration_id}", headers=headers)

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/integrations/{integration_id}", headers=headers)
    assert get_response.status_code == 404


def test_get_integration_logs(client, test_user, db_session):
    """Test getting integration logs."""
    # Assign permissions (need manager to create, viewer to read logs)
    manager_headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

    # Create an integration
    integration_data = {
        "name": "Test Integration",
        "integration_type": "webhook",
        "config": {"url": "https://example.com/webhook"},
    }
    create_response = client.post(
        "/api/v1/integrations",
        json=integration_data,
        headers=manager_headers,
    )
    integration_id = create_response.json()["data"]["id"]

    # Get logs (viewer permission)
    headers = create_user_with_permission(db_session, test_user, "integrations", "viewer")
    response = client.get(
        f"/api/v1/integrations/{integration_id}/logs",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)
    # Should have at least the creation log
    assert len(data) >= 1


def test_create_webhook(client, test_user, db_session):
    """Test creating a webhook."""
    # Assign integrations.manage permission
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

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
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Webhook"
    assert data["event_type"] == "product.created"
    assert data["enabled"] is True
    assert "id" in data


def test_list_webhooks(client, test_user, db_session):
    """Test listing webhooks."""
    # Assign integrations.view permission
    headers = create_user_with_permission(db_session, test_user, "integrations", "viewer")

    response = client.get("/api/v1/integrations/webhooks", headers=headers)

    # Debug 422 errors
    if response.status_code == 422:
        print(f"422 Error details: {response.json()}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.json() if response.status_code < 500 else response.text[:200]}"
    data = response.json()["data"]
    assert isinstance(data, list)
    assert "meta" in response.json()
    assert "total" in response.json()["meta"]


def test_get_webhook(client, test_user, db_session):
    """Test getting a webhook."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

    # Create a webhook
    webhook_data = {
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "event_type": "product.created",
    }
    create_response = client.post(
        "/api/v1/integrations/webhooks",
        json=webhook_data,
        headers=headers,
    )
    webhook_id = create_response.json()["data"]["id"]

    # Get it
    response = client.get(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == webhook_id
    assert data["name"] == "Test Webhook"


def test_update_webhook(client, test_user, db_session):
    """Test updating a webhook."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

    # Create a webhook
    webhook_data = {
        "name": "Original Name",
        "url": "https://example.com/webhook",
        "event_type": "product.created",
    }
    create_response = client.post(
        "/api/v1/integrations/webhooks",
        json=webhook_data,
        headers=headers,
    )
    webhook_id = create_response.json()["data"]["id"]

    # Update it
    update_data = {"name": "Updated Name", "enabled": False}
    response = client.put(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        json=update_data,
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Name"
    assert data["enabled"] is False


def test_delete_webhook(client, test_user, db_session):
    """Test deleting a webhook."""
    # Assign permissions
    headers = create_user_with_permission(db_session, test_user, "integrations", "manager")

    # Create a webhook
    webhook_data = {
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "event_type": "product.created",
    }
    create_response = client.post(
        "/api/v1/integrations/webhooks",
        json=webhook_data,
        headers=headers,
    )
    webhook_id = create_response.json()["data"]["id"]

    # Delete it
    response = client.delete(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=headers,
    )

    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(
        f"/api/v1/integrations/webhooks/{webhook_id}",
        headers=headers,
    )
    assert get_response.status_code == 404





