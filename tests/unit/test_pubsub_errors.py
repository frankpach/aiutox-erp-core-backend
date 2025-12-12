"""Unit tests for Pub-Sub errors."""

import pytest

from app.core.pubsub.errors import (
    ConsumeError,
    GroupNotFoundError,
    PubSubError,
    PublishError,
    StreamNotFoundError,
)


def test_pubsub_error_base():
    """Test PubSubError base exception."""
    error = PubSubError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_stream_not_found_error():
    """Test StreamNotFoundError."""
    error = StreamNotFoundError("Stream not found")
    assert str(error) == "Stream not found"
    assert isinstance(error, PubSubError)


def test_group_not_found_error():
    """Test GroupNotFoundError."""
    error = GroupNotFoundError("Group not found")
    assert str(error) == "Group not found"
    assert isinstance(error, PubSubError)


def test_publish_error():
    """Test PublishError."""
    error = PublishError("Publish failed")
    assert str(error) == "Publish failed"
    assert isinstance(error, PubSubError)


def test_consume_error():
    """Test ConsumeError."""
    error = ConsumeError("Consume failed")
    assert str(error) == "Consume failed"
    assert isinstance(error, PubSubError)


def test_error_inheritance():
    """Test error inheritance hierarchy."""
    assert issubclass(StreamNotFoundError, PubSubError)
    assert issubclass(GroupNotFoundError, PubSubError)
    assert issubclass(PublishError, PubSubError)
    assert issubclass(ConsumeError, PubSubError)
    assert issubclass(PubSubError, Exception)


