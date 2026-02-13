"""Unit tests for CalendarService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.calendar.service import CalendarService, ReminderService
from app.core.pubsub import EventPublisher


@pytest.fixture
def mock_event_publisher():
    """Create a mock EventPublisher."""
    publisher = MagicMock(spec=EventPublisher)
    publisher.publish = AsyncMock(return_value="message-id-123")
    return publisher


@pytest.fixture
def calendar_service(db_session, mock_event_publisher):
    """Create CalendarService instance."""
    return CalendarService(db=db_session, event_publisher=mock_event_publisher)


def test_create_calendar(calendar_service, test_user, test_tenant, mock_event_publisher):
    """Test creating a calendar."""
    calendar = calendar_service.create_calendar(
        calendar_data={
            "name": "Test Calendar",
            "description": "Test Description",
            "calendar_type": "user",
            "is_public": False,
        },
        tenant_id=test_tenant.id,
        owner_id=test_user.id,
    )

    assert calendar.name == "Test Calendar"
    assert calendar.tenant_id == test_tenant.id
    assert calendar.owner_id == test_user.id
    assert calendar.calendar_type == "user"

    # Verify event was published
    assert mock_event_publisher.publish.called


def test_create_event(calendar_service, test_user, test_tenant, mock_event_publisher):
    """Test creating a calendar event."""
    # First create a calendar
    calendar = calendar_service.create_calendar(
        calendar_data={
            "name": "Test Calendar",
            "calendar_type": "user",
        },
        tenant_id=test_tenant.id,
        owner_id=test_user.id,
    )

    start_time = datetime.now(UTC) + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    event = calendar_service.create_event(
        event_data={
            "calendar_id": calendar.id,
            "title": "Test Event",
            "start_time": start_time,
            "end_time": end_time,
            "status": "scheduled",
        },
        tenant_id=test_tenant.id,
        organizer_id=test_user.id,
    )

    assert event.title == "Test Event"
    assert event.calendar_id == calendar.id
    assert event.organizer_id == test_user.id

    # Verify event was published
    assert mock_event_publisher.publish.called


def test_get_user_calendars(calendar_service, test_user, test_tenant):
    """Test getting user calendars."""
    # Create multiple calendars
    calendar1 = calendar_service.create_calendar(
        calendar_data={"name": "Calendar 1", "calendar_type": "user"},
        tenant_id=test_tenant.id,
        owner_id=test_user.id,
    )
    calendar2 = calendar_service.create_calendar(
        calendar_data={"name": "Calendar 2", "calendar_type": "user"},
        tenant_id=test_tenant.id,
        owner_id=test_user.id,
    )

    calendars = calendar_service.get_user_calendars(
        user_id=test_user.id,
        tenant_id=test_tenant.id,
    )

    assert len(calendars) >= 2
    assert any(c.id == calendar1.id for c in calendars)
    assert any(c.id == calendar2.id for c in calendars)


def test_cancel_event(calendar_service, test_user, test_tenant):
    """Test cancelling an event."""
    # Create calendar and event
    calendar = calendar_service.create_calendar(
        calendar_data={"name": "Test Calendar", "calendar_type": "user"},
        tenant_id=test_tenant.id,
        owner_id=test_user.id,
    )

    start_time = datetime.now(UTC) + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    event = calendar_service.create_event(
        event_data={
            "calendar_id": calendar.id,
            "title": "Test Event",
            "start_time": start_time,
            "end_time": end_time,
        },
        tenant_id=test_tenant.id,
        organizer_id=test_user.id,
    )

    # Cancel event
    cancelled_event = calendar_service.cancel_event(event.id, test_tenant.id)

    assert cancelled_event is not None
    assert cancelled_event.status == "cancelled"


def _create_test_event(calendar_service, test_user, test_tenant, **overrides):
    """Helper to create a calendar + event for testing."""
    calendar = calendar_service.create_calendar(
        calendar_data={"name": "Test Calendar", "calendar_type": "user"},
        tenant_id=test_tenant.id,
        owner_id=test_user.id,
    )
    start_time = overrides.pop("start_time", datetime.now(UTC) + timedelta(days=1))
    end_time = overrides.pop("end_time", start_time + timedelta(hours=1))

    event = calendar_service.create_event(
        event_data={
            "calendar_id": calendar.id,
            "title": "Test Event",
            "start_time": start_time,
            "end_time": end_time,
            **overrides,
        },
        tenant_id=test_tenant.id,
        organizer_id=test_user.id,
    )
    return event


def test_resize_event_rejects_end_before_start(calendar_service, test_user, test_tenant):
    """Test that resize_event raises APIException when new_end_time <= start_time."""
    from app.core.exceptions import APIException

    event = _create_test_event(calendar_service, test_user, test_tenant)

    with pytest.raises(APIException) as exc_info:
        calendar_service.resize_event(
            event_id=event.id,
            tenant_id=test_tenant.id,
            new_end_time=event.start_time - timedelta(hours=1),
        )

    assert exc_info.value.code == "INVALID_EVENT_DURATION"
    assert "end_time must be after start_time" in exc_info.value.message


def test_resize_event_rejects_short_duration(calendar_service, test_user, test_tenant):
    """Test that resize_event raises APIException when duration < 15 minutes."""
    from app.core.exceptions import APIException

    event = _create_test_event(calendar_service, test_user, test_tenant)

    with pytest.raises(APIException) as exc_info:
        calendar_service.resize_event(
            event_id=event.id,
            tenant_id=test_tenant.id,
            new_end_time=event.start_time + timedelta(minutes=10),
        )

    assert exc_info.value.code == "INVALID_EVENT_DURATION"
    assert "15 minutes" in exc_info.value.message


def test_update_event_rejects_invalid_time_range(calendar_service, test_user, test_tenant):
    """Test that update_event raises APIException when end_time <= start_time."""
    from app.core.exceptions import APIException

    event = _create_test_event(calendar_service, test_user, test_tenant)

    with pytest.raises(APIException) as exc_info:
        calendar_service.update_event(
            event_id=event.id,
            tenant_id=test_tenant.id,
            event_data={"end_time": event.start_time - timedelta(hours=1)},
        )

    assert exc_info.value.code == "INVALID_EVENT_DURATION"


def test_resize_event_accepts_valid_end_time(calendar_service, test_user, test_tenant):
    """Test that resize_event succeeds with a valid new_end_time."""
    event = _create_test_event(calendar_service, test_user, test_tenant)

    new_end = event.start_time + timedelta(hours=2)
    updated = calendar_service.resize_event(
        event_id=event.id,
        tenant_id=test_tenant.id,
        new_end_time=new_end,
    )

    assert updated is not None
    assert updated.end_time == new_end

