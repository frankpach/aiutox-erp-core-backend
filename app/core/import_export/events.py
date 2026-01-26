"""Import/Export module webhook events registry."""

from app.core.integrations.event_registry import (
    EventCategory,
    ModuleEventRegistry,
    WebhookEvent,
)


def get_import_export_events() -> ModuleEventRegistry:
    """Get import/export module webhook events.

    Returns:
        ModuleEventRegistry with all import/export events
    """
    return ModuleEventRegistry(
        module_name="import_export",
        display_name="Importar/Exportar",
        description="Eventos del módulo de importación y exportación",
        events=[
            WebhookEvent(
                type="import.started",
                description="Importación iniciada",
                category=EventCategory.SYSTEM,
            ),
        ],
    )
