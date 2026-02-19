"""Event models for the events system."""

from typing import Any


class EventMetadata:
    """Event metadata."""

    def __init__(
        self,
        version: str = "1.0",
        additional_data: dict[str, Any] | None = None
    ):
        """Initialize event metadata."""
        self.version = version
        self.additional_data = additional_data or {}
