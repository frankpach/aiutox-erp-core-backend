"""Integration service for managing integrations."""

import json
import logging
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.models.integration import Integration, IntegrationLog, IntegrationStatus, IntegrationType
from app.repositories.integration_repository import IntegrationRepository

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for integration management."""

    def __init__(self, db: Session, encryption_key: str | None = None):
        """Initialize integration service.

        Args:
            db: Database session
            encryption_key: Encryption key for credentials (from env if not provided)
        """
        self.db = db
        self.repository = IntegrationRepository(db)

        # Get encryption key from environment or use provided
        import os

        key = encryption_key or os.getenv("INTEGRATION_ENCRYPTION_KEY")
        if key:
            try:
                self.cipher = Fernet(key.encode())
            except Exception as e:
                logger.warning(f"Failed to initialize encryption: {e}")
                self.cipher = None
        else:
            logger.warning("No encryption key provided for integrations")
            self.cipher = None

    def _encrypt_credentials(self, credentials: dict[str, Any]) -> str:
        """Encrypt credentials.

        Args:
            credentials: Credentials dictionary

        Returns:
            Encrypted credentials as JSON string
        """
        if not self.cipher:
            logger.warning("Encryption not available, storing credentials in plain text")
            return json.dumps(credentials)

        credentials_json = json.dumps(credentials)
        encrypted = self.cipher.encrypt(credentials_json.encode())
        return encrypted.decode()

    def _decrypt_credentials(self, encrypted_credentials: str) -> dict[str, Any]:
        """Decrypt credentials.

        Args:
            encrypted_credentials: Encrypted credentials as string

        Returns:
            Decrypted credentials dictionary
        """
        if not self.cipher:
            # Try to parse as plain JSON
            try:
                return json.loads(encrypted_credentials)
            except Exception:
                logger.warning("Failed to decrypt credentials and encryption not available")
                return {}

        try:
            decrypted = self.cipher.decrypt(encrypted_credentials.encode())
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            return {}

    def create_integration(
        self,
        name: str,
        tenant_id: UUID,
        integration_type: str,
        config: dict[str, Any],
        credentials: dict[str, Any] | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Integration:
        """Create a new integration.

        Args:
            name: Integration name
            tenant_id: Tenant ID
            integration_type: Integration type (webhook, api, oauth, custom)
            config: Integration configuration
            credentials: Integration credentials (will be encrypted)
            description: Integration description (optional)
            metadata: Additional metadata (optional)

        Returns:
            Created Integration object
        """
        encrypted_credentials = None
        if credentials:
            encrypted_credentials = self._encrypt_credentials(credentials)

        integration = self.repository.create_integration(
            {
                "tenant_id": tenant_id,
                "name": name,
                "description": description,
                "integration_type": integration_type,
                "status": IntegrationStatus.ACTIVE,
                "config": config,
                "credentials": encrypted_credentials,
                "metadata": metadata,
            }
        )

        # Log integration creation
        self.repository.create_log(
            {
                "integration_id": integration.id,
                "tenant_id": tenant_id,
                "action": "created",
                "status": "success",
                "message": f"Integration {name} created",
            }
        )

        logger.info(f"Integration created: {integration.id} ({name})")
        return integration

    def get_integration(self, integration_id: UUID, tenant_id: UUID) -> Integration | None:
        """Get an integration by ID.

        Args:
            integration_id: Integration ID
            tenant_id: Tenant ID

        Returns:
            Integration object or None if not found
        """
        return self.repository.get_integration_by_id(integration_id, tenant_id)

    def get_integrations(
        self,
        tenant_id: UUID,
        integration_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Integration]:
        """Get integrations for a tenant.

        Args:
            tenant_id: Tenant ID
            integration_type: Filter by integration type (optional)
            status: Filter by status (optional)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Integration objects
        """
        return self.repository.get_all_integrations(tenant_id, integration_type, status, skip, limit)

    def update_integration(
        self, integration_id: UUID, tenant_id: UUID, integration_data: dict
    ) -> Integration | None:
        """Update an integration.

        Args:
            integration_id: Integration ID
            tenant_id: Tenant ID
            integration_data: Integration data to update

        Returns:
            Updated Integration object or None if not found
        """
        # Encrypt credentials if provided
        if "credentials" in integration_data and isinstance(
            integration_data["credentials"], dict
        ):
            integration_data["credentials"] = self._encrypt_credentials(
                integration_data["credentials"]
            )

        return self.repository.update_integration(integration_id, tenant_id, integration_data)

    def delete_integration(self, integration_id: UUID, tenant_id: UUID) -> bool:
        """Delete an integration.

        Args:
            integration_id: Integration ID
            tenant_id: Tenant ID

        Returns:
            True if deleted successfully, False otherwise
        """
        return self.repository.delete_integration(integration_id, tenant_id)

    def get_credentials(self, integration_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Get decrypted credentials for an integration.

        Args:
            integration_id: Integration ID
            tenant_id: Tenant ID

        Returns:
            Decrypted credentials dictionary
        """
        integration = self.get_integration(integration_id, tenant_id)
        if not integration or not integration.credentials:
            return {}

        return self._decrypt_credentials(integration.credentials)

    def get_logs(
        self, integration_id: UUID, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[IntegrationLog]:
        """Get logs for an integration.

        Args:
            integration_id: Integration ID
            tenant_id: Tenant ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of IntegrationLog objects
        """
        return self.repository.get_logs_by_integration(integration_id, tenant_id, skip, limit)







