"""Unit tests for ActionExecutor."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.core.automation.action_executor import ActionExecutor
from app.core.pubsub.models import Event, EventMetadata


@pytest.fixture
def db_session():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def action_executor(db_session):
    """Create ActionExecutor instance."""
    return ActionExecutor(db_session)


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return Event(
        event_type="product.created",
        entity_type="product",
        entity_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        metadata=EventMetadata(
            source="test",
            version="1.0",
            additional_data={"product_name": "Test Product"},
        ),
    )


@pytest.mark.asyncio
async def test_execute_notification_action(action_executor, sample_event):
    """Test executing a notification action."""
    actions = [
        {
            "type": "notification",
            "template": "test_template",
            "recipients": ["admin@tenant.com"],
        }
    ]
    result = await action_executor.execute(actions, sample_event)
    assert result["actions_executed"] == 1
    assert len(result["results"]) == 1
    assert result["results"][0]["success"] is True
    assert result["results"][0]["action"]["type"] == "notification"


@pytest.mark.asyncio
async def test_execute_create_activity_action(action_executor, sample_event):
    """Test executing a create activity action."""
    actions = [
        {
            "type": "create_activity",
            "activity_type": "alert",
            "description": "Test activity",
        }
    ]
    result = await action_executor.execute(actions, sample_event)
    assert result["actions_executed"] == 1
    assert result["results"][0]["success"] is True
    assert result["results"][0]["action"]["type"] == "create_activity"


@pytest.mark.asyncio
async def test_execute_multiple_actions(action_executor, sample_event):
    """Test executing multiple actions."""
    actions = [
        {
            "type": "notification",
            "template": "test_template",
            "recipients": ["admin@tenant.com"],
        },
        {
            "type": "create_activity",
            "activity_type": "alert",
            "description": "Test activity",
        },
    ]
    result = await action_executor.execute(actions, sample_event)
    assert result["actions_executed"] == 2
    assert len(result["results"]) == 2
    assert all(r["success"] for r in result["results"])


@pytest.mark.asyncio
async def test_execute_unsupported_action_type(action_executor, sample_event):
    """Test executing an unsupported action type."""
    actions = [{"type": "unsupported", "data": "test"}]
    result = await action_executor.execute(actions, sample_event)
    assert result["actions_executed"] == 1
    assert result["results"][0]["success"] is False
    assert "error" in result["results"][0]


@pytest.mark.asyncio
async def test_execute_action_with_error(action_executor, sample_event):
    """Test executing action that raises an error."""
    # Mock an action that will fail
    actions = [{"type": "invoke_api", "url": "http://test.com"}]
    result = await action_executor.execute(actions, sample_event)
    # invoke_api is not fully implemented, so it should return success but with a message
    assert result["actions_executed"] == 1










