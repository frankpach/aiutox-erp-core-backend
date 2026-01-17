"""Calendar router for calendar and event management."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import require_permission
from app.core.calendar.service import CalendarService, ReminderService
from app.core.db.deps import get_db
from app.core.exceptions import APIException
from app.models.user import User
from app.schemas.calendar import (
    CalendarCreate,
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarEventUpdate,
    CalendarResponse,
    CalendarUpdate,
    EventAttendeeCreate,
    EventAttendeeResponse,
    EventReminderCreate,
    EventReminderResponse,
)
from app.schemas.common import StandardListResponse, StandardResponse

router = APIRouter()


def get_calendar_service(db: Annotated[Session, Depends(get_db)]) -> CalendarService:
    """Dependency to get CalendarService."""
    return CalendarService(db)


def get_reminder_service(db: Annotated[Session, Depends(get_db)]) -> ReminderService:
    """Dependency to get ReminderService."""
    return ReminderService(db)


@router.post(
    "/calendars",
    response_model=StandardResponse[CalendarResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create calendar",
    description="Create a new calendar. Requires calendar.manage permission.",
)
async def create_calendar(
    calendar_data: CalendarCreate,
    current_user: Annotated[User, Depends(require_permission("calendar.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[CalendarResponse]:
    """Create a new calendar."""
    calendar = service.create_calendar(
        calendar_data=calendar_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        owner_id=current_user.id,
    )

    return StandardResponse(
        data=CalendarResponse.model_validate(calendar),
        message="Calendar created successfully",
    )


@router.get(
    "/calendars",
    response_model=StandardListResponse[CalendarResponse],
    status_code=status.HTTP_200_OK,
    summary="List calendars",
    description="List calendars for the current user. Requires calendar.view permission.",
)
async def list_calendars(
    current_user: Annotated[User, Depends(require_permission("calendar.view"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    calendar_type: str | None = Query(None, description="Filter by calendar type"),
) -> StandardListResponse[CalendarResponse]:
    """List calendars."""
    calendars = service.get_user_calendars(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        calendar_type=calendar_type,
    )

    return StandardListResponse(
        data=[CalendarResponse.model_validate(c) for c in calendars],
        meta={
            "total": len(calendars),
            "page": 1,
            "page_size": max(len(calendars), 1),
            "total_pages": 1,
        },
    )


@router.get(
    "/calendars/{calendar_id}",
    response_model=StandardResponse[CalendarResponse],
    status_code=status.HTTP_200_OK,
    summary="Get calendar",
    description="Get a specific calendar by ID. Requires calendar.view permission.",
)
async def get_calendar(
    calendar_id: Annotated[UUID, Path(..., description="Calendar ID")],
    current_user: Annotated[User, Depends(require_permission("calendar.view"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[CalendarResponse]:
    """Get a specific calendar."""
    calendar = service.get_calendar(calendar_id, current_user.tenant_id)
    if not calendar:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CALENDAR_NOT_FOUND",
            message=f"Calendar with ID {calendar_id} not found",
        )

    return StandardResponse(
        data=CalendarResponse.model_validate(calendar),
        message="Calendar retrieved successfully",
    )


@router.put(
    "/calendars/{calendar_id}",
    response_model=StandardResponse[CalendarResponse],
    status_code=status.HTTP_200_OK,
    summary="Update calendar",
    description="Update a calendar. Requires calendar.manage permission.",
)
async def update_calendar(
    calendar_id: Annotated[UUID, Path(..., description="Calendar ID")],
    calendar_data: CalendarUpdate,
    current_user: Annotated[User, Depends(require_permission("calendar.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[CalendarResponse]:
    """Update a calendar."""
    calendar = service.update_calendar(
        calendar_id=calendar_id,
        tenant_id=current_user.tenant_id,
        calendar_data=calendar_data.model_dump(exclude_none=True),
    )

    if not calendar:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CALENDAR_NOT_FOUND",
            message=f"Calendar with ID {calendar_id} not found",
        )

    return StandardResponse(
        data=CalendarResponse.model_validate(calendar),
        message="Calendar updated successfully",
    )


@router.delete(
    "/calendars/{calendar_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete calendar",
    description="Delete a calendar. Requires calendar.manage permission.",
)
async def delete_calendar(
    calendar_id: Annotated[UUID, Path(..., description="Calendar ID")],
    current_user: Annotated[User, Depends(require_permission("calendar.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> None:
    """Delete a calendar."""
    success = service.delete_calendar(calendar_id, current_user.tenant_id)
    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="CALENDAR_NOT_FOUND",
            message=f"Calendar with ID {calendar_id} not found",
        )


@router.post(
    "/events",
    response_model=StandardResponse[CalendarEventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create event",
    description="Create a new calendar event. Requires calendar.events.manage permission.",
)
async def create_event(
    event_data: CalendarEventCreate,
    current_user: Annotated[User, Depends(require_permission("calendar.events.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[CalendarEventResponse]:
    """Create a new calendar event."""
    event = service.create_event(
        event_data=event_data.model_dump(exclude_none=True),
        tenant_id=current_user.tenant_id,
        organizer_id=current_user.id,
    )

    return StandardResponse(
        data=CalendarEventResponse.model_validate(event),
        meta={"message": "Event created successfully"},
    )


@router.get(
    "/events",
    response_model=StandardListResponse[CalendarEventResponse],
    status_code=status.HTTP_200_OK,
    summary="List events",
    description="List calendar events. Requires calendar.events.view permission.",
)
async def list_events(
    current_user: Annotated[User, Depends(require_permission("calendar.events.view"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    calendar_id: UUID | None = Query(None, description="Filter by calendar ID"),
    start_date: datetime | None = Query(None, description="Filter by start date"),
    end_date: datetime | None = Query(None, description="Filter by end date"),
    status: str | None = Query(None, description="Filter by status"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Page size"),
) -> StandardListResponse[CalendarEventResponse]:
    """List calendar events."""
    skip = (page - 1) * page_size

    if calendar_id:
        events = service.get_events_by_calendar(
            calendar_id=calendar_id,
            tenant_id=current_user.tenant_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            skip=skip,
            limit=page_size,
        )
        total = service.count_events_by_calendar(
            calendar_id=calendar_id,
            tenant_id=current_user.tenant_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )
    else:
        events = service.get_user_events(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            start_date=start_date,
            end_date=end_date,
            skip=skip,
            limit=page_size,
        )
        total = service.count_user_events(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return StandardListResponse(
        data=[CalendarEventResponse.model_validate(e) for e in events],
        meta={
            "total": total,
            "page": page,
            "page_size": max(page_size, 1) if total == 0 else page_size,
            "total_pages": total_pages,
        },
    )


@router.get(
    "/events/{event_id}",
    response_model=StandardResponse[CalendarEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Get event",
    description="Get a specific event by ID. Requires calendar.events.view permission.",
)
async def get_event(
    event_id: Annotated[UUID, Path(..., description="Event ID")],
    current_user: Annotated[User, Depends(require_permission("calendar.events.view"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[CalendarEventResponse]:
    """Get a specific event."""
    event = service.get_event(event_id, current_user.tenant_id)
    if not event:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message=f"Event with ID {event_id} not found",
        )

    return StandardResponse(
        data=CalendarEventResponse.model_validate(event),
        message="Event retrieved successfully",
    )


@router.put(
    "/events/{event_id}",
    response_model=StandardResponse[CalendarEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Update event",
    description="Update a calendar event. Requires calendar.events.manage permission.",
)
async def update_event(
    event_id: Annotated[UUID, Path(..., description="Event ID")],
    current_user: Annotated[User, Depends(require_permission("calendar.events.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    event_data: CalendarEventUpdate,
) -> StandardResponse[CalendarEventResponse]:
    """Update a calendar event."""
    event = service.update_event(
        event_id=event_id,
        tenant_id=current_user.tenant_id,
        event_data=event_data.model_dump(exclude_none=True),
    )

    if not event:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message=f"Event with ID {event_id} not found",
        )

    return StandardResponse(
        data=CalendarEventResponse.model_validate(event),
        message="Event updated successfully",
    )


@router.post(
    "/events/{event_id}/cancel",
    response_model=StandardResponse[CalendarEventResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel event",
    description="Cancel a calendar event. Requires calendar.events.manage permission.",
)
async def cancel_event(
    event_id: Annotated[UUID, Path(..., description="Event ID")],
    current_user: Annotated[User, Depends(require_permission("calendar.events.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[CalendarEventResponse]:
    """Cancel a calendar event."""
    event = service.cancel_event(event_id, current_user.tenant_id)
    if not event:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message=f"Event with ID {event_id} not found",
        )

    return StandardResponse(
        data=CalendarEventResponse.model_validate(event),
        message="Event cancelled successfully",
    )


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete event",
    description="Delete a calendar event. Requires calendar.events.manage permission.",
)
async def delete_event(
    event_id: Annotated[UUID, Path(..., description="Event ID")],
    current_user: Annotated[User, Depends(require_permission("calendar.events.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> None:
    """Delete a calendar event."""
    success = service.delete_event(event_id, current_user.tenant_id)
    if not success:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="EVENT_NOT_FOUND",
            message=f"Event with ID {event_id} not found",
        )


@router.post(
    "/events/{event_id}/attendees",
    response_model=StandardResponse[EventAttendeeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add attendee",
    description="Add an attendee to an event. Requires calendar.events.manage permission.",
)
async def add_attendee(
    event_id: Annotated[UUID, Path(..., description="Event ID")],
    attendee_data: EventAttendeeCreate,
    current_user: Annotated[User, Depends(require_permission("calendar.events.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[EventAttendeeResponse]:
    """Add an attendee to an event."""
    attendee = service.add_attendee(
        event_id=event_id,
        tenant_id=current_user.tenant_id,
        attendee_data=attendee_data.model_dump(exclude_none=True),
    )

    return StandardResponse(
        data=EventAttendeeResponse.model_validate(attendee),
        message="Attendee added successfully",
    )


@router.put(
    "/events/{event_id}/attendees/me",
    response_model=StandardResponse[EventAttendeeResponse],
    status_code=status.HTTP_200_OK,
    summary="Update attendee response",
    description="Update your response to an event invitation. Requires calendar.events.view permission.",
)
async def update_attendee_response(
    event_id: Annotated[UUID, Path(..., description="Event ID")],
    response_status: Annotated[str, Query(..., description="Response status (accepted, declined, tentative)", alias="status")],
    current_user: Annotated[User, Depends(require_permission("calendar.events.view"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
    comment: str | None = Query(None, description="Optional comment"),
) -> StandardResponse[EventAttendeeResponse]:
    """Update your response to an event invitation."""
    attendee = service.update_attendee_response(
        event_id=event_id,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        status=response_status,
        comment=comment,
    )

    if not attendee:
        raise APIException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ATTENDEE_NOT_FOUND",
            message="You are not an attendee of this event",
        )

    return StandardResponse(
        data=EventAttendeeResponse.model_validate(attendee),
        message="Response updated successfully",
    )


@router.post(
    "/events/{event_id}/reminders",
    response_model=StandardResponse[EventReminderResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add reminder",
    description="Add a reminder to an event. Requires calendar.events.manage permission.",
)
async def add_reminder(
    event_id: Annotated[UUID, Path(..., description="Event ID")],
    reminder_data: EventReminderCreate,
    current_user: Annotated[User, Depends(require_permission("calendar.events.manage"))],
    service: Annotated[CalendarService, Depends(get_calendar_service)],
) -> StandardResponse[EventReminderResponse]:
    """Add a reminder to an event."""
    reminder = service.add_reminder(
        event_id=event_id,
        tenant_id=current_user.tenant_id,
        reminder_data=reminder_data.model_dump(exclude_none=True),
    )

    return StandardResponse(
        data=EventReminderResponse.model_validate(reminder),
        message="Reminder added successfully",
    )
