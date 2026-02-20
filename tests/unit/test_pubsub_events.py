from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.calendar.service import CalendarService
from app.core.tasks.service import TaskService


def test_task_service_publishes_events(monkeypatch, db_session, test_tenant, test_user):
    published: list[dict[str, Any]] = []

    # Create a mock event publisher
    class MockEventPublisher:
        def publish(
            self,
            event_type,
            entity_type,
            entity_id,
            tenant_id,
            user_id=None,
            metadata=None,
        ):
            published.append(
                {
                    "event_type": event_type,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "metadata": metadata,
                }
            )

    service = TaskService(db_session, event_publisher=MockEventPublisher())

    async def create_task_async():
        return await service.create_task(
            title="Test task",
            tenant_id=test_tenant.id,
            created_by_id=test_user.id,
        )

    task = asyncio.run(create_task_async())

    print(f"Published events count: {len(published)}")
    print(f"Published events: {published}")

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

    async def delete_task_async():
        return await service.delete_task(
            task_id=task.id, tenant_id=test_tenant.id, user_id=test_user.id
        )

    deleted = asyncio.run(delete_task_async())
    assert deleted is True
    assert any(call.get("event_type") == "task.deleted" for call in published)


def test_calendar_service_publishes_events(
    monkeypatch, db_session, test_tenant, test_user
):
    published: list[dict[str, Any]] = []

    def fake_safe_publish_event(**kwargs):
        published.append(kwargs)

    monkeypatch.setattr(
        "app.core.pubsub.event_helpers.safe_publish_event",
        fake_safe_publish_event,
        raising=True,
    )

    service = CalendarService(
        db_session, event_publisher=None, notification_service=None
    )

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
