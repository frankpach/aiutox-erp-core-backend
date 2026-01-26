"""Event registry for webhook autodiscovery."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventCategory(str, Enum):
    """Event category classification."""

    LIFECYCLE = "lifecycle"  # Created, updated, deleted
    STATUS = "status"  # Status changes, state transitions
    INTERACTION = "interaction"  # Comments, mentions, assignments
    SYSTEM = "system"  # Automated events, scheduled tasks


@dataclass
class WebhookEvent:
    """Webhook event definition."""

    type: str
    description: str
    category: EventCategory
    payload_schema: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "description": self.description,
            "category": self.category.value,
            "payload_schema": self.payload_schema,
        }


@dataclass
class ModuleEventRegistry:
    """Module event registry."""

    module_name: str
    display_name: str
    description: str
    events: list[WebhookEvent]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.display_name,
            "description": self.description,
            "events": [event.to_dict() for event in self.events],
        }


class WebhookEventRegistry:
    """Central registry for all webhook events."""

    def __init__(self):
        """Initialize event registry."""
        self._modules: dict[str, ModuleEventRegistry] = {}

    def register_module(self, registry: ModuleEventRegistry) -> None:
        """Register a module's events.

        Args:
            registry: Module event registry
        """
        self._modules[registry.module_name] = registry

    def get_all_events(self) -> dict[str, dict[str, Any]]:
        """Get all registered events grouped by module.

        Returns:
            Dictionary of modules and their events
        """
        return {
            module_name: registry.to_dict()
            for module_name, registry in self._modules.items()
        }

    def get_module_events(self, module_name: str) -> ModuleEventRegistry | None:
        """Get events for a specific module.

        Args:
            module_name: Module name

        Returns:
            Module event registry or None if not found
        """
        return self._modules.get(module_name)

    def get_event_types(self) -> list[str]:
        """Get all event types across all modules.

        Returns:
            List of event type strings
        """
        event_types = []
        for registry in self._modules.values():
            event_types.extend([event.type for event in registry.events])
        return event_types


# Global registry instance
_event_registry = WebhookEventRegistry()


def get_event_registry() -> WebhookEventRegistry:
    """Get global event registry instance.

    Returns:
        WebhookEventRegistry instance
    """
    return _event_registry
