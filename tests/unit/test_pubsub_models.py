"""Unit tests for Pub-Sub models."""

import pytest
from uuid import uuid4

from app.core.pubsub.models import Event, EventMetadata


def test_event_metadata_creation():
    """Test EventMetadata creation."""
    metadata = EventMetadata(source="test_service", version="1.0", additional_data={"key": "value"})
    assert metadata.source == "test_service"
    assert metadata.version == "1.0"
    assert metadata.additional_data == {"key": "value"}


def test_event_metadata_defaults():
    """Test EventMetadata with defaults."""
    metadata = EventMetadata(source="test_service")
    assert metadata.version == "1.0"
    assert metadata.additional_data == {}


def test_event_creation():
    """Test Event creation."""
    tenant_id = uuid4()
    entity_id = uuid4()
    metadata = EventMetadata(source="test_service")

    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        metadata=metadata,
    )

    assert event.event_type == "product.created"
    assert event.entity_type == "product"
    assert event.entity_id == entity_id
    assert event.tenant_id == tenant_id
    assert event.user_id is None
    assert event.metadata.source == "test_service"


def test_event_with_user_id():
    """Test Event with user_id."""
    tenant_id = uuid4()
    entity_id = uuid4()
    user_id = uuid4()
    metadata = EventMetadata(source="test_service")

    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        user_id=user_id,
        metadata=metadata,
    )

    assert event.user_id == user_id


def test_event_type_validation_valid():
    """Test valid event type formats."""
    tenant_id = uuid4()
    entity_id = uuid4()
    metadata = EventMetadata(source="test_service")

    valid_types = ["product.created", "inventory.stock_low", "system.error", "user_activity.logged"]

    for event_type in valid_types:
        event = Event(
            event_type=event_type,
            entity_type="test",
            entity_id=entity_id,
            tenant_id=tenant_id,
            metadata=metadata,
        )
        assert event.event_type == event_type


def test_event_type_validation_invalid():
    """Test invalid event type formats."""
    tenant_id = uuid4()
    entity_id = uuid4()
    metadata = EventMetadata(source="test_service")

    invalid_types = [
        "Product.Created",  # uppercase
        "product-created",  # hyphen instead of dot
        "product",  # no dot
        "product.created.extra",  # too many dots
        "product created",  # space
    ]

    for event_type in invalid_types:
        with pytest.raises(ValueError, match="event_type must match pattern"):
            Event(
                event_type=event_type,
                entity_type="test",
                entity_id=entity_id,
                tenant_id=tenant_id,
                metadata=metadata,
            )


def test_event_to_redis_dict():
    """Test Event serialization to Redis dict."""
    tenant_id = uuid4()
    entity_id = uuid4()
    user_id = uuid4()
    metadata = EventMetadata(source="test_service", additional_data={"key": "value"})

    event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        user_id=user_id,
        metadata=metadata,
    )

    redis_dict = event.to_redis_dict()

    assert redis_dict["event_id"] == str(event.event_id)
    assert redis_dict["event_type"] == "product.created"
    assert redis_dict["entity_type"] == "product"
    assert redis_dict["entity_id"] == str(entity_id)
    assert redis_dict["tenant_id"] == str(tenant_id)
    assert redis_dict["user_id"] == str(user_id)
    assert redis_dict["metadata_source"] == "test_service"
    assert "metadata_additional_data" in redis_dict


def test_event_from_redis_dict():
    """Test Event deserialization from Redis dict."""
    tenant_id = uuid4()
    entity_id = uuid4()
    user_id = uuid4()
    event_id = uuid4()

    redis_dict = {
        "event_id": str(event_id),
        "event_type": "product.created",
        "entity_type": "product",
        "entity_id": str(entity_id),
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "timestamp": "2025-01-01T00:00:00+00:00",
        "metadata_source": "test_service",
        "metadata_version": "1.0",
        "metadata_additional_data": '{"key": "value"}',
    }

    event = Event.from_redis_dict(redis_dict)

    assert event.event_id == event_id
    assert event.event_type == "product.created"
    assert event.entity_type == "product"
    assert event.entity_id == entity_id
    assert event.tenant_id == tenant_id
    assert event.user_id == user_id
    assert event.metadata.source == "test_service"
    assert event.metadata.additional_data == {"key": "value"}


def test_event_from_redis_dict_no_user_id():
    """Test Event deserialization without user_id."""
    tenant_id = uuid4()
    entity_id = uuid4()
    event_id = uuid4()

    redis_dict = {
        "event_id": str(event_id),
        "event_type": "product.created",
        "entity_type": "product",
        "entity_id": str(entity_id),
        "tenant_id": str(tenant_id),
        "user_id": "",
        "timestamp": "2025-01-01T00:00:00+00:00",
        "metadata_source": "test_service",
        "metadata_version": "1.0",
        "metadata_additional_data": "{}",
    }

    event = Event.from_redis_dict(redis_dict)

    assert event.user_id is None


def test_event_round_trip():
    """Test Event serialization round trip."""
    tenant_id = uuid4()
    entity_id = uuid4()
    user_id = uuid4()
    metadata = EventMetadata(source="test_service", additional_data={"key": "value", "number": 42})

    original_event = Event(
        event_type="product.created",
        entity_type="product",
        entity_id=entity_id,
        tenant_id=tenant_id,
        user_id=user_id,
        metadata=metadata,
    )

    redis_dict = original_event.to_redis_dict()
    restored_event = Event.from_redis_dict(redis_dict)

    assert restored_event.event_id == original_event.event_id
    assert restored_event.event_type == original_event.event_type
    assert restored_event.entity_type == original_event.entity_type
    assert restored_event.entity_id == original_event.entity_id
    assert restored_event.tenant_id == original_event.tenant_id
    assert restored_event.user_id == original_event.user_id
    assert restored_event.metadata.source == original_event.metadata.source
    assert restored_event.metadata.additional_data == original_event.metadata.additional_data










