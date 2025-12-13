"""Webhook handler for processing webhooks."""

import hashlib
import hmac
import json
import logging
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.integration import Webhook, WebhookDelivery, WebhookStatus
from app.repositories.integration_repository import IntegrationRepository

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handler for processing and delivering webhooks."""

    def __init__(self, db: Session, event_publisher: EventPublisher | None = None):
        """Initialize webhook handler.

        Args:
            db: Database session
            event_publisher: EventPublisher instance (created if not provided)
        """
        self.db = db
        self.repository = IntegrationRepository(db)
        self.event_publisher = event_publisher or get_event_publisher()

    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload.

        Args:
            payload: Webhook payload as string
            secret: Secret key

        Returns:
            HMAC signature
        """
        return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

    async def trigger_webhook(
        self,
        tenant_id: UUID,
        event_type: str,
        payload: dict[str, Any],
        user_id: UUID | None = None,
    ) -> list[WebhookDelivery]:
        """Trigger webhooks for an event type.

        Args:
            tenant_id: Tenant ID
            event_type: Event type (e.g., 'product.created')
            payload: Webhook payload
            user_id: User ID who triggered the event (optional)

        Returns:
            List of WebhookDelivery objects
        """
        # Get all enabled webhooks for this event type
        webhooks = self.repository.get_webhooks_by_event(tenant_id, event_type, enabled_only=True)

        deliveries = []
        for webhook in webhooks:
            delivery = await self._deliver_webhook(webhook, payload)
            deliveries.append(delivery)

        return deliveries

    async def _deliver_webhook(self, webhook: Webhook, payload: dict[str, Any]) -> WebhookDelivery:
        """Deliver a webhook.

        Args:
            webhook: Webhook configuration
            payload: Webhook payload

        Returns:
            WebhookDelivery object
        """
        # Create delivery record
        delivery = self.repository.create_delivery(
            {
                "webhook_id": webhook.id,
                "tenant_id": webhook.tenant_id,
                "status": WebhookStatus.PENDING,
                "event_type": webhook.event_type,
                "payload": payload,
            }
        )

        try:
            # Prepare headers
            headers = webhook.headers or {}
            headers.setdefault("Content-Type", "application/json")

            # Generate signature if secret is provided
            payload_json = json.dumps(payload)
            if webhook.secret:
                signature = self._generate_signature(payload_json, webhook.secret)
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            # Send webhook
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=webhook.method,
                    url=webhook.url,
                    headers=headers,
                    content=payload_json,
                )

            # Update delivery status
            delivery.status = (
                WebhookStatus.SENT if response.is_success else WebhookStatus.FAILED
            )
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Limit response body size

            if not response.is_success:
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:500]}"

            from datetime import datetime, timezone

            delivery.sent_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Failed to deliver webhook {webhook.id}: {e}")
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = str(e)[:500]

        # Update delivery
        self.repository.update_delivery(
            delivery.id, webhook.tenant_id, {"status": delivery.status}
        )

        return delivery

    async def retry_failed_deliveries(self, tenant_id: UUID) -> int:
        """Retry failed webhook deliveries.

        Args:
            tenant_id: Tenant ID

        Returns:
            Number of deliveries retried
        """
        # Get failed deliveries that haven't exceeded max retries
        # This would require additional repository methods
        # For now, return 0 as placeholder
        logger.info(f"Retrying failed webhook deliveries for tenant {tenant_id}")
        return 0

