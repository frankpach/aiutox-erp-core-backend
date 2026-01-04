from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.calendar.service import CalendarService
from app.core.tasks.service import TaskService


def test_task_service_publishes_events(monkeypatch, db_session, test_tenant, test_user):
    published: list[dict[str, Any]] = []

    def fake_safe_publish_event(**kwargs):
        published.append(kwargs)

    monkeypatch.setattr(
        "app.core.pubsub.event_helpers.safe_publish_event",
        fake_safe_publish_event,
        raising=True,
    )

    service = TaskService(db_session, event_publisher=None)

    task = service.create_task(
        title="Test task",
        tenant_id=test_tenant.id,
        created_by_id=test_user.id,
    )

    assert any(call.get("event_type") == "task.created" for call in published)

    published.clear()
    updated = service.update_task(
        task_id=task.id,
        tenant_id=test_tenant.id,
        task_data={"title": "Updated title"},
        user_id=test_user.id,
    )
    assert updated is not None
    assert any(call.get("event_type") == "task.updated" for call in published)

    published.clear()
    deleted = service.delete_task(task_id=task.id, tenant_id=test_tenant.id, user_id=test_user.id)
    assert deleted is True
    assert any(call.get("event_type") == "task.deleted" for call in published)


def test_calendar_service_publishes_events(monkeypatch, db_session, test_tenant, test_user):
    published: list[dict[str, Any]] = []

    def fake_safe_publish_event(**kwargs):
        published.append(kwargs)

    monkeypatch.setattr(
        "app.core.pubsub.event_helpers.safe_publish_event",
        fake_safe_publish_event,
        raising=True,
    )

    service = CalendarService(db_session, event_publisher=None, notification_service=None)

    calendar = service.create_calendar(
        calendar_data={"name": "Test Calendar"},
        tenant_id=test_tenant.id,
        owner_id=test_user.id,
    )

    assert any(call.get("event_type") == "calendar.created" for call in published)

    published.clear()
    now = datetime.now(UTC)
    event = service.create_event(
        event_data={
            "calendar_id": calendar.id,
            "title": "Test Event",
            "start_time": now + timedelta(hours=1),
            "end_time": now + timedelta(hours=2),
        },
        tenant_id=test_tenant.id,
        organizer_id=test_user.id,
    )

    assert event is not None
    assert any(call.get("event_type") == "calendar.event_created" for call in published)
