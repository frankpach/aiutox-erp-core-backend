"""Integration repository for data access operations."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.integration import (
    Integration,
    IntegrationLog,
    Webhook,
    WebhookDelivery,
)


class IntegrationRepository:
    """Repository for integration data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    # Integration operations
    def create_integration(self, integration_data: dict) -> Integration:
        """Create a new integration."""
        integration = Integration(**integration_data)
        self.db.add(integration)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def get_integration_by_id(
        self, integration_id: UUID, tenant_id: UUID
    ) -> Integration | None:
        """Get integration by ID and tenant."""
        return (
            self.db.query(Integration)
            .filter(Integration.id == integration_id, Integration.tenant_id == tenant_id)
            .first()
        )

    def get_all_integrations(
        self,
        tenant_id: UUID,
        integration_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Integration]:
        """Get all integrations for a tenant."""
        query = self.db.query(Integration).filter(Integration.tenant_id == tenant_id)
        if integration_type:
            query = query.filter(Integration.integration_type == integration_type)
        if status:
            query = query.filter(Integration.status == status)
        return query.order_by(Integration.created_at.desc()).offset(skip).limit(limit).all()

    def update_integration(
        self, integration_id: UUID, tenant_id: UUID, integration_data: dict
    ) -> Integration | None:
        """Update an integration."""
        integration = self.get_integration_by_id(integration_id, tenant_id)
        if not integration:
            return None
        for key, value in integration_data.items():
            setattr(integration, key, value)
        self.db.commit()
        self.db.refresh(integration)
        return integration

    def delete_integration(self, integration_id: UUID, tenant_id: UUID) -> bool:
        """Delete an integration."""
        integration = self.get_integration_by_id(integration_id, tenant_id)
        if not integration:
            return False
        self.db.delete(integration)
        self.db.commit()
        return True

    # Webhook operations
    def create_webhook(self, webhook_data: dict) -> Webhook:
        """Create a new webhook."""
        webhook = Webhook(**webhook_data)
        self.db.add(webhook)
        self.db.commit()
        self.db.refresh(webhook)
        return webhook

    def get_webhook_by_id(self, webhook_id: UUID, tenant_id: UUID) -> Webhook | None:
        """Get webhook by ID and tenant."""
        return (
            self.db.query(Webhook)
            .filter(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id)
            .first()
        )

    def get_webhooks_by_event(
        self, tenant_id: UUID, event_type: str, enabled_only: bool = True
    ) -> list[Webhook]:
        """Get webhooks for a specific event type."""
        query = self.db.query(Webhook).filter(
            Webhook.tenant_id == tenant_id, Webhook.event_type == event_type
        )
        if enabled_only:
            query = query.filter(Webhook.enabled == True)
        return query.all()

    def get_all_webhooks(
        self, tenant_id: UUID, enabled_only: bool = False, skip: int = 0, limit: int = 100
    ) -> list[Webhook]:
        """Get all webhooks for a tenant."""
        query = self.db.query(Webhook).filter(Webhook.tenant_id == tenant_id)
        if enabled_only:
            query = query.filter(Webhook.enabled == True)
        return query.order_by(Webhook.created_at.desc()).offset(skip).limit(limit).all()

    def update_webhook(
        self, webhook_id: UUID, tenant_id: UUID, webhook_data: dict
    ) -> Webhook | None:
        """Update a webhook."""
        webhook = self.get_webhook_by_id(webhook_id, tenant_id)
        if not webhook:
            return None
        for key, value in webhook_data.items():
            setattr(webhook, key, value)
        self.db.commit()
        self.db.refresh(webhook)
        return webhook

    def delete_webhook(self, webhook_id: UUID, tenant_id: UUID) -> bool:
        """Delete a webhook."""
        webhook = self.get_webhook_by_id(webhook_id, tenant_id)
        if not webhook:
            return False
        self.db.delete(webhook)
        self.db.commit()
        return True

    # WebhookDelivery operations
    def create_delivery(self, delivery_data: dict) -> WebhookDelivery:
        """Create a new webhook delivery."""
        delivery = WebhookDelivery(**delivery_data)
        self.db.add(delivery)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def get_delivery_by_id(
        self, delivery_id: UUID, tenant_id: UUID
    ) -> WebhookDelivery | None:
        """Get webhook delivery by ID and tenant."""
        return (
            self.db.query(WebhookDelivery)
            .filter(
                WebhookDelivery.id == delivery_id,
                WebhookDelivery.tenant_id == tenant_id,
            )
            .first()
        )

    def get_deliveries_by_webhook(
        self, webhook_id: UUID, tenant_id: UUID, status: str | None = None, skip: int = 0, limit: int = 100
    ) -> list[WebhookDelivery]:
        """Get all deliveries for a webhook."""
        query = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.webhook_id == webhook_id,
            WebhookDelivery.tenant_id == tenant_id,
        )
        if status:
            query = query.filter(WebhookDelivery.status == status)
        return query.order_by(WebhookDelivery.created_at.desc()).offset(skip).limit(limit).all()

    def update_delivery(
        self, delivery_id: UUID, tenant_id: UUID, delivery_data: dict
    ) -> WebhookDelivery | None:
        """Update a webhook delivery."""
        delivery = self.get_delivery_by_id(delivery_id, tenant_id)
        if not delivery:
            return None
        for key, value in delivery_data.items():
            setattr(delivery, key, value)
        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    # IntegrationLog operations
    def create_log(self, log_data: dict) -> IntegrationLog:
        """Create a new integration log."""
        log = IntegrationLog(**log_data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_logs_by_integration(
        self, integration_id: UUID, tenant_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[IntegrationLog]:
        """Get logs for an integration."""
        return (
            self.db.query(IntegrationLog)
            .filter(
                IntegrationLog.integration_id == integration_id,
                IntegrationLog.tenant_id == tenant_id,
            )
            .order_by(IntegrationLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )








