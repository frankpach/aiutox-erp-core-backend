"""Events system for the application."""

from typing import Any, Optional


class EventPublisher:
    """Simple event publisher for task events."""

    def __init__(self):
        """Initialize event publisher."""
        pass

    async def publish(self, event_name: str, data: dict[str, Any]) -> None:
        """Publish an event."""
        # Simple implementation - in production this would use a message broker
        print(f"Event published: {event_name} with data: {data}")


def get_event_publisher() -> EventPublisher:
    """Get event publisher instance."""
    return EventPublisher()


class EventMetadata:
    """Event metadata."""

    def __init__(
        self,
        version: str = "1.0",
        additional_data: Optional[dict[str, Any]] = None
    ):
        """Initialize event metadata."""
        self.version = version
        self.additional_data = additional_data or {}
