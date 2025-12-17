"""Calendar schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# Calendar schemas
class CalendarBase(BaseModel):
    """Base schema for calendar."""

    name: str = Field(..., description="Calendar name", max_length=255)
    description: str | None = Field(None, description="Calendar description")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    calendar_type: str = Field(..., description="Calendar type (user, organization, shared)")
    organization_id: UUID | None = Field(None, description="Organization ID (for organization calendars)")
    is_public: bool = Field(False, description="Whether calendar is public")
    is_default: bool = Field(False, description="Whether this is the default calendar")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarCreate(CalendarBase):
    """Schema for creating a calendar."""

    pass


class CalendarUpdate(BaseModel):
    """Schema for updating a calendar."""

    name: str | None = Field(None, description="Calendar name", max_length=255)
    description: str | None = Field(None, description="Calendar description")
    color: str | None = Field(None, description="Hex color code", max_length=7)
    is_public: bool | None = Field(None, description="Whether calendar is public")
    is_default: bool | None = Field(None, description="Whether this is the default calendar")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarResponse(CalendarBase):
    """Schema for calendar response."""

    id: UUID
    tenant_id: UUID
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="meta_data", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Event schemas
class CalendarEventBase(BaseModel):
    """Base schema for calendar event."""

    calendar_id: UUID = Field(..., description="Calendar ID")
    title: str = Field(..., description="Event title", max_length=255)
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location", max_length=500)
    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    timezone: str | None = Field(None, description="Timezone (e.g., 'America/New_York')", max_length=50)
    all_day: bool = Field(False, description="Whether event is all-day")
    status: str = Field("scheduled", description="Event status")
    recurrence_type: str = Field("none", description="Recurrence type (none, daily, weekly, monthly, yearly)")
    recurrence_end_date: datetime | None = Field(None, description="Recurrence end date")
    recurrence_count: int | None = Field(None, description="Number of occurrences")
    recurrence_interval: int = Field(1, description="Recurrence interval (every N days/weeks/months)")
    recurrence_days_of_week: str | None = Field(None, description="Days of week for recurrence (e.g., '1,3,5')")
    recurrence_day_of_month: int | None = Field(None, description="Day of month for monthly recurrence")
    recurrence_month_of_year: int | None = Field(None, description="Month of year for yearly recurrence")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarEventCreate(CalendarEventBase):
    """Schema for creating a calendar event."""

    pass


class CalendarEventUpdate(BaseModel):
    """Schema for updating a calendar event."""

    title: str | None = Field(None, description="Event title", max_length=255)
    description: str | None = Field(None, description="Event description")
    location: str | None = Field(None, description="Event location", max_length=500)
    start_time: datetime | None = Field(None, description="Event start time")
    end_time: datetime | None = Field(None, description="Event end time")
    timezone: str | None = Field(None, description="Timezone", max_length=50)
    all_day: bool | None = Field(None, description="Whether event is all-day")
    status: str | None = Field(None, description="Event status")
    recurrence_type: str | None = Field(None, description="Recurrence type")
    recurrence_end_date: datetime | None = Field(None, description="Recurrence end date")
    recurrence_count: int | None = Field(None, description="Number of occurrences")
    recurrence_interval: int | None = Field(None, description="Recurrence interval")
    recurrence_days_of_week: str | None = Field(None, description="Days of week for recurrence")
    recurrence_day_of_month: int | None = Field(None, description="Day of month for monthly recurrence")
    recurrence_month_of_year: int | None = Field(None, description="Month of year for yearly recurrence")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class CalendarEventResponse(CalendarEventBase):
    """Schema for calendar event response."""

    id: UUID
    tenant_id: UUID
    organizer_id: UUID | None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] | None = Field(None, alias="meta_data", description="Additional metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Attendee schemas
class EventAttendeeBase(BaseModel):
    """Base schema for event attendee."""

    event_id: UUID = Field(..., description="Event ID")
    user_id: UUID | None = Field(None, description="User ID (for internal attendees)")
    email: str | None = Field(None, description="Email (for external attendees)", max_length=255)
    name: str | None = Field(None, description="Name (for external attendees)", max_length=255)
    status: str = Field("pending", description="Attendee status (pending, accepted, declined, tentative)")
    comment: str | None = Field(None, description="Optional comment with response")


class EventAttendeeCreate(EventAttendeeBase):
    """Schema for creating an event attendee."""

    pass


class EventAttendeeUpdate(BaseModel):
    """Schema for updating an event attendee."""

    status: str | None = Field(None, description="Attendee status")
    comment: str | None = Field(None, description="Optional comment with response")


class EventAttendeeResponse(EventAttendeeBase):
    """Schema for event attendee response."""

    id: UUID
    tenant_id: UUID
    response_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Reminder schemas
class EventReminderBase(BaseModel):
    """Base schema for event reminder."""

    event_id: UUID = Field(..., description="Event ID")
    reminder_type: str = Field(..., description="Reminder type (email, in_app, push)")
    minutes_before: int = Field(..., description="Minutes before event start")


class EventReminderCreate(EventReminderBase):
    """Schema for creating an event reminder."""

    pass


class EventReminderResponse(EventReminderBase):
    """Schema for event reminder response."""

    id: UUID
    tenant_id: UUID
    sent_at: datetime | None
    is_sent: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)





