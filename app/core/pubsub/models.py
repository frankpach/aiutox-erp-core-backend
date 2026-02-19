"""Pydantic models for events."""

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventMetadata(BaseModel):
    """Metadata for an event."""

    source: str = Field(..., description="Source service/module (e.g., 'product_service')")
    version: str = Field(default="1.0", description="Version of the event schema")
    additional_data: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Event(BaseModel):
    """Event model for Pub-Sub system."""

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: str = Field(..., description="Event type in format '<module>.<action>'")
    entity_type: str = Field(..., description="Type of entity (e.g., 'product')")
    entity_id: UUID = Field(..., description="ID of the entity")
    tenant_id: UUID = Field(..., description="Tenant ID")
    user_id: UUID | None = Field(default=None, description="User ID (optional)")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Event timestamp (UTC)"
    )
    metadata: EventMetadata = Field(..., description="Event metadata")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type format: <module>.<action>."""
        pattern = r"^[a-z_]+\.([a-z_]+)$"
        if not re.match(pattern, v):
            raise ValueError(
                f"event_type must match pattern '<module>.<action>' (lowercase, underscores). Got: {v}"
            )
        return v

    def to_redis_dict(self) -> dict[str, str]:
        """Convert event to dictionary for Redis Streams."""
        import json

        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id else "",
            "timestamp": self.timestamp.isoformat(),
            "metadata_source": self.metadata.source,
            "metadata_version": self.metadata.version,
            "metadata_additional_data": json.dumps(self.metadata.additional_data),
        }

    @classmethod
    def from_redis_dict(cls, data: dict[str, str] | Any) -> "Event":
        """Create Event from Redis Streams dictionary."""
        import json

        # Ensure data is a dictionary (handle both dict and list of tuples from Redis)
        if not isinstance(data, dict):
            # If data is a list of tuples (from Redis xreadgroup), convert to dict
            if isinstance(data, (list, tuple)):
                data = dict(data)
            else:
                data = dict(data) if hasattr(data, 'items') else {}

        # Parse additional_data if it's a string representation
        additional_data = {}
        metadata_additional_data = data.get("metadata_additional_data")
        if metadata_additional_data:
            try:
                # Try JSON first
                if isinstance(metadata_additional_data, str):
                    additional_data = json.loads(metadata_additional_data)
                elif isinstance(metadata_additional_data, dict):
                    # If it's already a dict (from Redis decode_responses), use it directly
                    additional_data = metadata_additional_data
                else:
                    additional_data = {}
            except (json.JSONDecodeError, TypeError):
                additional_data = {}

        # Extract metadata fields - ensure we get the actual values
        metadata_source = data.get("metadata_source")
        if not metadata_source or metadata_source == "":
            metadata_source = "unknown"

        metadata_version = data.get("metadata_version")
        if not metadata_version or metadata_version == "":
            metadata_version = "1.0"

        return cls(
            event_id=UUID(data["event_id"]),
            event_type=data["event_type"],
            entity_type=data["entity_type"],
            entity_id=UUID(data["entity_id"]),
            tenant_id=UUID(data["tenant_id"]),
            user_id=UUID(data["user_id"]) if data.get("user_id") and data["user_id"] else None,
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=EventMetadata(
                source=metadata_source,
                version=metadata_version,
                additional_data=additional_data,
            ),
        )










