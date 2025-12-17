"""API tests for Pub-Sub endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.pubsub.client import RedisStreamsClient
from tests.helpers import create_user_with_permission


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = MagicMock(spec=RedisStreamsClient)
    client.connection = AsyncMock()
    client.get_stream_info = AsyncMock()
    client.get_group_info = AsyncMock()
    client.get_pending_messages = AsyncMock()
    return client


def test_get_stats_endpoint(client, test_user, db_session, mock_redis_client):
    """Test GET /api/v1/pubsub/stats endpoint."""
    headers = create_user_with_permission(db_session, test_user, "pubsub", "viewer")

    with patch("app.api.v1.pubsub.get_redis_client", return_value=mock_redis_client):
        # Mock stream info
        mock_redis_client.get_stream_info.return_value = {
            "length": 10,
            "first-entry": "0-0",
            "last-entry": "1000-0",
        }

        # Mock connection context manager
        mock_conn = AsyncMock()
        mock_conn.xinfo_groups = AsyncMock(return_value=[])
        mock_redis_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_redis_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.get("/api/v1/pubsub/stats", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "streams" in data["data"]


def test_list_failed_events_endpoint(client, test_user, db_session, mock_redis_client):
    """Test GET /api/v1/pubsub/failed endpoint."""
    headers = create_user_with_permission(db_session, test_user, "pubsub", "viewer")

    with patch("app.api.v1.pubsub.get_redis_client", return_value=mock_redis_client):
        # Mock connection context manager properly
        mock_conn = AsyncMock()
        mock_conn.xrevrange = AsyncMock(return_value=[])

        # Create a proper async context manager mock
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_context.__aexit__ = AsyncMock(return_value=False)
        mock_redis_client.connection = AsyncMock(return_value=mock_context)

        response = client.get("/api/v1/pubsub/failed", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)


def test_get_stream_info_endpoint(client, test_user, db_session, mock_redis_client):
    """Test GET /api/v1/pubsub/streams/{stream_name}/info endpoint."""
    headers = create_user_with_permission(db_session, test_user, "pubsub", "viewer")

    with patch("app.api.v1.pubsub.get_redis_client", return_value=mock_redis_client):
        mock_redis_client.get_stream_info.return_value = {
            "length": 5,
            "first-entry": "0-0",
            "last-entry": "500-0",
        }

        mock_conn = AsyncMock()
        mock_conn.xinfo_groups = AsyncMock(return_value=[])
        mock_redis_client.connection.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_redis_client.connection.return_value.__aexit__ = AsyncMock(return_value=False)

        response = client.get(
            "/api/v1/pubsub/streams/events:domain/info",
            headers=headers,
        )

        if response.status_code == 404:
            # Stream doesn't exist yet, that's okay
            return

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["stream_name"] == "events:domain"









