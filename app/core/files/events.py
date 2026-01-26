"""Files module webhook events registry."""

from app.core.integrations.event_registry import (
    EventCategory,
    ModuleEventRegistry,
    WebhookEvent,
)


def get_file_events() -> ModuleEventRegistry:
    """Get files module webhook events.

    Returns:
        ModuleEventRegistry with all file events
    """
    return ModuleEventRegistry(
        module_name="files",
        display_name="Archivos",
        description="Eventos del módulo de gestión de archivos",
        events=[
            WebhookEvent(
                type="file.uploaded",
                description="Archivo subido",
                category=EventCategory.LIFECYCLE,
            ),
            WebhookEvent(
                type="file.deleted",
                description="Archivo eliminado",
                category=EventCategory.LIFECYCLE,
            ),
            WebhookEvent(
                type="file.permanently_deleted",
                description="Archivo eliminado permanentemente",
                category=EventCategory.LIFECYCLE,
            ),
            WebhookEvent(
                type="file.restored",
                description="Archivo restaurado",
                category=EventCategory.LIFECYCLE,
            ),
        ],
    )
