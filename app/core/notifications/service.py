"""Notification service for sending notifications."""

import logging
from datetime import UTC
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.preferences.service import PreferencesService
from app.core.pubsub import EventPublisher, get_event_publisher
from app.models.notification import (
    NotificationQueue,
    NotificationStatus,
    NotificationTemplate,
)
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
                from datetime import datetime

                queue_entry.sent_at = datetime.now(UTC)
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
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            import aiosmtplib

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

        Raises:
            ValueError: If user not found, has no phone, or SMS not configured
        """
        from app.core.config.service import ConfigService
        from app.repositories.user_repository import UserRepository

        # Get user
        user_repo = UserRepository(self.db)
        user = user_repo.get_by_id(recipient_id)
        if not user:
            raise ValueError(f"User {recipient_id} not found")

        # Get user phone number from contact methods
        from app.models.contact_method import ContactMethodType, EntityType
        from app.repositories.contact_method_repository import ContactMethodRepository

        contact_repo = ContactMethodRepository(self.db)
        contact_methods = contact_repo.get_by_entity(entity_type=EntityType.USER, entity_id=recipient_id)

        # Find phone or mobile contact method
        phone = None
        for contact in contact_methods:
            if contact.method_type == ContactMethodType.MOBILE:
                phone = contact.value
                break
            elif contact.method_type == ContactMethodType.PHONE and not phone:
                phone = contact.value

        if not phone:
            raise ValueError(f"User {recipient_id} has no phone number")

        # Get SMS configuration
        config_service = ConfigService(self.db, use_cache=True)
        tenant_id = user.tenant_id

        sms_enabled = config_service.get(
            tenant_id=tenant_id,
            module="notifications",
            key="channels.sms.enabled",
            default=False,
        )
        if not sms_enabled:
            logger.warning(
                f"SMS not enabled for tenant {tenant_id}, skipping SMS to {phone}"
            )
            return

        provider = config_service.get(
            tenant_id=tenant_id,
            module="notifications",
            key="channels.sms.provider",
            default="twilio",
        )
        account_sid = config_service.get(
            tenant_id=tenant_id,
            module="notifications",
            key="channels.sms.account_sid",
        )
        auth_token = config_service.get(
            tenant_id=tenant_id,
            module="notifications",
            key="channels.sms.auth_token",
        )
        from_number = config_service.get(
            tenant_id=tenant_id,
            module="notifications",
            key="channels.sms.from_number",
        )

        if not account_sid or not auth_token or not from_number:
            logger.warning(
                f"SMS not configured for tenant {tenant_id}, skipping SMS to {phone}"
            )
            return

        # Send SMS based on provider
        if provider.lower() == "twilio":
            await self._send_sms_twilio(account_sid, auth_token, from_number, phone, message)
        else:
            raise ValueError(f"Unsupported SMS provider: {provider}")

    async def _send_sms_twilio(
        self, account_sid: str, auth_token: str, from_number: str, to_number: str, message: str
    ) -> None:
        """Send SMS using Twilio API.

        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            from_number: Twilio phone number to send from
            to_number: Recipient phone number
            message: SMS message body

        Raises:
            Exception: If SMS sending fails
        """
        import base64

        import httpx

        # Twilio API endpoint
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        # Basic auth with account_sid:auth_token
        auth_header = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

        # Request payload
        payload = {
            "From": from_number,
            "To": to_number,
            "Body": message,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    data=payload,
                    headers={"Authorization": f"Basic {auth_header}"},
                )
                response.raise_for_status()
                logger.info(f"SMS sent successfully to {to_number} via Twilio")
        except httpx.HTTPStatusError as e:
            logger.error(f"Twilio API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to send SMS: {e.response.status_code}") from e
        except httpx.TimeoutException as e:
            logger.error(f"SMS sending timeout: {e}")
            raise Exception("SMS sending timeout") from e
        except Exception as e:
            logger.error(f"Failed to send SMS to {to_number}: {e}", exc_info=True)
            raise

    async def _send_webhook(self, url: str | None, payload: dict[str, Any]) -> None:
        """Send webhook notification.

        Args:
            url: Webhook URL
            payload: Payload to send

        Raises:
            ValueError: If URL is not provided
            Exception: If webhook sending fails
        """
        import httpx

        if not url:
            raise ValueError("Webhook URL is required")

        # Get webhook configuration for timeout
        from app.core.config.service import ConfigService

        # Try to get timeout from config (default: 30 seconds)
        timeout = 30.0
        try:
            # Get tenant_id from payload if available, otherwise use default
            tenant_id = payload.get("tenant_id")
            if tenant_id:
                config_service = ConfigService(self.db, use_cache=True)
                timeout = config_service.get(
                    tenant_id=tenant_id,
                    module="notifications",
                    key="channels.webhook.timeout",
                    default=30,
                )
                if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
                    timeout = 30.0  # Safety: max 5 minutes
        except Exception:
            # If config lookup fails, use default
            pass

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                logger.info(f"Webhook sent successfully to {url}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Webhook HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to send webhook: {e.response.status_code}") from e
        except httpx.TimeoutException as e:
            logger.error(f"Webhook timeout: {e}")
            raise Exception("Webhook sending timeout") from e
        except httpx.ConnectError as e:
            logger.error(f"Webhook connection error: {e}")
            raise Exception("Failed to connect to webhook URL") from e
        except Exception as e:
            logger.error(f"Failed to send webhook to {url}: {e}", exc_info=True)
            raise


