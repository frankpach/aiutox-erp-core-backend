"""Unit tests for IntegrationService."""

import pytest
from unittest.mock import patch
from uuid import uuid4

from app.core.integrations.service import IntegrationService
from app.models.integration import IntegrationStatus, IntegrationType


@pytest.fixture
def integration_service(db_session):
    """Create IntegrationService instance."""
    return IntegrationService(db=db_session)


def test_create_integration(integration_service, test_tenant):
    """Test creating an integration."""
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
        credentials={"api_key": "secret-key"},
        description="Test description",
    )

    assert integration.name == "Test Integration"
    assert integration.integration_type == IntegrationType.WEBHOOK
    assert integration.status == IntegrationStatus.ACTIVE
    assert integration.tenant_id == test_tenant.id
    assert integration.credentials is not None  # Should be encrypted


def test_get_integration(integration_service, test_tenant):
    """Test getting an integration."""
    # Create an integration first
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Get it
    retrieved = integration_service.get_integration(integration.id, test_tenant.id)

    assert retrieved is not None
    assert retrieved.id == integration.id
    assert retrieved.name == "Test Integration"


def test_get_integrations(integration_service, test_tenant):
    """Test getting integrations with filters."""
    # Create multiple integrations
    integration1 = integration_service.create_integration(
        name="Integration 1",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook1"},
    )
    integration2 = integration_service.create_integration(
        name="Integration 2",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.API,
        config={"endpoint": "https://api.example.com"},
    )

    # Get all integrations
    integrations = integration_service.get_integrations(test_tenant.id)
    assert len(integrations) >= 2

    # Filter by type
    webhook_integrations = integration_service.get_integrations(
        test_tenant.id, integration_type=IntegrationType.WEBHOOK
    )
    assert any(i.id == integration1.id for i in webhook_integrations)
    assert not any(i.id == integration2.id for i in webhook_integrations)


def test_update_integration(integration_service, test_tenant):
    """Test updating an integration."""
    # Create an integration
    integration = integration_service.create_integration(
        name="Original Name",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Update it
    updated = integration_service.update_integration(
        integration.id,
        test_tenant.id,
        {"name": "Updated Name", "status": IntegrationStatus.INACTIVE},
    )

    assert updated is not None
    assert updated.name == "Updated Name"
    assert updated.status == IntegrationStatus.INACTIVE


def test_delete_integration(integration_service, test_tenant):
    """Test deleting an integration."""
    # Create an integration
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Delete it
    deleted = integration_service.delete_integration(integration.id, test_tenant.id)

    assert deleted is True

    # Verify it's deleted
    retrieved = integration_service.get_integration(integration.id, test_tenant.id)
    assert retrieved is None


def test_get_credentials(integration_service, test_tenant):
    """Test getting decrypted credentials."""
    # Create an integration with credentials
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
        credentials={"api_key": "secret-key-123"},
    )

    # Get decrypted credentials
    credentials = integration_service.get_credentials(integration.id, test_tenant.id)

    assert credentials == {"api_key": "secret-key-123"}


def test_get_logs(integration_service, test_tenant):
    """Test getting integration logs."""
    # Create an integration
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        integration_type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Get logs (should have at least the creation log)
    logs = integration_service.get_logs(integration.id, test_tenant.id)

    assert isinstance(logs, list)
    assert len(logs) >= 1
    assert any(log.action == "created" for log in logs)

