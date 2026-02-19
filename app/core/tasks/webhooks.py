"""Webhooks system for Tasks module integrations."""

from datetime import datetime
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


class TaskWebhook:
    """Task webhook configuration."""

    def __init__(
        self,
        id: UUID,
        tenant_id: UUID,
        url: str,
        events: list[str],
        secret: str | None = None,
        is_active: bool = True,
        headers: dict | None = None,
        retry_count: int = 3,
        timeout: int = 30,
        created_by_id: UUID | None = None,
        created_at: datetime | None = None,
        last_triggered: datetime | None = None,
        success_count: int = 0,
        failure_count: int = 0,
    ):
        """Initialize webhook."""
        self.id = id
        self.tenant_id = tenant_id
        self.url = url
        self.events = events
        self.secret = secret
        self.is_active = is_active
        self.headers = headers or {}
        self.retry_count = retry_count
        self.timeout = timeout
        self.created_by_id = created_by_id
        self.created_at = created_at or datetime.utcnow()
        self.last_triggered = last_triggered
        self.success_count = success_count
        self.failure_count = failure_count

    def to_dict(self) -> dict:
        """Convert webhook to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "url": self.url,
            "events": self.events,
            "is_active": self.is_active,
            "headers": self.headers,
            "retry_count": self.retry_count,
            "timeout": self.timeout,
            "created_by_id": str(self.created_by_id) if self.created_by_id else None,
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
        }


class TaskWebhookService:
    """Service for managing task webhooks."""

    def __init__(self, db):
        """Initialize webhook service."""
        self.db = db
        self._webhooks = {}  # TODO: Replace with database storage

    def create_webhook(
        self,
        tenant_id: UUID,
        url: str,
        events: list[str],
        secret: str | None = None,
        headers: dict | None = None,
        retry_count: int = 3,
        timeout: int = 30,
        created_by_id: UUID | None = None,
    ) -> TaskWebhook:
        """Create a new webhook."""
        webhook = TaskWebhook(
            id=UUID(),
            tenant_id=tenant_id,
            url=url,
            events=events,
            secret=secret,
            headers=headers,
            retry_count=retry_count,
            timeout=timeout,
            created_by_id=created_by_id,
        )

        # TODO: Save to database
        self._webhooks[str(webhook.id)] = webhook

        logger.info(f"Webhook created: {webhook.id} for events {events}")
        return webhook

    def get_webhooks(
        self,
        tenant_id: UUID,
        event: str | None = None,
        is_active: bool | None = None
    ) -> list[TaskWebhook]:
        """Get webhooks for a tenant."""
        webhooks = []

        for webhook in self._webhooks.values():
            if webhook.tenant_id != tenant_id:
                continue

            if is_active is not None and webhook.is_active != is_active:
                continue

            if event and event not in webhook.events:
                continue

            webhooks.append(webhook)

        return webhooks

    def get_webhook(self, webhook_id: UUID, tenant_id: UUID) -> TaskWebhook | None:
        """Get a specific webhook."""
        webhook = self._webhooks.get(str(webhook_id))
        if webhook and webhook.tenant_id == tenant_id:
            return webhook
        return None

    def update_webhook(
        self,
        webhook_id: UUID,
        tenant_id: UUID,
        updates: dict
    ) -> TaskWebhook | None:
        """Update a webhook."""
        webhook = self.get_webhook(webhook_id, tenant_id)
        if not webhook:
            return None

        for key, value in updates.items():
            if hasattr(webhook, key):
                setattr(webhook, key, value)

        # TODO: Update in database
        logger.info(f"Webhook updated: {webhook_id}")
        return webhook

    def delete_webhook(self, webhook_id: UUID, tenant_id: UUID) -> bool:
        """Delete a webhook."""
        webhook = self.get_webhook(webhook_id, tenant_id)
        if not webhook:
            return False

        # TODO: Delete from database
        del self._webhooks[str(webhook_id)]
        logger.info(f"Webhook deleted: {webhook_id}")
        return True

    async def trigger_webhooks(
        self,
        event: str,
        data: dict,
        tenant_id: UUID
    ) -> list[dict]:
        """Trigger webhooks for an event."""
        results = []
        webhooks = self.get_webhooks(tenant_id, event=event, is_active=True)

        for webhook in webhooks:
            try:
                result = await self._send_webhook(webhook, event, data)
                results.append(result)

                # Update stats
                if result["success"]:
                    webhook.success_count += 1
                else:
                    webhook.failure_count += 1

                webhook.last_triggered = datetime.utcnow()

            except Exception as e:
                logger.error(f"Failed to trigger webhook {webhook.id}: {e}")
                results.append({
                    "webhook_id": str(webhook.id),
                    "success": False,
                    "error": str(e),
                    "status_code": None,
                })

        return results

    async def _send_webhook(
        self,
        webhook: TaskWebhook,
        event: str,
        data: dict
    ) -> dict:
        """Send webhook payload."""
        import httpx

        # Prepare payload
        payload = {
            "event": event,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "webhook_id": str(webhook.id),
        }

        # Add signature if secret is provided
        headers = webhook.headers.copy()
        if webhook.secret:
            import hashlib
            import hmac

            signature = hmac.new(
                webhook.secret.encode(),
                str(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        # Add content type
        headers["Content-Type"] = "application/json"

        try:
            async with httpx.AsyncClient(timeout=webhook.timeout) as client:
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers=headers
                )

                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Webhook {webhook.id} delivered successfully")
                    return {
                        "webhook_id": str(webhook.id),
                        "success": True,
                        "status_code": response.status_code,
                        "response": response.text,
                    }
                else:
                    logger.warning(f"Webhook {webhook.id} failed with status {response.status_code}")
                    return {
                        "webhook_id": str(webhook.id),
                        "success": False,
                        "status_code": response.status_code,
                        "response": response.text,
                    }

        except Exception as e:
            logger.error(f"Webhook {webhook.id} failed: {e}")
            return {
                "webhook_id": str(webhook.id),
                "success": False,
                "error": str(e),
                "status_code": None,
            }

    def get_webhook_stats(self, webhook_id: UUID, tenant_id: UUID) -> dict | None:
        """Get webhook statistics."""
        webhook = self.get_webhook(webhook_id, tenant_id)
        if not webhook:
            return None

        total_calls = webhook.success_count + webhook.failure_count
        success_rate = (webhook.success_count / total_calls * 100) if total_calls > 0 else 0

        return {
            "webhook_id": str(webhook.id),
            "total_calls": total_calls,
            "success_count": webhook.success_count,
            "failure_count": webhook.failure_count,
            "success_rate": round(success_rate, 2),
            "last_triggered": webhook.last_triggered.isoformat() if webhook.last_triggered else None,
            "is_active": webhook.is_active,
        }

    def test_webhook(self, webhook_id: UUID, tenant_id: UUID) -> dict:
        """Test a webhook with sample data."""
        webhook = self.get_webhook(webhook_id, tenant_id)
        if not webhook:
            return {"error": "Webhook not found"}

        sample_data = {
            "test": True,
            "message": "This is a test webhook",
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Trigger test event
        import asyncio
        results = asyncio.run(self.trigger_webhooks("webhook.test", sample_data, tenant_id))

        return results[0] if results else {"error": "No results"}


# Available task events
TASK_WEBHOOK_EVENTS = [
    "task.created",
    "task.updated",
    "task.deleted",
    "task.status.changed",
    "task.assigned",
    "task.completed",
    "task.overdue",
    "task.checklist.updated",
    "bulk.operation.completed",
    "webhook.test",
]


# Global webhook service instance
task_webhook_service = None

def get_task_webhook_service(db) -> TaskWebhookService:
    """Get task webhook service instance."""
    global task_webhook_service
    if task_webhook_service is None:
        task_webhook_service = TaskWebhookService(db)
    return task_webhook_service
