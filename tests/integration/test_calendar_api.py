"""Integration tests for Calendar API endpoints."""

from datetime import UTC, datetime, timedelta

from app.models.module_role import ModuleRole


def test_create_calendar(client_with_db, test_user, auth_headers, db_session):
    """Test creating a calendar."""
    # Assign calendar.manage permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="calendar",
        role_name="manager",  # Maps to internal.manager -> calendar.view, calendar.manage, calendar.events.view, calendar.events.manage
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    calendar_data = {
        "name": "Test Calendar",
        "description": "Test Description",
        "calendar_type": "user",
        "is_public": False,
    }

    response = client_with_db.post(
        "/api/v1/calendar/calendars",
        json=calendar_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "Test Calendar"
    assert "id" in data


def test_list_calendars(client_with_db, test_user, auth_headers, db_session):
    """Test listing calendars."""
    # Assign calendar.view permission
    module_role = ModuleRole(
        user_id=test_user.id,
        module="calendar",
        role_name="viewer",  # Maps to internal.viewer -> calendar.view, calendar.events.view
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    response = client_with_db.get("/api/v1/calendar/calendars", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)


def test_create_event(client_with_db, test_user, auth_headers, db_session):
    """Test creating a calendar event."""
    # Assign permissions
    module_role = ModuleRole(
        user_id=test_user.id,
        module="calendar",
        role_name="manager",  # Maps to internal.manager -> calendar.view, calendar.manage, calendar.events.view, calendar.events.manage
        granted_by=test_user.id,
    )
    db_session.add(module_role)
    db_session.commit()

    # First create a calendar
    calendar_data = {"name": "Test Calendar", "calendar_type": "user"}
    calendar_response = client_with_db.post(
        "/api/v1/calendar/calendars",
        json=calendar_data,
        headers=auth_headers,
    )
    calendar_id = calendar_response.json()["data"]["id"]

    # Create event
    start_time = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    end_time = (datetime.now(UTC) + timedelta(days=1, hours=1)).isoformat()

    event_data = {
        "calendar_id": calendar_id,
        "title": "Test Event",
        "start_time": start_time,
        "end_time": end_time,
    }

    response = client_with_db.post(
        "/api/v1/calendar/events",
        json=event_data,
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Test Event"
    assert "id" in data
