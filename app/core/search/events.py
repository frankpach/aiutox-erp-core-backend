"""Search module webhook events registry."""

from app.core.integrations.event_registry import (
    EventCategory,
    ModuleEventRegistry,
    WebhookEvent,
)


def get_search_events() -> ModuleEventRegistry:
    """Get search module webhook events.

    Returns:
        ModuleEventRegistry with all search events
    """
    return ModuleEventRegistry(
        module_name="search",
        display_name="Búsqueda",
        description="Eventos del módulo de búsqueda avanzada",
        events=[
            WebhookEvent(
                type="search.performed",
                description="Búsqueda realizada",
                category=EventCategory.INTERACTION,
            ),
            WebhookEvent(
                type="search.entity_indexed",
                description="Entidad indexada",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="search.entity_removed",
                description="Entidad removida del índice",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="search.entity_type_reindexed",
                description="Tipo de entidad reindexado",
                category=EventCategory.SYSTEM,
            ),
            WebhookEvent(
                type="search.bulk_indexed",
                description="Indexación masiva completada",
                category=EventCategory.SYSTEM,
            ),
        ],
    )
