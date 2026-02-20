"""Integration repository for data access operations."""

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.integration import (
    Integration,
    IntegrationStatus,
    IntegrationType,
    Webhook,
    WebhookDelivery,
    WebhookStatus,
)


class IntegrationRepository:
    """Repository for integration data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def get_by_id(self, integration_id: UUID, tenant_id: UUID) -> Integration | None:
        """Get integration by ID and tenant."""
        return (
            self.db.query(Integration)
            .filter(
                Integration.id == integration_id,
                Integration.tenant_id == tenant_id,
            )
            .first()
        )

    def get_all(
        self, tenant_id: UUID, type: IntegrationType | None = None
    ) -> list[Integration]:
        """Get all integrations for a tenant, optionally filtered by type."""
        query = self.db.query(Integration).filter(Integration.tenant_id == tenant_id)
        if type:
            query = query.filter(Integration.type == type.value)
        return query.all()

    def get_all_paginated(
        self,
        tenant_id: UUID,
        integration_type: IntegrationType | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get integrations with pagination."""
        query = self.db.query(Integration).filter(Integration.tenant_id == tenant_id)
        if integration_type:
            query = query.filter(Integration.type == integration_type.value)

        total = query.count()
        offset = (page - 1) * limit
        items = query.offset(offset).limit(limit).all()

        return {
            "items": items,
            "total": total,
        }

    def get_by_type(self, tenant_id: UUID, type: IntegrationType) -> Integration | None:
        """Get integration by type for a tenant."""
        return (
            self.db.query(Integration)
            .filter(
                Integration.tenant_id == tenant_id,
                Integration.type == type.value,
            )
            .first()
        )

    def create(
        self,
        tenant_id: UUID,
        name: str,
        type: IntegrationType,
        config: dict[str, Any],
        status: IntegrationStatus = IntegrationStatus.INACTIVE,
    ) -> Integration:
        """Create a new integration."""
        integration = Integration(
            tenant_id=tenant_id,
            name=name,
            type=type.value,
            status=status.value,
            config=config,
        )
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def update(
        self,
        integration_id: UUID,
        tenant_id: UUID,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        status: IntegrationStatus | None = None,
        error_message: str | None = None,
    ) -> Integration:
        """Update an existing integration."""
        integration = self.get_by_id(integration_id, tenant_id)
        if not integration:
            raise ValueError(f"Integration not found: {integration_id}")

        if name is not None:
            integration.name = name
        if config is not None:
            integration.config = config
        if status is not None:
            integration.status = status.value
        if error_message is not None:
            integration.error_message = error_message

        self.db.commit()
        self.db.refresh(integration)
        return integration

    def delete(self, integration_id: UUID, tenant_id: UUID) -> None:
        """Delete an integration."""
        integration = self.get_by_id(integration_id, tenant_id)
        if integration:
            self.db.delete(integration)
            self.db.commit()

    def get_webhooks_by_event(
        self, tenant_id: UUID, event_type: str, enabled_only: bool = True
    ) -> list[Webhook]:
        """Get webhooks for a specific event type.

        Args:
            tenant_id: Tenant ID
            event_type: Event type (e.g., 'product.created')
            enabled_only: If True, only return enabled webhooks

        Returns:
            List of Webhook objects
        """
        query = self.db.query(Webhook).filter(
            Webhook.tenant_id == tenant_id, Webhook.event_type == event_type
        )
        if enabled_only:
            query = query.filter(Webhook.enabled)
        return query.all()

    def create_delivery(self, data: dict[str, Any]) -> WebhookDelivery:
        """Create a webhook delivery record.

        Args:
            data: Dictionary with delivery data (webhook_id, tenant_id, status, event_type, payload)

        Returns:
            WebhookDelivery object
        """
        delivery = WebhookDelivery(
            webhook_id=data["webhook_id"],
            tenant_id=data["tenant_id"],
            status=data.get("status", WebhookStatus.PENDING.value),
            event_type=data["event_type"],
            payload=data["payload"],
        )
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def update_delivery(
        self, delivery_id: UUID, tenant_id: UUID, data: dict[str, Any]
    ) -> WebhookDelivery:
        """Update a webhook delivery record.

        Args:
            delivery_id: Delivery ID
            tenant_id: Tenant ID
            data: Dictionary with fields to update

        Returns:
            Updated WebhookDelivery object

        Raises:
            ValueError: If delivery not found
        """
        delivery = (
            self.db.query(WebhookDelivery)
            .filter(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.tenant_id == tenant_id,
            )
            .first()
        )
        if not delivery:
            raise ValueError(f"Webhook delivery not found: {delivery_id}")

        for key, value in data.items():
            if hasattr(delivery, key):
                setattr(delivery, key, value)

        self.db.commit()
        self.db.refresh(delivery)
        return delivery
