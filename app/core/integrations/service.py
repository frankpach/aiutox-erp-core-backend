"""Integration service for managing third-party integrations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import create_audit_log_entry
from app.models.integration import IntegrationStatus, IntegrationType
from app.repositories.integration_repository import IntegrationRepository


class IntegrationService:
    """Service for managing integrations."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.repository = IntegrationRepository(db)

    def get_integration(self, integration_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Get integration by ID."""
        integration = self.repository.get_by_id(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")
        return {
            "id": integration.id,
            "tenant_id": integration.tenant_id,
            "name": integration.name,
            "type": integration.type,
            "status": integration.status,
            "config": integration.config,
            "last_sync_at": integration.last_sync_at,
            "error_message": integration.error_message,
            "created_at": integration.created_at,
            "updated_at": integration.updated_at,
        }

    def list_integrations(
        self, tenant_id: UUID, type: IntegrationType | None = None
    ) -> list[dict[str, Any]]:
        """List all integrations for a tenant."""
        integrations = self.repository.get_all(tenant_id, type)
        return [
            {
                "id": i.id,
                "tenant_id": i.tenant_id,
                "name": i.name,
                "type": i.type,
                "status": i.status,
                "config": i.config,
                "last_sync_at": i.last_sync_at,
                "error_message": i.error_message,
                "created_at": i.created_at,
                "updated_at": i.updated_at,
            }
            for i in integrations
        ]

    def create_integration(
        self,
        tenant_id: UUID,
        name: str,
        type: IntegrationType,
        config: dict[str, Any],
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Create a new integration."""
        integration = self.repository.create(
            tenant_id=tenant_id,
            name=name,
            type=type,
            config=config,
            status=IntegrationStatus.INACTIVE,
        )

        # Create audit log
        if user_id:
            create_audit_log_entry(
                db=self.db,
                user_id=user_id,
                tenant_id=tenant_id,
                action="create_integration",
                resource_type="integration",
                resource_id=str(integration.id),
                details={"name": name, "type": type.value},
            )

        return {
            "id": integration.id,
            "tenant_id": integration.tenant_id,
            "name": integration.name,
            "type": integration.type,
            "status": integration.status,
            "config": integration.config,
            "last_sync_at": integration.last_sync_at,
            "error_message": integration.error_message,
            "created_at": integration.created_at,
            "updated_at": integration.updated_at,
        }

    def update_integration(
        self,
        integration_id: UUID,
        tenant_id: UUID,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        status: IntegrationStatus | None = None,
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Update an integration."""
        integration = self.repository.update(
            integration_id=integration_id,
            tenant_id=tenant_id,
            name=name,
            config=config,
            status=status,
        )

        # Create audit log
        if user_id:
            create_audit_log_entry(
                db=self.db,
                user_id=user_id,
                tenant_id=tenant_id,
                action="update_integration",
                resource_type="integration",
                resource_id=str(integration.id),
                details={"name": name, "status": status.value if status else None},
            )

        return {
            "id": integration.id,
            "tenant_id": integration.tenant_id,
            "name": integration.name,
            "type": integration.type,
            "status": integration.status,
            "config": integration.config,
            "last_sync_at": integration.last_sync_at,
            "error_message": integration.error_message,
            "created_at": integration.created_at,
            "updated_at": integration.updated_at,
        }

    def activate_integration(
        self,
        integration_id: UUID,
        tenant_id: UUID,
        config: dict[str, Any],
        user_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Activate an integration with configuration."""
        integration = self.repository.update(
            integration_id=integration_id,
            tenant_id=tenant_id,
            config=config,
            status=IntegrationStatus.ACTIVE,
            error_message=None,
        )

        # Create audit log
        if user_id:
            create_audit_log_entry(
                db=self.db,
                user_id=user_id,
                tenant_id=tenant_id,
                action="activate_integration",
                resource_type="integration",
                resource_id=str(integration.id),
                details={"name": integration.name, "type": integration.type},
            )

        return {
            "id": integration.id,
            "tenant_id": integration.tenant_id,
            "name": integration.name,
            "type": integration.type,
            "status": integration.status,
            "config": integration.config,
            "last_sync_at": integration.last_sync_at,
            "error_message": integration.error_message,
            "created_at": integration.created_at,
            "updated_at": integration.updated_at,
        }

    def deactivate_integration(
        self, integration_id: UUID, tenant_id: UUID, user_id: UUID | None = None
    ) -> dict[str, Any]:
        """Deactivate an integration."""
        integration = self.repository.update(
            integration_id=integration_id,
            tenant_id=tenant_id,
            status=IntegrationStatus.INACTIVE,
        )

        # Create audit log
        if user_id:
            create_audit_log_entry(
                db=self.db,
                user_id=user_id,
                tenant_id=tenant_id,
                action="deactivate_integration",
                resource_type="integration",
                resource_id=str(integration.id),
                details={"name": integration.name, "type": integration.type},
            )

        return {
            "id": integration.id,
            "tenant_id": integration.tenant_id,
            "name": integration.name,
            "type": integration.type,
            "status": integration.status,
            "config": integration.config,
            "last_sync_at": integration.last_sync_at,
            "error_message": integration.error_message,
            "created_at": integration.created_at,
            "updated_at": integration.updated_at,
        }

    def delete_integration(
        self, integration_id: UUID, tenant_id: UUID, user_id: UUID | None = None
    ) -> None:
        """Delete an integration."""
        integration = self.repository.get_by_id(integration_id, tenant_id)
        if integration:
            # Create audit log before deletion
            if user_id:
                create_audit_log_entry(
                    db=self.db,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    action="delete_integration",
                    resource_type="integration",
                    resource_id=str(integration.id),
                    details={"name": integration.name, "type": integration.type},
                )

            self.repository.delete(integration_id, tenant_id)

    def test_integration(
        self, integration_id: UUID, tenant_id: UUID
    ) -> dict[str, Any]:
        """Test an integration connection."""
        integration = self.repository.get_by_id(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        # TODO: Implement actual integration testing based on type
        # For now, return a mock success response
        return {
            "success": True,
            "message": f"Integration '{integration.name}' test successful",
            "details": {"type": integration.type, "status": integration.status},
        }
