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
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    assert integration["name"] == "Test Integration"
    assert integration["type"] == IntegrationType.WEBHOOK.value
    assert integration["status"] == IntegrationStatus.INACTIVE.value
    assert integration["tenant_id"] == test_tenant.id


def test_get_integration(integration_service, test_tenant):
    """Test getting an integration."""
    # Create an integration first
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Get it
    retrieved = integration_service.get_integration(integration["id"], test_tenant.id)

    assert retrieved is not None
    assert retrieved["id"] == integration["id"]
    assert retrieved["name"] == "Test Integration"


def test_get_integrations(integration_service, test_tenant):
    """Test getting integrations with filters."""
    # Create multiple integrations
    integration1 = integration_service.create_integration(
        name="Integration 1",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook1"},
    )
    integration2 = integration_service.create_integration(
        name="Integration 2",
        tenant_id=test_tenant.id,
        type=IntegrationType.CUSTOM,
        config={"endpoint": "https://api.example.com"},
    )

    # Get all integrations
    integrations = integration_service.list_integrations(test_tenant.id)
    assert len(integrations) >= 2

    # Filter by type
    webhook_integrations = integration_service.list_integrations(
        test_tenant.id, integration_type=IntegrationType.WEBHOOK
    )
    assert any(i["id"] == integration1["id"] for i in webhook_integrations)
    assert not any(i["id"] == integration2["id"] for i in webhook_integrations)


def test_update_integration(integration_service, test_tenant):
    """Test updating an integration."""
    # Create an integration
    integration = integration_service.create_integration(
        name="Original Name",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Update it
    updated = integration_service.update_integration(
        integration["id"],
        test_tenant.id,
        name="Updated Name",
        status=IntegrationStatus.INACTIVE,
    )

    assert updated is not None
    assert updated["name"] == "Updated Name"
    assert updated["status"] == IntegrationStatus.INACTIVE.value


def test_delete_integration(integration_service, test_tenant):
    """Test deleting an integration."""
    # Create an integration
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Delete it
    integration_service.delete_integration(integration["id"], test_tenant.id)

    # Verify it's deleted
    with pytest.raises(ValueError):
        integration_service.get_integration(integration["id"], test_tenant.id)


def test_get_credentials_success(integration_service, test_tenant, db_session):
    """Test getting decrypted credentials successfully."""
    import json
    from app.core.security.encryption import encrypt_credentials

    # Create integration with encrypted credentials
    credentials_dict = {"api_key": "sk_test_1234567890", "secret": "secret_key_abc"}
    credentials_json = json.dumps(credentials_dict)
    encrypted_credentials = encrypt_credentials(credentials_json, test_tenant.id)

    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Update integration with encrypted credentials (simulating storage)
    from app.repositories.integration_repository import IntegrationRepository
    repo = IntegrationRepository(db_session)
    integration_model = repo.get_by_id(integration["id"], test_tenant.id)
    integration_model.credentials = encrypted_credentials
    db_session.commit()
    db_session.refresh(integration_model)

    # Get credentials
    credentials = integration_service.get_credentials(integration["id"], test_tenant.id)

    assert credentials == credentials_dict
    assert credentials["api_key"] == "sk_test_1234567890"
    assert credentials["secret"] == "secret_key_abc"


def test_get_credentials_not_found(integration_service, test_tenant):
    """Test getting credentials for non-existent integration."""
    from uuid import uuid4

    fake_id = uuid4()
    with pytest.raises(ValueError, match="Integration not found"):
        integration_service.get_credentials(fake_id, test_tenant.id)


def test_get_credentials_from_config(integration_service, test_tenant):
    """Test getting credentials from config (backward compatibility)."""
    # Create integration with credentials in config
    credentials_dict = {"api_key": "sk_test_123", "secret": "secret_123"}

    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook", "credentials": credentials_dict},
    )

    # Get credentials (should get from config)
    credentials = integration_service.get_credentials(integration["id"], test_tenant.id)

    assert credentials == credentials_dict


def test_get_credentials_from_column(integration_service, test_tenant, db_session):
    """Test getting credentials from credentials column (new method)."""
    import json
    from app.core.security.encryption import encrypt_credentials
    from app.repositories.integration_repository import IntegrationRepository

    # Create integration
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Add encrypted credentials to column
    credentials_dict = {"api_key": "sk_test_456", "secret": "secret_456"}
    credentials_json = json.dumps(credentials_dict)
    encrypted_credentials = encrypt_credentials(credentials_json, test_tenant.id)

    repo = IntegrationRepository(db_session)
    integration_model = repo.get_by_id(integration["id"], test_tenant.id)
    integration_model.credentials = encrypted_credentials
    db_session.commit()
    db_session.refresh(integration_model)

    # Get credentials (should get from column, not config)
    credentials = integration_service.get_credentials(integration["id"], test_tenant.id)

    assert credentials == credentials_dict


def test_get_credentials_empty(integration_service, test_tenant):
    """Test getting credentials when none exist returns empty dict."""
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Get credentials (should return empty dict)
    credentials = integration_service.get_credentials(integration["id"], test_tenant.id)

    assert credentials == {}


def test_get_credentials_decryption_error(integration_service, test_tenant, db_session):
    """Test handling of decryption errors."""
    from app.repositories.integration_repository import IntegrationRepository

    # Create integration
    integration = integration_service.create_integration(
        name="Test Integration",
        tenant_id=test_tenant.id,
        type=IntegrationType.WEBHOOK,
        config={"url": "https://example.com/webhook"},
    )

    # Add invalid encrypted data
    repo = IntegrationRepository(db_session)
    integration_model = repo.get_by_id(integration["id"], test_tenant.id)
    integration_model.credentials = "invalid_encrypted_data"
    db_session.commit()
    db_session.refresh(integration_model)

    # Should handle error gracefully and return empty dict or raise
    # For now, we'll expect it to return empty dict as fallback
    credentials = integration_service.get_credentials(integration["id"], test_tenant.id)

    # Should return empty dict when decryption fails
    assert credentials == {}


# Note: get_logs method doesn't exist in the service
# This test is skipped as the service doesn't implement log retrieval
@pytest.mark.skip(reason="get_logs method not implemented in service")
def test_get_logs(integration_service, test_tenant):
    """Test getting integration logs."""
    pass








