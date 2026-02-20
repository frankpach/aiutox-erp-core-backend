"""Unit tests for Pub-Sub group management."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.pubsub.client import RedisStreamsClient
from app.core.pubsub.errors import PubSubError
from app.core.pubsub.groups import ensure_group_exists, get_or_create_group


@pytest.mark.asyncio
async def test_ensure_group_exists_creates_group():
    """Test ensure_group_exists creates a new group."""
    mock_client = MagicMock(spec=RedisStreamsClient)
    mock_client.create_group = AsyncMock(return_value=True)

    result = await ensure_group_exists(mock_client, "test_stream", "test_group")

    assert result is True
    mock_client.create_group.assert_called_once_with(
        "test_stream", "test_group", "0", recreate_if_exists=False
    )


@pytest.mark.asyncio
async def test_ensure_group_exists_group_already_exists():
    """Test ensure_group_exists when group already exists."""
    mock_client = MagicMock(spec=RedisStreamsClient)
    mock_client.create_group = AsyncMock(return_value=False)

    result = await ensure_group_exists(mock_client, "test_stream", "test_group")

    assert result is False
    mock_client.create_group.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_group_exists_handles_error():
    """Test ensure_group_exists handles errors."""
    mock_client = MagicMock(spec=RedisStreamsClient)
    mock_client.create_group = AsyncMock(side_effect=PubSubError("Connection failed"))

    with pytest.raises(PubSubError, match="Connection failed"):
        await ensure_group_exists(mock_client, "test_stream", "test_group")


@pytest.mark.asyncio
async def test_get_or_create_group():
    """Test get_or_create_group is an alias for ensure_group_exists."""
    mock_client = MagicMock(spec=RedisStreamsClient)
    mock_client.create_group = AsyncMock(return_value=True)

    result = await get_or_create_group(mock_client, "test_stream", "test_group")

    assert result is True
    mock_client.create_group.assert_called_once_with(
        "test_stream", "test_group", "0", recreate_if_exists=False
    )
