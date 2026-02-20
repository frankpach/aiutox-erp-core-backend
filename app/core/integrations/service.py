"""Integration service for managing third-party integrations."""

import json
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

    @staticmethod
    def _ensure_config_is_dict(config: Any) -> dict[str, Any]:
        """Ensure config is a dict, handling JSON strings."""
        if config is None:
            return {}
        if isinstance(config, dict):
            return config
        if isinstance(config, str):
            try:
                return json.loads(config)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def get_integration(self, integration_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Get integration by ID."""
        integration = self.repository.get_by_id(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        config = self._ensure_config_is_dict(integration.config)

        return {
            "id": integration.id,
            "tenant_id": integration.tenant_id,
            "name": integration.name,
            "type": integration.type,
            "status": integration.status,
            "config": config,
            "last_sync_at": integration.last_sync_at,
            "error_message": integration.error_message,
            "created_at": integration.created_at,
            "updated_at": integration.updated_at,
        }

    def list_integrations(
        self,
        tenant_id: UUID,
        integration_type: IntegrationType | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """List integrations for a tenant, with optional pagination.

        Args:
            tenant_id: Tenant ID
            integration_type: Optional filter by integration type
            page: Optional page number for pagination
            limit: Optional limit per page for pagination

        Returns:
            If page and limit are provided: dict with 'items' and 'total'
            Otherwise: list of integration dicts
        """
        if page is not None and limit is not None:
            result = self.repository.get_all_paginated(
                tenant_id=tenant_id,
                integration_type=integration_type,
                page=page,
                limit=limit,
            )
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                f"get_all_paginated result type: {type(result)}, value: {result}"
            )

            items_list = []
            for idx, i in enumerate(result["items"]):
                try:
                    item_dict = {
                        "id": i.id,
                        "tenant_id": i.tenant_id,
                        "name": i.name,
                        "type": i.type,
                        "status": i.status,
                        "config": self._ensure_config_is_dict(i.config),
                        "last_sync_at": i.last_sync_at,
                        "error_message": i.error_message,
                        "created_at": i.created_at,
                        "updated_at": i.updated_at,
                    }
                    items_list.append(item_dict)
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(
                        f"Error converting integration {idx} to dict: {e}",
                        exc_info=True,
                    )
                    logger.error(f"Integration object: {i}, type: {type(i)}")
                    logger.error(
                        f"Integration config: {i.config}, type: {type(i.config)}"
                    )
                    raise
            return_value = {
                "items": items_list,
                "total": result["total"],
            }
            logger.info(
                f"list_integrations return value type: {type(return_value)}, value: {return_value}"
            )
            return return_value
        else:
            integrations = self.repository.get_all(tenant_id, integration_type)
            return [
                {
                    "id": i.id,
                    "tenant_id": i.tenant_id,
                    "name": i.name,
                    "type": i.type,
                    "status": i.status,
                    "config": self._ensure_config_is_dict(i.config),
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
            "config": self._ensure_config_is_dict(integration.config),
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

    def test_integration(self, integration_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Test an integration connection."""
        from app.core.integrations.integration_test import (
            IntegrationTestResult,
            test_integration,
        )

        integration = self.repository.get_by_id(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        # Test the integration based on its type
        try:
            integration_type = IntegrationType(integration.type)
            test_result: IntegrationTestResult = test_integration(
                integration_type, integration.config
            )

            # Update integration status based on test result
            if test_result.success:
                self.repository.update(
                    integration_id=integration_id,
                    tenant_id=tenant_id,
                    status=IntegrationStatus.ACTIVE,
                    error_message=None,
                )
            else:
                self.repository.update(
                    integration_id=integration_id,
                    tenant_id=tenant_id,
                    status=IntegrationStatus.ERROR,
                    error_message=test_result.error or test_result.message,
                )

            return {
                "success": test_result.success,
                "message": test_result.message,
                "details": test_result.details or {},
                "error": test_result.error,
            }

        except ValueError as e:
            # Invalid integration type
            error_msg = f"Invalid integration type: {integration.type}"
            self.repository.update(
                integration_id=integration_id,
                tenant_id=tenant_id,
                status=IntegrationStatus.ERROR,
                error_message=error_msg,
            )
            return {
                "success": False,
                "message": error_msg,
                "details": {"type": integration.type},
                "error": str(e),
            }
        except Exception as e:
            # Unexpected error
            error_msg = f"Integration test failed: {str(e)}"
            self.repository.update(
                integration_id=integration_id,
                tenant_id=tenant_id,
                status=IntegrationStatus.ERROR,
                error_message=error_msg,
            )
            return {
                "success": False,
                "message": error_msg,
                "details": {"type": integration.type},
                "error": str(e),
            }

    def get_credentials(
        self, integration_id: UUID, tenant_id: UUID, user_id: UUID | None = None
    ) -> dict[str, Any]:
        """Get decrypted credentials for an integration.

        Security:
        - Credentials are decrypted using tenant-specific key
        - Access is logged for audit purposes
        - Returns empty dict if no credentials found
        - Handles decryption errors gracefully

        Args:
            integration_id: Integration UUID
            tenant_id: Tenant UUID
            user_id: User requesting credentials (for audit)

        Returns:
            Dictionary with decrypted credentials

        Raises:
            ValueError: If integration not found
        """
        import json

        from app.core.security.encryption import decrypt_credentials

        integration = self.repository.get_by_id(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        credentials_dict: dict[str, Any] = {}

        # Try to get credentials from credentials column first (new method)
        if integration.credentials:
            try:
                decrypted_json = decrypt_credentials(integration.credentials, tenant_id)
                credentials_dict = json.loads(decrypted_json)
            except (ValueError, json.JSONDecodeError):
                # If decryption fails, fall back to config or return empty
                pass

        # Fallback to config.credentials (backward compatibility)
        if not credentials_dict and isinstance(integration.config, dict):
            credentials_dict = integration.config.get("credentials", {})
            if not isinstance(credentials_dict, dict):
                credentials_dict = {}

        # Create audit log entry
        if user_id:
            create_audit_log_entry(
                db=self.db,
                user_id=user_id,
                tenant_id=tenant_id,
                action="view_credentials",
                resource_type="integration",
                resource_id=str(integration.id),
                details={
                    "name": integration.name,
                    "type": integration.type,
                    # DO NOT include credentials in audit log
                },
            )

        return credentials_dict
