"""Notifications module webhook events registry."""

from app.core.integrations.event_registry import (
    EventCategory,
    ModuleEventRegistry,
    WebhookEvent,
)


def get_notification_events() -> ModuleEventRegistry:
    """Get notifications module webhook events.

    Returns:
        ModuleEventRegistry with all notification events
    """
    return ModuleEventRegistry(
        module_name="notifications",
        display_name="Notificaciones",
        description="Eventos del módulo de notificaciones",
        events=[
            WebhookEvent(
                type="notification.sent",
                description="Notificación enviada",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="notification.failed",
                description="Notificación fallida",
                category=EventCategory.SYSTEM,
            ),
        ],
    )
