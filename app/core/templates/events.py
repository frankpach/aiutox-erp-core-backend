"""Templates module webhook events registry."""

from app.core.integrations.event_registry import (
    EventCategory,
    ModuleEventRegistry,
    WebhookEvent,
)


def get_template_events() -> ModuleEventRegistry:
    """Get templates module webhook events.

    Returns:
        ModuleEventRegistry with all template events
    """
    return ModuleEventRegistry(
        module_name="templates",
        display_name="Plantillas",
        description="Eventos del módulo de plantillas",
        events=[
            WebhookEvent(
                type="template.created",
                description="Plantilla creada",
                category=EventCategory.LIFECYCLE,
            ),
            WebhookEvent(
                type="template.updated",
                description="Plantilla actualizada",
                category=EventCategory.LIFECYCLE,
            ),
            WebhookEvent(
                type="template.rendered",
                description="Plantilla renderizada",
                category=EventCategory.INTERACTION,
            ),
        ],
    )
