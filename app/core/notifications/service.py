"""Notification service for sending notifications."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.preferences.service import PreferencesService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.core.pubsub.models import EventMetadata
from app.models.notification import NotificationQueue, NotificationStatus, NotificationTemplate
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications."""

    def __init__(self, db: Session, event_publisher: EventPublisher | None = None):
        """Initialize service with database session."""
        self.db = db
        self.repository = NotificationRepository(db)
        self.preferences_service = PreferencesService(db)
        self.event_publisher = event_publisher or get_event_publisher()

    async def send(
        self,
        event_type: str,
        recipient_id: UUID,
        channels: list[str],
        data: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Send a notification.

        Args:
            event_type: Event type that triggered the notification
            recipient_id: User ID to send notification to
            channels: List of channels ('email', 'sms', 'webhook', 'in-app')
            data: Event data for template rendering
            tenant_id: Tenant ID (optional, will be fetched from user if not provided)

        Returns:
            List of notification queue records
        """
        # TODO: Get tenant_id from user if not provided
        if not tenant_id:
            # For now, we'll require tenant_id
            raise ValueError("tenant_id is required")

        # Check user preferences
        notification_prefs = self.preferences_service.get_preference(
            user_id=recipient_id,
            tenant_id=tenant_id,
            preference_type="notification",
            key=event_type,
            default={"enabled": True, "channels": ["in-app"]},
        )

        if not notification_prefs.get("enabled", True):
            logger.info(
                f"Notifications disabled for user {recipient_id} and event {event_type}"
            )
            return []

        # Filter channels based on preferences
        preferred_channels = notification_prefs.get("channels", ["in-app"])
        channels_to_use = [ch for ch in channels if ch in preferred_channels]

        if not channels_to_use:
            logger.info(
                f"No matching channels for user {recipient_id} and event {event_type}"
            )
            return []

        # Get template for each channel
        notifications = []
        for channel in channels_to_use:
            template = self.repository.get_template(event_type, channel, tenant_id)
            if not template:
                logger.warning(
                    f"No template found for event_type={event_type}, channel={channel}"
                )
                continue

            # Create notification queue entry
            queue_entry = self.repository.create_queue_entry(
                {
                    "event_type": event_type,
                    "recipient_id": recipient_id,
                    "tenant_id": tenant_id,
                    "channel": channel,
                    "template_id": template.id,
                    "data": data,
                    "status": NotificationStatus.PENDING,
                }
            )
            notifications.append(queue_entry)

            # Send notification (async processing)
            try:
                await self._send_notification(queue_entry, template, data or {})
                queue_entry.status = NotificationStatus.SENT
                from datetime import datetime, timezone

                queue_entry.sent_at = datetime.now(timezone.utc)
                self.db.commit()

                # Publish notification.sent event
                await self.event_publisher.publish(
                    event_type="notification.sent",
                    entity_type="notification",
                    entity_id=queue_entry.id,
                    tenant_id=tenant_id,
                    user_id=recipient_id,
                    metadata={
                        "channel": channel,
                        "event_type": event_type,
                        "template_id": str(template.id),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to send notification {queue_entry.id}: {e}", exc_info=True)
                queue_entry.status = NotificationStatus.FAILED
                queue_entry.error_message = str(e)
                self.db.commit()

                # Publish notification.failed event
                await self.event_publisher.publish(
                    event_type="notification.failed",
                    entity_type="notification",
                    entity_id=queue_entry.id,
                    tenant_id=tenant_id,
                    user_id=recipient_id,
                    metadata={
                        "channel": channel,
                        "event_type": event_type,
                        "error": str(e),
                    },
                )

        return [
            {
                "id": n.id,
                "event_type": n.event_type,
                "channel": n.channel,
                "status": n.status,
            }
            for n in notifications
        ]

    async def _send_notification(
        self, queue_entry: NotificationQueue, template: NotificationTemplate, data: dict[str, Any]
    ) -> None:
        """Send a notification using the template.

        Args:
            queue_entry: Queue entry
            template: Notification template
            data: Event data for rendering
        """
        # Render template
        rendered_body = self._render_template(template.body, data)
        rendered_subject = (
            self._render_template(template.subject, data) if template.subject else None
        )

        # Send based on channel
        if template.channel == "email":
            await self._send_email(queue_entry.recipient_id, rendered_subject, rendered_body)
        elif template.channel == "sms":
            await self._send_sms(queue_entry.recipient_id, rendered_body)
        elif template.channel == "in-app":
            # In-app notifications are stored in the queue
            pass
        elif template.channel == "webhook":
            await self._send_webhook(data.get("webhook_url"), {"body": rendered_body})
        else:
            raise ValueError(f"Unsupported channel: {template.channel}")

    def _render_template(self, template: str, data: dict[str, Any]) -> str:
        """Render template with variables.

        Args:
            template: Template string with {{variables}}
            data: Data dictionary

        Returns:
            Rendered template
        """
        result = template
        for key, value in data.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result

    async def _send_email(self, recipient_id: UUID, subject: str | None, body: str) -> None:
        """Send email notification.

        Args:
            recipient_id: User ID
            subject: Email subject
            body: Email body
        """
        from app.core.config_file import get_settings
        from app.repositories.user_repository import UserRepository

        settings = get_settings()

        # Get user email
        user_repo = UserRepository(self.db)
        user = user_repo.get_by_id(recipient_id)
        if not user or not user.email:
            raise ValueError(f"User {recipient_id} not found or has no email")

        # Skip email sending if SMTP is not configured
        if not settings.SMTP_HOST or settings.SMTP_HOST == "localhost":
            logger.warning(
                f"SMTP not configured, skipping email to {user.email}. "
                "Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD to enable email sending."
            )
            return

        try:
            import aiosmtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = settings.SMTP_FROM
            message["To"] = user.email
            if subject:
                message["Subject"] = subject

            # Add body
            message.attach(MIMEText(body, "html" if "<html>" in body.lower() else "plain"))

            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER if settings.SMTP_USER else None,
                password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
                use_tls=settings.SMTP_USE_TLS,
            )

            logger.info(f"Email sent successfully to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send email to {user.email}: {e}", exc_info=True)
            raise

    async def _send_sms(self, recipient_id: UUID, message: str) -> None:
        """Send SMS notification.

        Args:
            recipient_id: User ID
            message: SMS message

        TODO: Implement actual SMS sending
        """
        logger.info(f"Sending SMS to user {recipient_id}: {message}")

    async def _send_webhook(self, url: str | None, payload: dict[str, Any]) -> None:
        """Send webhook notification.

        Args:
            url: Webhook URL
            payload: Payload to send

        TODO: Implement actual webhook sending
        """
        if not url:
            raise ValueError("Webhook URL is required")
        logger.info(f"Sending webhook to {url}: {payload}")


